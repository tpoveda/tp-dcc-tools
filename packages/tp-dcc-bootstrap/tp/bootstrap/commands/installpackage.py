#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains DCC tools package manager command to install packages
"""

from tp.bootstrap import log
from tp.bootstrap.core import exceptions, command

logger = log.bootstrapLogger


class InstallPackage(command.PackageCommand):
    """
    Custom tpDcc package manager command that installs the given package path into the current tpDcc environment.

    A package can be provided either as a physical storage path or a git path and tag.
    """

    ID = 'installPackage'

    def arguments(self, sub_parser):
        sub_parser.add_argument(
            '--path', required=True, type=str,
            help='Path to either a physical disk location or a https://*/*/*.git path. If provide a git path then '
                 'arguments "name" and "tag" should be specified.')
        sub_parser.add_argument(
            '--name', required=False, type=str,
            help='The name of the package, valid only if "path" argument is a git path')
        sub_parser.add_argument('--tag', required=False, type=str, help='The git tag to use')
        sub_parser.add_argument(
            '--in_place', action='store_true',
            help='Valid only if "path" argument is a physical path. If True, then the specified path will be used '
                 'directly else the package will be copied')

    def run(self):
        path = self.options.path
        tag = self.options.tag
        name = self.options.name
        if not path:
            raise exceptions.MissingCommandArgumentError('path')
        if path.endswith('.git'):
            if not tag:
                raise exceptions.MissingCommandArgumentError('tag')
            elif not name:
                raise exceptions.MissingCommandArgumentError('name')
            descriptor_dict = dict(path=path, version=tag, name=name)
        else:
            descriptor_dict = dict(path=path)
        logger.debug(f'Running install command: {path}')
        descriptor_found = self.manager.descriptor_from_path(path, descriptor_dict)
        try:
            descriptor_found.resolve()
        except ValueError:
            logger.error(
                f'Failed to resolve descriptor: {descriptor_dict}', exc_info=True, extra=descriptor_dict)
            return
        descriptor_found.install(in_place=self.options.in_place)
