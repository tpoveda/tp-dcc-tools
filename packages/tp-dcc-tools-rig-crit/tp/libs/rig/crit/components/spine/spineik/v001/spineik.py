from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.core import component
from tp.libs.rig.crit.meta import nodes as meta_nodes


class SpineIkComponent(component.Component):

    ID = 'spineIk'

    _JOINT_NUM_PREFIX = 'bind'
    _FK_NUM_PREFIX = 'fk'
    _IK_SPLINE_NUM_PREFIX = 'spineIk'
    _CONTROL_IDS = ('cog', 'hipSwing', 'cogGimbal', 'hips', 'ctrl02', 'tweaker00', 'tweaker01', 'tweaker02')

    @classmethod
    def joint_id_for_number(cls, index: int) -> str:
        return cls._JOINT_NUM_PREFIX + str(index).zfill(2)

    @classmethod
    def fk_guide_id_for_number(cls, index: int) -> str:
        return cls._FK_NUM_PREFIX + str(index).zfill(2)

    @override
    def id_mapping(self) -> dict:

        guide_layer = self.descriptor.guide_layer
        bind_joint_count = guide_layer.guide_setting('jointCount').value

        skeleton_ids: dict[str, str] = {}
        input_ids: dict[str, str] = {}
        output_ids: dict[str, str] = {}
        rig_layer_ids = {i: i for i in self._CONTROL_IDS}

        for i in range(bind_joint_count):
            joint_id = self.joint_id_for_number(i)
            skeleton_ids[joint_id] = joint_id
            output_ids[joint_id] = joint_id

        for i in range(guide_layer.guide_setting('fkCtrlCount').value):
            control_id = self.fk_guide_id_for_number(i)
            rig_layer_ids[control_id] = control_id

        return {
            crit.consts.SKELETON_LAYER_TYPE: skeleton_ids,
            crit.consts.INPUT_LAYER_TYPE: input_ids,
            crit.consts.OUTPUT_LAYER_TYPE: output_ids,
            crit.consts.RIG_LAYER_TYPE: rig_layer_ids
        }

    @override(check_signature=False)
    def setup_rig(self, parent_node: meta_nodes.Joint | api.DagNode | None = None):

        descriptor = self.descriptor
        guide_layer_descriptor = descriptor.guide_layer
        naming = self.naming_manager()
        component_name, component_side = self.name(), self.side()
        input_layer = self.input_layer()
        skeleton_layer = self.skeleton_layer()
        rig_layer = self.rig_layer()
        control_panel = self.control_panel()
        highlighting = self.configuration.selection_child_highlighting
        rig_layer_root = rig_layer.root_transform()

        bind_joints = list(skeleton_layer.iterate_joints())
        bind_joints_map = {i.id() for i in bind_joints}



