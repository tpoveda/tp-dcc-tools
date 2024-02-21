from __future__ import annotations

from typing import Any

from overrides import override
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.dcc.abstract import callback

logger = log.tpLogger


class FnCallback(callback.AFnCallback):
    """
    Overloads of AFnCallback function set class to handle behaviour for Maya callbacks.
    """

    __slots__ = ()

    @override
    def unregister_callback(self, callback_id: Any):
        """
        Unregisters the given DCC callback ID.

        :param Any callback_id: ID of the callback to remove.
        """

        logger.info(f'Removing callback: {callback_id}')
        OpenMaya.MMessage.removeCallback(callback_id)

    @override
    def add_pre_file_open_callback(self, func: callable):
        """
        Adds callback that is called before a new scene is opened.

        :param callable func: callback function.
        """

        callback_id = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeOpen, func)
        self.register_callback(self.Callback.PreFileOpen, callback_id)

    @override
    def add_post_file_open_callback(self, func: callable):
        """
        Adds callback that is called after a new scene is opened.

        :param callable func: callback function.
        """

        callback_id = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterOpen, func)
        self.register_callback(self.Callback.PostFileOpen, callback_id)

    @override
    def add_selection_changed_callback(self, func: callable):
        """
        Adds callback that is called when the active selection is changed.

        :param callable func: callback function.
        """

        callback_id = OpenMaya.MEventMessage.addEventCallback('SelectionChanged', func)
        self.register_callback(self.Callback.SelectionChanged, callback_id)

    @override
    def add_undo_callback(self, func: callable):
        """
        Adds callback that is called each time the user undoes a command.

        :param callable func: callback function.
        """

        callback_id = OpenMaya.MEventMessage.addEventCallback('Undo', func)
        self.register_callback(self.Callback.Undo, callback_id)

    @override
    def add_redo_callback(self, func: callable):
        """
        Adds callback that is called each time the user redoes a command.

        :param callable func: callback function.
        """

        callback_id = OpenMaya.MEventMessage.addEventCallback('Redo', func)
        self.register_callback(self.Callback.Redo, callback_id)
