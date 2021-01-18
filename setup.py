#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>

from __future__ import print_function

import os
from setuptools import setup
from os.path import join as path_join, dirname as path_dirname


CURRDIR = path_dirname(__file__)

setup_args = dict(
    name='kmailbox',
    version='0.0.1',
    py_modules=["kmailbox"],
    author='Huoty',
    author_email='sudohuoty@163.com',
    maintainer="Huoty",
    maintainer_email="sudohuoty@163.com",
    description="Python email utils",
    url="https://github.com/kuanghy/kmailbox",
    keywords=["email", "mailbox", "smtp", "imap", "sendmail"],
    zip_safe=False,
    license='Apache License v2',
    python_requires='>=2.7',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows',
    ],
)


def get_version():
    scope = {}
    version = '1.0'
    version_file = path_join(CURRDIR, "kmailbox.py")
    if os.path.exists(version_file):
        with open(version_file) as fp:
            exec(fp.read(), scope)
        version = scope.get('__version__', '1.0')
    return version


def get_long_description():
    with open(os.path.join(CURRDIR, 'README.rst'), 'rb') as f:
        long_description = f.read().decode('utf-8')
    return long_description


def main():
    setup_args["version"] = get_version()
    setup_args["long_description"] = get_long_description()
    setup_args["entry_points"] = {
        'console_scripts': [
            'kmailbox=kmailbox:_main',
        ],
    }
    setup(**setup_args)


if __name__ == "__main__":
    main()
