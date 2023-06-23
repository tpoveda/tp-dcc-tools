from tp.core import log, dcc
from tp.preferences.interfaces import crit

if dcc.is_maya():
	from tp.libs.rig.crit.maya import plugin as crit_plugin


logger = log.tpLogger


def startup(package_manager):
	"""
	This function is automatically called by tpDcc packages Manager when environment setup is initialized.

	:param package_manager: current tpDcc packages Manager instance.
	:return: tpDccPackagesManager
	"""

	logger.info('Loading CRIT rigging package...')
	crit_interface = crit.crit_interface()
	crit_interface.upgrade_preferences()
	crit_interface.upgrade_assets()

	if dcc.is_maya():
		crit_plugin.load()


def shutdown(package_manager):
	"""
	Shutdown function that is called during tpDcc framework shutdown.
	This function is called at the end of tpDcc framework shutdown.
	"""

	logger.info('Shutting down CRIT rigging package...')

	if dcc.is_maya():
		crit_plugin.unload()