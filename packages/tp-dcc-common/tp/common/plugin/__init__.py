#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementations for Plugin Factory mechanism
"""

from __future__ import annotations

import os
import re
import sys
import timeit
import inspect
import operator
from typing import Any
from distutils import version
try:
    from inspect import getfullargspec
except ImportError:
    from inspect import getargspec as getfullargspec

from tp.bootstrap import log
from tp.core import dcc, dccs
from tp.common.python import helpers, modules, osplatform, path as path_utils, folder as folder_utils


class Plugin:
    """
    Base plugin class.
    """

    ID: str = ''
    DCCS: list[str] = []

    def __init__(self, factory=None):
        self._factory = factory
        self._stats = PluginStats(self)

    @property
    def stats(self) -> PluginStats:
        return self._stats


class PluginStats:
    def __init__(self, plugin, id_attr='ID'):
        self._plugin = plugin
        self._id = getattr(self._plugin, id_attr)
        self._start_time = 0.0
        self._end_time = 0.0
        self._execution_time = 0.0

        self._info = {}
        self._init()

    @property
    def info(self):
        return self._info

    def start(self):
        """
        Sets the start time for metrics.
        """

        self._start_time = timeit.default_timer()

    def finish(self, traceback=None):
        """
        Called when the plugin has finish executing.
        """

        self._end_time = timeit.default_timer()
        self._execution_time = self._end_time - self._start_time
        self._info['executionTime'] = self._execution_time
        self._info['lastUsed'] = self._end_time
        if traceback:
            self._info['traceback'] = traceback

    def _init(self):
        """
        Internal function that initializes some basic info about the plugin and the use environment
        """

        try:
            file_path = inspect.getfile(self._plugin.__class__)
        except TypeError:
            file_path = '__main__'
        self._info.update({
            'name': self._plugin.__class__.__name__,
            'module': self._plugin.__class__.__module__,
            'filepath': file_path,
            'id': self._id,
            'application': dcc.name()})
        self._info.update(osplatform.machine_info())


class PluginFactory:

    class PluginLoadingMechanism:
        """
        Class that contains variables used to define how the plugins on a registered path should be loaded.
        """

        # Default mechanism. It will attempt to use the IMPORTABLE method first, and if the module is not
        # accessible from within sys modules it will fall back to LOAD_SOURCE.
        GUESS = 0

        # Mechanism to use when your plugin code is outside of the interpreter sys path. The plugin file
        # be loaded instead of imported. Gives flexibility in terms of structure but you cannot use
        # relative import paths within the plugins loaded with this mechanism. All loaded plugins using
        # this module are imported into a namespace defined through a uuid.
        LOAD_SOURCE = 1

        # Mechanism to use when your plugin code resides within already importable locations. Mandatory
        # to use when your plugin contains relative imports. Because this is importing modules which
        # are available on the sys.path, the class names will resolve nicely too
        IMPORTABLE = 2

    # Regex validator for plugin folder directories
    REGEX_FOLDER_VALIDATOR = re.compile('^((?!__pycache__).)*$')

    # Regex validator for plugin file names
    REGEX_FILE_VALIDATOR = re.compile(r'([a-zA-Z].*)(\.py$|\.pyc$)')

    def __init__(
            self, interface=Plugin, paths=None, package_name=None, plugin_id=None, version_id=None, env_var=None,
            name=None):
        """

        :param interface: Abstract class to use when searching for plugins within the registered paths.
        :param paths: list(str), list of absolute paths to search for plugins.
        :param plugin_id: str, plugin identifier to distinguish between different plugins. If not given, plugin
            class name will be used
        :param version_id: str, plugin version identifier. If given, allows plugins with the same identifier to be
            differentiated.
        :param env_var: str, optional environment variable name containing paths to register separated by OS separator.
        """

        self._interfaces = helpers.force_list(interface)
        self._plugin_identifier = plugin_id or '__name__'
        self._version_identifier = version_id
        module_path = self.__class__.__module__
        if name:
            self._name = '.'.join([module_path, f'{name}PluginFactory'])
        else:
            self._name = '.'.join([module_path, self.__class__.__name__])
        self._logger = log.get_logger(self._name)

        self._plugins = dict()
        self._registered_paths = dict()
        self._loaded_plugins = dict()

        self.register_paths(paths, package_name=package_name)
        if env_var:
            self.register_paths_from_env_var(env_var, package_name=package_name)

    def __repr__(self):
        return '[{} - Identifier: {}, Plugin Count: {}]'.format(
            self.__class__.__name__, self._plugin_identifier, len(self._plugins))

    @classmethod
    def get_regex_folder_validator(cls):
        """
        Returns regex validator for plugin folder directories.
        """

        dcc_name = dcc.name()
        all_dccs = dccs.ALL
        dcc_exclude = ''
        for _dcc in all_dccs:
            if _dcc == dcc_name:
                continue
            dcc_exclude += '(?!{})'.format(_dcc)

        return re.compile('^((?!__pycache__)' + dcc_exclude + '(?!plugins)(?!vendors)(?!art)(?!src).)*$')

    @classmethod
    def get_regex_file_validator(cls):
        """
        Returns regex validator for plugin files
        """

        return re.compile(r'([a-zA-Z_].*)(\.py$)')

    @property
    def loaded_plugins(self):
        return self._loaded_plugins

    def register_path(self, path_to_register, package_name=None, mechanism=PluginLoadingMechanism.GUESS):
        """
        Registers a search path within the factory. The factory will immediately being searching recursively withing
        this location for any plugin.
        :param path: str, absolute path to register into the factory
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :param mechanism: PluginLoadingMechanism, plugin load mechanism to use
        :return: int, total amount of registered plugins
        """

        plugins_found = list()

        if not path_utils.exists(path_to_register):
            return 0, list()

        package_name = package_name or 'tp-dcc'

        # Regardless of what is found in the given path, we store it
        self._registered_paths.setdefault(package_name, dict()).setdefault(path_to_register, dict())
        self._registered_paths[package_name][path_to_register] = mechanism

        current_plugins_count = len(self._plugins)

        file_paths = list()
        if path_utils.is_dir(path_to_register):
            for root, _, files in folder_utils.walk_level(path_to_register):
                if not self.get_regex_folder_validator().match(root):
                    continue

                for file_name in files:

                    # Skip files that do not match PluginFactory regex validator.
                    if not self.get_regex_file_validator().match(file_name):
                        continue
                    if file_name.startswith('test') or file_name in ['setup.py']:
                        continue

                    file_paths.append(path_utils.join_path(root, file_name))
        elif path_utils.is_file(path_to_register):
            file_paths.append(path_to_register)

        # Loop through all the found files searching for plugins definitions
        for file_path in file_paths:

            module_to_inspect = None

            if mechanism in (self.PluginLoadingMechanism.IMPORTABLE, self.PluginLoadingMechanism.GUESS):
                module_to_inspect = self._mechanism_import(file_path)
                # if module_to_inspect:
                #     logger.debug('Module Import : {}'.format(file_path))

            if not module_to_inspect:
                if mechanism in (self.PluginLoadingMechanism.LOAD_SOURCE, self.PluginLoadingMechanism.GUESS):
                    module_to_inspect = self._mechanism_load(file_path)
                    # if module_to_inspect:
                    #     logger.debug('Direct Load : {}'.format(file_path))

            if not module_to_inspect:
                continue

            try:
                for interface in self._interfaces:
                    for item_name in dir(module_to_inspect):
                        item = getattr(module_to_inspect, item_name)
                        if inspect.isclass(item):
                            if item == interface:
                                continue
                            if issubclass(item, interface):
                                item.ROOT = path_to_register
                                item.PATH = file_path
                                item.MODULE = module_to_inspect
                                self._plugins.setdefault(package_name, list())
                                self._plugins[package_name].append(item)
                                plugins_found.append(item)
            except Exception:
                self._logger.debug('', exc_info=True)

        return len(self._plugins) - current_plugins_count, plugins_found

    def register_paths(self, paths_to_register, package_name=None, mechanism=PluginLoadingMechanism.GUESS):
        """
        Registers given paths within the factory. The factory will immediately being searching recursively withing
        this location for any plugin.
        :param paths_to_register: list(str), absolute paths to register into the factory
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :param mechanism: PluginLoadingMechanism, plugin load mechanism to use
        :return: int, total amount of registered plugins
        """

        paths_to_register = helpers.force_list(paths_to_register)

        total_plugins = 0
        visited = set()
        plugins_found = list()
        for path_to_register in paths_to_register:
            if not path_to_register:
                continue
            base_name = path_utils.clean_path(
                os.path.splitext(path_to_register)[0] if os.path.isfile(path_to_register) else path_to_register)
            if base_name in visited:
                continue
            visited.add(base_name)
            plugins_count, found = self.register_path(path_to_register, mechanism=mechanism, package_name=package_name)
            total_plugins += plugins_count
            plugins_found.extend(found)

        plugins_found = helpers.remove_dupes(plugins_found)

        return plugins_found

    def register_paths_from_env_var(self, env_var, package_name=None, mechanism=PluginLoadingMechanism.GUESS):
        """
        Registers paths contained in given environment variables. Paths must be separated with OS separator
        :param env_var: str, environment variable we are going to retrieve paths from
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :param mechanism: PluginLoadingMechanism, plugin load mechanism to use
        :return: int, total amount of registered plugins
        """

        paths = os.environ.get(env_var, '').split(os.pathsep)
        if not paths:
            return

        return self.register_paths(paths, package_name=package_name, mechanism=mechanism)

    def register_plugin_from_class(self, plugin_class, package_name=None):
        """
        Registers the given class type as a plugin for this factory. Note that the given type class must be inherited
        from the factory interface. Useful when you have direct access to the plugin classes without the need of
        searching disk locations (which is slow)
        :param plugin_class: type, class type to add to the factory
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :return: True if the registration is successful; False otherwise.
        """

        for interface in self._interfaces:
            if not inspect.isclass(plugin_class) or not issubclass(plugin_class, interface):
                return False

        if not package_name:
            class_id = self._get_identifier(plugin_class)
            split_id = class_id.replace('.', '-').split('-')[0]
            package_name = split_id if split_id != class_id else 'tp-dcc'

        self._plugins.setdefault(package_name, list()).append(plugin_class)

        return True

    def register_by_package(self, package_path):
        """
        Registers all plugins located in the given package.

        :param str package_path: package path.

        ..note:: this is a costly operation because it requires a recursive search by importing all submodules and
            searching them.
        """

        for sub_module in modules.iterate_modules(package_path):
            file_name = os.path.splitext(path_utils.basename(sub_module))[0]
            if file_name.startswith('__') or sub_module.endswith('.pyc'):
                continue
            module_path = os.path.normpath(sub_module)
            module_dotted_path = modules.convert_to_dotted_path(module_path)
            if not module_dotted_path:
                self._logger.warning(
                    'Skipping module due to invalid path: {} -> {}'.format(sub_module, module_dotted_path))
                continue
            sub_module_obj = None
            try:
                sub_module_obj = modules.import_module(module_dotted_path, skip_errors=True)
            except ValueError:
                self._logger.error('Failed to load plugin module: {}'.format(sub_module))
            except ImportError:
                self._logger.error('Failed to import plugin module: {}'.format(sub_module), exc_info=True)
                continue
            if not sub_module_obj:
                self._logger.debug('Failed to load/import plugin module: {}'.format(sub_module))
                continue
            for member in modules.iterate_module_members(sub_module_obj, predicate=inspect.isclass):
                self.register_plugin_from_class(member[1])

    def paths(self, package_name=None):
        """
        Returns all registered paths in the factory
        :return: list(str)
        """

        package_name = package_name or 'tp-dcc'
        return list(self._registered_paths.get(package_name, dict()).keys())

    def identifiers(self, package_name=None):
        """
        Returns a list of plugin class names within the factory. The list of class names is unique, so classes which
        share the same name will not appear twice.
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :return: list(str)
        """

        package_name = package_name or 'tp-dcc'
        return {self._get_identifier(plugin) for plugin in self._plugins.get(package_name, list())}

    def versions(self, identifier, package_name=None):
        """
        Returns a list of all the versions available for the plugins with the given identifier
        :param identifier: str, Plugin identifier to check
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        :return: list(str)
        """

        package_name = package_name or 'tp-dcc'

        if not self._version_identifier:
            return list()

        return sorted(
            self._get_version(plugin) for plugin in self._plugins.get(
                package_name, list()) if self._get_identifier(plugin) == identifier
        )

    def plugins(self, package_name=None):
        """
        Returns a unique list of plugins. Where multiple versions are available the highest version will be given
        :param package_name: str, package name current registered plugins will belong to.
        :return: list(class)
        """

        package_name = package_name or 'tp-dcc'

        ordered_plugins = list()
        plugins = [self.get_plugin_from_id(
            identifier, package_name=package_name) for identifier in self.identifiers(package_name=package_name)]
        plugins_to_order = [plugin for plugin in plugins if hasattr(plugin, 'ORDER')]
        plugins_ordered = sorted(plugins_to_order, key=operator.attrgetter("ORDER"))
        ordered_plugins.extend(plugins_ordered)
        for plugin in plugins:
            if plugin in ordered_plugins:
                continue
            ordered_plugins.append(plugin)

        return ordered_plugins

    def get_plugin_from_id(self, plugin_id, package_name=None, plugin_version=None) -> type[Any] | None:
        """
        Retrieves the plugin with given plugin identifier. If you require a specific version of a plugin (in a
        scenario where there are multiple plugins with the same identifier) this can also be specified
        :param plugin_id: str, identifying value of the plugin you want to retrieve
        :param package_name: str, package name current registered plugins will belong to.
        :param plugin_version: int or float, version of the plugin you want. If factory has no versioning identifier
            specified this argument has no effect.
        :return: Plugin
        :rtype: type[Any] or None
        """

        package_name = package_name or 'tp-dcc'

        if package_name and package_name not in self._plugins:
            self._logger.error('Impossible to retrieve plugin from id: {} package: "{}" not registered!'.format(
                plugin_id, package_name))
            return None

        if package_name:
            matching_plugins = [plugin for plugin in self._plugins.get(
                package_name, list()) if self._get_identifier(plugin) == plugin_id]
        else:
            matching_plugins = list()
            for plugins in list(self._plugins.values()):
                for plugin in plugins:
                    if self._get_identifier(plugin) == plugin_id:
                        matching_plugins.append(plugin)

        if not matching_plugins:
            # self._logger.warning('No plugin with id "{}" found in package "{}"'.format(plugin_id, package_name))
            return None

        if not self._version_identifier:
            return matching_plugins[0]

        if dcc:
            _matching_plugins = []
            for plugin_cls in matching_plugins:
                if hasattr(plugin_cls, 'DCCS') and dcc not in plugin_cls.DCCS:
                    continue
                _matching_plugins.append(plugin_cls)
            matching_plugins = _matching_plugins
        if not matching_plugins:
            self._logger.warning(
                'No plugin with id "{}" found in package "{}" for DCC: {}'.format(plugin_id, package_name, dcc))
            return None

        versions = {
            self._get_version(plugin): plugin for plugin in matching_plugins
        }
        ordered_versions = [version.LooseVersion(str(v)) for v in list(versions.keys())]

        # If not version given, we return the plugin with the highest value
        if not plugin_version:
            return versions[str(ordered_versions[0])]

        plugin_version = version.LooseVersion(str(plugin_version))
        if plugin_version not in ordered_versions:
            self._logger.warning('No Plugin with id "{}" and version "{}" found in package "{}"'.format(
                plugin_id, plugin_version, package_name))
            return None

        return versions[str(plugin_version)]

    def get_loaded_plugin_from_id(self, plugin_id, package_name=None, plugin_version=None, dcc=None) -> Plugin | None:
        """
        Retrieves the plugin with given plugin identifier. If you require a specific version of a plugin (in a
        scenario where there are multiple plugins with the same identifier) this can also be specified.

        :param plugin_id: str, identifying value of the plugin you want to retrieve
        :param package_name: str, package name current registered plugins will belong to.
        :param plugin_version: int or float, version of the plugin you want. If factory has no versioning identifier
            specified this argument has no effect.
        :param dcc: str, optional DCC to retrieve plugin of.
        :return: plugin instance.
        :rtype: Plugin
        """

        package_name = package_name or 'tp-dcc'

        if package_name and package_name not in self._loaded_plugins:
            self._logger.debug('Impossible to retrieve loaded plugin from id: {} package: "{}" not registered!'.format(
                plugin_id, package_name))
            return None

        if package_name:
            matching_plugins = [plugin for plugin in self._loaded_plugins.get(
                package_name, []) if self._get_identifier(plugin) == plugin_id]
        else:
            matching_plugins = []
            for plugins in list(self._loaded_plugins.values()):
                for plugin in plugins:
                    if self._get_identifier(plugin) == plugin_id:
                        matching_plugins.append(plugin)

        if not matching_plugins:
            self._logger.warning('No loaded plugin with id "{}" found in package "{}"'.format(plugin_id, package_name))
            return None

        if dcc:
            matching_plugins = [plugin_cls for plugin_cls in matching_plugins if dcc in plugin_cls.DCCS]
        if not matching_plugins:
            self._logger.warning(
                'No loaded plugin with id "{}" found in package "{}" for DCC: {}'.format(plugin_id, package_name, dcc))
            return None

        if not self._version_identifier:
            return matching_plugins[0]

        versions = {
            self._get_version(plugin): plugin for plugin in matching_plugins
        }
        ordered_versions = [version.LooseVersion(str(v)) for v in list(versions.keys())]

        # If not version given, we return the plugin with the highest value
        if not plugin_version:
            return versions[str(ordered_versions[0])]

        plugin_version = version.LooseVersion(plugin_version)
        if plugin_version not in ordered_versions:
            self._logger.warning('No Plugin with id "{}" and version "{}" found in package "{}"'.format(
                plugin_id, plugin_version, package_name))
            return None

        return versions[str(plugin_version)]

    def load_plugin(self, plugin_id, package_name=None, **kwargs):
        """
        Loads a given plugin by the given name.

        :param str plugin_id: id of the plugin to load.
        :param str package_name: optional package name plugin we want to load belongs to.
        :param dict kwargs: extra keyword arguments.
        :return: instance of the loaded plugin.
        :rtype: object or None
        """

        package_name = package_name or 'tp-dcc'

        plugin_class = self.get_plugin_from_id(plugin_id, package_name=package_name)
        if not plugin_class:
            return None

        self._logger.debug('Loading plugin: {}'.format(plugin_id))
        spec = getfullargspec(plugin_class.__init__)
        try:
            keywords = spec.kwonlyargs
        except AttributeError:
            keywords = spec.keywords
        args = spec.args
        if (args and 'factory' in args) or (keywords and 'factory' in keywords):
            kwargs['factory'] = self
        try:
            plugin_instance = plugin_class(**kwargs)
        except Exception:
            self._logger.error("Failed to load plugin: {}".format(plugin_id), exc_info=True)
            return None

        self._loaded_plugins.setdefault(package_name, list())
        plugin_instance.is_loaded = True
        self._loaded_plugins[package_name].append(plugin_instance)

        return plugin_instance

    def load_all_plugins(self, package_name=None, **kwargs):
        """
        Loops over all registered plugin and loads them.

        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        """

        package_name = package_name or 'tp-dcc'

        for pkg_name, plugin_classes in self._plugins.items():
            if package_name and pkg_name != package_name:
                continue
            for plugin_class in plugin_classes:
                plugin_id = self._get_identifier(plugin_class)
                self.load_plugin(plugin_id, package_name=package_name, **kwargs)

    def unload_all_plugins(self, package_name=None):
        """
        Loops over all loaded plugins and unloads them.

        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        """

        package_name = package_name or 'tp-dcc'
        if package_name not in self._loaded_plugins:
            return
        self._loaded_plugins[package_name].clear()

    def unregister_path(self, path, package_name=None):
        """
        Unregister given path from the list of registered paths
        :param path: Absolute path we want to unregister from registered factory paths
        :param package_name: str, package name current registered plugins will belong to. Default to tDcc.
        """

        registered_paths = self._registered_paths.copy()

        self._plugins = list()
        self._registered_paths = dict()

        for pkg_name, registered_paths_dict in registered_paths.items():
            for original_path, mechanism in registered_paths_dict.items():
                if package_name == pkg_name and path_utils.clean_path(original_path) == path_utils.clean_path(path):
                    continue
                self.register_path(original_path, package_name=pkg_name, mechanism=mechanism)

    def reload(self):
        """
        Clears all registered plugins and performs a search over all registered paths
        """

        registered_paths = self._registered_paths.copy()

        self.clear()

        for package_name, registered_paths_dict in registered_paths.items():
            for original_path, mechanism in registered_paths_dict.items():
                self.register_path(original_path, package_name=package_name, mechanism=mechanism)

    def clear(self):
        """
        Clears all the plugins and registered paths
        """

        self._plugins.clear()
        self._registered_paths.clear()
        self._loaded_plugins.clear()

    def _mechanism_import(self, file_path):
        """
        Internal function that will try to retrieve a module from a given path by looking current sys.path
        :param file_path: str, absolute file path of a Python file
        :return: module or None
        """

        # In Python 2 we check the existence of an __init__ file
        has_init = True
        if helpers.is_python2():
            has_init = False
            file_dir = os.path.dirname(file_path)
            for extension in ('.py', '.pyc'):
                if os.path.isfile(os.path.join(file_dir, '__init__{}'.format(extension))):
                    has_init = True
                    break
        if not has_init:
            return None

        module_name = modules.convert_to_dotted_path(file_path)
        if module_name:
            try:
                return sys.modules[module_name]
            except KeyError:
                return modules.import_module(module_name, skip_errors=True)

        return None

    def _mechanism_load(self, file_path):
        """
        Internal function that will try to retrieve a module by directly loading its source code
        :param file_path: str, absolute file path of a Python file
        :return: module or None
        """

        return modules.load_module_from_source(file_path)

    def _get_identifier(self, plugin):
        """
        Internal function that uses plugin identifier to request the identifying name of the plugin
        :param plugin: str, plugin to take name from
        :return: str
        """

        identifier = getattr(plugin, self._plugin_identifier)

        predicate = inspect.ismethod if helpers.is_python2() else inspect.isfunction
        if predicate(identifier):
            return identifier()

        return identifier

    def _get_version(self, plugin):
        """
        Internal function that uses plugin version identifier to request the version number of the plugin
        :param plugin: str, plugin to take version from
        :return: int or float
        """

        identifier = getattr(plugin, self._version_identifier)

        predicate = inspect.ismethod if helpers.is_python2() else inspect.isfunction
        if predicate(identifier):
            return str(identifier())

        return str(identifier)
