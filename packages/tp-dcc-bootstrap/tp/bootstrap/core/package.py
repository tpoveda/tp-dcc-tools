#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc tools package manager package implementation
"""

from __future__ import annotations

import os
import re
import sys
import copy
import shutil
import platform
import tempfile
from typing import Dict, Any, Callable
from distutils.version import LooseVersion

import six

from tp.bootstrap import log, consts
from tp.bootstrap.core import requirements
from tp.bootstrap.utils import fileio, env, modules

logger = log.bootstrapLogger


def is_package_directory(directory: str) -> bool:
    """
    Returns whether given directory contains a package.

    :param str directory: absolute path to a directory.
    :return: True if given directory contains a pacakge; False otherwise.
    :rtype: bool
    """

    return directory and os.path.isdir(directory) and os.path.isfile(os.path.join(directory, consts.PACKAGE_NAME))


class Package:
    """
    Class that represents a tp-dcc-tools framework package
    """

    def __init__(self, package_path: str | None = None):
        super().__init__()

        self._path = package_path or ''
        self._root = ''
        self._environ = {}
        self._cache = {}
        self._enabled = True
        self._required = False
        self._version = LooseVersion()
        self._name = ''
        self._display_name = ''
        self._description = ''
        self._author = ''
        self._author_email = ''
        self._tokens = {}
        self._requirements = requirements.RequirementsList()
        self._requirements_path = ''
        self._pip_requirements = requirements.RequirementsList()
        self._tests = []
        self._documentation = {}
        self._resolved = False                      # whether this package has been loaded into the current environment.
        self._command_paths = []
        self._resolved_env = {}
        self._dccs = {}

        if package_path is not None and os.path.exists(package_path):
            self._process_file(package_path=package_path)

    def __hash__(self):
        return hash(id(self))

    def __repr__(self) -> str:
        return self.search_str()

    def __eq__(self, other: Any) -> bool:
        if other is None or not isinstance(other, Package):
            return False
        return self.name == other.name and self.version == other.version

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    @property
    def path(self) -> str:
        return self._path

    @property
    def root(self) -> str:
        return self._root

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def version(self) -> LooseVersion:
        return self._version

    @version.setter
    def version(self, value: LooseVersion):
        self._version = value

    @property
    def requirements(self) -> requirements.RequirementsList:
        return self._requirements

    @property
    def resolved(self) -> bool:
        return self._resolved

    @property
    def required(self) -> bool:
        return self._required

    @property
    def dccs(self):
        return self._dccs

    @staticmethod
    def name_from_package_name_and_version(package_name: str, package_version: str) -> str:
        """
        Returns full package name nad version based on given name and version.

        :param str package_name: package name.
        :param str package_version: package version.
        :return: full package name.
        :rtype: str
        """

        return '-'.join([package_name, package_version])

    @staticmethod
    def copy_to(
            package: Package, destination: str,
            ignore: Callable = shutil.ignore_patterns(*consts.FILE_FILTER_EXCLUDE)) -> Package:
        """
        Copies given package instance to given directory.

        :param Package package: package to copy.
        :param str destination: directory to move package into.
        :param Callable ignore: list of files to skip from moving.
        :return: copied package instance.
        :rtype: Package
        :raises FileNotFoundError: if destination directory already exists.
        """

        if os.path.exists(destination):
            raise FileNotFoundError(destination)

        shutil.copytree(package.dirname(), destination, ignore=ignore)

        return Package(os.path.join(destination, consts.PACKAGE_NAME))

    @classmethod
    def from_data(cls, data: Dict) -> Package:
        """
        Instantiates a new Package based on given data.

        :param Dict data: package data.
        :return: new package instance.
        :rtype: Package
        """

        new_package = cls()
        new_package._process_data(data)

        return new_package

    def exists(self) -> bool:
        """
        Returns whether this package exists in disk.

        :return: True if package exists in disk; False otherwise.
        :rtype: bool
        """

        return os.path.exists(self._path)

    def dirname(self) -> str:
        """
        Returns package directory name.

        :return: package directory.
        :rtype: str
        """

        return os.path.dirname(self._path)

    def search_str(self) -> str:
        """
        Returns the package name properly formatted.

        :return: formatted package name.
        :rtype: str
        """

        try:
            return self.name + '-' + str(self.version)
        except AttributeError:
            return self.path + '- (Fail)'

    def set_name(self, name: str):
        """
        Sets package name.

        :param str name: new package name.
        """

        self._name = name
        self.save()

    def set_path(self, path: str):
        """
        Sets package path.

        :param str path: new absolute package path.
        """

        self._path = os.path.normpath(path)
        self._root = os.path.dirname(path)

    def set_version(self, version_str: str):
        """
        Sets package version.

        :param str version_str: new package version as string.
        """

        self._version = LooseVersion(version_str)
        self._cache['version'] = str(self._version)

    def set_enabled(self, flag: bool):
        """
        Sets whether this package is enabled.

        :param bool flag: True to enable package; False otherwise.
        """

        self._enabled = flag

    def resolve(self, apply_environment: bool = True) -> bool:
        """
        Resolves package internal data and environment variables.

        :param bool apply_environment: whether to update "sys.path" environment variable based on package "PYTHONPATH"
            defined environment variables.
        :return: True if package was resolved successfully; False otherwise.
        :rtype: bool
        """

        environ = self._environ
        if not environ:
            logger.warning(f'Unable to resolve package environment due to invalid package: {self.path}')
            self._resolved = False
            return False

        # If package only should work with specific DCCs, we check that and avoid resolving if we are not running
        # the specific DCC.
        if self._dccs:
            if not env.application() in self._dccs:
                logger.debug(
                    f'Skipping package resolving because is not compatible with current DCC: {env.application()}')
                return False
            if self._dccs[env.application()] and env.application_version() not in self._dccs[env.application()]:
                logger.debug('Skipping package resolving because is not compatible with current '
                             f'DCC version: {env.application()} {env.application_version()}')
                return False

        self._command_paths = Variable('commands', self._command_paths).solve(self._tokens)

        pkg_variables = dict()
        for key, paths in environ.items():
            var = Variable(key, [paths] if isinstance(paths, six.string_types) else paths)
            var.solve(self._tokens)
            if apply_environment:
                env.add_to_env(key, var.values)
            pkg_variables[key] = var
        if apply_environment and 'PYTHONPATH' in pkg_variables:
            for py_var in pkg_variables['PYTHONPATH'].values:
                py_var = env.clean_path(py_var)
                if py_var not in sys.path:
                    sys.path.append(py_var)
        self._resolved_env = pkg_variables
        logger.debug(f'Resolved {self.name}: {self.root}')
        self._resolved = True

    def resolve_env_path(self, key, values, apply_environment=True):
        """
        Resolves package speicifc key with given values.

        :param str key: environment variable key.
        :param list[str] values: list of values.
       :param bool apply_environment: whether to update sys.path environment variable based on package PYTHONPATH
            defined environment variables.
        """

        existing_var = self._resolved_env.get(key)
        if existing_var:
            existing_var.values += values
            existing_var.solve(self._tokens)
        else:
            existing_var = Variable(key, values)
            existing_var.solve(self._tokens)
            self._resolved_env[key] = existing_var

        if not apply_environment:
            return
        env.add_to_env(key, existing_var.values)
        if key == 'PYTHONPATH':
            for py_var in existing_var['PYTHONPATH'].values:
                py_var = env.clean_path(py_var)
                if py_var not in sys.path:
                    sys.path.append(py_var)

    def save(self):
        """
        Saves internal package data into disk.

        :return: True if package was saved successfully; False otherwise.
        :rtype: bool
        """

        data = self._cache
        data.update(
            version=str(self._version), name=self._name, displayName=self._display_name, description=self._description,
            requirements=list(map(str, self._requirements)), author=self._author, authorEmail=self._author_email)
        return fileio.save_yaml(data, self._path)

    def delete(self):
        """
        Deletes package from disk.

        :return: True if package was deleted successfully; False otherwise.
        :rtype: bool
        """

        if not os.path.exists(self.root):
            return False
        try:
            shutil.rmtree(self.root)
        except OSError:
            logger.error(f'Failed to remove package: {os.path.dirname(self.name)}', exc_info=True, extra=self._cache)
            return False

        return True

    def create_zip(self, destination_directory=None):
        """
        Creates a ZIP version of this package and stores it into disk.

        :param str or None destination_directory: optional destionation directory.
        :return: tuple with the created Zip file and the destination directory.
        :rtype: tuple[str, str]
        :raises OSError: if it was not possible to create Zip file.
        """


        temp_dir = destination_directory or tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f'{self._name}-{self._version}')
        zipped = fileio.zip_dir(self.dirname(), zip_path, consts.FILE_FILTER_EXCLUDE)
        if not zipped:
            msg = f'Failed to write zip to: {zip_path}'
            logger.error(msg)
            raise OSError(msg)

        return zip_path, temp_dir

    def update_and_write_version(self, new_version):
        """
        Update package file with given new version.

        :param str new_version: new package version.
        :raises IOError: if something happened when writing package file in disk with new version.
        """

        data = self._cache
        self._version = new_version
        data['version'] = str(new_version)
        if not self.save():
            raise IOError(f'Failed to save out package YAML file: {self._path}')

    def run_install(self):
        """
        Install package into current environment.
        """

        self._run_command('install')

    def run_uninstall(self):
        """
        Uninstall package from current environment.
        """

        self._run_command('uninstall')

    def run_startup(self):
        """
        Startup package.
        """

        self._run_command('startup')

    def shutdown(self):
        """
        Shutdown package.
        """

        self._run_command('shutdown')

    def _process_file(self, package_path):
        """
        Internal function that updates the internal package data based on the data contained in the given package file
        path.

        :param str package_path: package file path.
        """

        self.set_path(package_path)
        try:
            data = fileio.load_yaml(self.path)
        except ValueError:
            logger.error(f'Failed to load package due to possible syntax error, {package_path}')
            data = dict()
        self._process_data(data)

    def _process_data(self, data):
        """
        Internal function that updates pacakge internal data based on given data.

        :param dict data: package data.
        """

        self._environ = data.get('environment', dict())
        self._cache = copy.deepcopy(data)
        self._version = LooseVersion(data.get('version', ''))
        self._required = data.get('required', False)
        self._name = data.get('name', 'NO_NAME')
        self._display_name = data.get('displayName', 'NO_NAME')
        self._description = data.get('description', 'No description')
        self._tokens = {
            'self': self._root,
            'self.name': self._name,
            'self.path': self._root,
            'self.version': str(self._version),
            'platform.system': platform.system().lower(),
            'platform.arch': platform.machine(),
            'dcc': env.application().lower()
        }
        self._requirements = requirements.RequirementsList(
            list(map(requirements.Requirement.from_line, data.get('requirements', list()))))
        self._command_paths = Variable('commands', data.get('commands', list())).solve(self._tokens)
        self._tests = Variable('tests', data.get('tests', list())).solve(self._tokens)
        self._author = data.get('author', '')
        self._author_email = data.get('authorEmail', '')
        self._documentation = data.get('documentation', dict())
        self._dccs = data.get('dccs', dict())

    def _run_command(self, command_name):
        """
        Internal function that runs given command name from registered command paths.

        :param str command_name: name of the command to execute.
        :return: return value of the command.
        :rtype: any
        """

        for command_path in self._command_paths:
            if not os.path.exists(command_path):
                continue
            logger.debug(f'Importing package {command_name} file: {command_path}')
            file_path = os.path.realpath(command_path)
            return modules.run_script_function(
                file_path, command_name, f'Running {command_name} function for module: {command_path}', self)


class Variable:
    def __init__(self, key, values):
        super().__init__()

        self._key = key
        self._values = values
        self._original_values = values
        env_var = os.getenv(key)
        if env_var:
            self._values.extend([i for i in env_var.split(os.pathsep)])

    def __str__(self):
        if len(self._values) > 1:
            return os.pathsep.join(self._values)
        return self._values[0]

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self):
        return self._values

    def split(self, sep):
        return str(self).split(sep)

    def dependencies(self):
        results = set()
        for i in self._values:
            results.union(set(re.findall(consts.DEPENDENT_FILTER, i)))

        return results

    def solve(self, tokens):
        self_path = tokens['self']
        app = env.application().lower()
        app_version = str(env.application_version())
        py_version_name = 'py3' if env.is_python3() else 'py2'
        project = os.environ.get('TPDCC_PROJECT', '') or 'undefined'

        result = [i.replace(
            consts.PACKAGE_FOLDER_TOKEN, self_path).replace(
            consts.APP_NAME_TOKEN, app).replace(
            consts.PROJECT_NAME_TOKEN, project).replace(
            consts.APP_VERSION_TOKEN, app_version).replace(
            consts.PY_VERSION_NAME_TOKEN, py_version_name) for i in self._values]
        for index, _ in enumerate(result):
            for key, replace_value in tokens.items():
                result[index] = result[index].replace(''.join(('{', key, '}')), replace_value)

        self._values = result

        return result
