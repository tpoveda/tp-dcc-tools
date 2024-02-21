from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.noddle.core import animcomponent, nodes


class WorldComponent(animcomponent.AnimComponent):

    ID = 'world'

    @override(check_signature=False)
    def setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        input_layer = self.input_layer()
        skeleton_layer = self.skeleton_layer()
        rig_layer = self.rig_layer()
        naming = self.naming_manager()
        component_name, component_side = self.name(), self.side()

        root_control_name = naming.resolve(
            'controlName',
            {'componentName': component_name, 'side': component_side, 'id': 'root', 'type': 'control'})
        root_control = rig_layer.create_control(
            name=root_control_name, id='root', shape='world', not_locked_attributes='trs',
            color=self.color(), orient_axis='y')
        root_control.addAttribute('Scale', value=1.0, default=1.0, type=api.kMFnNumericFloat, keyable=True)
        root_control.Scale.connect(root_control.scaleX)
        root_control.Scale.connect(root_control.scaleY)
        root_control.Scale.connect(root_control.scaleZ)
        if self.rig.clamped_size() > 0.0:
            root_control.scale_shapes(self.rig.clamped_size())
        root_control.lock_attributes(exclude_attributes=['t', 'r'])

        srt = rig_layer.create_srt_buffer('root', '_'.join([root_control.name(False), 'srt']))
        input_node = input_layer.input_node('root')
        if input_node is not None:
            input_node.attribute('worldMatrix')[0].connect(srt.offsetParentMatrix)
            srt.resetTransform()

        extras: list[api.DGNode] = []
        root_joint = skeleton_layer.joints()[0]
        parent_constraint, _ = api.build_constraint(
            root_joint, drivers={'targets': (
                (root_control.fullPathName(partial_name=True, include_namespace=False), root_control),)},
            constraint_type='parent', maintainOffset=True, track=False)
        scale_constraint, _ = api.build_constraint(
            root_joint, drivers={'targets': (
                (root_control.fullPathName(partial_name=True, include_namespace=False), root_control),)},
            constraint_type='scale', maintainOffset=True, track=False)
        extras.extend(
            list(parent_constraint.iterate_utility_nodes()) + list(scale_constraint.iterate_utility_nodes()))
        rig_layer.add_extra_nodes(extras)

    @override
    def post_setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        output_layer = self.output_layer()
        rig_layer = self.rig_layer()

        outputs = output_layer.find_output_nodes('root',)
        controls = rig_layer.find_controls('root',)
        for i, (output, control) in enumerate(zip(outputs, controls)):
            if control is None:
                continue
            _, constraint_nodes = api.build_constraint(output, drivers={
                'targets': ((control.fullPathName(partial_name=True, include_namespace=False), control),)},
                constraint_type='matrix', maintainOffset=False
            )
            rig_layer.add_extra_nodes(constraint_nodes)

        super().post_setup_rig(parent_node=parent_node)
