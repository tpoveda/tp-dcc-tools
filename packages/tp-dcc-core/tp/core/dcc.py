#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains DCC core functions an classes
"""

from __future__ import annotations

import os
import sys
import importlib
import traceback
from functools import wraps
from typing import Callable, Any
from importlib.util import find_spec

from Qt.QtWidgets import QMainWindow, QMenuBar

from tp.core import log, dccs
from tp.common.python import osplatform

logger = log.tpLogger

# Cached current DCC name.
CURRENT_DCC = None

# Cached used to store all the rerouting paths done during a session.
DCC_REROUTE_CACHE = {}


def dcc_port(dcc_name: str | None = None) -> int:
    """
    Returns the port assigned for given DCC.

    :param str or None dcc_name: optional name of the DCC to get port of. If not given, current DCC will be used.
    :return: tp-dcc-tools framework client/server port to use.
    :rtype: int
    """

    dcc = dcc_name or current_dcc()
    if not dcc:
        return dccs.Ports['Standalone']

    return dccs.Ports.get(dcc_name, dccs.Ports['Undefined'])


def importable(module_name: str) -> bool:
    """
    Returns whether given module is importable.

    :param str module_name: name of the module to check.
    :return: True if given module is importable; False otherwise.
    :rtype: bool
    """

    try:
        return bool(find_spec(module_name))
    except TypeError:
        return False


def current_dcc() -> str:
    """
    Returns name of the current DCC being used.

    :return: DCC being used.
    :rtype: str
    """

    global CURRENT_DCC
    if CURRENT_DCC:
        return CURRENT_DCC

    for dcc_package, dcc_name in dccs.Packages.items():
        if importable(dcc_package) and dccs.Executables[dcc_name][osplatform.get_platform()] in sys.executable:
            CURRENT_DCC = dcc_name
            break
    if not CURRENT_DCC:
        try:
            import unreal
            CURRENT_DCC = dccs.Unreal
        except ImportError:
            try:
                if os.path.splitext(os.path.basename(sys.executable))[0].lower() == 'motionbuilder':
                    import pyfbsdk
                    CURRENT_DCC = dccs.MotionBuilder
                else:
                    CURRENT_DCC = dccs.Standalone
            except ImportError:
                CURRENT_DCC = dccs.Standalone

    return CURRENT_DCC


def reroute(fn: Callable):
    """
    Decorator that reroutes the function call on runtime to the specific DCC implementation of the function
    Rerouted function calls are cached, and are only loaded once.
    The used DCC API will be retrieved from the current session, taking into account the current available
    implementations

    :param Callable fn: decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):

        global DCC_REROUTE_CACHE

        dcc = current_dcc()
        if not dcc:
            return None

        # From the current function and DCC we retrieve module path where DCC implementation should be located
        fn_split = fn.__module__.split('.')
        dcc_reroute_path = f'tp.{dcc}'
        fn_split_str = '.'.join(fn_split[3:])
        if fn_split_str:
            dcc_reroute_path = f'{dcc_reroute_path}.{fn_split_str}'
        dcc_reroute_path = f'{dcc_reroute_path}.dcc'
        dcc_reroute_fn_path = f'{dcc_reroute_path}.{fn.__name__}'
        if dcc_reroute_fn_path not in DCC_REROUTE_CACHE:
            try:
                dcc_reroute_module = importlib.import_module(dcc_reroute_path)
            except ImportError:
                raise NotImplementedError(
                    f'{dcc} | Function {dcc_reroute_fn_path} not implemented! {traceback.format_exc()}')
            except Exception as exc:
                raise exc

            # Cache reroute call, next calls to that function will use cache data
            if not hasattr(dcc_reroute_module, fn.__name__):
                raise NotImplementedError(
                    f'{dcc} | Function {dcc_reroute_fn_path} not implemented within {dcc_reroute_module}!')

            dcc_reroute_fn = getattr(dcc_reroute_module, fn.__name__)
            DCC_REROUTE_CACHE[dcc_reroute_fn_path] = dcc_reroute_fn

        return DCC_REROUTE_CACHE[dcc_reroute_fn_path](*args, **kwargs)

    return wrapper


def callbacks() -> list[str]:
    """
    Return a full list of callbacks based on DccCallbacks dictionary.

    :return: list of callback names.
    :rtype: list[str]
    """

    new_list = []
    for k, v in dccs.Callbacks.__dict__.items():
        if k.startswith('__') or k.endswith('__'):
            continue
        new_list.append(v[0])

    return new_list


def is_standalone() -> bool:
    """
    Check if current environment is standalone or not.

    :return: True if current environment is standalone; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Standalone


def is_maya() -> bool:
    """
    Checks if Maya is available or not.

    :return: True if current environment is Autodesk Maya; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Maya


def is_mayapy() -> bool:
    """
    Checks if MayaPy is available or not.

    :return: True if current environment is Autodesk MayaPy; False otherwise.
    :rtype: bool
    """

    return is_maya() and 'mayapy' in sys.executable


def is_max() -> bool:
    """
    Checks if 3ds Max is available or not.

    :return: True if current environment is Autodesk 3ds Max; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Max


def is_mobu() -> bool:
    """
    Checks if MotionBuilder is available or not.

    :return: True if current environment is Autodesk MotionBuilder; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.MotionBuilder


def is_houdini() -> bool:
    """
    Checks if Houdini is available or not.

    :return: True if current environment is SideFX Houdini; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Houdini


def is_unreal() -> bool:
    """
    Checks if Houdini is available or not.

    :return: True if current environment is Epic Games Unreal Engine; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Unreal


def is_nuke() -> bool:
    """
    Checks if Nuke is available or not.

    :return: True if current environment is Nuke; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Nuke


def is_blender() -> bool:
    """
    Checks if Blender is available or not.

    :return: True if current environment is Blender; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Blender


def is_substance_painter() -> bool:
    """
    Checks if Substance Painter is available or not.

    :return: True if current environment is Adobe Substance Painter; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.SubstancePainter


def is_substance_designer() -> bool:
    """
    Checks if Substance Designer is available or not.

    :return: True if current environment is Adobe Substance Painter; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.SubstancePainter


def is_fusion() -> bool:
    """
    Checks if Fusion is available or not.

    :return: True if current environment is Fusion; False otherwise.
    :rtype: bool
    """

    return current_dcc() == dccs.Fusion


# ======================================================================================================================
# GENERAL
# ======================================================================================================================


@reroute
def name() -> str:
    """
    Returns the name of the DCC.

    :return: DCC name ('maya', 'mobu', ...).
    :rtype: str
    """

    raise NotImplementedError()


@reroute
def file_extensions() -> list[str]:
    """
    Returns supported file extensions of the DCC.

    :return: list of DCC file extensions (['.mb', '.ma'], ['.max'], ...).
    :rtype: List[str]
    """

    raise NotImplementedError()


@reroute
def version() -> int | float:
    """
    Returns integer version of the DCC.

    :return: DCC version (2022, 2023.5, ...).
    :rtype: int or float
    """

    raise NotImplementedError()


@reroute
def version_name() -> str:
    """
    Returns name version of the DCC.

    :return: DCC version ('2022', '2023.5', ...).
    :rtype: str
    """

    raise NotImplementedError()


@reroute
def is_batch() -> bool:
    """
    Returns whether DCC is being executed in batch mode.

    :return: True if DCC is being executed in batch mode; False otherwise.
    :rtype: bool
    """

    raise NotImplementedError()


@reroute
def execute_deferred(fn: Callable) -> Any:
    """
    Executes given function in deferred mode

    :param Callable fn: function to defer execution of.
    :return: function result.
    :rtype: Any
    """

    raise NotImplementedError()


@reroute
def deferred_function(fn, *args, **kwargs) -> Any:
    """
    Calls given function with given arguments in a deferred way.

    :param Callable fn: function to defer.
    :param List args: list of arguments to pass to the function.
    :param Dict kwargs: keyword arguments to pass to the function.
    :return: function result.
    :rtype: Any
    """

    raise NotImplementedError()


# ======================================================================================================================
# GUI
# ======================================================================================================================


@reroute
def dpi(value: int | float = 1) -> int | float:
    """
    Returns current DPI used by DCC.

    :param int or float value: base value to apply DPI of.
    :return: DPI value.
    :rtype: int or float
    """

    raise NotImplementedError()


@reroute
def dpi_scale(value: int | float) -> int | float:
    """
    Returns current DPI scale used by DCC.

    :param int or float value: base value to apply DPI of.
    :return: DPI scale value.
    :rtype: int or float
    """

    raise NotImplementedError()


@reroute
def main_window() -> QMainWindow | None:
    """
    Returns Qt object that references to the main DCC window.

    :return: Qt main window instance.
    :rtype: QMainWindow or None
    """

    raise NotImplementedError()


@reroute
def main_menubar() -> QMenuBar | None:
    """
    Returns Qt object that references to the main DCC menubar.

    :return: Qt menu bar instance.
    :rtype: QMenuBar or None
    """

    raise NotImplementedError()


@reroute
def register_resource_path(resources_path: str):
    """
    Registers path into given DCC, so it can find specific resources (such as icons).

    :param str resources_path: path we want DCC to register.
    .note:: some DCCs such us Maya need to register resource paths to load plug icons for example.
    """

    raise NotImplementedError()


# =================================================================================================================
# SCENE
# =================================================================================================================

@reroute
def current_time() -> int:
    """
    Returns current scene time.

    :return: scene time.
    :rtype: int
    """

    raise NotImplementedError()


@reroute
def new_scene(force: bool = True, do_save: bool = True) -> bool:
    """
    Creates a new DCC scene.

    :param bool force: True if we want to save the scene without any prompt dialog
    :param bool do_save: True if you want to save the current scene before creating new scene
    :return: True if new scene operation was completed successfully; False otherwise.
    :rtype: bool
    """

    raise NotImplementedError()


@reroute
def scene_is_modified() -> bool:
    """
    Returns whether current opened DCC file has been modified by the user or not.

    :return: True if current DCC file has been modified by the user; False otherwise
    :rtype: bool
    """

    raise NotImplementedError()


@reroute
def scene_name() -> str:
    """
    Returns the name of the current scene.

    :return: scene name.
    :rtype: str
    """

    raise NotImplementedError()


@reroute
def clear_selection():
    """
    Clears current scene selection.
    """

    raise NotImplementedError()


@reroute
def fit_view(animation: bool = True):
    """
    Fits current viewport to current selection.

    :param bool animation: whether fit should be animated.
    """

    raise NotImplementedError()