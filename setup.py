#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Stephen Larroque <LRQ3000@gmail.com>

# See:
# https://docs.python.org/2/distutils/setupscript.html
# http://docs.cython.org/src/reference/compilation.html
# https://docs.python.org/2/extending/building.html
# http://docs.cython.org/src/userguide/source_files_and_compilation.html

try:
    from setuptools import setup
    from setuptools import Extension
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension

import codecs, os, re

# Get version, better than importing the module because can fail if the requirements aren't met
# See https://packaging.python.org/guides/single-sourcing-package-version/
curpath = os.path.abspath(os.path.dirname(__file__))
def read(*parts):
    with codecs.open(os.path.join(*parts), 'r') as fp:
        return fp.read()
def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(name = "pyugt",
    version = find_version(curpath, "pyugt", "_version.py"),
    description = "Universal Game Translator from on-screen text in Python",
    author = "Stephen Larroque",
    author_email = "lrq3000@gmail.com",
    license = "MIT",
    url = "https://github.com/lrq3000/pyugt",
    py_modules = ["pyugt"],
    platforms = ["any"],
    long_description = open("README.md", "r").read(),
    long_description_content_type = 'text/markdown',
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Topic :: Games/Entertainment",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        'Operating System :: MacOS :: MacOS X',
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    include_package_data=True,  # use MANIFEST.in to include config file
    packages=['pyugt'],  # to force the wheel to use the MANIFEST.in
    entry_points = {
        'console_scripts': ['pyugt=pyugt.pyugt:main'],  # create a binary that will be callable directly from the console
    },
    install_requires=[
        'PILLOW>=6.1.0',
        'keyboard>=0.13.4',
        'mss>=5.0.0',
        'pytesseract>=0.3.3',
        'googletrans>=2.4.0',
    ],
)

