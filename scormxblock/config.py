# -*- coding: utf-8 -*-

TAG_VIDEO = r'Video'
TAG_QUIZ = r'Quiz'
TAG_ELEARNING_AUTHORING_RECORDER= r'eLearning authoring tools'
# The order of items in `ALL_TAGS` would be used as Tabs order in Author_View
ALL_TAGS = [TAG_QUIZ, TAG_ELEARNING_AUTHORING_RECORDER, TAG_VIDEO]


class ScormProvider(object):
    """Hold information of an scorm web content component on Studio page.
    """

    def __init__(self, xblock, name, icon, description, tags, paying, site_link):
        self.xblock = xblock
        self.name = name
        self.icon = xblock.runtime.local_resource_url(xblock, icon)
        self.description = description
        self.tags = [tag for tag in tags if tag in ALL_TAGS]
        self.paying = paying
        self.site_link = site_link

    def __str__(self):
        return self.name


class SupportedScormResources(object):
    """An iterable object definition for listed `Tags` & `Sites`
    """

    def __init__(self, xblock):
        self.xblock = xblock
        self._resources = []

        self._add_resource(
            name='Adobe Captivate',
            icon='public/images/adope-captivate.svg',
            tags=[TAG_ELEARNING_AUTHORING_RECORDER],
            paying=True,
            site_link=r'https://www.adobe.com/products/captivate.html',
            description=r'Create stunning courses in minutes.'
        )
        self._add_resource(
            name='Articulate 360',
            icon='public/images/ispring-suite.svg',
            tags=[TAG_ELEARNING_AUTHORING_RECORDER],
            paying=True,
            site_link=r'https://articulate.com/360',
            description=r'Use Storyline 360 to create courses with custom interactivity. Use Rise 360 to create responsive courses right in your web browser.'
        )
        self._add_resource(
            name='iSpring Suite',
            icon='public/images/ispring-suite.svg',
            tags=[TAG_ELEARNING_AUTHORING_RECORDER],
            paying=True,
            site_link=r'https://www.ispringsolutions.com/ispring-suite',
            description=r'Create interactive courses and assessments in record time.'
        )
        self._add_resource(
            name='Kumullus',
            icon='public/images/kumullus.svg',
            tags=[TAG_VIDEO, TAG_QUIZ],
            paying=True,
            site_link=r'https://kumullus.com/',
            description=r'Add interactive video to your course.'
        )

    def _add_resource(self, *args, **kwargs):
        self._resources.append(ScormProvider(self.xblock, *args, **kwargs))

    def __iter__(self):
        """Return an iterable object"""
        return iter(self._resources)

    @property
    def tags(self):
        """Return supported tags which were appended in method def __init__()
        """
        listed_tags = [provider.tags for provider in self._resources].flatten()
        return [tag for tag in ALL_TAGS if tag in listed_tags]
