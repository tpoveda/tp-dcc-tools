#! /usr/bin/env python
# -*- coding: utf-8 -*-

# tpDcc Tools startup script for Autodesk Maya

import os
import sys
import json

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya


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
            OpenMaya.MGlobal.displayError(f'Failed to load tpDcc Tools Framework for Autodesk Maya: \n\t{exc}')
            return False

    if prefs.get('autoload', False):
        OpenMaya.MGlobal.displayInfo('Initializing tpDcc Tools framework, please wait!')
        OpenMaya.MGlobal.displayInfo(f'tpDcc Tools framework Root Path: "{root_path}"')
        import tp.bootstrap
        tp.bootstrap.init()
        OpenMaya.MGlobal.displayInfo("tpDcc Tools framework initialized successfully!")


if __name__ == '__main__':
    cmds.evalDeferred(init_tpdcc)
