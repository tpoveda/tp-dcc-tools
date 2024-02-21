"""
Module that contains tp-dcc-tools-rig-crit startup/shutdown functionality
"""

from __future__ import annotations

import os
import typing
import inspect

from tp.core import log, dcc
from tp.common.python import path
from tp.preferences.interfaces import crit
from tp.common.resources import api as resources

if dcc.is_maya():
	from tp.libs.rig.crit import plugin as crit_plugin

if typing.TYPE_CHECKING:
	from tp.bootstrap.core.package import Package


logger = log.tpLogger


def startup(package: Package):
	"""
	This function is automatically called by tp-dcc packages Manager when environment setup is initialized.

	:param package: package instance that is going to be startup.
	"""

	logger.info('Loading CRIT rigging package...')

	# Register resources
	root_file_path = path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	resources_path = path.join_path(os.path.dirname(root_file_path), 'resources')
	resources.register_resource(resources_path)

	# Update CRIT preferences
	crit_interface = crit.crit_interface()
	crit_interface.upgrade_preferences()
	crit_interface.upgrade_assets()

	# Load CRIT Maya plugins
	if dcc.is_maya():
		crit_plugin.load()


def shutdown(package: Package):
	"""
	Shutdown function that is called during tp-dcc framework shutdown.
	This function is called at the end of tp-dcc framework shutdown.

:param package: package instance that is going to be shutdown.
	"""

	logger.info('Shutting down CRIT rigging package...')

	if dcc.is_maya():
		crit_plugin.unload()
