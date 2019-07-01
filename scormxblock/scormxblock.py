import json
import re
import pkg_resources
import zipfile
import shutil

from django.utils import timezone
from django.utils.dateparse import parse_datetime

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from django.conf import settings
from django.template import Context, Template
from webob import Response
from crum import get_current_request
from xblock.core import XBlock
from xblock.fields import Scope, String, Float, Boolean, Dict, DateTime
from xblock.fragment import Fragment
import os
import logging
from scorm_default import *
# TODO After upgrade to new release, add more required function from
# API doc: https://openedx.atlassian.net/wiki/spaces/AC/pages/161400730/Open+edX+Runtime+XBlock+API
# TODO old data migrate how to
# TODO test all features
# TODO try to store advanvced cmi data in dict form

file_path = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger(__name__)

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

def dt2str(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

def str2dt(dtstr):
    return parse_datetime(dtstr)

@XBlock.needs('request')
class ScormXBlock(XBlock):
    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Scorm",
        scope=Scope.settings,
    )
    scorm_file = String(
        display_name=_("Upload scorm file"),
        scope=Scope.settings,
    )
    scorm_modified = DateTime(
        scope=Scope.settings,
    )
    version_scorm = String(
        default="SCORM_12",
        scope=Scope.settings,
    )
    # save completion_status for SCORM_2004
    lesson_status = String(
        scope=Scope.user_state,
        default='not attempted'
    )
    success_status = String(
        scope=Scope.user_state,
        default='unknown'
    )
    lesson_location = String(
        scope=Scope.user_state,
        default=''
    )
    suspend_data = String(
        scope=Scope.user_state,
        default=''
    )
    data_scorm = Dict(
        scope=Scope.user_state,
        default={}
    )
    lesson_score = Float(
        scope=Scope.user_state,
        default=0
    )
    weight = Float(
        display_name=_('Weight'),
        default=1.0,
        values={"min": 0, "step": .1},
        help=_("Weight of this Scorm, by default keep 1"),
        scope=Scope.settings
    )
    has_score = Boolean(
        display_name=_("Scored"),
        help=_("Select true if this component will receive a numerical score from the Scorm"),
        default=False,
        scope=Scope.settings
    )
    icon_class = String(
        default="video",
        scope=Scope.settings,
    )

    cmi_modified = DateTime(
        scope=Scope.user_state
    )
    cmi_data = Dict(
        scope=Scope.user_state,
        default={},
    )

    has_author_view = True


    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_fields_data(self, only_value=False, *fields):

        data = {}
        for k, v in self.fields.iteritems():
            if k in fields:
                if not only_value:
                    data[k] = v
                data["{}_value".format(k)] = getattr(self, k)

        if 'scorm_file' in data and self.scorm_file:
            request = get_current_request()
            scheme = 'https' if settings.HTTPS == 'on' else 'http'
            scorm_file_value = '{}://{}{}'.format(scheme, request.site.domain, self.scorm_file)
            data['scorm_file_value'] = scorm_file_value

        if 'scorm_modified_value' in data and data['scorm_modified_value']:
            data['scorm_modified_value'] = dt2str(data['scorm_modified_value'])
        if 'cmi_modified_value' in data and data['cmi_modified_value']:
            data['cmi_modified_value'] = dt2str(data['cmi_modified_value'])

        return data

    def studio_view(self, context=None):
        # context_html = self.get_context_studio()
        fields_data = self.get_fields_data(False, 'display_name', 'scorm_file', 'has_score', 'weight')
        template = self.render_template('static/html/studio.html', fields_data)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/studio.js"))
        frag.initialize_js('ScormStudioXBlock')
        return frag

    def get_student_data(self):
        fields_data = self.get_fields_data(False, 'lesson_score', 'weight',
                                           'has_score', 'success_status', 'scorm_file')
        return fields_data

    def student_view(self, context=None):
        template = self.render_template('static/html/scormxblock.html', self.get_student_data())
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/scormxblock.js"))
        frag.initialize_js('ScormXBlock', json_args=self.get_fields_data(True, 'version_scorm', 'scorm_modified'))
        return frag

    @XBlock.handler
    def studio_submit(self, request, suffix=''):
        self.display_name = request.params['display_name']
        self.has_score = request.params['has_score']
        self.weight = request.params['weight']
        self.icon_class = 'problem' if self.has_score == 'True' else 'video'
        if hasattr(request.params['file'], 'file'):
            file = request.params['file'].file
            zip_file = zipfile.ZipFile(file, 'r')
            path_to_file = os.path.join(settings.PROFILE_IMAGE_BACKEND['options']['location'], self.location.block_id)
            path_to_file = str(path_to_file)
            if os.path.exists(path_to_file):
                shutil.rmtree(path_to_file, ignore_errors=True)
            zip_file.extractall(path_to_file)
            self.set_scorm(path_to_file)
        return Response(json.dumps({'result': 'success'}), content_type='application/json')

    def author_view(self, context):
        html = self.resource_string("static/html/author_view.html")
        frag = Fragment(html)
        return frag

    # @XBlock.json_handler
    # def scorm_get_value(self, data, suffix=''):
    #     name = data.get('name')
    #     if name in ['cmi.core.lesson_status', 'cmi.completion_status']:
    #         return {'value': self.lesson_status}
    #     elif name == 'cmi.success_status':
    #         return {'value': self.success_status}
    #     elif name == 'cmi.core.lesson_location':
    #         return {'value': self.lesson_location}
    #     elif name == 'cmi.suspend_data':
    #         return {'value': self.suspend_data}
    #     else:
    #         return {'value': self.data_scorm.get(name, '')}
    # @XBlock.json_handler
    # def commit(self, data, suffix=''):
    #     context = {'result': 'success'}
    #     for name, value in data.iteritems():
    #         if name in ['cmi.core.lesson_status', 'cmi.completion_status']:
    #             self.lesson_status = value
    #             if self.has_score and value in ['completed', 'failed', 'passed']:
    #                 context.update({"lesson_score": self.lesson_score})
    #
    #         elif name == 'cmi.success_status':
    #             self.success_status = value
    #             if self.has_score:
    #                 if self.success_status == 'unknown':
    #                     self.lesson_score = 0
    #                 context.update({"lesson_score": self.lesson_score})
    #
    #         elif name in ['cmi.core.score.raw', 'cmi.score.raw'] and self.has_score:
    #             score = float(data.get(name, 0))
    #             self.lesson_score = score / 100.0
    #             if self.lesson_score > self.weight:
    #                 logger.error("error score, user {}: {}".format(
    #                     self.get_user_id(),
    #                     self.data
    #                 ))
    #             context.update({"lesson_score": self.lesson_score})
    #
    #         elif name == 'cmi.core.lesson_location':
    #             self.lesson_location = str(value) or ''
    #
    #         elif name == 'cmi.suspend_data':
    #             self.suspend_data = value or ''
    #         else:
    #             self.data_scorm[name] = value or ''
    #
    #     self.publish_grade()
    #     context.update({"completion_status": self.get_completion_status()})
    #     return context

    def is_cmi_data_expired(self, package_date):
        expired = False
        need_update = True
        if self.scorm_modified:
            if package_date and str2dt(package_date) < self.scorm_modified:
                # when user still visit one scorm, but new package uploaded
                # so, no update, only update when user next time visit new uploaded scorm
                expired = True
                need_update = False
            elif self.cmi_modified and self.cmi_modified < self.scorm_modified:
                # normal case
                expired = True
                need_update = True
        return expired, need_update

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        name = data['name']
        package_version = data.pop('package_version', '')

        if package_version == 'SCORM_12':
            default = SCORM_12_RUNTIME_DEFAULT.get(name, '')
        else:
            default = SCORM_2004_RUNTIME_DEFAULT.get(name, '')

        package_date = data.pop('package_date', '')
        if self.is_cmi_data_expired(package_date)[0]:
            value = default
        else:
            value = self.cmi_data.get(name, default)

        return {"value": value}


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
            if 'cmi.core.score.min' in data and 'cmi.core.score.max' in data:
                score = (float(data['cmi.core.score.raw']) - float(data['cmi.core.score.min']))/(float(data['cmi.core.score.max']) - float(data['cmi.core.score.min']))
                self.lesson_score = score
                score_updated = True
            else:
                score = float(data['cmi.core.score.raw'])
                '''
                if score < 0:
                    score = float(0)
                if self.lesson_score != float(100):
                    self.lesson_score = score
                '''
                self.lesson_score = score
                score_updated = True

        if 'cmi.core.lesson_status' in data:
            self.cmi_data['cmi.core.lesson_status'] = data['cmi.core.lesson_status']
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

    def publish_grade(self):
        self.runtime.publish(
            self,
            'grade',
            {
                'value': self.lesson_score,
                'max_value': 1.0,
            })

    def get_user_id(self):
        return getattr(self.runtime, 'user_id', None)

    def max_score(self):
        """
        Return the maximum score possible.
        """
        return self.weight if self.has_score else None


    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

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

    def get_completion_status(self):
        return self.success_status

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
