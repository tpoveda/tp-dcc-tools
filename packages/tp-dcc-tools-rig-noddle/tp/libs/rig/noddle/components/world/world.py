from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.noddle.core import animcomponent, nodes


class WorldComponent(animcomponent.AnimComponent):

    ID = 'world'

    def setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        print('Building world component ...')