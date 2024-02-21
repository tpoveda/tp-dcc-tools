from __future__ import annotations

from tp.common import plugin


class BaseBuildScript(plugin.PluginFactory):

	ID = ''

	def __init__(self):
		super(BaseBuildScript, self).__init__()

		self._rig = None
