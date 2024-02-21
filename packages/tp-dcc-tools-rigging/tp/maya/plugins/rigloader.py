#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tp-dcc-tools-rig Maya plugins loader functions
"""

from __future__ import print_function, division, absolute_import

import os
import inspect

from tp.core import log, dcc
from tp.common.python import osplatform, path
from tp.maya.cmds import helpers

logger = log.rigLogger


def get_root_path():
	return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def load_all_plugins(reload=False, debug=False):
	load_base_loc_plugin(reload=reload, debug=debug)


def unload_all_plugins():
	unload_base_loc_plugin()


def load_base_loc_plugin(reload=False, debug=False):
	helpers.add_trusted_plugin_location_path(get_root_path())
	plugin_name = 'baseLoc_maya{}.mll'.format(dcc.version())
	plugin_path = path.join_path(get_root_path(), 'baseLoc', 'plug-in', dcc.version(), 'Debug' if debug else 'Release')
	return _load_plugin(plugin_name, plugin_path, reload=reload, add_to_trusted_paths=False)


def unload_base_loc_plugin():
	plugin_name = 'baseLoc_maya{}.mll'.format(dcc.version())
	return _unload_plugin(plugin_name)


def _load_plugin(plugin_name, plugin_path=None, reload=False, add_to_trusted_paths=True):
	logger.info('Loading Maya Plugin: {} : {}'.format(plugin_name, plugin_path))
	try:
		if path.is_dir(plugin_path):
			osplatform.append_path_env_var('MAYA_PLUG_IN_PATH', plugin_path)
		if not helpers.is_plugin_loaded(plugin_name):
			helpers.load_plugin(plugin_name)
		elif helpers.is_plugin_loaded(plugin_name) and reload:
			helpers.unload_plugin(os.path.basename(plugin_name))
			helpers.load_plugin(plugin_name)
		if path.is_dir(plugin_path) and add_to_trusted_paths:
			helpers.add_trusted_plugin_location_path(plugin_path)
		return True
	except Exception as exc:
		logger.error('Failed to {} plugin: {}'.format(plugin_name, exc))

	return False


def _unload_plugin(plugin_name):
	logger.info('Unloading Maya Plugin: {} : {}'.format(plugin_name, plugin_name))
	try:
		if helpers.is_plugin_loaded(plugin_name):
			helpers.unload_plugin(os.path.basename(plugin_name))
		return True
	except Exception as exc:
		logger.error('Failed to unload {} plugin! {}'.format(plugin_name, exc))

	return False
