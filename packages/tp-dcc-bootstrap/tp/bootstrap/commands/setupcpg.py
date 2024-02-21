#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc package manager command to setup tpDcc environment
"""

import os
import shutil
from datetime import datetime

from tp.bootstrap import log
from tp.bootstrap.utils import fileio
from tp.bootstrap.core import manager, command

logger = log.bootstrapLogger


class Setup(command.PackageCommand):

    ID = 'setup'

    def arguments(self, sub_parser):
        sub_parser.add_argument(
            '--destination', required=True, type=str, help='The destination for tpDcc tools to be installed')
        sub_parser.add_argument(
            '--force', action='store_true',
            help='If True and destination path exists, it will be automatically deleted')
        sub_parser.add_argument(
            '--include_git', required=False, type=bool,
            help='If True, then git related files and folders will not be deleted')

    def run(self):
        logger.debug(f'Validating root path: {self.options.destination}')
        destination = self.options.destination
        if os.path.exists(destination):
            if not self.options.force:
                raise ValueError(f'tpDcc environment already exists at: {destination}')
            logger.debug('Force option specified, starting back up')
            backup_folder = os.path.join(
                os.path.dirname(destination), 'tpdcc_env_backup')
            target_backup_folder = os.path.join(backup_folder, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
            if os.path.isdir(target_backup_folder):
                shutil.rmtree(target_backup_folder)
            fileio.ensure_folder_exists(backup_folder)
            logger.debug(f'Copying old root folder, {destination} --> {target_backup_folder}')
            shutil.copytree(destination, target_backup_folder)
            logger.debug('Finished backup of old root')
            try:
                shutil.rmtree(destination)
            except OSError:
                logger.error(
                    f'Failed to remove destination path maybe because it is currently opened: {destination}',
                    exc_info=True)
                raise

        manager_instance = None
        try:
            manager_instance = self._build_tpdcc_folder_structure()
        except OSError:
            logger.error('Failed to setup folder structure', exc_info=True)
            self._cleanup()

        return manager_instance

    def _build_tpdcc_folder_structure(self):
        install_folder = os.path.join(self.options.destination, 'install')
        fileio.ensure_folder_exists(self.options.destination)
        fileio.ensure_folder_exists(os.path.join(self.options.destination, 'config'))
        source_folder = os.path.join(self.manager.root_path)
        logger.debug(f'Recursively copying config: {source_folder} --> {install_folder}')
        args = {"src": source_folder, "dst": install_folder}
        if not self.options.include_git:
            args['ignore'] = shutil.ignore_patterns(".gitignore", "*.git", "__pycache__", ".vscode", ".idea")
        shutil.copytree(**args)
        pkg_folder = os.path.join(install_folder, 'packages')
        logger.debug(f'Creating packages folder: {pkg_folder}')
        fileio.ensure_folder_exists(pkg_folder)
        installed_manager = manager.package_manager_from_path(self.options.destination)
        installed_manager.resolver.create_environment_file()
        self._update_preferences(installed_manager)

        return installed_manager

    def _update_preferences(self, package_manager):
        pass

    def _cleanup(self):
        if os.path.exists(self.options.destination):
            shutil.rmtree(self.options.destination)
