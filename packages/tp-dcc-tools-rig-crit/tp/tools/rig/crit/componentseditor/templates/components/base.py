from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.core import component


class Component(component.Component):

	ID = None
	PRIORITY = 5

	@override
	def setup_rig(self, parent_node: crit.Joint | api.DagNode | None = None):
		pass
