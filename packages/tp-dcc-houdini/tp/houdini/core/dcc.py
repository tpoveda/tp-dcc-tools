#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains DCC functionality for 3ds Max
"""

import hou
import hdefereval

from Qt.QtWidgets import QMessageBox

from tp.core import dcc
from tp.houdini.core import helpers, gui


def get_name():
    """
    Returns the name of the DCC
    :return: str
    """

    return dcc.Dccs.Houdini


def get_extensions():
    """
    Returns supported extensions of the DCC
    :return: list(str)
    """

    return ['.hip', '.hiplc', '.hipnc', '.hip*']


def get_dpi(value=1):
    """
    Returns current DPI used by DCC
    :param value: float
    :return: float
    """

    return 1.0


def get_dpi_scale(value):
    """
    Returns current DPI scale used by DCC
    :return: float
    """

    return 1.0


def get_version():
    """
    Returns version of the DCC
    :return: int
    """

    return helpers.get_houdini_version(as_string=False)


def get_version_name():
    """
    Returns version of the DCC
    :return: str
    """

    return helpers.get_houdini_version(as_string=True)


def get_main_window():
    """
    Returns Qt object that references to the main DCC window
    :return:
    """

    return gui.get_houdini_window()


def execute_deferred(fn):
    """
    Executes given function in deferred mode
    """

    hdefereval.executeDeferred(fn)


def node_exists(node):
    """
    Returns whether given object exists or not
    :return: bool
    """

    hou_node = hou.node(node)
    if hou_node:
        return True

    return False


def node_name(node):
    """
    Returns the name of the given node
    :param node: str
    :return: str
    """

    return node.name()


def selected_nodes(full_path=True, **kwargs):
    """
    Returns a list of selected nodes
    :param full_path: bool
    :return: list<hou.Node>
    """

    return hou.selectedNodes(True)


def node_short_name(node, **kwargs):
    """
    Returns short name of the given node
    :param node: str
    :return: str
    """

    return node


def scene_name():
    """
    Returns the name of the current scene
    :return: str
    """

    return hou.hipFile.name()


def scene_path():
    """
    Returns the path of the current scene
    :return: str
    """

    return hou.hipFile.path()


def confirm_dialog(title, message, button=None, cancel_button=None, default_button=None, dismiss_string=None):
    """
    Shows DCC confirm dialog
    :param title:
    :param message:
    :param button:
    :param cancel_button:
    :param default_button:
    :param dismiss_string:
    :return:
    """

    return QMessageBox.question(dcc.main_window(), title, message)


def warning(message):
    """
    Prints a warning message
    :param message: str
    :return:
    """

    QMessageBox.warning(dcc.main_window(), 'Warning', message)


def shelf_exists(shelf_name):
    """
    Returns whether given shelf already exists or not
    :param shelf_name: str
    :return: bool
    """

    return gui.shelf_exists(shelf_name=shelf_name)


def create_shelf(shelf_name, shelf_label=None):
    """
    Creates a new shelf with the given name
    :param shelf_name: str
    :param shelf_label: str
    """

    return gui.create_shelf(shelf_name=shelf_name, shelf_label=shelf_label)


def select_file_dialog(title, start_directory=None, pattern=None):
    """
    Shows select file dialog
    :param title: str
    :param start_directory: str
    :param pattern: str
    :return: str
    """

    return hou.ui.selectFile(start_directory=start_directory, title=title, pattern=pattern)


def get_current_frame():
    """
    Returns current frame set in time slider
    :return: int
    """

    return gui.get_current_frame()


def get_time_slider_range():
    """
    Return the time range from Maya time slider
    :return: list<int, int>
    """

    return gui.get_time_slider_range()
