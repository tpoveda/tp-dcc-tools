#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc package command implementation
"""

import os
import subprocess

from tp.bootstrap import log

logger = log.bootstrapLogger


class PackageCommand(object):

    ID = ''         # unique package command ID

    def __init__(self, package_manager):
        self._manager = package_manager
        self._argument_parser = None
        self._options = None

    @property
    def manager(self):
        return self._manager

    @property
    def options(self):
        return self._options

    def process_arguments(self, parent_parser):
        self._argument_parser = parent_parser.add_parser(self.ID, help=self.__doc__)
        self._argument_parser.set_defaults(func=self._execute)
        self.arguments(self._argument_parser)

    def arguments(self, sub_parser):
        pass

    def run(self):
        pass

    def cleanup(self):
        pass

    def _execute(self, args, extra_arguments=None):
        self._options = args
        logger.debug(f'Running command with arguments: \n{args}')
        res = self.run()
        if extra_arguments:
            subprocess.Popen(extra_arguments, universal_newlines=True, env=os.environ, shell=False)

        return res
