from __future__ import annotations

from typing import Any

from overrides import override

from tp.core import log
from tp.dcc.abstract import callback

logger = log.tpLogger


class FnCallback(callback.AFnCallback):
    """
    Overloads of AFnCallback function set class to handle behaviour for standalone callbacks.
    """

    __slots__ = ()

    @override
    def unregister_callback(self, callback_id: Any):
        """
        Unregisters the given DCC callback ID.

        :param Any callback_id: ID of the callback to remove.
        """

        pass

    @override
    def add_pre_file_open_callback(self, func: callable):
        """
        Adds callback that is called before a new scene is opened.

        :param callable func: callback function.
        """

        pass

    @override
    def add_post_file_open_callback(self, func: callable):
        """
        Adds callback that is called after a new scene is opened.

        :param callable func: callback function.
        """

        pass

    @override
    def add_selection_changed_callback(self, func: callable):
        """
        Adds callback that is called when the active selection is changed.

        :param callable func: callback function.
        """

        pass

    @override
    def add_undo_callback(self, func: callable):
        """
        Adds callback that is called each time the user undoes a command.

        :param callable func: callback function.
        """

        pass

    @override
    def add_redo_callback(self, func: callable):
        """
        Adds callback that is called each time the user redoes a command.

        :param callable func: callback function.
        """

        pass
