from __future__ import annotations

import enum

from overrides import override

import maya.cmds as cmds

import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.dcc.abstract import scene
from tp.maya.cmds import scene as cmds_scene
from tp.maya.om import dagpath

logger = log.tpLogger


class FileExtensions(enum.IntEnum):
    """
    Enumerator that defines available file extensions for Maya
    """

    mb = 0
    ma = 1


class FnScene(scene.AFnScene):
    """
    Overloads of AFnScene function set class to handle behaviour for Maya scenes.
    """

    __slots__ = ()
    __extensions__ = FileExtensions

    @override(check_signature=False)
    def extensions(self) -> tuple[FileExtensions, ...]:
        """
        Returns a list of scene file extensions.

        :return: tuple[enum.IntEnum]
        """

        return FileExtensions.mb, FileExtensions.ma

    @override
    def is_batch_mode(self) -> bool:
        """
        Returns whether scene is running in batch mode.

        :return: True if scene is running in batch mode; False otherwise.
        :rtype: bool
        """

        return cmds_scene.is_batch()

    @override
    def is_new_scene(self) -> bool:
        """
        Returns whether this is an untitled scene file.

        :return: True if scene is new; False otherwise.
        :rtype: bool
        """

        return cmds_scene.is_new_scene()

    @override
    def is_save_required(self) -> bool:
        """
        Returns whether the open scene file has changes that need to be saved.

        :return: True if scene has been modified; False otherwise.
        :rtype: bool
        """

        return cmds_scene.current_scene_is_modified()

    @override
    def new(self):
        """
        Opens a new scene file.
        """

        cmds.file(newFile=True, force=True)

    @override
    def save(self):
        """
        Saves any changes to the current scene file.
        """

        cmds_scene.save_scene()

    @override
    def save_as(self, file_path: str):
        """
        Saves the current scene to given file path.

        :param str file_path: file path where we want to store scene.
        """

        cmds_scene.save_as(file_path)

    @override
    def open(self, file_path: str) -> bool:
        """
        Opens the given scene file.

        :param str file_path: absolute file path pointing to a valid scene.
        :return: True if the scene was opened successfully; False otherwise.
        :rtype: bool
        """

        try:
            cmds.file(file_path, open=True, prompt=False, force=True)
            return True
        except RuntimeError as exception:
            logger.error(exception)
            return False

    @override
    def current_file_path(self) -> str:
        """
        Returns the path of the open scene file.

        :return: scene file path.
        :rtype: str
        """

        return cmds_scene.current_file_path()

    @override
    def current_directory(self) -> str:
        """
        Returns the directory of the open scene file.

        :return: scene file directory.
        :rtype: str
        """

        return cmds_scene.current_directory()

    @override
    def current_file_name(self) -> str:
        """
        Returns the name of the open scene file with extension.

        :return: scene name with extension.
        :rtype: str
        """

        return cmds_scene.current_file_name()

    @override
    def current_project_directory(self) -> str:
        """
        Returns the current project directory.

        :return: project directory.
        :rtype: str
        """

        return cmds_scene.current_project_directory()

    @override(check_signature=False)
    def active_selection(self) -> list[OpenMaya.MObject]:
        """
        Returns current active selection.

        :return: list of active nodes.
        :rtype: list[OpenMaya.MObject]
        """

        selection: OpenMaya.MSelectionList = OpenMaya.MGlobal.getActiveSelectionList()
        return [selection.getDependNode(i) for i in range(selection.length())]

    @override(check_signature=False)
    def set_active_selection(self, selection: list[OpenMaya.MObject], replace: bool = True):
        """
         Updates active selection.

         :param list[OpenMaya.MObject] selection: list of nodes to set as the active ones.
         :param bool replace: whether to replace selection or add to current one.
         """

        if not replace:
            selection.extend(self.active_selection())

        selection_list = dagpath.create_selection_list(selection)
        OpenMaya.MGlobal.setActiveSelectionList(selection_list)

    @override
    def clear_active_selection(self):
        """
        Clears current active selection.
        """

        OpenMaya.MGlobal.clearSelectionList()
