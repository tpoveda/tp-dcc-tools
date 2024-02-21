import os

from tp.common.python import osplatform, path
from tp.maya.cmds import helpers


def load(reload=False):
	"""
	Loads CRIT Maya plugin

	:param bool reload: whether to reload plugin.
	"""

	root_path = path.clean_path(path.dirname(os.path.abspath(__file__)))
	plugin_path = path.join_path(root_path, 'crit.py')

	osplatform.append_path_env_var('MAYA_PLUG_IN_PATH', plugin_path)

	if not helpers.is_plugin_loaded(plugin_path):
		helpers.load_plugin(plugin_path)
	elif helpers.is_plugin_loaded(plugin_path) and reload:
		helpers.unload_plugin(path.basename(plugin_path))
		helpers.load_plugin(plugin_path)

	helpers.add_trusted_plugin_location_path(plugin_path)

	return True


def unload():
	"""
	Unloads CRIT Maya plugin
	"""

	plugin_name = 'crit.py'
	if helpers.is_plugin_loaded(plugin_name):
		helpers.unload_plugin(plugin_name)
		return True

	return False
