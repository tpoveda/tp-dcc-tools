from __future__ import annotations

import enum
from typing import Any

from overrides import override

from tp.dcc.abstract import scene


class FnScene(scene.AbstractScene):
    """
    Overload of skin.AbstractNode used to interface with nodes for standalone scenes.
    """

    @override
    def extensions(self) -> tuple[enum.IntEnum]:
        """
        Returns a list of scene file extensions.

        :return: tuple[enum.IntEnum]
        """

        return tuple()

    @override
    def is_batch_mode(self) -> bool:
        """
        Returns whether scene is running in batch mode.

        :return: True if scene is running in batch mode; False otherwise.
        :rtype: bool
        """

        return False

    @override
    def is_new_scene(self) -> bool:
        """
        Returns whether this is an untitled scene file.

        :return: True if scene is new; False otherwise.
        :rtype: bool
        """

        return True

    @override
    def is_save_required(self) -> bool:
        """
        Returns whether the open scene file has changes that need to be saved.

        :return: True if scene has been modified; False otherwise.
        :rtype: bool
        """

        return False

    @override
    def new(self):
        """
        Opens a new scene file.
        """

        pass

    @override
    def save(self):
        """
        Saves any changes to the current scene file.
        """

        pass

    @override
    def save_as(self, file_path: str):
        """
        Saves the current scene to given file path.

        :param str file_path: file path where we want to store scene.
        """

        pass

    @override
    def open(self, file_path: str) -> bool:
        """
        Opens the given scene file.

        :param str file_path: absolute file path pointing to a valid scene.
        :return: True if the scene was opened successfully; False otherwise.
        :rtype: bool
        """

        return False

    @override
    def current_file_path(self) -> str:
        """
        Returns the path of the open scene file.

        :return: scene file path.
        :rtype: str
        """

        return ''

    @override
    def current_directory(self) -> str:
        """
        Returns the directory of the open scene file.

        :return: scene file directory.
        :rtype: str
        """

        return ''

    @override
    def current_file_name(self) -> str:
        """
        Returns the name of the open scene file with extension.

        :return: scene name with extension.
        :rtype: str
        """

        return ''

    @override
    def current_project_directory(self) -> str:
        """
        Returns the current project directory.

        :return: project directory.
        :rtype: str
        """

        return ''

    @override
    def active_selection(self) -> list[Any]:
        """
        Returns current active selection.

        :return: list of active nodes.
        :rtype: list[Any]
        """

        return []

    @override
    def set_active_selection(self, selection: list[Any], replace: bool = True):
        """
        Updates active selection.

        :param list[Any] selection: list of nodes to set as the active ones.
        :param bool replace: whether to replace selection or add to current one.
        """

        pass

    @override
    def clear_active_selection(self):
        """
        Clears current active selection.
        """

        pass
