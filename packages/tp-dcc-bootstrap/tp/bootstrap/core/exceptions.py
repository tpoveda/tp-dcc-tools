#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains custom exceptions used by tpDcc packages manager
"""


class MissingCommandArgumentError(Exception):
    """
    Exception that raises when an argument is missing during a tpDcc client action execution
    """

    pass


class MissingEnvironmentPathError(Exception):
    """
    Exception that raises when the package_version.config file does not exist
    """

    pass


class PackageAlreadyExistsError(Exception):
    """
    Exception that raises when the package requested already exists.
    """

    pass


class InvalidPackagePathError(Exception):
    """
    Exception that raises when the package path requested is not compatible with tpDcc tools.
    """

    pass


class MissingPackage(Exception):
    """
    Exception that raises when the requested package does not exist
    """

    pass


class MissingPackageVersionError(Exception):
    """
    Exception that raises when the requested package does not exist in the packages location
    """

    pass


class DescriptorMissingKeysError(Exception):
    """
    Exception that raises when the provided descriptor keys does not meet the required descriptor keys
    """

    pass


class UnsupportedDescriptorTypeError(Exception):
    """
    Exception that raises when the provided descriptor information nodes not match any existing descriptor.
    """

    pass


class MissingGitPythonError(Exception):
    """
    Exception that raises when git python is not installed in the current Python environment.
    """

    def __init__(self, *args, **kwargs):
        msg = 'Must have GitPython installed in current environment to work with Git'
        super(MissingGitPythonError, self).__init__(msg, *args, **kwargs)


class GitTagAlreadyExistsError(Exception):
    """
    Exception that raises when requrest for tag creation on an already existing tag.
    """

    pass


class InvalidGitRepositoryError(Exception):
    """
    Exception that raises when an invalid repository is requrested.
    """

    pass


class DirtyGitRepoError(Exception):
    """
    Exception that raises when a repo has uncommited changes
    """

    pass


class IncorrectCurrentBranchError(Exception):
    """
    Exception that raises when a new release is tried to be done in a branch that is not master
    """

    pass


class GitCommandError(Exception):
    """
    Exception that raises when a Git command fails
    """

    pass


class ProjectNotDefinedError(Exception):
    """
    Custom exception raised when tpDcc project is not defined
    """

    pass
