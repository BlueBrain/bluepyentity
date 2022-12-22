#!/usr/bin/env python
# SPDX-License-Identifier: LGPL-3.0-or-later

from setuptools import setup, find_packages

with open("README.rst", encoding="utf-8") as f:
    README = f.read()

EXTRA_KRB = [
    "requests_kerberos",
]

setup(
    name="bluepyentity",
    author="'Blue Brain Project, EPFL'",
    description="NEXUS Productivity Layer",
    long_description=README,
    long_description_content_type="text/x-rst",
    url="https://github.com/BlueBrain/bluepyentity/",
    project_urls={
        "Tracker": "https://github.com/BlueBrain/bluepyentity/",
        "Source": "https://github.com/BlueBrain/bluepyentity/",
    },
    license="BBP-internal-confidential",
    entry_points="""
        [console_scripts]
        bluepyentity=bluepyentity.app.main:main
    """,
    install_requires=[
        "click",
        "keyring",
        "lazy-object-proxy>=1.5.2,<2.0.0",
        "more-itertools>=8.2.0,<9.0.0",
        "nexusforge>=0.7.0,<1.0.0",
        "pyjwt",
        "rich",
        "more-itertools",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    extras_require={
        "docs": ["sphinx", "sphinx-bluebrain-theme"],
        "krb": EXTRA_KRB,
    },
    use_scm_version={
        "local_scheme": "no-local-version",
    },
    setup_requires=[
        "setuptools_scm",
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
