#!/usr/bin/env python

import importlib.util
import sys

from setuptools import setup, find_packages

# read the contents of the README file
with open("README.rst", encoding="utf-8") as f:
    README = f.read()

spec = importlib.util.spec_from_file_location(
    "entity_management.version",
    "entity_management/version.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VERSION = module.__version__

setup(
    name="entity-management",
    author="'Blue Brain Project, EPFL'",
    version=VERSION,
    description="NEXUS Productivity Layer",
    long_description=README,
    long_description_content_type="text/x-rst",
    url="https://github.com/BlueBrain/entity-management/",
    project_urls={
        "Tracker": "https://github.com/BlueBrain/entity-management/",
        "Source": "https://github.com/BlueBrain/entity-management/",
    },
    license="BBP-internal-confidential",
    install_requires=[],
    packages=find_packages(),
    python_requires=">=3.6",
    extras_require={"docs": ["sphinx", "sphinx-bluebrain-theme"]},
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
