#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions to handle Python modules
"""

from __future__ import annotations

import os
import sys
import uuid
import pkgutil
import inspect
import importlib
import traceback
import importlib.util
from types import ModuleType
from typing import Iterator, Any

from tp.core import log
from tp.common.python import helpers, path as path_utils

logger = log.tpLogger


def is_dotted_module_path(module_path):
    """
    Returns whether given module path is a dotted one (tpDcc.libs.python.modules) or not
    :param module_path: str
    :return: bool
    """

    return len(module_path.split('.')) > 2


def convert_to_dotted_path(path):
    """
    Returns a dotted path relative to the given path
    :param path: str, (eg. randomPath/folder/test.py)
    :return: str, dotted path (eg. folder.test)
    """

    directory, file_path = os.path.split(path)
    directory = path_utils.clean_path(directory)
    file_name = os.path.splitext(file_path)[0]
    package_path = [file_name]
    sys_path = list(set([path_utils.clean_path(p) for p in sys.path]))

    # We ignore current working directory. Useful if we want to execute tools directly inside PyCharm
    current_work_dir = path_utils.clean_path(os.getcwd())
    if current_work_dir in sys_path:
        sys_path.remove(current_work_dir)

    drive_letter = os.path.splitdrive(path)[0] + '\\'
    while directory not in sys_path:
        directory, name = os.path.split(directory)
        directory = path_utils.clean_path(directory)
        if directory == drive_letter or name == '':
            return ''
        package_path.append(name)

    return '.'.join(reversed(package_path))


def file_path_to_module_path(file_path: str) -> str:
    """
    Converts a file path into a module path compatible with import statements.

    :param str file_path: file path to convert to module path.
    :return: module path.
    :rtype: str
    """

    python_paths = [os.path.normpath(x) for x in sys.path]
    file_path = os.path.normpath(os.path.expandvars(file_path))
    if file_path.endswith('__init__.py') or file_path.endswith('__init__.pyc'):
        file_path = os.path.dirname(file_path)
    elif os.path.isfile(file_path):
        file_path, extension = os.path.splitext(file_path)

    found = [x for x in python_paths if file_path.startswith(x)]
    num_found = len(found)
    if num_found == 0:
        return ''

    start_path = max(found)
    relative_path = os.path.relpath(file_path, start_path)

    return '.'.join(relative_path.split(os.sep))


def import_module(module_path, name=None, skip_warnings=True, skip_errors=False, force_reload=False):
    """
    Imports the given module path. If the given module path is a dotted one, import lib will be used. Otherwise, it's
    expected that given module path is the absolute path to the source file. If name argument is not given, then the
    basename without the extension will be used
    :param module_path: str, module path. Can be a dotted path (tp.common.python.modules) or an absolute one
    :param name: str, name for the imported module which will be used if the module path is an absolute path
    :param skip_warnings: bool, whether warnings should be skipped
    :param skip_errors: bool, whether errors should be skipped
    :return: ModuleObject, imported module object
    """

    if is_dotted_module_path(module_path) and not path_utils.exists(module_path):
        try:
            return importlib.import_module(module_path)
        except (NameError, KeyError, AttributeError) as exc:
            if '__init__' in str(exc) or '__path__' in str(exc):
                pass
            else:
                msg = 'Failed to load module: "{}"'.format(module_path)
                logger.error(msg, exc_info=True) if not skip_errors else logger.debug(
                    '{} | {}'.format(msg, traceback.format_exc()))
        except (ImportError, ModuleNotFoundError):
            msg = 'Failed to import module: "{}"'.format(module_path)
            logger.error(msg, exc_info=True) if not skip_errors else logger.debug(
                '{} | {}'.format(msg, traceback.format_exc()))
            return None
        except SyntaxError:
            msg = 'Module contains syntax errors: "{}"'.format(module_path)
            logger.error(msg, exc_info=True) if not skip_errors else logger.debug(
                '{} | {}'.format(msg, traceback.format_exc()))
            return None
    try:
        if path_utils.exists(module_path):
            if not name:
                name = path_utils.basename(module_path, with_extension=False)
            if name in sys.modules:
                if force_reload:
                    pass
                    # logger.info('Force module reloading: {}'.format(name))
                    # sys.modules.pop(name)
                return sys.modules[name]
        if not name:
            if not skip_warnings:
                logger.warning(
                    'Impossible to load module because module path: {} was not found!'.format(module_path))
            return None
        if path_utils.is_dir(module_path):
            module_path = path_utils.join_path(module_path, '__init__.py')
            if not path_utils.exists(module_path):
                raise ValueError('Cannot find module path: "{}"'.format(module_path))
        spec = importlib.util.spec_from_file_location(name, os.path.realpath(module_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[name] = mod
        return mod
    except ImportError:
        logger.error('Failed to load module: "{}"'.format(module_path))
        raise


def resolve_module(name, log_error=False):
    """
    Resolves a dotted module name to a global object
    :param name: str
    :return:
    """

    name = name.split('.')
    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used = used + '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            try:
                __import__(used)
            except ImportError:
                if log_error:
                    logger.error(traceback.format_exc())
                return None
            found = getattr(found, n)

    return found


def iterate_module(
        module: ModuleType, include_abstract: bool = False, class_filter: type = object) -> Iterator[tuple[str, type]]:
    """
    Returns a generator that yields all the classes from the given module.

    :param ModuleType module: module to iterate.
    :param bool include_abstract: whether to include abstract classes.
    :param type class_filter: class to filter by.
    :return: iterated classes.
    :rtype: Iterator[tuple[str, type]
    """

    for key, item in module.__dict__.items():
        if not inspect.isclass(item):
            continue
        if inspect.isabstract(item) and not include_abstract:
            continue
        if issubclass(item, class_filter) or item in class_filter:
            yield key, item
        else:
            logger.debug(f'Skipping {key} class')


def iterate_package(package_path: str, force_reload: bool = False) -> Iterator[ModuleType]:
    """
    Returns a generator that yields all the modules from the given package folder.

    :param str package_path: package path to iterate.
    :param bool force_reload: whether to reload module.
    :return: iterated modules.
    :rtype: Iterator[ModuleType]
    :raises TypeError: if the given package path does not exist.
    """

    if not os.path.exists(package_path):
        raise TypeError(f'iterate_package() cannot locate package: {package_path}')

    if os.path.isfile(package_path):
        package_path = os.path.dirname(package_path)

    for file_name in os.listdir(package_path):
        module_name, extension = os.path.splitext(file_name)
        if module_name == '__init__' or extension != '.py':
            continue

        # Try and import module
        file_path = os.path.join(package_path, f'{module_name}.py')
        module_path = file_path_to_module_path(file_path)
        logger.info(f'Attempting to import: "{module_path}" module, from: {file_path}')
        try:
            # Import module and check if it should be reloaded
            module = __import__(module_path, locals=locals(), globals=globals(), fromlist=[file_path], level=0)
            if force_reload:
                logger.info('Reloading module...')
                importlib.reload(module)
            yield module
        except ImportError as exception:
            logger.warning(exception)
            continue


def iterate_modules(path, exclude=None, skip_inits=True, recursive=True, return_pyc=False):
    """
    Iterates all the modules of the given path
    :param path: str, folder path to iterate
    :param exclude: list(str), list of files to exclude
    :return: iterator
    """

    exclude = helpers.force_list(exclude)
    _exclude = ['__init__.py', '__init__.pyc'] if skip_inits else list()

    modules_found = dict()

    extension_to_skip = '.pyc' if not return_pyc else '.py'

    if recursive:
        for root, dirs, files in os.walk(path):
            if '__init__.py' not in files:
                continue
            for f in files:
                base_name = os.path.splitext(f)[0]
                if f not in exclude and base_name not in exclude:
                    module_path = path_utils.clean_path(os.path.join(root, f))
                    if f.endswith('.py') or f.endswith('.pyc') and base_name:
                        if base_name in modules_found:
                            if base_name.endswith(extension_to_skip):
                                continue
                            else:
                                if base_name.endswith(extension_to_skip) and base_name not in modules_found:
                                    modules_found[base_name] = module_path
                        else:
                            modules_found[base_name] = module_path
    else:
        files = os.listdir(path)
        if '__init__.py' not in files:
            return list(modules_found.values())
        for file_name in files:
            base_name = os.path.splitext(file_name)[0]
            if file_name not in exclude and base_name not in exclude:
                module_path = path_utils.clean_path(os.path.join(path, file_name))
                if file_name.endswith('.py') or file_name.endswith('.pyc') and base_name:
                    if base_name in modules_found:
                        if base_name.endswith(extension_to_skip):
                            continue
                        else:
                            if base_name.endswith(extension_to_skip) and base_name not in modules_found:
                                modules_found[base_name] = module_path
                    else:
                        modules_found[base_name] = module_path

    return list(modules_found.values())


def iterate_module_members(module_to_iterate, predicate=None):
    """
    Iterates all the members of the given modules
    :param module_to_iterate: ModuleObject, module object to iterate members of
    :param predicate: inspect.cass, if given members will be restricted to given inspect class
    :return: iterator
    """

    for mod in inspect.getmembers(module_to_iterate, predicate=predicate):
        yield mod


def iterate_module_subclasses(module, class_type):
    """
    Iterates all classes within a module object returning all subclasses of given type
    :param module: ModuleObject, module object to iterate subclasses of
    :param class_type: object, class object to find
    :return: generator(object), generator function returning class objects
    """

    for member in iterate_module_members(module, predicate=inspect.isclass):
        if issubclass(member, class_type):
            yield member


def get_package_children(module_path):
    """
    Returns all package children in given module path
    :param module_path: str
    :return: list(str)
    """

    return [name for _, name, _ in pkgutil.iter_modules([module_path])]


def load_module_from_source(file_path: str, unique_namespace=False) -> ModuleType | None:
    """
    Loads a Python from given source file
    :param str file_path: absolute path pointing to a Python file.
    :param bool unique_namespace: whether to load module within a unique namespace.
    :return: loaded module.
    :rtype: ModuleType or None
    """

    file_name = os.path.splitext(os.path.basename(file_path))[0]

    module_name = '{}{}'.format(file_name, str(uuid.uuid4())) if unique_namespace else file_name

    try:
        spec = importlib.util.spec_from_file_location(module_name, os.path.realpath(file_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[module_name] = mod
        return mod
    except BaseException:
        logger.info('Failed trying to direct load : {} | {}'.format(file_path, traceback.format_exc()))
        return None


def find_class(
        class_name: str, module_path: str, __locals__: dict | None = None,
        __globals__: dict | None = None) -> type | None:
    """
    Returns the class associated with the given string.

    :param str class_name: class name to find.
    :param str module_path: module path.
    :param dict or None __locals__: locals dictionary.
    :param dict or None __globals__: globals dictionary.
    :return: found class.
    :rtype: type or None
    """

    if helpers.is_null_or_empty(class_name):
        return None

    from_list = module_path.split('.', 1)
    module = __import__(module_path, locals=__locals__, globals=__globals__, fromlist=from_list, level=0)

    return getattr(module, class_name)


def try_import(path: str, default: Any = None, __locals__: dict | None = None, __globals__: dict | None = None) -> Any:
    """
    Tries to import the given module path.

    :param str path: moduel path to import.
    :param default: value to return if no module exists.
    :param dict or None __locals__: locals dictionary.
    :param dict or None __globals__: globals dictionary.
    :return: import module.
    :rtype: ModuleType or None
    """

    try:

        from_list = path.split('.', 1)
        return __import__(path, locals=__locals__, globals=__globals__, fromlist=from_list, level=0)
    except ImportError as exception:
        logger.info(exception)
        return default
