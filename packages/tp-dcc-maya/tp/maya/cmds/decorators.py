#!#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains collections of decorators related with Maya
"""

from __future__ import annotations

import sys
import traceback
from typing import Any
from functools import wraps

import maya.mel as mel
import maya.cmds as cmds

from tp.core import log
from tp.common.python import helpers, decorators

logger = log.tpLogger


def try_except(fn):
    """
    Exception wrapper with undo functionality. Use @try_except above the function to wrap it.
    @param fn: function to wrap
    @return: wrapped function
    """

    error_text = '\n ====== tpRigLib: Something bad happened :( ======'

    def wrapper(*args, **kwargs):
        try:
            cmds.undoInfo(openChunk=True)
            result = fn(*args, **kwargs)
            cmds.undoInfo(closeChunk=True)
            return result
        except Exception as e:
            cmds.undoInfo(closeChunk=True)
            gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

            et, ei, tb = sys.exc_info()
            print(error_text, '\n')
            print("ERROR IN: ", fn.__name__, "Function.")
            print(e, '\n')
            print(traceback.print_exc(), '\n')
            print("=================== HELP ===================")
            print(fn.__doc__, 'n')
            print("=================== ERROR ===================")
            cmds.inViewMessage(
                amg='<span style=\"color:#F05A5A;'
                    '\">Error: </span>' + str(e) + ' <span style=\"color:#FAA300;\">Look at the script '
                                                   'editor for more info about the error.</span>',
                pos='topCenter', fade=True, fst=4000, dk=True)
            raise Exception(e, tb)

    return wrapper


def viewport_off(f):
    """
    Function decorator that turns off Maya display while the function is running
    if the function fails, the error will be raised after
    :param f: fn, function
    """

    @wraps(f)
    def wrap(*args, **kwargs):
        # Turn $gMainPanel off
        gMainPane = mel.eval('global string $gMainPane; $temp = $gMainPane;')
        cmds.paneLayout(gMainPane, edit=True, manage=False)
        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            cmds.paneLayout(gMainPane, edit=True, manage=True)
    return wrap


def undo(fn):
    """
    Function decorator that enables undo functionality using Maya Python commands
    :param f: fn, function
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            cmds.undoInfo(openChunk=True, chunkName=fn.__name__)
            return fn(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper


# def maya_undo(fn):
#     @functools.wraps(fn)
#     def wrapper(*args, **kwargs):
#         try:
#             cmds.undoInfo(openChunk=True)
#             return fn(*args, **kwargs)
#         finally:
#             cmds.undoInfo(closeChunk=True)
#
#     return lambda *args, **kwargs: utils.executeDeferred(wrapper, *args, **kwargs)


def disable_undo(fn):

    @wraps(fn)
    def wrapped(*args, **kwargs):
        initial_undo_state = cmds.undoInfo(query=True, state=True)
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            return fn(*args, **kwargs)
        finally:
            cmds.undoInfo(stateWithoutFlush=initial_undo_state)
    return wrapped


def operate_on_selected(f):
    """
    Function decorator that enables a function to operate only on selected objects
    :param f: fn, function
    """

    def wrapper(*args, **kwargs):
        selection = cmds.ls(sl=True)
        return f(selection, *args, **kwargs)

    return wrapper


def suspend_refresh(f):
    """
    Function decorator that suspend the refersh of Maya viewport
    :param f: fn, function
    """

    def wrapper(*args, **kwargs):
        with SuspendRefresh():
            return f(*args, **kwargs)

    return wrapper


def restore_context(f):
    """
    Function decorator that restores Maya context
    :param f: fn, function
    """

    def wrapper(*args, **kwargs):
        with RestoreContext():
            return f(*args, **kwargs)

    return wrapper


def undo_chunk(f):
    """
    Function decorator that enables Maya undo functionality for a function
    :param f: fn, function
    """

    def wrapper(*args, **kwargs):
        with UndoChunk():
            return f(*args, **kwargs)

    return wrapper


def skip_undo(f):
    """
    Function decorator that skip Maya undo functionality for a function
    :param f; fn, function
    """

    def wrapper(*args, **kwargs):
        with SkipUndo():
            return f(*args, **kwargs)

    return wrapper


def toggle_scrub(f):
    """
    Function decorator that enables Maya scrub toggling functionality for a function
    :param f: fn, function
    """

    def wrapper(*args, **kwargs):
        with ToggleScrub():
            return f(*args, **kwargs)

    return wrapper


def repeat_static_command(class_name, skip_arguments=False):
    """
    Decorator that will make static functions repeatable for Maya
    :param class_name, str, path to the Python module where function we want to repeat is located
    :param skip_arguments, bool, Whether or not force the execution of the repeat function without passing any argument
    """

    def repeat_command(fn):
        def wrapper(*args, **kwargs):
            arg_str = ''
            if args:
                for each in args:
                    arg_str += str(each) + ', '
                    arg_str += '"{}", '.format(each)

            if kwargs:
                for k, v in kwargs.items():
                    arg_str += str(k) + '=' + str(v) + ', '

            if not skip_arguments:
                cmd = 'python("' + class_name + '.' + fn.__name__ + '(' + arg_str + ')")'
            else:
                cmd = 'python("' + class_name + '.' + fn.__name__ + '()")'
            fn_return = fn(*args, **kwargs)
            try:
                cmds.repeatLast(ac=cmd, acl=fn.__name__)
            except Exception:
                pass
            return fn_return
        return wrapper
    return repeat_command


def disable_auto_key(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        initial_state = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(edit=True, state=False)
        try:
            return fn(*args, **kwargs)
        finally:
            cmds.autoKeyframe(edit=True, state=initial_state)
    return wrapped


def restore_selection(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        selection = cmds.ls(selection=True, long=True) or []
        try:
            return fn(*args, **kwargs)
        finally:
            if selection:
                cmds.select([i for i in selection if cmds.objExists(i)])
    return wrapped


def restore_current_time(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        initial_time = cmds.currentTime(query=True)
        try:
            return fn(*args, **kwargs)
        finally:
            cmds.currentTime(initial_time, edit=True)
    return wrapped


def show_wait_cursor(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        cmds.waitCursor(state=True)
        try:
            return fn(*args, **kwargs)
        finally:
            cmds.currentTime(state=False)
    return wrapped


def disable_views(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        model_panels = cmds.getPanel(vis=True)
        empty_selection_connection = cmds.selectionConnection()
        for panel in model_panels:
            cmds.isolateSelect(panel, state=True)
            cmds.modelEditor(panel, edit=True, mainListConnection=empty_selection_connection)
        try:
            return fn(*args, **kwargs)
        finally:
            for panel in model_panels:
                if cmds.getPanel(typeOf=panel) == 'modelPanel':
                    cmds.isolateSelect(panel, state=False)
            cmds.deleteUI(empty_selection_connection)
    return wrapped


def disable_cycle_check_decorator(fn):
    """
    Function decorator that disables the cycle check then restores it to previous values.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            cycle_check = cmds.cycleCheck(q=True, e=True)
            cmds.cycleCheck(e=False)
            result = None
            try:
                result = fn(*args, **kwargs)
            except Exception:
                raise
            finally:
                cmds.cycleCheck(e=cycle_check)
            return result
        except Exception:
            raise
    return wrapper


def keep_current_frame_decorator(fn):
    """
    Function decorator that makes sure that starting keyframe is kept after executing the wrapped function.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            current_frame = cmds.currentTime(q=True)
            result = None
            try:
                result = fn(*args, **kwargs)
            except Exception:
                raise
            finally:
                cmds.currentTime(current_frame)
            return result
        except Exception:
            raise

    return wrapper


def keep_selection_decorator(fn):
    """
    Function decorator that makes sure that original selection is keep after executing the wrapped function.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            tmp_selection = cmds.ls(sl=True, l=True)
            result = None
            try:
                result = fn(*args, **kwargs)
            except Exception:
                raise
            finally:
                cmds.select(tmp_selection)
            return result
        except Exception:
            raise
    return wrapper


def keep_namespace_decorator(fn):
    """
    Function decorator that restores the active namespace after execution.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            original_namespace = cmds.namespaceInfo(cur=True)
            result = None
            try:
                result = fn(*args, **kwargs)
            except Exception:
                raise
            finally:
                cmds.namespace(set=':')
                cmds.namespace(set=original_namespace)
            return result
        except Exception:
            raise
    return wrapper


def make_display_layers_visible_decorator(fn):
    """
    Function decorator that toggles on all display layers during execution then restores them.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            display_layer_dict = {}
            default_display_layer = 'defaultLayer' if cmds.objExists('defaultLayer') else None
            result = None
            for display_layer in cmds.ls(type='displayLayer'):
                if display_layer != default_display_layer:
                    display_layer_dict[display_layer] = cmds.getAttr('{}.visibility'.format(display_layer))
                    cmds.setAttr('{}.visibility'.format(display_layer), True)
            try:
                result = fn(*args, **kwargs)
            except Exception:
                raise
            finally:
                for display_layer, value in display_layer_dict.items():
                    if cmds.objExists(display_layer):
                        cmds.setAttr('{}.visibility'.format(display_layer), value)
            return result
        except Exception:
            raise
    return wrapper


class ShowMayaProgress(object):

    """
    Function decorator to show user (progress) feedback
    http://josbalcaen.com/maya-python-progress-decorator/
    @usage
    from tpRigLib.utils.tpDecorators import showMayaProgress
    @showMayaProgress(status='Creating cubes...', end=10)
    def createCubes():
    for i in range(10):
        time.sleep(1)
        if createCubes.isInterrupted(): break
        iCube = cmds.polyCube(w=1,h=1,d=1)
        cmds.move(i,i*.2,0,iCube)
        createCubes.step()
    createCubes()
    """

    def __init__(self, status='Working...', start=0, end=100, interruptable=True):

        self._start_value = start
        self._end_value = end
        self._status = status
        self._interruptable = interruptable

        self._main_progressbar = mel.eval('$tmp = $gMainProgressBar')

    def start(self):
        """
        Start progress bar
        """

        if self._main_progressbar is None:
            return

        cmds.waitCursor(state=True)
        cmds.progressBar(self._main_progressbar, edit=True, beginProgress=True,
                         isInterruptable=self._interruptable, status=self._status,
                         minValue=self._start_value, maxValue=self._end_value)
        cmds.refresh()

    def end(self):
        """
        Mark the progress bar as ended
        """

        if self._main_progressbar is None:
            return

        cmds.progressBar(self._main_progressbar, edit=True, endProgress=True)
        cmds.waitCursor(state=False)

    def step(self, value=1):
        """
        Increases progress bar step by value
        :param value: int, step
        """

        if self._main_progressbar is None:
            return

        cmds.progressBar(self._main_progressbar, edit=True, step=value)

    def is_interrupted(self):
        """
        Checks if the user has interrupted the progress
        """

        if self._main_progressbar is None:
            return False

        return cmds.progressBar(self._main_progressbar, query=True, isCancelled=True)

    def __call__(self, fn):
        """
        Override call method
        If there are decorator aguments, __cal__() is only called once, as part of the decoration process!
        You can only give it a single argument, which is the function object
        :param fn: Original function
        :return Wrapped function
        """

        def wrapped_fn(*args, **kwargs):
            self.start()                # Start progress
            fn(*args, **kwargs)         # Call original function
            self.end()                  # End progress

        # Add special method to the wrapped function
        wrapped_fn.step = self.step
        wrapped_fn.is_interrupted = self.is_interrupted

        # Copy over attributes
        wrapped_fn.__doc__ = fn.__doc__
        wrapped_fn.__name__ = fn.__name__
        wrapped_fn.__module__ = fn.__module__

        return wrapped_fn


class SuspendRefresh(object):
    def __enter__(self):
        cmds.refresh(suspend=True)

    def __exit__(self, *exc_info):
        cmds.refresh(suspend=False)


class RestoreContext(object):
    def __init__(self):
        self.auto_key_state = None
        self.time = None
        self.selection = None

    def __enter__(self):
        self.auto_key_state = cmds.autoKeyframe(query=True, state=True)
        self.time = int(cmds.currentTime(q=True))
        self.selection = cmds.ls(sl=True)

    def __exit__(self, *exc_info):
        cmds.autoKeyframe(state=self.auto_key_state)
        cmds.currentTime(self.time)
        if self.selection:
            cmds.select(self.selection)


class UndoChunk:
    def __enter__(self):
        cmds.undoInfo(openChunk=True)

    def __exit__(self, *exc_info):
        cmds.undoInfo(closeChunk=True)


class SkipUndo:
    def __enter__(self):
        cmds.undoInfo(swf=False)

    def __exit__(self, *exc_info):
        cmds.undoInfo(swf=True)


class ToggleScrub:
    def __init__(self):
        self._playblack_slider = mel.eval('$tmp=$gPlayBackSlider')

    def __enter__(self):
        cmds.timeControl(self._playblack_slider, beginScrub=True, e=True)

    def __exit__(self, *exc_info):
        cmds.timeControl(self._playblack_slider, endScrub=True, e=True)


class Undo(decorators.AbstractDecorator):
    """
    Overload of AbstractDecorator that defines Maya undo chunks.
    """

    __slots__ = ('_state', '_name')
    __chunk__: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._state = kwargs.get('state', True)
        self._name = kwargs.get('name', '').replace(' ', '_')

    def __enter__(self, *args, **kwargs):
        """
        Private method that is called when this instance is entered using a with statement.
        """

        if self.state:
            # Check if chunk is already open.
            if not helpers.is_null_or_empty(self.chunk):
                return
            # Open undo chunk.
            self.__class__.__chunk__ = self.name
            cmds.undoInfo(openChunk=True, chunkName=self.name)
        else:
            # Disable undo.
            cmds.undoInfo(stateWithoutFlush=False)

    def __call__(self, *args, **kwargs) -> Any:
        """
        Private method that is called whenever this instance is evoked.

        :return: call result.
        :rtype: Any
        """

        try:
            self.__enter__(*args, **kwargs)
            results = self.func(*args, **kwargs)
            self.__exit__(None, None, None)
            return results
        except RuntimeError as exception:
            logger.error(exception, exc_info=True)
            return None

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """
        Private method that is called when this instance is exited using a with statement.

        :param Any exc_type: exception type.
        :param Any exc_val: exception value.
        :param Any exc_tb: exception traceback.
        """

        if self.state:
            # Check if chunk can be closed.
            if self.name != self.chunk:
                return

            # Close undo chunk
            self.__class__.__chunk__ = None
            cmds.undoInfo(closeChunk=True)
        else:
            cmds.undoInfo(stateWithoutFlush=True)

    @property
    def chunk(self) -> str  | None:
        """
        Getter method that returns the current undo chunk.

        :return: undo chunk.
        :rtype: str or None
        """

        return self.__class__.__chunk__

    @property
    def state(self) -> bool:
        """
        Getter method that returns current undo state.

        :return: undo state.
        :rtype: bool
        """

        return self._state

    @property
    def name(self) -> str:
        """
        Getter method that returns the name of this undo.

        :return: undo name.
        :rtype: str
        """

        return self._name
