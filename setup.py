#!/usr/bin/env python

import importlib.util
import sys

from setuptools import setup, find_packages

# read the contents of the README file
with open("README.rst", encoding="utf-8") as f:
    README = f.read()

spec = importlib.util.spec_from_file_location(
    "bluepyentity.version",
    "bluepyentity/version.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VERSION = module.__version__

setup(
    name="bluepyentity",
    author="'Blue Brain Project, EPFL'",
    version=VERSION,
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
    install_requires=
    [
        "click",
        "keyring",
        "lazy-object-proxy>=1.5.2,<2.0.0",
        "more-itertools>=8.2.0,<9.0.0",
        "nexusforge>=0.7.0,<1.0.0",
        "pyjwt",
        "rich",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    extras_require={"docs": ["sphinx", "sphinx-bluebrain-theme"]},
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
