#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc tools package resolver environment implementation
"""

from __future__ import annotations

import os
import sys
import glob
import timeit
import typing
import traceback
from importlib import reload
from typing import Set, List, Dict, Callable

from tp.bootstrap import log, consts
from tp.bootstrap.utils import fileio
from tp.bootstrap.core import exceptions, package

if typing.TYPE_CHECKING:
    from tp.bootstrap.core.descriptors import Descriptor
    from tp.bootstrap.core.manager import PackagesManager

logger = log.bootstrapLogger


class Environment:
    """
    Class that represents tp-dcc-tools framework environment.
    """

    def __init__(self, package_manager: PackagesManager):
        super().__init__()

        self._manager = package_manager
        self._cache = {}                            # type: Dict[str, package.Package]
        self._callbacks = {}                        # type: Dict[str, List[Callable]]

    @property
    def cache(self) -> Dict[package.Package]:
        return self._cache

    def resolve_from_path(self, path: str, override: bool = True, apply: bool = True, run_command_scripts: bool = True):
        """
        Resolves environment based on given path.

        :param str path: root path to resolve environment from.
        :param bool override: whether to resolve environment from override file.
        :param bool apply: whether to initialize environment packages.
        :param bool run_command_scripts: whether to run package commmand scripts.
        :return:
        """

        logger.debug(f'Reading environment configuration file: {path}')
        try:
            requests = fileio.load_yaml(path)
        except ValueError:
            logger.error(f'Request YAML path has incorrect syntax: {path}', exc_info=True)
            raise
        if override:
            override_path = self.override_environment_path()
            override_data = dict()
            if override_path and os.path.isfile(override_path):
                logger.debug(f'Reading environment override configuration file: {path}')
                env_override_data = fileio.load_yaml(override_path) or dict()
                requirements = env_override_data.get('requirements', list())
                for requirement_url, requirement_version in requirements.items():
                    requirement_id = os.path.splitext(os.path.basename(requirement_url))[0]
                    override_data[requirement_id] = {'enable': True, 'version': requirement_version}
            if override_data:
                requests.update(override_data)

        return self.resolve(requests, apply=apply, run_command_scripts=run_command_scripts)

    def resolve(self, request_data: Dict, apply: bool = True, run_command_scripts: bool = True) -> Set:
        """
        Resolves environment from given data.

        :param dict request_data: environment package data to resolve.
        :param bool apply: whether to initialize environment packages.
        :param bool run_command_scripts: whether to run package commmand scripts.
        :return: set of resolved packages.
        :rtype: Set
        """

        resolved = set()

        if not request_data:
            logger.warning('No packages to resolve')
            return resolved

        logger.debug('Resolving requested packages:')
        for k, v in request_data.items():
            logger.debug(f'\t{k}: {v}')

        # Retrieve all package instances without applying to current environment
        for package_name, raw_descriptor in request_data.items():
            raw_descriptor['name'] = package_name
            pkg_descriptor = self._manager.descriptor_from_dict(raw_descriptor)
            logger.debug(f'Descriptor for package {package_name} found: {pkg_descriptor}')
            if not pkg_descriptor.enabled:
                logger.info(f'Package {package_name} is not enabled!')
                continue
            if pkg_descriptor.type != pkg_descriptor.LOCAL_PATH:
                existing_pkg = self._cache.get(
                    package.Package.name_from_package_name_and_version(package_name, pkg_descriptor.version))
                if existing_pkg:
                    resolved.add(existing_pkg)
                    continue
                valid = pkg_descriptor.resolve()
                if valid:
                    resolved.add(pkg_descriptor.package)

        # Apply packages to current environment
        for pkg in resolved:
            if str(pkg) in self._cache:
                continue
            pkg.resolve(apply_environment=apply)
            self._cache[str(pkg)] = pkg

        self._reload_tp_namespace_package()

        if not apply:
            return resolved

        site_packages_folder = self._manager.site_packages_path()
        if site_packages_folder and os.path.isdir(site_packages_folder) and site_packages_folder not in sys.path:
            sys.path.append(site_packages_folder)

        self._run_callbacks('preStartupCommands')

        start_time = timeit.default_timer()
        visited = set()
        for pkg_name, pkg in self._cache.items():
            dependencies = pkg.requirements
            for dependency in dependencies:
                dependent_pkg = self.package_by_name(dependency)
                if dependent_pkg and str(dependent_pkg) not in visited:
                    if run_command_scripts:
                        dependent_pkg.run_startup()
                    visited.add(str(dependent_pkg))
            if str(pkg) not in visited:
                if run_command_scripts:
                    try:
                        pkg.run_startup()
                    except exceptions.ProjectNotDefinedError:
                        raise
                    except Exception:
                        if pkg.required:
                            logger.error(f'Was not possible to resolve required package "{pkg_name}"!')
                            raise
                        logger.error(f'Exception while loading package: {str(pkg_name)} | {traceback.format_exc()}')
                    visited.add(str(pkg))
        logger.info('Packages loaded in {0:.2f}s'.format(timeit.default_timer() - start_time))

        return resolved

    def environment_path(self) -> str:
        """
        Returns the environment config path on disk.

        :return: package_version.config file path
        :rtype: str
        :raises exceptions.MissingEnvironmentPathError: if environment config file does not exist at expected location.
        """

        config_path = self._environment_path()
        if os.path.isfile(config_path):
            return config_path
        raise exceptions.MissingEnvironmentPathError(
            f'Environment config file does not exist at location: {config_path}')

    def override_environment_path(self) -> str:
        """
        Returns the environment override config path on disk.

        :return: package_version.override file path.
        :rtype: str
        """

        return self._override_environment_path()

    def load_environment_file(self) -> Dict:
        """
        Loads the environment file.

        :return: dictionary data from the environment file.
        :rtype: Dict
        """

        env_path = self.environment_path()
        logger.debug(f'Loading environment: {env_path}')
        env_data = fileio.load_yaml(env_path)
        for n, info in env_data.items():
            info['name'] = n

        override_data = dict()
        override_env_path = self.override_environment_path()
        if override_env_path:
            logger.debug(f'Loading override environment: {env_path}')
            env_override_data = fileio.load_yaml(override_env_path) or dict()
            requirements = env_override_data.get('requirements', list())
            for requirement in requirements:
                requirement_url, requirement_version = requirement.split(': ')
                requirement_id = os.path.splitext(os.path.basename(requirement_url))[0]
                override_data[requirement_id] = {'enable': True, 'version': requirement_version}
        if override_data:
            env_data.update(override_data)

        return env_data

    def existing_package(self, pkg: package.Package) -> package.Package | None:
        """
        Returns existing package if exists, otherwise a new Package instance will be created.

        :param Package pkg: package instance.
        :return: existing package instance
        :rtype: Package or None
        """

        cached_package = self._cache.get(str(pkg))
        if cached_package is not None:
            return cached_package

        package_locations = self._search_for_package(pkg.name, pkg.version)
        if not package_locations:
            return None

        pkg = package.Package(package_locations[0])
        self._cache[str(pkg)] = pkg

        return pkg

    def package_by_name(self, package_name: str) -> package.Package | None:
        """
        Returns the package with given name from the cache.

        :param str package_name: name of the package to retrieve.
        :return: package found.
        :rtype: Package or None
        """

        found_package = None
        for _, pkg in self._cache.items():
            if pkg.name == package_name:
                found_package = pkg
                break

        return found_package

    def package_from_path(self, path: str) -> package.Package:
        """
        Returns a package instance from the given path.

        :param str path: the director yor the TPDCC_package.yaml absolute path.
        :return: package instance.
        :rtype: package.Package

        ..note:: the path can either be the directory containing the package or the package.yaml file.
        """

        if path.endswith(consts.PACKAGE_NAME):
            return package.Package(path)

        package_yaml = os.path.join(path, consts.PACKAGE_NAME)

        return package.Package(package_yaml)

    def package_for_descriptor(self, descriptor: Descriptor) -> package.Package | None:
        """
        Returns a package manager instance from the given descriptor.

        :param Descriptor descriptor: descriptor to retrieve package manager from.
        :return: tp-dcc-tools package instance for given descriptor.
        :rtype: package.Package or None
        """

        if descriptor.is_descriptor_of_type(descriptor.LOCAL_PATH):
            paths = [os.path.join(descriptor.path, consts.PACKAGE_NAME)]
        else:
            paths = self._search_for_package(descriptor.name, descriptor.version)
        if not paths:
            return None

        pkg = package.Package(paths[0])

        return self._cache.get(str(pkg), pkg)

    def create_environment_file(self, env: Dict | None = None) -> bool:
        """
        Creates an environment file with the given package data if the file does not already exist.

        :param Dict or None env: package data.
        :return: True if the environment was created successfully; False otherwise.
        :rtype: bool

        ..note:: location of the environment file: rootpath/config/env/package_version.config
        """

        env = env or dict()
        config_path = os.path.join(self._manager.config_path, 'env', 'package_version.config')
        if not os.path.exists(config_path):
            logger.debug(f'Creating new environment file: {config_path}')
            fileio.save_yaml(env, config_path)
            return True

        return False

    def update_environment_descriptor_from_dict(self, descriptor: Dict):
        """
        Updates the currently loaded environment with the provided descriptor dictionary.

        :param Dict descriptor: the descriptor dictionary in the same format as the environment data.
        """

        desc = dict(descriptor)
        name = descriptor['name']
        del desc['name']
        desc = {name: desc}
        env_path = self._environment_path()
        try:
            env_data = self.load_environment_file()
            env_data.update(desc)
        except exceptions.MissingEnvironmentPathError:
            self.create_environment_file(desc)
            return

        logger.debug(f'Updating environment: {env_path} with: {descriptor}')
        fileio.save_yaml(env_data, str(env_path), default_flow_style=False, sort_keys=False)

    def remove_descriptor_from_environment(self, descriptor: Descriptor) -> bool:
        """
        Removes the given descriptor instance from the currently loaded environment.

        :param Descriptor descriptor: descriptor instance to delete.
        :return: True if the deletion of the descriptor was successful; False otherwise.
        :rtype: bool
        """

        try:
            env_data = self.load_environment_file()
        except exceptions.MissingEnvironmentPathError:
            raise
        try:
            del env_data[descriptor.name]
        except KeyError:
            logger.error(f'Descriptor: {descriptor.name} does not exist in current environment')
            raise
        fileio.save_yaml(env_data, self._environment_path(), indent=4)

        return True

    def shutdown(self):
        """
        Shutdowns all resolved packages
        """

        visited = set()

        logger.debug(f'Shutting down packages resolver: {self} with the following cached packages')

        for package_name, pkg in self._cache.items():
            if not pkg.resolved:
                continue
            dependencies = pkg.requirements
            for dependency in dependencies:
                dependency_pkg = self.package_by_name(dependency)
                if dependency_pkg and str(dependency_pkg) not in visited:
                    dependency.shutdown()
                    visited.add(str(dependency_pkg))
            if str(pkg) in visited:
                continue

            try:
                pkg.shutdown()
            except Exception:
                logger.error(f'Exception while unloading package: {package_name}', exc_info=True)
            visited.add(str(pkg))

    def _environment_path(self) -> str:
        """
        Internal function that handles the discovery of the environment path for tpDcc configuration.

        :return: path representing absolute path.
        :rtype: str
        """

        defined_path = os.path.expandvars(os.path.expanduser(os.getenv(consts.TPDCC_PACKAGE_VERSION_PATH, '')))
        if os.path.isfile(defined_path):
            logger.debug(f'Loading package environment configuration from "{defined_path}"')
            return defined_path

        config_file = os.getenv(consts.TPDCC_PACKAGE_VERSION_FILE, 'package_version.config')
        defined_path = os.path.join(self._manager.config_path, 'env', config_file)
        if os.path.isfile(defined_path):
            logger.debug(f'Loading pacakge environment configuration from: {defined_path}')
            return defined_path

        logger.debug(f'Loading pacakge environment configuration from: {default_path}')

        return defined_path

    def _override_environment_path(self) -> str | None:
        """
        Internal function that handles the discovery of the override environment path for tpDcc configuration.

        :return: path representing absolute path.
        :rtype: str or None
        """

        defined_path = os.getenv(consts.TPDCC_PACKAGE_OVERRIDE_VERSION_PATH, '')
        config_file = os.getenv(consts.TPDCC_PACKAGE_OVERRIDE_VERSION_FILE, 'package_version.override')
        if not os.path.isfile(defined_path):
            return os.path.join(self._manager.config_path, 'env', config_file)
        env_path = defined_path
        env_path = os.path.expandvars(os.path.expanduser(env_path))
        if os.path.exists(env_path):
            return env_path

        return None

    def _search_for_package(self, package_name: str, package_version: str) -> List[str]:
        """
        Internal function that searches for a specific package with a given name and version.

        :param str package_name: package name.
        :param str package_version: package version.
        :return: list of package paths found.
        :rtype: List[str]
        """

        is_dev = self._manager.is_dev()

        logger.debug(f'Searching package ({package_name} | {package_version}) paths ...')
        logger.debug(f'\tPackages Path: {self._manager.packages_path}')
        logger.debug(f'\tPackage Configuration file name: "{consts.PACKAGE_NAME}"')
        logger.debug(f'\tIs Dev: {is_dev}')

        if is_dev:
            search_path = os.path.join(self._manager.packages_path, package_name, consts.PACKAGE_NAME)
            logger.debug(f'Looking for packages within path: {search_path}')
            package_paths = glob.glob(search_path)
        else:
            search_path = os.path.join(
                self._manager.packages_path, package_name, str(package_version), consts.PACKAGE_NAME)
            logger.debug(f'Looking for packages within path: {search_path}')
            package_paths = glob.glob(search_path)
            if not package_paths:
                logger.debug(f'No package found, trying to find package "{package_name}" in development environment...')
                search_path = os.path.join(self._manager.packages_path, package_name, consts.PACKAGE_NAME)
                logger.debug(f'Looking for packages within path: {search_path}')
                package_paths = glob.glob(search_path)
                if package_paths:
                    logger.debug(f'Package "{package_name}" found within development environment: "{search_path}"')

        logger.debug(f'Found descriptor ({package_name} | {package_version}) paths: {package_paths}')

        return package_paths

    def _reload_tp_namespace_package(self):
        """
        Internal function that forces the reloading of tpDcc namespace after all current package have been loaded.
        """

        import tp
        reload(tp)

    def _run_callbacks(self, name: str):
        """
        Internal function that loads all callbacks of the given name ('preStartupCommands', ...).

        :param str name: callbacks name to execute.
        """

        for callback in self._callbacks.get(name, []):
            callback()