from __future__ import annotations

from typing import Any
from uuid import uuid4

import pymxs
from overrides import override

from tp.core import log
from tp.dcc.abstract import callback

logger = log.tpLogger


class FnCallback(callback.AFnCallback):
    """
    Overloads of AFnCallback function set class to handle behaviour for 3ds Max callbacks.
    """

    __slots__ = ()

    @override
    def unregister_callback(self, callback_id: Any):
        """
        Unregisters the given DCC callback ID.

        :param Any callback_id: ID of the callback to remove.
        """

        if pymxs.runtime.isKindOf(callback_id, pymxs.runtime.Name):
            logger.info(f'Removing callback: {callback_id}')
            pymxs.runtime.callbacks.removeScripts(id=callback_id)

    @override
    def add_pre_file_open_callback(self, func: callable):
        """
        Adds callback that is called before a new scene is opened.

        :param callable func: callback function.
        """

        callback_id = pymxs.runtime.Name(uuid4().hex)
        pymxs.runtime.callbacks.addScript(pymxs.runtime.Name('filePreOpen'), func, id=callback_id, persistent=False)
        self.register_callback(self.Callback.PreFileOpen, callback_id)

    @override
    def add_post_file_open_callback(self, func: callable):
        """
        Adds callback that is called after a new scene is opened.

        :param callable func: callback function.
        """

        callback_id = pymxs.runtime.Name(uuid4().hex)
        pymxs.runtime.callbacks.addScript(pymxs.runtime.Name('filePostOpen'), func, id=callback_id, persistent=False)
        self.register_callback(self.Callback.PostFileOpen, callback_id)

    @override
    def add_selection_changed_callback(self, func: callable):
        """
        Adds callback that is called when the active selection is changed.

        :param callable func: callback function.
        """

        callback_id = pymxs.runtime.nodeEventCallback(selectionChanged=func, subobjectSelectionChanged=func)
        self.register_callback(self.Callback.SelectionChanged, callback_id)

    @override
    def add_undo_callback(self, func: callable):
        """
        Adds callback that is called each time the user undoes a command.

        :param callable func: callback function.
        """

        callback_id = pymxs.runtime.Name(uuid4().hex)
        pymxs.runtime.callbacks.addScript(pymxs.runtime.Name('sceneUndo'), func, id=callback_id, persistent=False)
        self.register_callback(self.Callback.Undo, callback_id)

    @override
    def add_redo_callback(self, func: callable):
        """
        Adds callback that is called each time the user redoes a command.

        :param callable func: callback function.
        """

        callback_id = pymxs.runtime.Name(uuid4().hex)
        pymxs.runtime.callbacks.addScript(pymxs.runtime.Name('sceneRedo'), func, id=callback_id, persistent=False)
        self.register_callback(self.Callback.Redo, callback_id)

    @override
    def clear(self):
        """
        Removes all callbacks.
        """

        super().clear()

        pymxs.runtime.gc(light=True)
