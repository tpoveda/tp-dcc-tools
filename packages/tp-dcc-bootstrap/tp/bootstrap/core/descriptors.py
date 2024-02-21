#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains DCC tools package manager descriptor implementations
"""

import os
import stat
import shutil
import tempfile

from tp.bootstrap import log, consts
from tp.bootstrap.core import exceptions

try:
    from tp.bootstrap.utils import git
except ImportError:
    git = None

logger = log.bootstrapLogger


def descriptor_from_manager(name, package_manager=None):
    """
    Returns the descriptor from the existing cached package manager environment instance.

    :param str name: name of the descriptor to find.
    :param tpDccPackagesManager or None package_manager: package manager instance.
    :return: descriptor found.
    :rtype: Descriptor or None
    """

    # import here to avoid cyclic imports
    from tp.bootstrap.core import manager

    package_manager = package_manager or manager.current_package_manager()
    for descriptor_name, descriptor_dict in package_manager.resolver.load_environment_file().items():
        if descriptor_name == name:
            return descriptor_from_dict(package_manager, descriptor_dict)


def descriptor_from_path(package_manager, location, descriptor_info):
    """
    Returns the matching descriptor object fro the given path.

    :param tpDccPackagesManager package_manager: current tpDcc tools package manager instance.
    :param str location: location of the package, can be any of the pats supported by our
        descriptors (git, physical path, etc).
    :param dict descriptor_info: descriptor dictionary.
    :return: Descriptor
    :rtype: Descriptor
    :raise: NotImplementedError
    """

    if location.endswith('.git') and not os.path.exists(location):
        descriptor_info.update({'type': 'git'})
        return GitDescriptor(package_manager, descriptor_info)
    elif os.path.exists(location):
        package_found = package_manager.resolver.package_from_path(location)
        if not package_found:
            raise exceptions.InvalidPackagePathError(location)
        descriptor_info.update(
            {'name': package_found.name, 'version': str(package_found.version), 'path': location, 'type': 'path'})
        return PathDescriptor(package_manager, descriptor_info)
    raise NotImplementedError(f'Descriptor not supported: {location}')


def descriptor_from_dict(package_manager, descriptor_info):
    """
    Returns the descriptor object from the given dictionary.

    :param tpDccPackagesManager package_manager: current tpDcc tools package manager instance.
    :param dict descriptor_info: descriptor dictionary.
    :return: Descriptor
    :rtype: Descriptor
    :raise: NotImplementedError
    """

    requested_type = descriptor_info.get('type', '') or Descriptor.TPDCCTOOLS
    logger.debug(f'Resolve descriptor for requested info: {descriptor_info} ({requested_type})')
    if requested_type == Descriptor.TPDCCTOOLS:
        return tpDccDescriptor(package_manager, descriptor_dict=descriptor_info)
    elif requested_type == Descriptor.LOCAL_PATH:
        return PathDescriptor(package_manager, descriptor_dict=descriptor_info)
    elif requested_type == Descriptor.GIT:
        return GitDescriptor(package_manager, descriptor_dict=descriptor_info)
    raise NotImplementedError(f'Descriptor not supported: {descriptor_info}')


class Descriptor:

    GIT = 'git'
    LOCAL_PATH = 'path'
    TPDCCTOOLS = 'tpdcctools'

    REQUIRED_KEYS = set()

    def __init__(self, package_manager, descriptor_dict):
        super().__init__()

        self._manager = package_manager
        self._descriptor_dict = descriptor_dict
        self._type = descriptor_dict.get('type', None)
        # by default, if not type is defined we use tpdcctools
        if not self._type:
            descriptor_dict['type'] = self.TPDCCTOOLS
            self._type = descriptor_dict['type']
        self._name = descriptor_dict.get('name')
        self._enabled = descriptor_dict.get('enable', True)
        self._version = ''
        self._package = None
        self._validate(descriptor_dict)

    def __eq__(self, other):
        other_dict = other.serialzie()
        return all(v == other_dict.get(k) for k, v in self.serialize().items())

    def __ne__(self, other):
        other_dict = other.serialzie()
        return not any(v != other_dict.get(k) for k, v in self.serialize().items())

    def __repr__(self):
        return f'<{self.__class__.__name__}> name: {self.name}, type: {str(self.type)}'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, flag):
        self._enabled = flag

    @property
    def type(self):
        return self._type

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value

    @property
    def package(self):
        return self._package

    @package.setter
    def package(self, pkg):
        self._package = pkg

    @property
    def manager(self):
        return self._manager

    def is_descriptor_of_type(self, descriptor_type):
        return self._type == descriptor_type

    def serialize(self):
        return self._descriptor_dict

    def resolve(self, *args, **kwargs):
        raise NotImplementedError()

    def install(self, *args, **kwargs):
        raise NotImplementedError()

    def uninstall(self, remove=False):
        logger.debug(f'Uninstalling descriptor: {self}')
        if self._package is None:
            logger.debug(f'Descriptor: {self.name} has no resolved package')
            return False
        package_root = self._package.root
        self._manager.resolver.remove_descriptor_from_environment(self)
        if remove:
            self._package.delete()
            versioned_pacakge_dir = os.path.dirname(package_root)
            if len(os.listdir(versioned_pacakge_dir)) == 0:
                os.rmdir(versioned_pacakge_dir)

        return True

    def _validate(self, descriptor_dict):
        keys = set(list(descriptor_dict.keys()))
        required_set = set(self.REQUIRED_KEYS)
        if not required_set.issubset(keys):
            missing_keys = required_set.difference(keys)
            raise exceptions.DescriptorMissingKeysError(
                f'<{self.__class__.__name__}>: {self.name} missing required keys: {missing_keys}')

        return True


class tpDccDescriptor(Descriptor):

    REQUIRED_KEYS = ('version', 'name', 'type')

    def __init__(self, package_manager, descriptor_dict):
        super(tpDccDescriptor, self).__init__(package_manager=package_manager, descriptor_dict=descriptor_dict)

        self._version = descriptor_dict['version']

    def resolve(self, *args, **kwargs):
        logger.debug(f'Resolving tpdcctools descriptor: {self.name} - {self.version}')
        existing_package = self._manager.resolver.package_for_descriptor(self)
        if not existing_package:
            raise exceptions.MissingPackageVersionError(f'Missing package: {self.name}')
        self.package = existing_package

        return True

    def install(self, *args, **kwargs):
        if self._package:
            logger.debug(f'Package: {self.name} already exists, skipping install')
            return True
        raise NotImplementedError('internal packages downloading is not currently supported')


class PathDescriptor(Descriptor):

    REQUIRED_KEYS = ('name', 'path', 'type')

    def __init__(self, package_manager, descriptor_dict):
        super(PathDescriptor, self).__init__(package_manager=package_manager, descriptor_dict=descriptor_dict)

        self._path = descriptor_dict['path']

    @property
    def path(self):
        return os.path.normpath(
            os.path.expandvars(self._path.replace(consts.INSTALL_FOLDER_TOKEN, self.manager.root_path)))

    @path.setter
    def path(self, value):
        self._path = value

    def resolve(self):
        package = self.manager.resolver.package_from_path(self.path)
        if not package:
            logger.warning(f'The specified package does not exist, please check your configuration: {self.path}')
            return False
        self.package = package
        self.version = package.version

        return True

    def install(self, **arguments):
        if self.package is None:
            raise exceptions.InvalidPackagePathError(self.path)
        if self.installed():
            raise exceptions.PackageAlreadyExistsError(self.package)
        inplace_install = arguments.get('in_place')
        logger.debug(f'Running path descriptor: {self.name}.install with arguments: {arguments}')
        package_directory = os.path.join(self.manager.packages_path, self.name, str(self.package.version))
        if not inplace_install:
            try:
                installed_pkg = self.package.copy_to(package_directory)
                logger.debug(f'Finished copying {self.package} --> {package_directory}')
            except OSError:
                logger.error(
                    f'Failed to copy package: {self.package.name} to destination: {package_directory}', exc_info=True)
                return False
            del self._descriptor_dict['path']
            self._descriptor_dict.update({'type': 'tpdcctools', 'version': str(self.package.version)})
        else:
            installed_pkg = self.manager.resolver.package_from_path(package_directory)
        self.manager.resolver.cache[str(installed_pkg)] = installed_pkg
        self.manager.resolver.update_environment_descriptor_from_dict(self._descriptor_dict)

        return True

    def installed(self):
        if not self.package:
            raise exceptions.InvalidPackagePathError(self.path)
        existing = self.manager.resolver.existing_package(self.package)

        return existing is not None


class GitDescriptor(Descriptor):

    REQUIRED_KEYS = ('version', 'path', 'type')

    def __init__(self, package_manager, descriptor_dict):
        super(GitDescriptor, self).__init__(package_manager=package_manager, descriptor_dict=descriptor_dict)

        self._path = descriptor_dict['path']
        self._version = descriptor_dict['version']

    @property
    def path(self):
        return self._path

    @staticmethod
    def _handle_delete_error(action, name, exc):
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    def resolve(self, *args, **kwargs):
        if not self.path.endswith('.git'):
            raise SyntaxError('Supplied git path does not ends with ".git"')
        if all(i is not None for i in (self.version, self.name)):
            package_found = self._manager.resolver.package_for_descriptor(self)
            if package_found is not None:
                self.package = package_found
                logger.warning(f'Package already exists: {self.name} - {self.version}')
                raise exceptions.PackageAlreadyExistsError(package_found)

        return True

    def install(self, **arguments):
        if self.package is not None or self.version is None:
            return

        local_folder = tempfile.mkdtemp('tpdcc_git')
        git_folder = os.path.join(local_folder, os.path.splitext(os.path.basename(self.path))[0])
        if git is None:
            logger.error('Currently environment does not have gitpython installed')
            raise exceptions.MissingGitPythonError()
        try:
            git.has_git()
        except Exception:
            raise
        try:
            logger.debug(f'Cloning path: {self.path} to {git_folder}')
            repo = git.RepoChecker.clone(self.path, local_folder)
            if self.version != 'DEV':
                repo.checkout(self.version)
        except Exception:
            shutil.rmtree(local_folder, onerror=self._handle_delete_error)
            raise
        package_found = self._manager.resolver.package_from_path(repo.repo_path)
        if package_found is None:
            shutil.rmtree(local_folder, onerror=self._handle_delete_error)
            raise
        exists = self._manager.resolver.existing_package(package_found)
        if exists is not None:
            shutil.rmtree(local_folder, onerror=self._handle_delete_error)
            self.package = exists
            raise ValueError(f'Package already exists: {str(exists)}')

        self.name = package_found.name
        self.package = package_found
        descriptor_version = self.version or self.package.version
        destination = os.path.join(self._manager.packages_path, self.name, str(descriptor_version))
        installed_package = package_found.copy_to(destination)
        shutil.rmtree(local_folder, onerror=self._handle_delete_error)
        self._manager.resolver.cache[str(installed_package)] = installed_package
        self._descriptor_dict['type'] = 'tpdcctools'
        del self._descriptor_dict['path']
        self._manager.resolver.update_environment_descriptor_from_dict(self._descriptor_dict)

        return True
