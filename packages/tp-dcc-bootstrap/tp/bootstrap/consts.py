#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains constant definitions used by tpDcc package manager
"""

# package environment YAML environment variable
TPDCC_PACKAGE_VERSION_PATH = 'TPDCC_PACKAGE_VERSION_PATH'
TPDCC_PACKAGE_OVERRIDE_VERSION_PATH = 'TPDCC_PACKAGE_OVERRIDE_VERSION_PATH'
TPDCC_PACKAGE_VERSION_FILE = 'TPDCC_PACKAGE_VERSION_FILE'
TPDCC_PACKAGE_OVERRIDE_VERSION_FILE = 'TPDCC_PACKAGE_OVERRIDE_VERSION_FILE'

# manager environment variables
TPDCC_CACHE_FOLDER_PATH_ENV = 'TPDCC_CACHE_FOLDER_PATH'
TPDCC_ADMIN_ENV = 'TPDCC_ADMIN'

# configuration folder name
CONFIG_FOLDER_NAME = 'config'

# packages folder name
PACKAGES_FOLDER_NAME = 'packages'
PACKAGES_FOLDER_PATH = 'TPDCC_PACKAGE_PACKAGES_PATH'

# environment variable which defines the location of commands
TPDCC_COMMAND_LIBRARY_ENV = 'TPDCC_COMMANDS_PATH'

# package file name
PACKAGE_NAME = 'package.yaml'

# Package manager commander runner
PACKAGE_MANAGER_ROOT_NAME = 'tp-dcc-tools Package Manager Command Runner'

# file names to exclude when installing/copying packages
FILE_FILTER_EXCLUDE = (
    '.gitignore', '.gitmodules', 'setup.py', 'docs', '*.git', '*.vscode', '*__pycache__', '*.idea',
    'MANIFEST.ini', '*.pyc')

# configuration folder token for descriptors
CONFIG_FOLDER_TOKEN = '{config}'

# package folder token for descriptors
PACKAGE_FOLDER_TOKEN = '{self}'

# application (dcc) token for descriptors
APP_NAME_TOKEN = '{app}'

# application (dcc version) token for descriptors
APP_VERSION_TOKEN = '{appversion}'

# interpreter (Python version) token for descriptors (py2, py3, ...)
PY_VERSION_NAME_TOKEN = '{pyversionname}'

# tpDcc project token for descriptors
PROJECT_NAME_TOKEN = '{project}'

# install folder token for descriptors
INSTALL_FOLDER_TOKEN = '{install}'

# regex filter used to define package variables dependencies
DEPENDENT_FILTER = r"\{(.*?)\}"