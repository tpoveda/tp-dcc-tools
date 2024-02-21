#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tp-dcc-tools framework Python entry point.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if os.getenv('TPDCC_LOG_LEVEL', 'INFO') == 'DEBUG' else logging.INFO)


def install(root_directory, args):
	"""
	Install tp-dcc-tools framework into the current environment.

	:param str root_directory: root directory.
	:param tuple args: tuple of extra arguments.
	:return:
	"""

	cmd_dir = os.path.abspath(os.path.dirname(root_directory))
	python_folder = os.path.join(cmd_dir, 'python')
	if python_folder not in sys.path:
		logger.debug(f'Installing tp-dcc-tools framework Python path into current environemnt: {python_folder}')
		sys.path.append(python_folder)

	from tp.bootstrap.utils import env
	env.add_to_env('PYTHONPATH', [python_folder])

	from tp.bootstrap import api
	package_manager = api.package_manager_from_path(cmd_dir)
	api.set_current_package_manager(package_manager)

	return api.run_command(package_manager, args)


def run(argv, _exit=True):
	"""
	Run commands based on given parsed arguments.
	"""

	root = os.path.dirname(argv[0])
	return_code = install(root, argv[1:])
	if _exit:
		sys.exit(return_code or 0)


if __name__ == '__main__':
	run(sys.argv)
