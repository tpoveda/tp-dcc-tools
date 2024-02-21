#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions related with OpenMaya callbacks
"""

from __future__ import annotations

import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.maya.om import output, scene

logger = log.tpLogger


def remove_callbacks_from_node(mobj):
    """
    Removes callbacks from the given Maya object.

    :param OpenMaya.MObject mobj: Maya object whose callbacks we want to remove.
    """

    callbacks = OpenMaya.MMessage.nodeCallbacks(mobj)
    count = len(callbacks)
    for callback in iter(callbacks):
        OpenMaya.MMessage.removeCallback(callback)

    return count


def remove_callbacks_from_nodes(mobjs):
    """
    Removes callbacks from the given list of Maya objects.

    :param list(OpenMaya.MObject) mobjs: list of Maya objects whose callbacks we want to remove.
    """

    callback_count = 0
    for mobj in iter(mobjs):
        callback_count += remove_callbacks_from_node(mobj)

    return callback_count


class MCallbackIdWrapper(object):
    """
    Wrapper class to handle cleaning up of Maya callbacks from registered MMessage.
    """

    def __init__(self, callback_id):
        super(MCallbackIdWrapper, self).__init__()
        self.callback_id = callback_id

    def __del__(self):
        OpenMaya.MMessage.removeCallback(self.callback_id)

    def __repr__(self):
        return f'MCallbackIdWrapper({self.callback_id})'


class CallbackSelection:
    """
    Wrapper callback class that handles the management of a single selection callback which can be stored in a GUI.

    :param func: function to call when the selection is changed.
    :param tuple args: arguments to pass to the callable each time the selection is changed
    :param dict kwargs: keyword arguments to pass to the callback each time the selection is changed

    ..note:: the selected nodes are passed to the callback as a keyword argument "selection"

    .. code-block:: python

        from tp.maya.utils import node as node_api

        def my_callback_function(selection):
            for mobj_handle in selection:
                if not i.isValid() or not i.isAlive():
                    continue
                print(mobj_handle)

        callback_instance = CallbackSelection(my_callback_function)  # add the function here
        callback_instance.start()
        callback_instance.stop()
    """

    def __init__(self, func: callable, *args, **kwargs):
        super(CallbackSelection, self).__init__()

        self.selection_change_callback: MCallbackIdWrapper | None = None
        self.current_selection: list[OpenMaya.MObjectHandle] = []
        self.current_callback_state = False
        self.callable = func
        self.arguments = args
        self.keywords_args = kwargs

    def __del__(self):
        """
        Overridden so we clean up the callback automatically on instance being deleted.
        """

        self.stop()

    def start(self):
        """
        Creates and stores the selection callback on this instance.
        """

        if self.current_callback_state:
            return
        if self.callable is None:
            logger.error('Callable must be given!')
            return

        # create callback and store it
        self.selection_change_callback = MCallbackIdWrapper(OpenMaya.MEventMessage.addEventCallback(
            'SelectionChanged', self._on_maya_selection_changed))
        self.current_callback_state = True

    def stop(self):
        """
        Cleans up the instance by removing the Maya API callback.
        """

        if not self.current_callback_state:
            return
        try:
            self.selection_change_callback = None

            self.current_callback_state = False
            self.current_selection: list[OpenMaya.MObjectHandle] = []
        except Exception:
            logger.error('Unknown Error Occurred during deleting callback', exc_info=True)
            output.display_error('Selection Callback Failed To Be Removed')

    def _on_maya_selection_changed(self, *args, **kwargs):
        """
        Internal callback function used to monitor a selection callback with a short and long name list of strings.
        """

        # make sure we store objects as MObjectHandles
        selection = scene.iterate_selected_nodes(OpenMaya.MFn.kTransform)
        self.current_selection = map(OpenMaya.MObjectHandle, selection)
        keywords = {'selection': self.current_selection}
        keywords.update(self.keywords_args)

        # call client function
        self.callable(*self.arguments, **keywords)
