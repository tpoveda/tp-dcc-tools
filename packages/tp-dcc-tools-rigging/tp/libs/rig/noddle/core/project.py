from __future__ import annotations

import os

from typing import Dict

from tp.core import log
from tp.common.python import path, folder, fileio, yamlio, timedate
from tp.preferences import manager as preferences

from tp.libs.rig.noddle.core import asset
from tp.libs.rig.noddle.interface import hud

logger = log.rigLogger


class Project:
    """
    Base class that represents a Noddle rigging project
    """

    TAG_FILE = 'noddle.proj'
    _INSTANCE = None						# type: Project

    def __init__(self, directory: str):
        super().__init__()

        self._path = directory
        self._interface = preferences.preference().interface('noddle')

    def __repr__(self):
        return f'{self.name}({self.path}): {self.meta_data}'

    @property
    def path(self) -> str:
        return self._path

    @property
    def name(self) -> str:
        return path.basename(self.path)

    @property
    def tag_path(self) -> str:
        return path.join_path(self.path, self.TAG_FILE)

    @property
    def meta_path(self) -> str:
        return path.join_path(self.path, f'{self.name}.meta')

    @property
    def meta_data(self) -> Dict:
        meta_dict = {}
        if path.is_file(self.meta_path):
            meta_dict = yamlio.read_file(self.meta_path)
        for category in os.listdir(self.path):
            category_path = path.join_path(self.path, category)
            if path.is_dir(category_path):
                asset_dirs = filter(path.is_dir, [path.join_path(category_path, item) for item in os.listdir(category_path)])
                meta_dict[category] = [path.basename(asset) for asset in asset_dirs]

        return meta_dict

    @classmethod
    def is_project(cls, directory: str) -> bool:
        """
        Returns whether given path contains a valid Noddle project.

        :param str directory: absolute path pointing to a directory within disk.
        :return: True if the given path contains a Noddle project; False otherwise.
        :rtype: bool
        """

        return path.is_file(path.join_path(directory, cls.TAG_FILE))

    @classmethod
    def create(cls, directory: str, silent: bool = False) -> Project | None:
        """
        Creates a new Noddle project instance and all necessary files within given directory.

        :param str directory: absolute path pointing to a directory within disk.
        :param bool silent: whether to silent some optional operations while project creation.
        :return: newly created project instance or None.
        :rtype: Project or None
        ..note:: If a Noddle project already exists in the given directory, the creation will be aborted.
        """

        if cls.is_project(directory):
            logger.error(f'Given directory: "{directory}" already contains a Noddle project')
            return None

        # create project tag and meta files
        new_project = cls(directory)
        folder.ensure_folder_exists(new_project.path)
        fileio.create_file(new_project.tag_path)
        creation_date = timedate.get_date_and_time()
        new_project.set_data('created', creation_date)

        # set environment variables
        cls._INSTANCE = new_project
        asset.Asset._INSTANCE = None

        if not silent:
            new_project.add_to_recent()

        return new_project

    @classmethod
    def get(cls):
        """
        Returns current active Noddle project instance.

        :return: active Noddle project.
        :rtype: Project or None
        """

        return cls._INSTANCE

    @classmethod
    def set(cls, directory: str, silent: bool = False) -> Project | None:
        """
        Sets current Noddle active project to the given directory.

        :param str directory: absolute path pointing to a directory that contains a valid Noddle project.
        :param bool silent: whether to silent some optional operations while project setting.
        :return: newly set project instance or None.
        :rtype: Project or None
        """

        if not cls.is_project(directory):
            logger.error(f'Given directory "{directory}" is not a valid Noddle project!')
            return None

        # create project instance
        project_instance = cls(directory)
        project_instance.update_meta()

        # set environment variables
        cls._INSTANCE = project_instance
        asset.Asset._INSTANCE = None

        if not silent:
            project_instance.add_to_recent()

        return project_instance

    @classmethod
    def exit(cls):
        """
        Unsets current active project.
        """

        cls._INSTANCE = None
        asset.Asset._INSTANCE = None
        hud.NoddleHUD.refresh()

    @staticmethod
    def refresh_recent():
        """
        Refreshes recent projects by ensuring recent project folders exist.
        """

        interface = preferences.preference().interface('noddle')
        interface.refresh_recent_projects()

    def set_data(self, key: str, value: str):
        """
        Sets given pair key/value within project metadata file.

        :param str key: metadata key to set value of.
        :param str value: metadata value to set.
        """

        data_dict = self.meta_data
        data_dict[key] = value
        yamlio.write_to_file(data_dict, self.meta_path, sort_keys=False)

    def update_meta(self):
        """
        Updates metadata file with the internal data of this instance.
        """

        yamlio.write_to_file(self.meta_data, self.meta_path, sort_keys=False)

    def add_to_recent(self):
        """
        Adds current project into the list of recent projects.
        """

        self._interface.set_previous_project(self.path)
        self._interface.add_recent_project(self.name, self.path)
        hud.NoddleHUD.refresh()
