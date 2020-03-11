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

setup(name = "pyugt",
    version = "0.2.2",
    description = "Pure-Python Universal Game Translator",
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
        #'Operating System :: MacOS :: MacOS X',  # hopefully in the future if we get hotkeys to work on this platform
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
)

