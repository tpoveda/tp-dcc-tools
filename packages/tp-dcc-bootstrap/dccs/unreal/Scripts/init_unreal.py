#! /usr/bin/env python
# -*- coding: utf-8 -*-

# tpDcc Tools startup script for Epic Games Unreal Engine

import os
import sys
import json

import unreal

from PySide2.QtWidgets import QApplication

APP = QApplication.instance()
if not APP:
    APP = QApplication(sys.argv)


def init_tpdcc():
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
            unreal.log_error(f'Failed to load tpDcc Tools Framework for Epic Games Unreal Engine: \n\t{exc}')
            return False

    if prefs.get('autoload', False):
        unreal.log('Initializing tpDcc Tools framework, please wait!')
        unreal.log(f'tpDcc Tools framework Root Path: "{root_path}"')
        import tp.bootstrap
        tp.bootstrap.init()
        unreal.log("tpDcc Tools framework initialized successfully!")


if __name__ == '__main__':
    init_tpdcc()
