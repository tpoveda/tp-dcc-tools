from __future__ import annotations

import abc
import enum
from typing import Any

from tp.dcc.abstract import base
from tp.dcc.collections import callback


class Callback(enum.IntEnum):
    """
    Enumerator class that contains all available callbacks.
    """

    PreFileOpen = 0
    PostFileOpen = 1
    SelectionChanged = 2
    Undo = 3
    Redo = 4


class AFnCallback(base.AFnBase):
    """
    Overloads of AFnBase function set class to handle behaviour for DCC callbacks.
    """

    Callback = Callback

    __slots__ = ('_callbacks', '__weakref__')

    __callbacks__ = {
        Callback.PreFileOpen: 'addPreFileOpenCallback',
        Callback.PostFileOpen: 'addPostFileOpenCallback',
        Callback.SelectionChanged: 'addSelectionChangedCallback',
        Callback.Undo: 'addUndoCallback',
        Callback.Redo: 'addRedoCallback',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._callbacks: dict[Callback, callback.CallbackList] = {}

        for member in Callback:
            self._callbacks[member] = callback.CallbackList()
            self._callbacks[member].add_callback('itemRemoved', self._on_callback_removed)

    def __del__(self):
        """
        Internal function that is called before this instance is sent for garbage collection.
        """

        self.clear()

    def add_callback(self, callback_type: Callback, func: callable):
        """
        Adds a new callback using the given callback type.

        :param Callback callback_type: callback type to add.
        :param callable func: callback function.
        """

        func_name = self.__callbacks__.get(callback_type, '')
        delegate = getattr(self, func_name, None)
        if callable(delegate):
            return delegate(func)
        else:
            raise TypeError(f'add_callback() expects a valid callback ({callback_type} given)!')

    def remove_callback(self, callback_type: Callback):
        """
        Removes the given callback from the scene.

        :param Callback callback_type: callback to remove.
        """

        self._callbacks[callback_type].clear()

    def register_callback(self, callback_type: Callback, callback_id: Any):
        """
        Registers a new callback within the internal callbacks trackers.

        :param Callback callback_type: callback type to register.
        :param Any callback_id: newly registered callback ID.
        ..warning:: You must call this function after creating a DCC callback for ti to be tracked properly!
        """

        self._callbacks[callback_type].append(callback_id)

    @abc.abstractmethod
    def unregister_callback(self, callback_id: Any):
        """
        Unregisters the given DCC callback ID.

        :param Any callback_id: ID of the callback to remove.
        """

        pass

    @abc.abstractmethod
    def add_pre_file_open_callback(self, func: callable):
        """
        Adds callback that is called before a new scene is opened.

        :param callable func: callback function.
        """

        pass

    @abc.abstractmethod
    def add_post_file_open_callback(self, func: callable):
        """
        Adds callback that is called after a new scene is opened.

        :param callable func: callback function.
        """

        pass

    @abc.abstractmethod
    def add_selection_changed_callback(self, func: callable):
        """
        Adds callback that is called when the active selection is changed.

        :param callable func: callback function.
        """

        pass

    @abc.abstractmethod
    def add_undo_callback(self, func: callable):
        """
        Adds callback that is called each time the user undoes a command.

        :param callable func: callback function.
        """

        pass

    @abc.abstractmethod
    def add_redo_callback(self, func: callable):
        """
        Adds callback that is called each time the user redoes a command.

        :param callable func: callback function.
        """

        pass

    def clear(self):
        """
        Removes all callbacks.
        """

        for callback_ids in self._callbacks.values():
            callback_ids.clear()

    def _on_callback_removed(self, value: Any):
        """
        Internal callback function that is called each time a DCC callback requires unregistering.

        :param Any value: removed callback.
        """

        self.unregister_callback(value)
