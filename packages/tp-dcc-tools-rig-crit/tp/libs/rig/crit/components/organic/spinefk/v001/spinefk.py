from __future__ import annotations

from tp.maya import api
from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.core import component


class SpineFkComponent(component.Component):

	ID = 'spinefk'
	DESCRIPTION = 'Spine FK component'

	def setup_rig(self, parent_node: crit.Joint | api.DagNode | None = None):
		pass
