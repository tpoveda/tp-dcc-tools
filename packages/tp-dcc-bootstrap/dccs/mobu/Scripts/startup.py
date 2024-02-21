#! /usr/bin/env python
# -*- coding: utf-8 -*-

# tpDcc Tools startup script for Autodesk MotionBuilder

import os
import sys
import json

try:
    from PySide.QtGui import QApplication, QMenuBar
except ImportError:
    from PySide2.QtWidgets import QApplication, QMenuBar

from pyfbsdk import FBSystem


fbsys = FBSystem()


def get_main_qt_window():
    parent = QApplication.activeWindow()
    grand_parent = parent
    while grand_parent is not None:
        parent = grand_parent
        grand_parent = parent.parent()

    return parent


def try_init_tpdcc(*args, **kwargs):
    main_window = get_main_qt_window()
    if not main_window:
        return
    parent_menubar = main_window.findChild(QMenuBar)
    if not parent_menubar:
        return

    init_tpdcc()


def init_tpdcc():

    import tp.bootstrap
    tp.bootstrap.init()

    fbsys.OnUIIdle.Remove(try_init_tpdcc)


root_path = os.getenv('TPDCC_TOOLS_ROOT', '')
root_path = os.path.abspath(root_path)

startup_file_path = os.getenv('TPDCC_BOOTSTRAP_FILE', '')
if not root_path:
    raise ValueError('TPDCC_TOOLS_ROOT path is not defined')
elif not os.path.isdir(root_path):
    raise ValueError(f'Failed to find valid TPDCC_TOOLS_ROOT folder: {root_path}')
if root_path not in sys.path:
    sys.path.append(root_path)

prefs = dict()
if startup_file_path and os.path.isfile(startup_file_path):
    try:
        with open(startup_file_path, 'r') as fh:
            prefs = json.load(fh)
    except ValueError as exc:
        print(f'Failed to load tpDcc Tools Framework for Autodesk Maya: \n\t{exc}')


if prefs.get('autoload', False):
    # We cannot load tpDCC framework during MoBu startup because it will crash when trying to access Qt related data
    # such as for example QMainWindow or QMenuBar (which we use for tpDCC menu creation). We call init_tpdcc function
    # during OnUIIdle callback until both QMainWindow and QMenuBar are available. On that point we can freely load
    # tpDCC framework. A bit hacky, but it works!
    fbsys.OnUIIdle.Add(try_init_tpdcc)
