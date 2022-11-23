# -*- coding: utf-8 -*-
import pkg_resources


class _ScromComponent(object):
    """Hold information of an scrom web content component on Studio page.
    """
    TAG_VIDEO = r'Video'
    TAG_QUIZ = r'Quiz'
    TAG_ELEARNING_AUTHORING_RECORDER= r'eLearning authoring tools'
    # The order of items in `ALL_TAGS` would be used as Tabs order in Author_View
    ALL_TAGS = [TAG_QUIZ, TAG_ELEARNING_AUTHORING_RECORDER, TAG_VIDEO]

    def __init__(self, icon, name, description, tags, paying, site_link, get_scrom_handler):
        """Constructor of Scrom  Web Content Configuration ( Support Image/Icon `SVG` only )
            @param icon:    path of Image SVG
            @type icon:     string
        """
        self.icon = icon
        self.name = name
        self.description = description
        self.tags = list(tags) if isinstance(tags, (list, tuple)) else [tags]
        self.paying = paying
        self.site_link = site_link
        self._get_scrom_handler = get_scrom_handler

        if not all([tag in _ScromComponent.ALL_TAGS for tag in self.tags]):
            raise NameError('Unsupported tags : {}'.format(str(self.tags)))
    def get_tags_set(self):
        return set(self.tags)

    @property
    def svg_image(self):
        """Return svg image description"""
        return self._get_scrom_handler().resource_string(self.icon)

    def __str__(self):
        return self.name
    


class SupportedScromResources(object):
    """An iterable object definition for listed `Tags` & `Sites`
    """
    _scrom_xblock_singleton = None

    def __init__(self):
        """Initialize scrom resources vector"""
        self._listed_tags = set()
        self._resources = []

        self._add_resource(
            icon='static/images/Loom.svg', name='Kumullus',
            tags=[_ScromComponent.TAG_VIDEO, _ScromComponent.TAG_QUIZ],
            paying=True,
            site_link=r'https://kumullus.com/',
            description=r'Add interactive video to your course'
        )
        self._add_resource(
            icon='static/images/Loom.svg', name='Articulate 360',
            tags=_ScromComponent.TAG_ELEARNING_AUTHORING_RECORDER,
            paying=True,
            site_link=r'https://articulate.com/360',
            description=r'Use Storyline 360 to create courses with custom interactivity or Rise to create responsive courses right in your web browser.'
        )
        self._add_resource(
            icon='static/images/ispring-suite.svg', name='iSpring Suite',
            tags=_ScromComponent.TAG_ELEARNING_AUTHORING_RECORDER,
            paying=True,
            site_link=r'https://www.ispringsolutions.com/ispring-suite',
            description=r'Create interactive courses and assessments in record time.'
        )
        self._add_resource(
            icon='static/images/adope-captivate.svg', name='Adobe Captivate',
            tags=_ScromComponent.TAG_ELEARNING_AUTHORING_RECORDER,
            paying=True,
            site_link=r'https://www.adobe.com/products/captivate.html',
            description=r'Create stunning courses in minutes.'
        )
        self._add_resource(
            icon='static/images/Loom.svg', name='Knowbly',
            tags=_ScromComponent.TAG_ELEARNING_AUTHORING_RECORDER,
            paying=True,
            site_link=r'https://echo360.com/the-echosystem/echoauthor/',
            description=r'Quickly create and customize beautiful interactive learning that works seamlessly on mobile and in any learning environment.'
        )
      

    def _add_resource(self, *args, **kwargs):
        """Add new Scrom Web Content Configuration to vector"""
        # append get method obj. of xblock instance method
        kwargs['get_scrom_handler'] = self.get_scrom_handler

        scrom_component = _ScromComponent(*args, **kwargs)
        self._listed_tags.update(scrom_component.get_tags_set())
        self._resources.append(scrom_component)

    def __iter__(self):
        """Return an iterable object"""
        return iter(self._resources)

    @property
    def listed_tags(self):
        """Return supported tags which were appended in method def __init__()
        """
        return [tag for tag in _ScromComponent.ALL_TAGS if tag in self._listed_tags]

    @classmethod
    def assign_scrom_handle(cls, obj):
        """Assign instance of scrom web content xblock to a class member
            @param obj:     instance of scrom web content xblock
            @type obj:      ScromContentXBlock
            @return:        instance of xblock
            @rtype:         ScromContentXBlock
        """
        if not cls._scrom_xblock_singleton:
            cls._scrom_xblock_singleton = obj

        return cls._scrom_xblock_singleton

    def get_scrom_handler(self):
        """Return instance of scrom web content xblock"""
        if not SupportedScromResources._scrom_xblock_singleton:
            raise ValueError('Invalid `SupportedScromResources._scrom_xblock_singleton`. (None)')

        return SupportedScromResources._scrom_xblock_singleton


SUPPORTED_SCROM_RESOURCES = SupportedScromResources()