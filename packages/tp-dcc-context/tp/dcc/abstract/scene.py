from __future__ import annotations

import os
import abc
import enum
from typing import Any

from tp.dcc.abstract import base
from tp.common.python import decorators


class AFnScene(base.AFnBase):
    """
    Overloads of AFnBase function set class to handle behaviour for DCC scenes.
    """

    __slots__ = ()
    __extensions__: enum.IntEnum | None = None

    @decorators.classproperty
    def file_extensions(cls) -> enum.IntEnum:
        """
        Getter method that returns the file extension enumerator for this scene context class.

        :return: file extension enumerator.
        :rtype: enum.IntEnum
        """

        return cls.__extensions__

    @abc.abstractmethod
    def extensions(self) -> tuple[enum.IntEnum]:
        """
        Returns a list of scene file extensions.

        :return: tuple[enum.IntEnum]
        """

        pass

    def is_valid_extension(self, path: str) -> bool:
        """
        Evaluates whether given supplied extension is supported.

        :param str path: extension or file path with extension.
        :return: True if given extension is valid; False otherwise.
        :rtype: bool
        """

        if os.path.isfile(path):
            filename = os.path.basename(path)
            _, extension = os.path.splitext(filename)
        else:
            extension = path

        extensions = [member.name.lower() for member in self.extensions()]
        extension = extension.lstrip('.').lower()

        return extension in extensions

    @abc.abstractmethod
    def is_batch_mode(self) -> bool:
        """
        Returns whether scene is running in batch mode.

        :return: True if scene is running in batch mode; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def is_new_scene(self) -> bool:
        """
        Returns whether this is an untitled scene file.

        :return: True if scene is new; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def is_save_required(self) -> bool:
        """
        Returns whether the open scene file has changes that need to be saved.

        :return: True if scene has been modified; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def new(self):
        """
        Opens a new scene file.
        """

        pass

    @abc.abstractmethod
    def save(self):
        """
        Saves any changes to the current scene file.
        """

        pass

    @abc.abstractmethod
    def save_as(self, file_path: str):
        """
        Saves the current scene to given file path.

        :param str file_path: file path where we want to store scene.
        """

        pass

    @abc.abstractmethod
    def open(self, file_path: str) -> bool:
        """
        Opens the given scene file.

        :param str file_path: absolute file path pointing to a valid scene.
        :return: True if the scene was opened successfully; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def current_file_path(self) -> str:
        """
        Returns the path of the open scene file.

        :return: scene file path.
        :rtype: str
        """

        pass

    @abc.abstractmethod
    def current_directory(self) -> str:
        """
        Returns the directory of the open scene file.

        :return: scene file directory.
        :rtype: str
        """

        pass

    @abc.abstractmethod
    def current_file_name(self) -> str:
        """
        Returns the name of the open scene file with extension.

        :return: scene name with extension.
        :rtype: str
        """

        pass

    def current_name(self) -> str:
        """
        Returns the name the open scene file without extension.

        :return: scene name without extension.
        :rtype: str
        """

        return os.path.splitext(self.current_file_name())[0] if not self.is_new_scene() else ''

    def current_file_extension(self) -> enum.IntEnum | None:
        """
        Returns the extension of the open scene file.

        :return: scene extension.
        :rtype: enum.IntEnum or None
        """

        if self.is_new_scene():
            return None

        _, extension = os.path.splitext(self.current_file_name())
        return self.__extensions__[extension.lstrip('.')]

    @abc.abstractmethod
    def current_project_directory(self) -> str:
        """
        Returns the current project directory.

        :return: project directory.
        :rtype: str
        """

        pass

    @abc.abstractmethod
    def active_selection(self) -> list[Any]:
        """
        Returns current active selection.

        :return: list of active nodes.
        :rtype: list[Any]
        """

        pass

    @abc.abstractmethod
    def set_active_selection(self, selection: list[Any], replace: bool = True):
        """
        Updates active selection.

        :param list[Any] selection: list of nodes to set as the active ones.
        :param bool replace: whether to replace selection or add to current one.
        """

        pass

    @abc.abstractmethod
    def clear_active_selection(self):
        """
        Clears current active selection.
        """

        pass
