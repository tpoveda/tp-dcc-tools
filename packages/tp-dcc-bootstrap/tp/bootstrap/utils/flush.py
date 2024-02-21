#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions that allows to reload tp-dcc-tools framework easily
"""

import os
import gc
import sys
import inspect
import logging

logger = logging.getLogger(__name__)


def flush_modules_in_directory(directory):
	"""
	Flushes all modules that live under the given directory.

	:param str directory: name of the top most directory to search under.
	:return: list containing tuples of the name and path of the reloaded modules.
	:rtype: list[tuple[str, str]]
	"""

	module_paths = list()
	for name, module in list(sys.modules.items()):
		if module is None:
			del sys.modules[name]
			continue
		try:
			module_dir_path = os.path.realpath(os.path.dirname(inspect.getfile(module)))
			if module_dir_path.startswith(directory):
				module_paths.append((name, inspect.getfile(sys.modules[name])))
				del sys.modules[name]
				logger.debug(f'Unloaded module: {name}')
		except TypeError:
			continue

	# Force garbage collection
	gc.collect()

	return module_paths


def reload_modules():
	"""
	Reloads all tp-dcc-tools modules from sys.modules

	..info:: this makes trivial to make changes to tp-dcc-tools code and avoids to use complex reload of the
		dependencies.
	"""

	bases = os.environ.get('TPDCC_BASE_PATHS', '').split(os.pathsep)
	[flush_modules_in_directory(base) for base in bases if os.path.exists(base)]


def reload_tp_namespace():
	"""
	Reloads tp namespace from sys.modules.
	"""

	modules_to_reload = ('tp',)
	for k in sys.modules.copy().keys():
		found = False
		for mod in modules_to_reload:
			if mod == k:
				del sys.modules[mod]
				found = True
				break
		if found:
			continue
		if k.startswith(modules_to_reload):
			del sys.modules[k]
