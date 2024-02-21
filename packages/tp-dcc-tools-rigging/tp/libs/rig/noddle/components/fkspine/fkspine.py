from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import animcomponent, nodes


class FkSpineComponent(animcomponent.AnimComponent):

    ID = 'fkspine'

    @staticmethod
    def fk_guide_id_for_number(number: int) -> str:
        return f'fk{str(number).zfill(2)}'

    @override
    def id_mapping(self) -> dict:
        descriptor = self.descriptor
        skeleton_layer_descriptor = descriptor.skeleton_layer
        joint_descriptors = skeleton_layer_descriptor.joints()
        joint_count = len(joint_descriptors)

        skeleton_ids: dict[str, str] = {'pelvis': 'pelvis'}
        input_ids: dict[str, str] = {}
        output_ids: dict[str, str] = {}
        rig_layer_ids: dict[str, str] = {}
        for i in range(1, joint_count):
            joint_id = joint_descriptors[i].id
            fk_joint_id = self.fk_guide_id_for_number(i)
            skeleton_ids[fk_joint_id] = joint_id
            input_ids[fk_joint_id] = joint_id
            output_ids[fk_joint_id] = joint_id
            rig_layer_ids[fk_joint_id] = fk_joint_id

        return {
            consts.SKELETON_LAYER_TYPE: skeleton_ids,
            consts.INPUT_LAYER_TYPE: input_ids,
            consts.OUTPUT_LAYER_TYPE: output_ids,
            consts.RIG_LAYER_TYPE: rig_layer_ids,
        }

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
        rig_layer = self.rig_layer()
        rig_layer_root = rig_layer.root_transform()
        control_panel = self.control_panel()
        joint_descriptors = self.descriptor.skeleton_layer.joints()

        cog_control_name = naming.resolve(
            'controlName', {'componentName': component_name, 'side': component_side, 'id': 'cog', 'type': 'control'})
        cog_control = rig_layer.create_control(
            name=cog_control_name, id='cog', shape='spine_cog',
            translate=joint_descriptors[0].translate, rotateOrder=joint_descriptors[0].rotateOrder, color=self.color(),
            selection_child_highlighting=self.configuration.selection_child_highlighting,
            srts=[{'id': 'cog', 'name': '_'.join([cog_control_name, 'srt'])}])
        rig_layer.create_srt_buffer('root', '_'.join([cog_control.name(False), 'srt']))

        gimbal_control_name = naming.resolve(
            'controlName', {'componentName': component_name, 'side': component_side, 'id': 'gimbal', 'type': 'control'})
        gimbal_control = rig_layer.create_control(
            name=gimbal_control_name, id='gimbal', shape='spine_gimbal', translate=joint_descriptors[0].translate,
            color=[0.0, 1.0, 0.0], selection_child_highlighting=self.configuration.selection_child_highlighting,
            srts=[{'id': 'cog', 'name': '_'.join([cog_control_name, 'srt'])}], parent='cog')
        rig_layer.create_srt_buffer('root', '_'.join([gimbal_control.name(False), 'srt']))

        hips_control_name = naming.resolve(
            'controlName', {'componentName': component_name, 'side': component_side, 'id': 'hips', 'type': 'control'})
        hips_control = rig_layer.create_control(
            name=hips_control_name, id='hips', shape='circle_up_arrow', translate=joint_descriptors[0].translate,
            color=[0.0, 1.0, 0.0], selection_child_highlighting=self.configuration.selection_child_highlighting,
            srts=[{'id': 'cog', 'name': '_'.join([cog_control_name, 'srt'])}], parent='gimbal')
        hips_control.setRotation((0.0, 0.0, 180.0))
        rig_layer.create_srt_buffer('root', '_'.join([hips_control.name(False), 'srt']))

        # Build FK controls
        created_fk_controls: dict[str, nodes.ControlNode] = {}
        for i in range(1, len(joint_descriptors)):
            joint_descriptor = joint_descriptors[i]
            joint_parent = joint_descriptor.parent
            if not joint_parent:
                control_parent = rig_layer_root
            elif joint_parent == 'pelvis':
                control_parent = gimbal_control
            else:
                control_parent = rig_layer.control(self.fk_guide_id_for_number(i - 1))

            control_name = naming.resolve(
                'controlName', {'componentName': component_name, 'side': component_side, 'id': joint_descriptor.id,
                                'type': 'control'})
            fk_control_id = self.fk_guide_id_for_number(i)
            fk_control = rig_layer.create_control(
                name=control_name, id=fk_control_id, shape='circle_up_arrow',
                translate=joint_descriptor.translate, rotate=joint_descriptor.rotate,
                rotateOrder=joint_descriptor.rotateOrder, color=[0.0, 1.0, 0.0], orient_axis='y',
                selection_child_highlighting=self.configuration.selection_child_highlighting,
                parent=control_parent, srts=[{'id': joint_descriptor.id, 'name': '_'.join([control_name, 'srt'])}])
        #     fk_control.rotate_shape((180.0, 0.0, 0.0))
            created_fk_controls[joint_descriptor.id] = fk_control
        #
        # visibility_switch_plug = control_panel.attribute('cogGimbalVis')
        #
        scale_dict = {
            cog_control: 0.5,
            gimbal_control: 0.4,
            hips_control: 0.35
        }
        for fk_control in created_fk_controls.values():
            scale_dict[fk_control] = 0.35
        self.scale_controls(scale_dict)

        # hips_control.move_shapes(api.Vector(0.0, -6.0, 0.0))

    def post_setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        super().post_setup_rig(parent_node=parent_node)

        input_layer = self.input_layer()
        skeleton_layer = self.skeleton_layer()
        rig_layer = self.rig_layer()
        root_input_node = input_layer.input_node('parent')
        joints: dict[str, nodes.Joint] = {joint.id(): joint for joint in skeleton_layer.iterate_joints()}
        controls: dict[str, nodes.ControlNode] = {control.id(): control for control in rig_layer.iterate_controls()}
        id_mapping = self.id_mapping()[consts.SKELETON_LAYER_TYPE]
        extras: list[api.DGNode] = []

        pelvis_joint = joints['pelvis']
        hips_control = controls['hips']
        parent_constraint, _ = api.build_constraint(
            pelvis_joint, drivers={'targets': (('hips', hips_control),)},
            constraint_type='parent', maintainOffset=True, track=False)
        scale_constraint, _ = api.build_constraint(
            pelvis_joint, drivers={'targets': (('hips', hips_control),)},
            constraint_type='scale', maintainOffset=True, track=False)
        extras.extend(
            list(parent_constraint.iterate_utility_nodes()) + list(scale_constraint.iterate_utility_nodes()))

        for control_id, control in controls.items():
            if not control_id.startswith('fk'):
                continue
            joint_id = id_mapping[control_id]
            joint = joints[joint_id]
            parent_constraint, _ = api.build_constraint(
                joint, drivers={'targets': ((control_id, control),)},
                constraint_type='parent', maintainOffset=True, track=False)
            scale_constraint, _ = api.build_constraint(
                joint, drivers={'targets': ((control_id, control),)},
                constraint_type='scale', maintainOffset=True, track=False)
            extras.extend(
                list(parent_constraint.iterate_utility_nodes()) + list(scale_constraint.iterate_utility_nodes()))

        _, matrix_util_nodes = api.build_constraint(
            controls['cog'].srt(),
            drivers={'targets': (('cog', root_input_node),)}, constraint_type='matrix', maintainOffset=True, track=False
        )
        extras.extend(matrix_util_nodes)

        rig_layer.add_extra_nodes(extras)
