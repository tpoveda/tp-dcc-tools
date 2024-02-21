#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation for Noddle library Preference interface.
"""

from __future__ import annotations

import os
from collections import deque

from tp.preferences import preference
from tp.common.python import helpers, path, folder

NAMING_PRESET_HIERARCHY = 'namingPresetHierarchy'
NAMING_PRESET_SAVE_PATH = 'namingPresetSavePath'
NAMING_PRESET_PATHS = 'namingPresetPaths'
COMPONENTS_PATHS_KEY = 'componentsPaths'


class NoddleInterface(preference.PreferenceInterface):

	ID = 'noddle'
	_RELATIVE_PATH = 'prefs/maya/noddle.pref'

	def upgrade_assets(self):
		"""
		Upgrades the local assets.
		"""

		templates_path = self.default_user_templates_path()
		folder.ensure_folder_exists(templates_path)

		asset_pkg = self.repository_asset_path()
		local_folder = path.join_path(self.manager.asset_path(), 'noddle')
		folder.copy_directory_contents_safe(asset_pkg, local_folder, skip_exists=True, overwrite_modified=True)

	@staticmethod
	def repository_asset_path() -> str:
		"""
		Returns the absolute path containing all Noddle related assets (templates, build scripts, etc).

		:return: default assets absolute path.
		:rtype: str
		"""

		return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))

	def default_user_templates_path(self) -> str:
		"""
		Returns the default Noddle templates path.

		:return: Noddle assets/noddle/templates absolute path.
		:rtype: str
		"""

		return path.join_path(self.manager.asset_path(), 'noddle', 'templates')

	def empty_scenes_path(self) -> str:
		"""
		Returns the absolute path where empty scene templates are located.

		:return: Noddle assets/noddle/templates/emptyScenes absolute path.
		:rtype: str
		"""

		return path.join_path(self.default_user_templates_path(), 'emptyScenes')

	def recent_max(self):
		"""
		Returns the maximum number of recent projects to retrieve.

		:return: maximum number of recent projects.
		:rtype: int
		"""

		return self.manager.find_setting(self._RELATIVE_PATH, root=None, name='maxRecent', default=3)

	def recent_projects_queue(self):
		"""
		Returns a queue of recent projects.

		:return: recent projects.
		:rtype: deque
		"""

		max_length = self.recent_max()
		projects = self.manager.find_setting(self._RELATIVE_PATH, root=None, name='recentProjects', default=[])
		if not projects:
			return deque(maxlen=max_length)

		return deque(projects, maxlen=max_length)

	def previous_project(self) -> str:
		"""
		Returns previous project path.

		:return: previous project path.
		:rtype: str
		"""

		return self.settings().get('settings', {}).get('project', {}).get('previousProject', '')

	def set_previous_project(self, project_path: str):
		"""
		Sets given path as the previous project path.

		:param str project_path: project path.
		"""

		self.settings().setdefault('settings', {}).setdefault('project', {})['previousProject'] = str(project_path)

	def add_recent_project(self, name: str, project_path: str):
		"""
		Adds given project name and path entry as a recent project.

		:param str name: name of the project to add as recent one.
		:param str project_path: path of the project to add as a recent one.
		:return: True if project was added into the list of recent projects; False otherwise.
		:rtype: bool
		"""

		recent_projects = self.recent_projects_queue()
		entry = [name, project_path]
		if entry in recent_projects:
			return False
		recent_projects.appendleft(entry)
		self.settings().setdefault('settings', {}).setdefault('project', {})['recentProjects'] = list(recent_projects)
		self.save_settings()

	def refresh_recent_projects(self):
		"""
		Refreshes recent projects by removing recent project folders that do not exist.
		"""

		recent_projects = self.recent_projects_queue()
		existing_projects = []
		for recent_project in recent_projects:
			if not path.is_dir(recent_project):
				continue
			existing_projects.append(recent_project)
		self.settings().setdefault('settings', {}).setdefault('project', {})['recentProjects'] = existing_projects
		self.save_settings()

	def asset_types(self, root: str | None = None) -> list[str]:
		"""
		Returns list of asset types.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: list of asset type names.
		:rtype: list[str]
		"""

		return self.settings(root=root).get('settings', {}).get('assets', {}).get('types', [])

	def default_naming_config_path(self) -> str:
		"""
		Returns the absolute path where default naming presets are located.

		:return: default naming presets absolute path.
		:rtype: str
		"""

		return path.join_path(self.manager.asset_path(), 'noddle', 'namingpresets')

	def naming_preset_paths(self, root: str | None = None) -> list[str]:
		"""
		Returns the paths whether presets are located.

		:return: list of naming preset paths.
		:rtype: list[str]
		"""

		preset_paths = self.settings(root=root).get('settings', {}).get(NAMING_PRESET_PATHS, [])
		return helpers.remove_dupes([self.default_naming_config_path()] + preset_paths)

	def naming_preset_hierarchy(self, root: str | None = None) -> dict:
		"""
		Returns the naming preset hierarchies from Noddle preference file.

		:return: dictionary with naming presets hierarchy.
		:rtype: dict
		"""

		return self.settings(root=root).get('settings', {}).get(NAMING_PRESET_HIERARCHY, {})

	def naming_preset_save_path(self, root: str | None = None) -> str:
		"""
		Returns path where new naming presets will be stored into.

		:return: absolute presets save folder.
		:rtype: str
		"""

		return self.settings(root=root).get('settings', {}).get(
			NAMING_PRESET_PATHS, list()) or self.default_naming_config_path()

	def set_naming_preset_paths(self, paths: list[str], save: bool = True):
		"""
		Sets the naming preset paths for Noddle preferences file.

		:param list[str] paths: list of naming preset paths.
		:param bool save: whether to save preferences file changes.
		"""

		settings = self.settings(root=None)
		settings['settings'][NAMING_PRESET_PATHS] = paths
		if save:
			settings.save()

	def set_naming_preset_hierarchy(self, hierarchy: dict, save: bool = True):
		"""
		Sets the naming preset hierarchies for Noddle preferences file.

		:param dict hierarchy: preset hierarchy dictionary.
		:param bool save: whether to save preferences file changes.
		"""

		settings = self.settings(root=None)
		settings['settings'][NAMING_PRESET_HIERARCHY] = hierarchy
		if save:
			settings.save()

	def set_naming_preset_save_path(self, save_path: str, save: bool = True):
		"""
		Sets the naming preset save path for Noddle preferences file.

		:param str save_path: preset save path to set.
		:param bool save: whether to save preferences file changes.
		"""

		default_naming_path = self.default_naming_config_path()
		if path.clean_path(save_path) == default_naming_path:
			return
		settings = self.settings(root=None)
		settings['settings'][NAMING_PRESET_SAVE_PATH] = save_path
		if save:
			settings.save()

	def user_components_paths(self, root: str | None = None) -> list[str]:
		"""
		Returns the user component folder paths.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: list of folder paths.
		:rtype: list[str]
		"""

		return self.settings(root=root).get('settings', {}).get(COMPONENTS_PATHS_KEY, [])

	def builder_history_enabled(self, root: str | None = None) -> bool:
		"""
		Returns whether builder history is enabled.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: True if builder history is enabled; False otherwise.
		:rtype: bool
		"""

		return self.settings(root=root).get('settings', {}).get('builder', {}).get('history', {}).get('enabled', True)

	def builder_history_size(self, root: str | None = None) -> int:
		"""
		Returns builder history size.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: builder history size.
		:rtype: bool
		"""

		return self.settings(root=root).get('settings', {}).get('builder', {}).get('history', {}).get('size', 32)

	def builder_node_title_font(self, root: str | None = None) -> tuple[str, int]:
		"""
		Returns default node title font.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: tuple with the name of the default font and its size.
		:rtype: tuple[str, int]
		"""

		return self.settings(root=root).get('settings', {}).get('builder', {}).get('titleFont', ['Roboto', 10])

	def naming_templates(self, root: str | None = None) -> dict:
		"""
		Returns Noddle naming templates.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: Noddle naming templates.
		:rtype: Dict
		"""

		return self.settings(root=root).get('settings', {}).get('naming', {}).get('templates', {})

	def current_naming_template(self, root: str | None = None) -> str:
		"""
		Returns current Noddle naming template.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: current Noddle naming template name.
		:rtype: str
		"""

		return self.settings(root=root).get(
			'settings', {}).get('naming', {}).get('profile', {}).get('template', 'default')

	def name_start_index(self, root: str | None = None) -> int:
		"""
		Returns the Noddle naming start index.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: name start index.
		:rtype: int
		"""

		return self.settings(root=root).get('settings', {}).get('naming', {}).get('profile', {}).get('startIndex', 2)

	def name_index_padding(self, root: str | None = None) -> int:
		"""
		Returns the Noddle naming index padding.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: name index padding.
		:rtype: int
		"""

		return self.settings(root=root).get('settings', {}).get('naming', {}).get('profile', {}).get('indexPadding', 2)

	def rig_display_line_width(self, root: str | None = None) -> float:
		"""
		Returns the default display line width for newly created rig controls.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: display line width.
		:rtype: float
		"""

		return self.settings(root=root).get('settings', {}).get('rig', {}).get('display', {}).get('lineWidth', 2.0)

	def skin_file_format(self, root: str | None = None) -> str:
		"""
		Returns the format to use when saving skin weights.

		:param str root: root name to search. If None, then all roots will be searched until relativePath is found.
		:return: skin file format.
		:rtype: str
		"""

		return self.settings(root=root).get(
			'settings', {}).get('rig', {}).get('io', {}).get('skin', {}).get('fileFormat', 'pickle')
