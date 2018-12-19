# -*- coding: utf-8 -*-
import tempfile
import os
import pkg_resources
import uuid
import logging

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from django.core.files.storage import FileSystemStorage
from django.template import Context, Template

from xblock.core import XBlock
from xblock.fields import String, Scope, Dict, Boolean, Float
from xblock.reference.plugins import Filesystem

from web_fragments.fragment import Fragment
from webob.response import Response
from fs.copy import copy_dir
from fs.zipfs import ZipFS
from xblockutils.studio_editable import StudioEditableXBlockMixin


from .fields import DateTime
from .mixins import ScorableXBlockMixin
logger = logging.getLogger(__name__)
# Make '_' a no-op so we can scrape strings
_ = lambda text: text

temp_storage = FileSystemStorage(location=os.path.join(tempfile.gettempdir(), 'scormxblock'))


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

    scorm_pkg = Filesystem(
        accept="application/zip",
        default=None,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Scorm Package"),
        help=_("Scorm package in `.zip` format")
    )

    scorm_pkg_id = String(
        default="",
        scope=Scope.settings,
        enforce_type=True,
        display_name=_('Scorm ID'),
        help=_('Scorm Id stored in system')
    )

    scorm_version = String(
        default="SCORM_12",
        scope=Scope.settings,
        values=("SCORM2004", "SCORM12"),
        enforce_type=True,
        display_name=_('Version'),
        help=_('Version of scorm, 1.2 or 2004')
    )

    _scorm_runtime_data = Dict(
        default={},
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

    @XBlock.handler
    def studio_upload_files(self, request, suffix=''):
        pkg = request.POST['scorm_pkg']
        pkg_id = uuid.uuid4().hex
        zipfs = ZipFS(pkg.file)
        try:
            copy_dir(zipfs, u'/', self.scorm_pkg, pkg_id)
        except IOError:
            return self._raise_pyfs_error('upload_screenshot')
        self.scorm_pkg_id = pkg_id
        self.save()
        resp = Response()
        resp.status = 200
        return resp

    def set_scorm(self, path_to_file):
        path_index_page = 'index.html'
        try:
            tree = ET.parse('{}/imsmanifest.xml'.format(path_to_file))
        except IOError:
            pass
        else:
            namespace = ''
            for node in [node for _, node in
                         ET.iterparse('{}/imsmanifest.xml'.format(path_to_file), events=['start-ns'])]:
                if node[0] == '':
                    namespace = node[1]
                    break
            root = tree.getroot()

            if namespace:
                resource = root.find('{{{0}}}resources/{{{0}}}resource'.format(namespace))
                schemaversion = root.find('{{{0}}}metadata/{{{0}}}schemaversion'.format(namespace))
            else:
                resource = root.find('resources/resource')
                schemaversion = root.find('metadata/schemaversion')

            if resource:
                path_index_page = resource.get('href')

            if (not schemaversion is None) and (re.match('^1.2$', schemaversion.text) is None):
                self.version_scorm = 'SCORM_2004'
            else:
                self.version_scorm = 'SCORM_12'

        self.scorm_modified = timezone.now()
        self.scorm_file = os.path.join(settings.PROFILE_IMAGE_BACKEND['options']['base_url'],
                                       '{}/{}'.format(self.location.block_id, path_index_page))


    def allows_rescore(self):
        return self.scorm_allow_rescore

    @property
    def scorm_runtime_data(self):
        return self._scorm_runtime_data

    @scorm_runtime_data.setter
    def scorm_runtime_data(self, value):
        # TODO: add validation s
        pass

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def student_view(self):
        template = self.render_template('static/html/scormxblock.html', {})
        return Fragment(template)

    def author_view(self, context):
        html = self.resource_string("static/html/author_view.html")
        frag = Fragment(html)
        return frag

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
