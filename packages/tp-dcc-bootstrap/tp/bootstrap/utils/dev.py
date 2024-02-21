#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that bootstrap development code
"""

import os
import sys

from tp.bootstrap import log

logger = log.bootstrapLogger

def reload_modules():
    """
    Function that forces the reloading of all tpDcc related modules
    """

    modules_to_reload = ('tp',)
    for k in sys.modules.copy().keys():
        found = False
        for mod in modules_to_reload:
            if 'bootstrap' in mod:
                continue
            if mod == k:
                del sys.modules[mod]
                found = True
                break
        if found:
            continue
        if k.startswith(modules_to_reload):
            if 'bootstrap' in k:
                continue
            del sys.modules[k]


def startup(project=None, force_new_scene=True, dev=None):

    # register environment variables
    os.environ['TPDCC_ENV_DEV'] = 'True'
    os.environ['TPDCC_TOOLS_ROOT'] = os.environ.get(
        'TPDCC_TOOLS_ROOT', None) or r'E:\tools\dev\tp-dcc\packages\tp-dcc-bootstrap'

    # make sure to update sys.path so tpDcc Tools package manager an dependencies are available
    root_path = os.environ['TPDCC_TOOLS_ROOT']
    if os.path.isdir(root_path) and root_path not in sys.path:
        sys.path.append(root_path)
    dependencies_path = r'E:\tools\dev\tp-dcc\venv\Lib\site-packages'
    if os.path.isdir(dependencies_path) and dependencies_path not in sys.path:
        sys.path.append(dependencies_path)

    shutdown(force_new_scene=force_new_scene)

    import tp.bootstrap

    if not project:
        logger.warning('No tpDcc Project defined!')

    # register environment variables after shutdown
    os.environ['TPDCC_PROJECT'] = ''
    os.environ['TPDCC_DEV'] = 'False' if not dev else 'True'

    # load framework
    import tp.bootstrap
    tp.bootstrap.init()


def shutdown(force_new_scene=True):

    try:
        if force_new_scene:
            from tp.core import dcc
            dcc.new_scene(force=True)
    except Exception:
        pass

    # cleanup framework
    import tp.bootstrap
    tp.bootstrap.shutdown()
