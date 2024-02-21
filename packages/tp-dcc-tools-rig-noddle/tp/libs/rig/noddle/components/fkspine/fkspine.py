from __future__ import annotations

from overrides import override

import maya.cmds as cmds

from tp.maya import api
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import animcomponent, nodes
from tp.libs.rig.noddle.functions import descriptors


class FkSpineComponent(animcomponent.AnimComponent):

    ID = 'fkspine'

    @override
    def setup_inputs(self):
        descriptor = self.descriptor
        skeleton_layer_descriptor = descriptor.skeleton_layer
        joint_descriptors = skeleton_layer_descriptor.joints()
        if not joint_descriptors:
            super().setup_inputs()
            return

        super().setup_inputs()

        input_layer = self.input_layer()
        input_node = input_layer.input_node('parent')
        transform_matrix = joint_descriptors[0].transformation_matrix(scale=False)
        input_node.setWorldMatrix(transform_matrix.asMatrix())

    @override
    def setup_outputs(self, parent_node: nodes.Joint | api.DagNode):
        component_name, component_side = self.name(), self.side()
        naming = self.naming_manager()
        descriptor = self.descriptor
        output_layer_descriptor = descriptor.output_layer

        for joint_descriptor in descriptor.skeleton_layer.iterate_joints():
            joint_id = joint_descriptor.id
            output_layer_descriptor.create_output(
                name=naming.resolve(
                    'outputName',
                    {'componentName': component_name, 'side': component_side, 'id': joint_id, 'type': 'output'}),
                id=joint_id,
                parent=joint_descriptor.parent,
                rotateOrder=joint_descriptor.rotateOrder)

        super().setup_outputs(parent_node=parent_node)

        output_layer = self.output_layer()
        skeleton_layer = self.skeleton_layer()
        joints: dict[str, nodes.Joint] = {joint.id(): joint for joint in skeleton_layer.joints()}
        for i, output in enumerate(output_layer.iterate_outputs()):
            driver_joint = joints.get(output.id())
            if i == 0:
                _, constraint_nodes = api.build_constraint(
                    output,
                    drivers={'targets': (
                        (driver_joint.fullPathName(partial_name=True, include_namespace=False), driver_joint),)},
                    constraint_type='matrix', maintainOffset=False)
                output_layer.add_extra_nodes(constraint_nodes)
            else:
                driver_joint.attribute('matrix').connect(output.attribute('offsetParentMatrix'))
                output.resetTransform()

    @override(check_signature=False)
    def setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):

        component_name, component_side = self.name(), self.side()
        naming = self.naming_manager()
        # rig_layer = self.rig_layer()
        # rig_layer_root = rig_layer.root_transform()
        # control_panel = self.control_panel()
        # joint_descriptors = self.descriptor.skeleton_layer.joints()
        #
        # cog_control_name = naming.resolve(
        #     'controlName', {'componentName': component_name, 'side': component_side, 'id': 'cog', 'type': 'control'})
        # cog_control = rig_layer.create_control(
        #     name=cog_control_name, id='cog', shape='spine_cog',
        #     translate=joint_descriptors[0].translate, rotateOrder=joint_descriptors[0].rotateOrder, color=self.color(),
        #     selection_child_highlighting=self.configuration.selection_child_highlighting,
        #     srts=[{'id': 'cog', 'name': '_'.join([cog_control_name, 'srt'])}])
        #
        # gimbal_control_name = naming.resolve(
        #     'controlName', {'componentName': component_name, 'side': component_side, 'id': 'gimbal', 'type': 'control'})
        # gimbal_control = rig_layer.create_control(
        #     name=gimbal_control_name, id='gimbal', shape='spine_gimbal', translate=joint_descriptors[0].translate,
        #     color=[0.0, 1.0, 0.0], selection_child_highlighting=self.configuration.selection_child_highlighting,
        #     srts=[{'id': 'cog', 'name': '_'.join([cog_control_name, 'srt'])}])

        # Build FK controls
        # created_fk_controls: dict[str, nodes.ControlNode] = {}
        # for joint_descriptor in self.descriptor.skeleton_layer.iterate_joints():
        #     joint_parent = joint_descriptor.parent
        #     if not joint_parent:
        #         control_parent = rig_layer_root
        #     else:
        #         control_parent = rig_layer.control(joint_parent)
        #
        #     control_name = naming.resolve(
        #         'controlName', {'componentName': component_name, 'side': component_side, 'id': joint_descriptor.id,
        #                         'type': 'control'})
        #     fk_control = rig_layer.create_control(
        #         name=control_name, id=joint_descriptor.id, shape='circle_up_arrow',
        #         translate=joint_descriptor.translate, rotate=joint_descriptor.rotate,
        #         rotateOrder=joint_descriptor.rotateOrder, color=self.color(),
        #         selection_child_highlighting=self.configuration.selection_child_highlighting,
        #         parent=control_parent, srts=[{'id': joint_descriptor.id, 'name': '_'.join([control_name, 'srt'])}])
        #     created_fk_controls[joint_descriptor.id] = fk_control
        #
        # visibility_switch_plug = control_parent.attribute('cogGimbalVis')

        # scale_dict = {
        #     cog_control: 0.5,
        #     gimbal_control: 0.4
        # }
        # self.scale_controls(scale_dict)