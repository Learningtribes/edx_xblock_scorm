# -*- coding: utf-8 -*-
from __future__ import division
import os
import pkg_resources
import uuid
import logging
import re
from collections import namedtuple
from lxml import etree
from urlparse import urlparse, urlunparse
import urllib
import user_agents

from crum import get_current_request
from django.template import Context, Template
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.conf import settings
from django.contrib.auth.models import User
from xblock.core import XBlock
from xblock.exceptions import XBlockSaveError, JsonHandlerError
from xblock.scorable import Score
from xblock.fields import String, Scope, Dict, Boolean, Float
from xblock.reference.plugins import Filesystem

from web_fragments.fragment import Fragment
from webob.response import Response
from fs.copy import copy_dir
from fs.zipfs import ZipFS
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblockutils.fields import File
try:
    from xmodule.progress import Progress
except ImportError:
    pass
from .scorm_default import *
from .fields import DateTime
from .mixins import ScorableXBlockMixin
logger = logging.getLogger(__name__)
# Make '_' a no-op so we can scrape strings
_ = lambda text: text


def dt2str(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

def str2dt(dtstr):
    return parse_datetime(dtstr)


SCORM_STATUS = namedtuple('ScormStatus', [
    'SUCCEED', 'FAILED', 'IN_PROGRESS', 'UNATTENDED'])(
    'SUCCEED', 'FAILED', 'IN PROGRESS', 'UNATTENDED')

SCORM_VERSION = namedtuple('ScormVersion', ['V12', 'V2004'])('SCORM12', 'SCORM2004')


def is_compatible(request):
    """Ignore IE/Safari browsers to open scorm content in new tab due to postMessage() limitation.
    """
    http_user_agent = request.META.get('HTTP_USER_AGENT')
    user_agent = user_agents.parse(http_user_agent)
    browser_family = user_agent.browser.family
    if browser_family == 'IE' or "Safari" in browser_family:
        return False
    return True


@XBlock.needs('request', 'fs', 'i18n', 'user')
class ScormXBlock(StudioEditableXBlockMixin, ScorableXBlockMixin, XBlock):
    """
    all fields private to `scorm` are prefix with `scorm`, in case any conflict
    with internal fields.
    """
    display_name = String(
        default="SCORM",
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Display Name"),
        help=_("Display name for this module"),
    )

    due = DateTime(
        default="2000-01-01T00:00:00.00+0000",
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Due Date"),
        help=_("Due Date"),
    )

    has_score = Boolean(
        default=True,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_('Score'),
        help=_("Does this SCORM need to be scored?")
    )

    icon_class = String(
        default='problem',
        scope=Scope.settings,
        values=("problem", "video", "other"),
        enforce_type=True,
        display_name=_("Icon"),
        help=_("Icon used in course page")
    )

    weight = Float(
        default=1.0,
        scope=Scope.settings,
        values={"min": 0, "step": 0.1},
        enforce_type=True,
        display_name=_('Weight'),
        help=_('Relative weight in this course section')
    )

    ratio = String(
        default="16:9",
        scope=Scope.settings,
        values=("16:9", "4:3", "1:1"),
        enforce_type=True,
        display_name=_('Ratio'),
        help=_('Aspect ratio of this module')
    )

    open_new_tab = Boolean(
        default=False,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_('Module'),
        help=_('Open module in a new tab. This option will only apply to users with a compatible browser.')
    )

    fs = Filesystem(scope=Scope.settings)

    scorm_pkg = File(
        accept="application/zip",
        default="",
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("SCORM module"),
        help=_("SCORM module in .zip format")
    )

    scorm_file = String(
        display_name=_("compatible with old version scorm file"),
        scope=Scope.settings,
        default="old"
    )

    scorm_pkg_version = String(
        default=SCORM_VERSION.V12,
        scope=Scope.settings,
        values=SCORM_VERSION,
        enforce_type=True,
        display_name=_('Version'),
        help=_('Version of scorm, 1.2 or 2004')
    )

    scorm_pkg_modified = DateTime(
        scope=Scope.settings,
        enforce_type=True,
        display_name=_('Upload time'),
        help=_('SCORM package upload time utc')
    )

    _scorm_runtime_data = Dict(
        default={},
        scope=Scope.user_state,
        enforce_type=True
    )

    scorm_runtime_modified = DateTime(
        scope=Scope.user_state,
        enforce_type=True,
        display_name=_('Runtime Modified Time'),
        help=_('SCORM runtime modified time utc')
    )

    scorm_status = String(
        default=SCORM_STATUS.UNATTENDED,
        scope=Scope.user_state,
        values=SCORM_STATUS,
        enforce_type=True
    )

    success_status = String(
        scope=Scope.user_state,
        default='unknown'
    )

    scorm_score = Float(
        default=0,
        scope=Scope.user_state,
        enforce_type=True
    )

    lesson_score = Float(
        scope=Scope.user_state,
        default=0
    )

    scorm_allow_rescore = Boolean(
        default=True,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Rescore"),
        help=_("Does this SCORM allow users to submit answer multiple times?")
    )

    version_scorm = String(
        default="SCORM_12",
        scope=Scope.settings,
    )

    scorm_modified = DateTime(
        scope=Scope.settings,
    )

    scorm_launch_data = String(
        default="",
        scope=Scope.settings
    )

    editable_fields = ('scorm_pkg', 'ratio', 'open_new_tab', 'display_name', 'due', 'has_score', 'icon_class', 'weight', 'scorm_allow_rescore')
    has_author_view = True

    # region Studio handler
    @XBlock.handler
    def studio_upload_files(self, request, suffix=''):
        pkg = request.POST.get('scorm_pkg', None)
        if not pkg:
            return Response(status=400)
        zipfs = ZipFS(pkg.file)
        with zipfs.open(u'imsmanifest.xml') as mf:
            self.scorm_pkg_version, scorm_index, scorm_launch = self._get_scorm_info(mf)
            #logger.info('uploadfile: ' +str(self.scorm_pkg_version) + str(scorm_index) + str(scorm_launch))
        pkg_id = self._upload_scorm_pkg(zipfs)
        self.scorm_pkg = os.path.join(pkg_id, scorm_index)
        self.scorm_pkg_modified = timezone.now()
        if scorm_launch is not None:
            self.scorm_launch_data = str(scorm_launch)
        return Response(status=200)

    def _upload_scorm_pkg(self, fs):
        _ = self.runtime.service(self, 'i18n').ugettext

        pkg_id = uuid.uuid4().hex
        try:
            copy_dir(fs, u'/', self.fs, pkg_id)
        except IOError:
            raise XBlockSaveError([], ['scorm_pkg'], _('Error in uploading scorm package'))
        return pkg_id

    @staticmethod
    def _get_scorm_info(manifest):
        index_page = 'index.html'
        launch_data = None
        datafromlms = 'organizations/organization/item/adlcp:datafromlms'
        root = etree.parse(manifest).getroot()
        id_ref = root.find('organizations/organization/item', root.nsmap).get('identifierref')
        resources = root.find('resources', root.nsmap)
        resource = resources.findall('resource', root.nsmap)
        schemaversion = root.find('metadata/schemaversion', root.nsmap)
        scorm_version = SCORM_VERSION.V12
        if resource:
            if len(resource) > 1:
                for i in resource:
                    if i.get('identifier') == id_ref:
                        index_page = i.get('href')
            else:
                index_page = resource[0].get('href')

        if (schemaversion is not None) and (re.match('^1.2$', schemaversion.text) is None):
            scorm_version = SCORM_VERSION.V2004
            datafromlms = 'organizations/organization/item/adlcp:dataFromLMS'
        launch_data = root.find(datafromlms, root.nsmap)
        if launch_data is not None:
            launch_data = launch_data.text
        return scorm_version, index_page, launch_data
    # endregion

    # region Runtime functions
    def max_score(self):
        return 1.0

    def allows_rescore(self):
        return self.scorm_allow_rescore

    def set_score(self, score):
        self.scorm_score = self.max_score() * score.raw_earned / score.raw_possible

    def get_score(self):
        return Score(raw_possible=self.max_score(), raw_earned=self.scorm_score)

    def calculate_score(self):
        return self.get_score()

    def has_submitted_answer(self):
        return self.scorm_status != SCORM_STATUS.UNATTENDED

    def get_progress(self):
        pg = 0
        if self.scorm_pkg_version == SCORM_VERSION.V2004:
            try:
                pg = float(self.scorm_runtime_data.get('cmi.progress_measure', 0))
            except ValueError:
                pg = 0
        return Progress(pg, 1)

    # endregion

    @property
    def scorm_runtime_data(self):
        return self._scorm_runtime_data

    @scorm_runtime_data.setter
    def scorm_runtime_data(self, value):
        # TODO: add validation ss
        self._scorm_runtime_data = value

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def get_fields_data(self, only_value=False, *fields):

        data = {}
        pkg_url = ''
        for k, v in self.fields.iteritems():
            if k in fields:
                if not only_value:
                    data[k] = v
                data["{}_value".format(k)] = getattr(self, k)
        #logger.info("Original: " + str(data))

        if 'scorm_pkg' in data and self.scorm_pkg:
            pkg_url = self.fs.get_url(self.scorm_pkg)
        if 'scorm_pkg' in data and self.scorm_pkg == '' and self.scorm_file != 'old':
            scorm_file_string = self.scorm_file[:22] + 'scorm/' + self.scorm_file[22:]
            pkg_url = self.fs.get_url(scorm_file_string)
        if pkg_url:
            #logger.info("Original URL: " + str(pkg_url))
            if settings.DJFS['type'] == 's3fs':
                parse = urlparse(pkg_url)
                pkg_url = parse.path
                pkg_url = urllib.unquote(pkg_url)
            data['scorm_pkg_value'] = pkg_url
            #logger.info("Return URL: " + str(pkg_url))

        if 'scorm_score' in data and self.scorm_score == float(0) and self.lesson_score != float(0):
            data['scorm_score_value'] = self.lesson_score

        if 'scorm_status' in data and self.scorm_status == SCORM_STATUS.UNATTENDED and self.success_status != 'unknown':
            data['scorm_status_value'] = self.success_status

        if 'scorm_pkg_version_value' in data and self.scorm_pkg_version == SCORM_VERSION.V12 and self.version_scorm == 'SCORM_2004':
            data['scorm_pkg_version_value'] = SCORM_VERSION.V2004

        if 'scorm_pkg_modified_value' in data and not self.scorm_pkg_modified and self.scorm_modified:
            data['scorm_pkg_modified_value'] = self.scorm_modified

        for k, v in data.items():
            if isinstance(v, timezone.datetime):
                data[k] = dt2str(v)

        #logger.info("Return: " + str(data))

        return data

    def get_student_data(self):
        fields_data = self.get_fields_data(False, 'scorm_score', 'weight', 'ratio',
                                           'has_score', 'scorm_status', 'scorm_pkg', 'scorm_file', 'lesson_score', 'success_status', 'open_new_tab')
        request = get_current_request()
        if fields_data['open_new_tab_value']:
            fields_data['open_new_tab_value'] = is_compatible(request)
        fields_data['graded_status'] = 'ungraded'
        if self.graded and fields_data['has_score'] and fields_data['weight'] != 0:
            fields_data['graded_status'] = 'graded'
        fields_data['display_name'] = self.display_name
        return fields_data

    def student_view(self, context=None):
        template = self.render_template('static/html/scormxblock.html', self.get_student_data())
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/scormxblock.js"))
        frag.initialize_js('ScormXBlock', json_args=self.get_fields_data(True, 'scorm_pkg_version', 'scorm_pkg_modified', 'ratio', 'version_scorm', 'scorm_modified', 'open_new_tab'))
        return frag

    def author_view(self, context):
        html = self.resource_string("static/html/author_view.html")
        frag = Fragment(html)
        return frag

    def raise_handler_error(self, msg):
        _ = self.ugettext
        raise JsonHandlerError(400, _(msg))

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        _ = self.ugettext
        try:
            name = data['name']
            package_version = data['package_version']
            package_date = data['package_date']
        except KeyError:
            self.raise_handler_error("missing parameters.")

        if package_version == SCORM_VERSION.V12:
            default = SCORM_12_RUNTIME_DEFAULT.get(name, '')
            if name == 'cmi.core.student_id':
                default = str(self.runtime.user_id)
            elif name == 'cmi.core.student_name':
                user = User.objects.get(id=self.runtime.user_id)
                default = user.username
            elif name == 'cmi.core.entry':
                if self.scorm_runtime_data.get('cmi.core.exit', None):
                    if self.scorm_runtime_data.get('cmi.core.exit') == 'suspend':
                        default = 'resume'
        elif package_version == SCORM_VERSION.V2004:
            default = SCORM_2004_RUNTIME_DEFAULT.get(name, '')
            if name == 'cmi.learner_id':
                default = str(self.runtime.user_id)
            elif name == 'cmi.learner_name':
                user = User.objects.get(id=self.runtime.user_id)
                default = user.username
            elif name == 'cmi.entry':
                if self.scorm_runtime_data.get('cmi.exit', None):
                    if self.scorm_runtime_data.get('cmi.exit') == 'suspend':
                        default = 'resume'
        else:
            self.raise_handler_error('error scorm package version')

        if name == 'cmi.launch_data':
            default = self.scorm_launch_data

        if self.is_pkg_expired(package_date):
            return {'error': _('scorm package expired, refresh page to get new content.')}
        #logger.info('get_value: ' + str(self.scorm_runtime_data.get(name, default)))

        return {"value": self.scorm_runtime_data.get(name, default)}

    def is_pkg_expired(self, package_date):
        return self.scorm_pkg_modified and package_date and str2dt(package_date) < self.scorm_pkg_modified

    def is_runtime_data_expired(self, package_date):
        expired = False
        need_update = True
        if self.scorm_pkg_modified:
            if package_date and str2dt(package_date) < self.scorm_pkg_modified:
                # when user still visit one scorm, but new package uploaded
                # so, no update, only update when user next time visit new uploaded scorm
                expired = True
                need_update = False
            elif self.scorm_runtime_modified and self.scorm_runtime_modified < self.scorm_pkg_modified:
                # normal case
                expired = True
                need_update = True
        return expired, need_update

    @XBlock.json_handler
    def scorm_commit(self, data, suffix=''):

        package_date = data.pop('package_date', '')
        package_version = data.pop('package_version', '')
        expired, need_update = self.is_runtime_data_expired(package_date)
        if expired:
            self.scorm_runtime_data = {}
        if need_update:
            self.scorm_runtime_data.update(data)

        self.scorm_runtime_modified = timezone.now()

        self.update_scorm_status(data, package_version)
        return self.get_fields_data(True, 'scorm_status', 'scorm_score')

    @XBlock.json_handler
    def scorm_enforce_commit(self, data, suffix=''):

        package_date = data.pop('package_date', '')
        package_version = data.pop('package_version', '')
        expired, need_update = self.is_runtime_data_expired(package_date)
        if expired:
            self.scorm_runtime_data = {}
        if need_update:
            self.scorm_runtime_data.update(data)

        self.scorm_runtime_modified = timezone.now()

        self.update_scorm_status(data, package_version)
        return self.get_fields_data(True, 'scorm_status', 'scorm_score')

    @XBlock.handler
    def scorm_ios_commit(self, request, suffix=''):

        post_data = request.POST.copy()
        post_data.pop('csrfmiddlewaretoken', '')
        package_date = post_data.pop('package_date', '')
        package_version = post_data.pop('package_version', '')
        expired, need_update = self.is_runtime_data_expired(package_date)
        update_data = {}
        for x,y in post_data.iteritems():
            update_data[x] = y
        if expired:
            self.scorm_runtime_data = {}
        if need_update:
            self.scorm_runtime_data.update(update_data)

        self.scorm_runtime_modified = timezone.now()

        self.update_scorm_status(update_data, package_version)
        response_data = self.get_fields_data(True, 'scorm_status', 'scorm_score')
        return Response(json_body=response_data, content_type='application/json')

    @XBlock.handler
    def sync_score_value(self, request, suffix=''):
        """
        Fix double refresh bug cause of unexpected terminal action
        """
        score_value = self.get_fields_data(True, 'scorm_score')
        return Response(json_body=score_value, content_type='application/json')

    @staticmethod
    def extract_runtime_info_12(data):
        info = {'status': SCORM_STATUS.IN_PROGRESS}
        if 'cmi.core.score.raw' in data:
            info["raw"] = float(data['cmi.core.score.raw'])
            info["maxi"] = float(data.get('cmi.core.score.max', 1.0))
            info["mini"] = float(data.get('cmi.core.score.min', 0.0))

        lesson_status = data.get('cmi.core.lesson_status', SCORM_STATUS.IN_PROGRESS)

        if lesson_status == 'passed':
            info['status'] = SCORM_STATUS.SUCCEED
        elif lesson_status == 'failed':
            info['status'] = SCORM_STATUS.FAILED

        return info

    @staticmethod
    def extract_runtime_info_2004(data):
        info = {'status': SCORM_STATUS.IN_PROGRESS}
        if 'cmi.score.raw' in data and 'cmi.score.max' in data and 'cmi.score.min' in data:
            info["raw"] = float(data['cmi.score.raw'])
            info["maxi"] = float(data['cmi.score.max'])
            info["mini"] = float(data['cmi.score.min'])
        elif 'cmi.score.scaled' in data:
            info['raw'] = float(data['cmi.score.scaled'])
            info['maxi'] = 1.0
            info['mini'] = 0.0

        success_status = data.get('cmi.success_status', SCORM_STATUS.IN_PROGRESS)
        if success_status == 'passed':
            info['status'] = SCORM_STATUS.SUCCEED
        elif success_status == 'failed':
            info['status'] = SCORM_STATUS.FAILED

        return info

    def update_scorm_status(self, data, version):
        if version == SCORM_VERSION.V12:
            info = self.extract_runtime_info_12(data)
        elif version == SCORM_VERSION.V2004:
            info = self.extract_runtime_info_2004(data)
        else:
            self.raise_handler_error('error scorm pkg version')

        score = None
        if 'raw' in info:
            score = Score(raw_earned=(info["raw"] - info["mini"]),
                          raw_possible=(info["maxi"] - info["mini"]))

        if score and (not self.has_submitted_answer() or self.allows_rescore()):
            self.set_score(score)
            self._publish_grade(self.get_score())

            self.scorm_status = info['status']

    @XBlock.handler
    def ping(self, request, suffix=''):
        return Response(status=200)

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("ScormXBlock",
             """<vertical_demo>
                <scormxblock/>
                </vertical_demo>
             """),
        ]
