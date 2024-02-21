#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc tools package manager command initialization module
"""

from __future__ import print_function, division, absolute_import

import os
import sys
import glob
import inspect
import logging
import argparse

if sys.version_info[0] == 2:
    import imp
else:
    import importlib

from tp.bootstrap import consts
from tp.bootstrap.core import command

logger = logging.getLogger('tp-dcc-bootstrap')


def import_module(name, path):
    """
    Imports a Python module from its name and path.

    :param str name: Python module name.
    :param str path: Python module path.
    :return: imported module.
    :rtype: object or None
    """

    if sys.version_info[0] < 3:
        if path.endswith('.py'):
            return imp.load_source(name, path)
        elif path.endswith('.pyc'):
            return imp.load_compiled(name, path)
        return __import__(name)
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def find_commands():
    """
    Discovers all tpDcc commands based on TPDCC_COMMAND_LIBRARY_ENV value.

    :return: a mapping of command action ids to the command action class.
    :rtype: dict(str, Action)
    """

    file_filter = ('__int__', '__pycache__')
    commands_path = os.getenv(consts.TPDCC_COMMAND_LIBRARY_ENV, '')
    commands_path = commands_path.split(os.pathsep)
    logger.debug('Finding bootstrap commands within the following paths:')
    for command_path in commands_path:
        logger.debug(f'\t{command_path}')

    visited_short_names = set()
    commands = dict()

    for command_path in commands_path:
        if not os.path.exists(command_path):
            continue
        for path in glob.glob(os.path.join(command_path, '*.py*')):
            basename = os.path.basename(path)
            name, ext = os.path.splitext(basename)
            if name in file_filter or name in visited_short_names:
                continue
            command_name = f'tp.bootstrap.commands.{name}'
            command_module = import_module(command_name, path)
            for mod in inspect.getmembers(command_module, predicate=inspect.isclass):
                if issubclass(mod[1], command.PackageCommand):
                    commands[mod[1].ID] = mod[1]
                    logger.debug(
                        f'Found Bootstrap command: {command_name} - id: {commands[mod[1].ID]}; module: {mod[1]}')
            visited_short_names.add(name)

    return commands


def create_root_parser():
    """
    Creates root argument parser for tp-dcc-tools.

    :return: tuple containing the parser and sub parsers.
    :rtype: tuple[Parser, list[Parser]]
    """

    help_reader = """
Welcome to tp-dcc-tools Framework

This command allows to modify tp-dcc-tools configuration from a shell.
To see the supported arguments for each tp-dcc-tools command run tpdcc_cmd [command] --help
    """
    arg_parser = Parser(
        prog=consts.PACKAGE_MANAGER_ROOT_NAME, description=help_reader,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub_parser = arg_parser.add_subparsers()

    return arg_parser, sub_parser


def run_command(package_manager, arguments):
    """
    Function that runs a tpDcc package manager command based on the given arguments.

    :param tpDccPackagesManager package_manager: tpDcc package manager instance
    :param list(str) arguments: list of command arguments
    :return: True if the command execution was successful; False otherwise.
    :rtype: bool
    """

    arg_parser, sub_parter = create_root_parser()
    for _, class_obj in package_manager.commands.items():
        instance = class_obj(package_manager=package_manager)
        instance.process_arguments(sub_parter)
    if not arguments:
        arg_parser.print_help()
        return False

    grouped_arguments = [[]]
    for arg in arguments:
        if arg == '--':
            grouped_arguments.append([])
            continue
        grouped_arguments[-1].append(arg)
    try:
        args = arg_parser.parse_args(grouped_arguments[0])
    except TypeError:
        arg_parser.error(f'Invalid command name: {grouped_arguments[0][0]}')
        return False

    extra_arguments = list()
    if len(grouped_arguments) > 1:
        extra_arguments = grouped_arguments[-1]

    try:
        func = args.func
    except AttributeError:
        arg_parser.error('Too few arguments')
    else:
        return func(args, extra_arguments=extra_arguments)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        pass
