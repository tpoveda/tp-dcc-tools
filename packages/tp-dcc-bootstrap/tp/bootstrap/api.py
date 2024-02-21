#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains API module for tpDcc Tools packages manager
"""

from tp.bootstrap.core.manager import package_manager_from_path, current_package_manager
from tp.bootstrap.core.manager import set_current_package_manager
from tp.bootstrap.commands import run_command
from tp.bootstrap import consts
from tp.bootstrap.core.exceptions import (
	PackageAlreadyExistsError, MissingPackage, MissingPackageVersionError, DescriptorMissingKeysError,
	UnsupportedDescriptorTypeError, MissingGitPythonError, InvalidPackagePathError, MissingEnvironmentPathError,
	GitTagAlreadyExistsError, MissingCommandArgumentError
)
