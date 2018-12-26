# -*- coding: utf-8 -*-
from __future__ import division
import os
import pkg_resources
import uuid
import logging
import re
from lxml import etree

from django.template import Context, Template
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from xblock.core import XBlock
from xblock.exceptions import XBlockSaveError
from xblock.scorable import Score
from xblock.fields import String, Scope, Dict, Boolean, Float
from xblock.reference.plugins import Filesystem

from web_fragments.fragment import Fragment
from webob.response import Response
from fs.copy import copy_dir
from fs.zipfs import ZipFS
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblockutils.fields import File

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


class ScormVersion(object):
    SCORM12 = 'SCORM12'
    SCORM2004 = 'SCORM2004'


@XBlock.needs('fs')
@XBlock.needs('i18n')
@XBlock.needs('request')
class ScormXBlock(StudioEditableXBlockMixin, ScorableXBlockMixin, XBlock):
    """
    all fields private to `scorm` are prefix with `scorm`, in case any conflict
    with internal fields.
    """
    display_name = String(
        default="Scorm",
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
        help=_("Does this scorm, need to be scored?")
    )

    icon_class = String(
        default='problem',
        scope=Scope.settings,
        values=("problem", "video", "other"),
        enforce_type=True,
        display_name=_("Icon"),
        help=_("Icon be used in course page")
    )

    weight = Float(
        default=1.0,
        scope=Scope.settings,
        values={"min": 0, "step": 0.1},
        enforce_type=True,
        display_name=_('Weight'),
        help=_('Relative weight in this course section')
    )

    fs = Filesystem(scope=Scope.settings)

    scorm_pkg = File(
        accept="application/zip",
        default="",
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Scorm Package"),
        help=_("Scorm package in `.zip` format")
    )

    scorm_pkg_version = String(
        default=ScormVersion.SCORM12,
        scope=Scope.settings,
        values=(ScormVersion.SCORM12, ScormVersion.SCORM2004),
        enforce_type=True,
        display_name=_('Version'),
        help=_('Version of scorm, 1.2 or 2004')
    )

    scorm_pkg_modified = DateTime(
        scope=Scope.settings,
        enforce_type=True,
        display_name=_('Upload time'),
        help=_('Scorm package upload time utc')
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
        help=_('Scorm runtime modified time utc')
    )

    scorm_status = String(
        default='UNATTENDED',
        scope=Scope.user_state,
        values=('FAILED', 'SUCCEED', 'IN PROGRESS', 'UNATTENDED'),
        enforce_type=True
    )

    scorm_score = Float(
        default=0,
        scope=Scope.user_state,
        enforce_type=True
    )

    scorm_allow_rescore = Boolean(
        default=True,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Rescore"),
        help=_("Does this scorm allow users submit answer multiple times?")
    )

    editable_fields = ('scorm_pkg', 'display_name', 'due', 'has_score', 'icon_class', 'weight', 'scorm_allow_rescore')
    has_author_view = True

    # region Studio handler
    @XBlock.handler
    def studio_upload_files(self, request, suffix=''):
        pkg = request.POST.get('scorm_pkg', None)
        if not pkg:
            return Response(status=400)
        zipfs = ZipFS(pkg.file)
        with zipfs.open(u'imsmanifest.xml') as mf:
            self.scorm_pkg_version, scorm_index = self._get_scorm_info(mf)
        pkg_id = self._upload_scorm_pkg(zipfs)
        self.scorm_pkg = os.path.join(pkg_id, scorm_index)
        self.scorm_pkg_modified = timezone.now()
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
        root = etree.parse(manifest).getroot()
        resource = root.find('resources/resource', root.nsmap)
        schemaversion = root.find('metadata/schemaversion', root.nsmap)
        scorm_version = ScormVersion.SCORM12
        if resource:
            index_page = resource.get('href')

        if (schemaversion is not None) and (re.match('^1.2$', schemaversion.text) is None):
            scorm_version = ScormVersion.SCORM2004
        return scorm_version, index_page
    # endregion

    # region Runtime functions
    def max_score(self):
        return 1.0

    def allows_rescore(self):
        return self.scorm_allow_rescore

    def set_score(self, score):
        self.scorm_score = self.max_score() * score.raw_earned / score.raw_possible
        self.save()

    def get_score(self):
        return Score(raw_possible=self.max_score(), raw_earned=self.scorm_score)

    def calculate_score(self):
        return self.get_score()

    def has_submitted_answer(self):
        return self.scorm_status in self.fields['scorm_status'].values

    # endregion


    @property
    def scorm_runtime_data(self):
        return self._scorm_runtime_data

    @scorm_runtime_data.setter
    def scorm_runtime_data(self, value):
        # TODO: add validation ss
        pass

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
        for k, v in self.fields.iteritems():
            if k in fields:
                if not only_value:
                    data[k] = v
                data["{}_value".format(k)] = getattr(self, k)

        if 'scorm_pkg' in data and self.scorm_pkg:
            data['scorm_pkg_value'] = self.fs.get_url(self.scorm_pkg)

        for k, v in data.items():
            if isinstance(v, timezone.datetime):
                data[k] = dt2str(v)

        return data

    def get_student_data(self):
        fields_data = self.get_fields_data(False, 'scorm_score', 'weight',
                                           'has_score', 'scorm_status', 'scorm_pkg')
        return fields_data

    def student_view(self, context=None):
        template = self.render_template('static/html/scormxblock.html', self.get_student_data())
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/scormxblock.js"))
        frag.initialize_js('ScormXBlock', json_args=self.get_fields_data(True, 'scorm_pkg_version', 'scorm_pkg_modified'))
        return frag

    def author_view(self, context):
        html = self.resource_string("static/html/author_view.html")
        frag = Fragment(html)
        return frag

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        name = data['name']
        package_version = data.pop('package_version', '')

        if package_version == 'SCORM_12':
            default = SCORM_12_RUNTIME_DEFAULT.get(name, '')
        else:
            default = SCORM_2004_RUNTIME_DEFAULT.get(name, '')

        package_date = data.pop('package_date', '')
        if self.is_runtime_data_expired(package_date)[0]:
            value = default
        else:
            value = self.scorm_runtime_data.get(name, default)

        return {"value": value}

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
    def commit(self, data, suffix=''):
        package_date = data.pop('package_date', '')
        package_version = data.pop('package_version', '')
        expired, need_update = self.is_cmi_data_expired(package_date)
        if expired:
            self.cmi_data = {}
        if need_update:
            self.cmi_data.update(data)

        self.cmi_modified = timezone.now()

        if self.set_lesson(data, package_version):
            self.publish_grade()
        return self.get_fields_data(True, 'success_status', 'lesson_score')

    def _set_lesson_12(self, data):
        score_updated = False
        if 'cmi.core.score.raw' in data:
            score = (float(data['cmi.core.score.raw']) - float(data['cmi.core.score.min'])
                     )/(float(data['cmi.core.score.max']) - float(data['cmi.core.score.min']))
            self.lesson_score = score
            score_updated = True

        if 'cmi.core.lesson_status' in data:
            self.success_status = data['cmi.core.lesson_status']

        return score_updated

    def _set_lesson_2004(self, data):
        score_updated = False
        if 'cmi.score.scaled' in data:
            self.lesson_score = float(data['cmi.score.scaled'])
            score_updated = True
        if 'cmi.success_status' in data:
            self.success_status = data['cmi.success_status']
        return score_updated

    def set_lesson(self, data, version):
        """
        all the score has been resize to [0, 1]
        """
        if version == 'SCORM_12':
            return self._set_lesson_12(data)
        else:
            return self._set_lesson_2004(data)

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
