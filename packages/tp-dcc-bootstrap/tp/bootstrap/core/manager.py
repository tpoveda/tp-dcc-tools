#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc Tools packages manager implementation
"""

import os
import sys
import json
import ctypes
from distutils.util import strtobool
try:
    # only accessible on windows
    from ctypes.wintypes import MAX_PATH
except (ImportError, ValueError):
    MAX_PATH = 260

from tp.bootstrap import log, consts
from tp.bootstrap.utils import fileio, env
from tp.bootstrap.core import resolver, descriptors
from tp.bootstrap import commands

logger = log.bootstrapLogger

# global variable that stores current tpDcc package manager instance
_TPDCC_MANAGER_CACHE = None


def package_manager_from_path(path, dev=False):
    """
    Returns the tpDcc package manager for the given root path.

    :param str path: root path to initialize tpDcc Tools package manager from.
    :param bool dev: whether package manager will run in development mode.
    :return: tpDcc package manager instance.
    :rtype: PackagesManager
    """

    assert os.path.exists(path), f'Path does not exists: {path}'
    tp_dcc_instance = PackagesManager(path, dev=dev)
    set_current_package_manager(tp_dcc_instance)

    return tp_dcc_instance


def current_package_manager():
    """
    Returns current global cached tpDcc Tools package manager instance.

    :return: currently initialized tpDcc Tools pacage manager instance..
    :rtype: PackagesManager or None
    """

    global _TPDCC_MANAGER_CACHE
    return _TPDCC_MANAGER_CACHE


def set_current_package_manager(package_manager):
    """
    Sets the tpDcc tools global package manager instance.

    :param PackagesManager or None package_manager: global tpDcc  tools packages manager instance to set.
    """

    global _TPDCC_MANAGER_CACHE
    _TPDCC_MANAGER_CACHE = package_manager


def resolve_tp_dcc_packages_manager_from_path(path, dev=False):
    """
    Resolves all tpDcc tools packages main paths.

    :param str path: root path to start searching packages from.
    :param bool dev: whether package manager is working in dev mode or not.
    :return: paths where tpDcc tools packages are located.
    :rtype: list(str)
    """

    logger.debug(f'Resolving tp-dcc-tools paths from given path: "{path}", dev: {dev}')

    output_paths = dict()

    install_folder = os.path.join(path, 'install')
    if not os.path.isdir(install_folder) or dev:
        install_folder = path

    config_folder = os.path.join(path, consts.CONFIG_FOLDER_NAME)
    packages_folder = os.path.join(install_folder, consts.PACKAGES_FOLDER_NAME)

    if not os.path.isdir(packages_folder):
        path = os.path.dirname(os.path.dirname(install_folder))
        packages_folder = os.path.join(path, 'packages')
        config_folder = os.path.join(path, consts.CONFIG_FOLDER_NAME)
        if not os.path.isdir(packages_folder):
            logger.warning('Could not find valid tpDcc Tools framework packages folder ...')
            config_folder = ''
            packages_folder = ''

    output_paths.update(dict(
        config=config_folder,
        packages=packages_folder,
        root=path
    ))

    env.add_to_env(consts.TPDCC_COMMAND_LIBRARY_ENV, [
        os.path.join(path, 'tp', 'bootstrap', 'commands')])

    return output_paths


def package_from_path(file_path, max_iterations=20):
    """
    Returns the current package of the given class.

    :param str file_path: file path whose package we want to look.
    :param int max_iterations: maximum number of iterations.
    :return: class package.
    :rtype: str
    """

    search = os.path.dirname(file_path)
    for i in range(max_iterations):
        if not os.path.exists(os.path.join(search, consts.PACKAGE_NAME)):
            search = os.path.dirname(search)
        else:
            pkg = current_package_manager().resolver.package_from_path(
                os.path.join(search, consts.PACKAGE_NAME))
            return pkg

    return None


def package_from_class(class_type, max_iterations=20):
    """
    Returns the current package of the given class.

    :param type class_type: root class whose package we are looking for.
    :param int max_iterations: maximum number of iterations.
    :return: class package.
    :rtype: str
    """

    class_file = sys.modules[class_type.__module__].__file__
    return package_from_path(class_file, max_iterations=max_iterations)


class PackagesManager:
    """
    Class that acts as the main entry points to work with tp-dcc-tools framework packages.
    """

    def __init__(self, root_path, dev=False):
        super().__init__()

        if not os.path.exists(root_path):
            raise FileNotFoundError(root_path)

        self._dev = dev or bool(strtobool(os.getenv('TPDCC_ENV_DEV', 'False')))

        tp_dcc_paths = resolve_tp_dcc_packages_manager_from_path(root_path, dev=self._dev)
        logger.debug(f'Initializing tp-dcc-tools framework from path: {root_path}')
        logger.debug('tp-dcc-tools framework Packages Manager paths:')
        for k, v in tp_dcc_paths.items():
            logger.debug(f'\t{k}: {v}')

        self._root_path = tp_dcc_paths['root']
        self._config_path = tp_dcc_paths['config']
        self._packages_path = os.getenv(consts.PACKAGES_FOLDER_PATH, None) or tp_dcc_paths['packages']
        self._resolver = resolver.Environment(self)
        self._command_lib_cache = commands.find_commands()

    @property
    def root_path(self):
        """
        Returns the root path of tpDcc tools.

        :return: root folder of tpDcc tools.
        :rtype: str

        ..note:: root path directory is the folder above install folder.
        """

        return self._root_path

    @property
    def config_path(self):
        """
        Returns the config folder which sits below the root foolder.

        :return: config folder cog tpDcc tools.
        :rtype: str
        """

        return self._config_path

    @property
    def packages_path(self):
        """
        Returns the package repository path under the install folder.
            Packages:
                - packageNmae
                    - packageVersion (LooseVersion)
                        - code

        :return: packages folder.
        :rtype: str

        ..note:: this folder is the location for all installed packages.
        """

        return self._packages_path

    @property
    def resolver(self):
        """
        Returns the environment resolver instance which contains the package cache.

        :return: environment resolver instance.
        :rtype: resolver.Environment
        """

        return self._resolver

    @property
    def commands(self):
        """
        Returns the executable client command dictionary cache.

        :return: command dictionary cache.
        :rtype: dict
        """

        return self._command_lib_cache

    @property
    def is_admin(self):
        """
        Returns whether the current user is in admin mode.

        :return: True if current user is an administrator; False otherwise.
        :rtype: bool
        """

        try:
            return strtobool(os.getenv(consts.TPDCC_ADMIN_ENV, '0'))
        except TypeError:
            return False

    @is_admin.setter
    def is_admin(self, flag: bool):
        """
        Sets whether current user is in admin mode.

        :param bool flag: True to allow tools to either allow certain behaviours; False otherwise.
        """

        logger.info(f'tp-dcc-tools framework admin mode set to: {flag}')
        os.environ[consts.TPDCC_ADMIN_ENV] = str(int(flag))

    def is_dev(self):
        """
        Returns whether packages manner is running in development mode.
        :return: True if manager is working in development mode; False otherwise.
        :rtype: bool
        """

        return self._dev

    def core_version(self):
        """
        Returns core package version string
        :return: core version
        :rtype: str
        """

        package = os.path.join(self._core_path, consts.PACKAGE_NAME)
        package_info = fileio.load_json(package)

        return package_info['version']

    def build_package_path(self):
        """
        Returns the absolute path to the package.yml which is the build package.

        :return: build package file path.
        :rtype: str
        """

        return os.path.join(self._root_path, consts.PACKAGE_NAME)

    def build_version(self):
        """
        Returns tpDcc Tools build version string.

        :return: tpDcc toosl build version.
        :rtype: str
        """

        package = self.build_package_path()
        if not os.path.exists(package):
            return 'DEV'
        build_package = fileio.load_yaml(package)
        return build_package.get('version', 'DEV')

    def descriptor_from_package_name(self, name):
        """
        Returns the matching descriptor instance for the package name.

        :param str name: name of the tpDcc package to find.
        :return: descriptor found.
        :rtype: Descriptor or None
        """

        return descriptors.descriptor_from_manager(name, package_manager=self)

    def descriptor_from_dict(self, descriptor_dict):
        """
        Returns descriptor from given dictionary.

        :param dict descriptor_dict: descriptor data dictionary
        :return: descriptor instance.
        :rtype: Descriptor
        """

        return descriptors.descriptor_from_dict(self, descriptor_dict)

    def descriptor_from_path(self, path, descriptor_dict):
        """
        Returns descriptor from given path.

        :param str path: path to descriptor.
        :param dict descriptor_dict: descriptor data dictionary.
        :return: descriptor instance.
        :rtype: Descriptor
        """

        return descriptors.descriptor_from_path(self, path, descriptor_dict)

    def preference_roots_path(self):
        """
        Returns the preferences roots config file path in the install root/config/env folder.

        :return: preference roots path.
        :rtype: str
        """

        return os.path.join(self._config_path, 'env', 'preference_roots.config')

    def preference_roots_config(self):
        """
        Loads and returns the preference_roots file contents as a dict.

        :return: preference root configs content.
        :rtype: dict
        """

        with open(self.preference_roots_path(), 'r') as f:
            data = json.load(f)

        return data

    def cache_folder_path(self):
        """
        Retunrs the current tp-dcc-tools framework cache folder.

        :return: absolute path to cache folder.
        :rtype: str
        ..info:: The cache folder is used to store temporary data like pip installed libraries, logs, temp files, etc.
        """

        cache_env = os.getenv(consts.TPDCC_CACHE_FOLDER_PATH_ENV)
        if cache_env is None:
            return self._solve_root_path(os.path.join(self.preference_roots_config()['user_preferences'], 'cache'))
        return os.path.expandvars(os.path.expanduser(cache_env))

    def site_packages_path(self):
        """
        Returns the site packages folder path where tp-dcc-tools framework install pip packages when nedded.

        :return: absolute path to site-packages folder.
        :rtype: str
        """

        cache_folder = self.cache_folder_path()
        python_version = '.'.join(map(str, sys.version_info[:3]))
        return os.path.abspath(os.path.join(cache_folder, 'site-pacakges', python_version))

    def run_command(self, command_name, arguments):
        """
        Runs the given Package Manager command.

        :param str command_name: name of the command to run.
        :param list(str) arguments: list of arguments to pass to the command
        :return: True if the command was run successfully; False otherwise.
        :rtype: bool
        """

        command_class = self._command_lib_cache.get(command_name)
        if not command_class:
            return False

        arguments_copy = list(arguments)
        if command_name not in arguments:
            arguments_copy.insert(0, command_name)
        argument_parser, sub_parser = commands.create_root_parser()
        command_instance = command_class(package_manager=self)
        command_instance.process_arguments(sub_parser)
        args = argument_parser.parse_args(arguments_copy)
        args.func(args)

        return True

    def reload(self):
        """
        Reloads all tp-dcc-tools framework packages, libraries and environment variables.

        :return: new tp-dcc-tools framework package manager instance.
        :rtype: PackagesManager
        """

        root = self._root_path
        self.shutdown()
        package_manager = package_manager_from_path(root)
        package_manager.resolver.resolve_from_path(package_manager.resolver.environment_path())

        return package_manager

    def shutdown(self):
        """
        Shutdown function.

        :param bool reload_modules: whether to reload tp-dcc-tools framework modules.
        """

        self.resolver.shutdown()

        # Clears out sys.modules of all tp modules currently in memory
        from tp.bootstrap.utils import flush
        flush.reload_modules()
        set_current_package_manager(None)

        dev = os.environ.get('TPDCC_ENV_DEV', False)
        if dev:
            logger.debug('Reloading tp namespace...')
            flush.reload_tp_namespace()

    def _solve_root_path(self, root_path):
        """
        Internal function that patches given root path. Python now prioritizes USERPROFILE over HOME, which makes DCC
        that supports Python 2 sets the USERPOFILE to ~/Documents but the ones using Python 3 sets to ~/.

        :param str root_path: absolute path.
        :return: patched path.
        """

        if env.is_windows():
            parts = os.path.normpath(root_path).split(os.path.sep)
            dll = ctypes.windll.shell32
            buf = ctypes.create_unicode_buffer(MAX_PATH)
            if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
                return os.path.join(buf.value, *parts[1:])

        return os.path.expanduser(root_path)