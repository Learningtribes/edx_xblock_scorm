# -*- coding: utf-8 -*-
import pkg_resources
from web_fragments.fragment import Fragment

from xblock.core import XBlock
from xblock.fields import String, Scope, Dict, Boolean, Float
from xblock.reference.plugins import Filesystem
from xblockutils.studio_editable import StudioEditableXBlockMixin

from django.template import Context, Template

from .fields import DateTime
from .mixins import ScorableXBlockMixin
# Make '_' a no-op so we can scrape strings
_ = lambda text: text


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
        default=None,
        scope=Scope.settings,
        enforce_type=True,
        display_name=_("Scorm Package"),
        help=_("Scorm package in `.zip` format")
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

    def allows_rescore(self):
        return self.scorm_allow_rescore

    @property
    def scorm_runtime_data(self):
        return self._scorm_runtime_data

    @scorm_runtime_data.setter
    def scorm_runtime_data(self, value):
        # TODO: add validation logic
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
