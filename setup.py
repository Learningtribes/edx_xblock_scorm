"""Setup for scormxblock XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setup(
    name='scormxblock-xblock',
    version='0.2',
    description='scormxblock XBlock',
    packages=[
        'scormxblock',
    ],
    python_requires='>=3.10',
    install_requires=[
        'Django>=5.2,<6',
        'XBlock>=6.1,<7',
        'lxml>=5,<6',
        'user-agents>=2.1',
        'fs>=2.4.16',
        'openedx-django-pyfs>=4.0.0',
        'six>=1.16',
    ],
    entry_points={
        'xblock.v1': [
            'scormxblock = scormxblock:ScormXBlock',
        ]
    },
    package_data=package_data("scormxblock", ["static", "public"]),
    license="Apache",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
    ]
)
