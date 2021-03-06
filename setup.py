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
    description='scormxblock XBlock',   # TODO: write a better description.
    packages=[
        'scormxblock',
    ],
    install_requires=[
        'XBlock==1.2.9',
        'lxml==3.8.0',
        'web-fragments==0.2.2',
        'user-agents==2.1',
    ],
    dependency_links=[
        'git+https://github.com/Learningtribes/xblock-utils.git@ec95e5e718c4144dc8a43d116a545f210d929667#egg=xblock-utils',
        'git+https://github.com/Learningtribes/django-pyfs.git@d52e58dc88d755e332bdcc4ab1dd0b004e11ad11#egg=django-pyfs',
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
