from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.core import component
from tp.libs.rig.crit.meta import nodes as meta_nodes


class WorldComponent(component.Component):

    ID = 'world'
    DESCRIPTION = 'Master component for all CRIT rigs'

    @override
    def id_mapping(self) -> dict:
        return {
            crit.consts.SKELETON_LAYER_TYPE: {
                'rootMotion': 'world',
                'offset': 'world',
                'world': 'world'
            },
            crit.consts.INPUT_LAYER_TYPE: {
                'world': 'world'
            },
            crit.consts.OUTPUT_LAYER_TYPE: {
                'rootMotion': 'rootMotion',
                'offset': 'offset',
                'world': 'world'
            },
            crit.consts.RIG_LAYER_TYPE: {
                'rootMotion': 'rootMotion',
                'offset': 'offset',
                'world': 'world'
            }
        }

    @override
    def set_skeleton_naming(self, naming_manager: crit.NameManager, mod: api.DGModifier):
        component_name, component_side = self.name(), self.side()
        skeleton_layer = self.skeleton_layer()
        name = naming_manager.resolve(
            'skinJointName', {'componentName': component_name, 'side': component_side, 'id': 'root', 'type': 'joint'})
        root_joint = skeleton_layer.joint('world')
        if root_joint is not None:
            root_joint.rename(name, mod=mod, apply=False)

    @override
    def space_switch_ui_data(self) -> dict:
        drivers = []
        guide_layer_descriptor = self.descriptor.guide_layer
        for guide_descriptor in guide_layer_descriptor.iterate_guides(include_root=False):
            drivers.append(crit.SpaceSwitchUIDriver(
                id=crit.path_as_descriptor_expression(
                    ('self', 'rigLayer', guide_descriptor.id)), label=guide_descriptor.name))

        return {'driven': [], 'drivers': drivers}

    @override
    def post_setup_guide(self):
        super().post_setup_guide()

        guide_layer = self.guide_layer()
        guide_settings = guide_layer.guide_settings()
        god_node_guide, offset_guide, root_motion_guide = guide_layer.find_guides('world', 'offset', 'rootMotion')

        for shape in god_node_guide.iterateShapes():
            vis = shape.visibility
            if vis.isDestination or vis.isLocked:
                continue
            guide_settings.worldVis.connect(vis)
        for shape in offset_guide.iterateShapes():
            vis = shape.visibility
            if vis.isDestination or vis.isLocked:
                continue
            guide_settings.offsetVis.connect(vis)
        for shape in root_motion_guide.iterateShapes():
            vis = shape.visibility
            if vis.isDestination or vis.isLocked:
                continue
            guide_settings.rootMotionVis.connect(vis)

    @override
    def setup_inputs(self):
        super().setup_inputs()

        descriptor = self.descriptor
        input_layer = self.input_layer()
        god_node_guide_descriptor = descriptor.guide_layer.guide('world')
        input_node = input_layer.input_node(god_node_guide_descriptor.id)
        transform_matrix = god_node_guide_descriptor.transformation_matrix(scale=False)
        input_node.setWorldMatrix(transform_matrix.asMatrix())

    def setup_outputs(self, parent_node: crit.Joint | api.DagNode):
        descriptor = self.descriptor
        guide_layer = descriptor.guide_layer
        output_layer_descriptor = descriptor.output_layer
        requires_joint = guide_layer.guide_setting('rootJoint').value
        if not requires_joint:
            output_layer_descriptor.delete_outputs('rootMotion')
            output_layer = self.output_layer()
            if output_layer is not None:
                output_layer.delete_output('rootMotion')
        else:
            name = self.naming_manager().resolve(
                'outputName', {'componentName': self.name(), 'side': self.side(), 'id': 'rootMotion', 'type': 'output'})
            output_layer_descriptor.create_output(id='rootMotion', name=name, critType='output', parent='offset')

        super().setup_outputs(parent_node)

    @override
    def setup_selection_set_joints(
            self, skeleton_layer: crit.CritSkeletonLayer, deform_joints: dict[str, crit.Joint]) -> list[crit.Joint]:
        # we dot not want the root joint to be displayed as a skinned joint
        return []

    @override
    def setup_skeleton_layer(self, parent_joint: crit.Joint):
        descriptor = self.descriptor
        guide_layer_descriptor = descriptor.guide_layer
        skeleton_layer_descriptor = descriptor.skeleton_layer
        requires_joint = guide_layer_descriptor.guide_setting('rootJoint').value
        has_existing_joint = skeleton_layer_descriptor.joint('world')
        if requires_joint and not has_existing_joint:
            guide_descriptor = guide_layer_descriptor.guide('world')
            skeleton_layer_descriptor.create_joint(
                name=guide_descriptor.name, id='world', rotateOrder=guide_descriptor.get('rotateOrder', 0),
                translate=guide_descriptor.get('translate', (0.0, 0.0, 0.0)),
                rotate=guide_descriptor.get('rotate', (0.0, 0.0, 0.0, 1.0)), parent=None)
        elif not requires_joint and has_existing_joint:
            skeleton_layer_descriptor.delete_joints('world')

        super().setup_skeleton_layer(parent_joint)

    @override(check_signature=False)
    def setup_rig(self, parent_node: meta_nodes.Joint | api.DagNode | None = None):
        guide_layer_descriptor = self.descriptor.guide_layer
        control_panel = self.control_panel()
        input_layer = self.input_layer()
        rig_layer = self.rig_layer()
        requires_joint = guide_layer_descriptor.guide_setting('rootJoint').value
        naming = self.naming_manager()
        component_name, component_side = self.name(), self.side()

        controls: dict[str, crit.ControlNode] = {}
        for guide in guide_layer_descriptor.iterate_guides(False):
            if guide.id == 'rootMotion' and not requires_joint:
                continue
            name = naming.resolve(
                'controlName',
                {'componentName': component_name, 'side': component_side, 'id': guide.id, 'type': 'control'})
            new_control = rig_layer.create_control(
                name=name, id=guide.id, translate=guide.translate, rotate=guide.rotate, parent=guide.parent,
                shape=guide.shape, rotateOrder=guide.rotateOrder,
                selectionChildHighlighting=self.configuration.selection_child_highlighting)
            controls[guide.id] = new_control
            srt = rig_layer.create_srt_buffer(guide.id, '_'.join([new_control.name(False), 'srt']))
            input_node = input_layer.input_node(guide.id)
            if not input_node:
                continue
            input_node.attribute('worldMatrix')[0].connect(srt.offsetParentMatrix)
            srt.resetTransform()

        control_panel.displayOffset.connect(controls['offset'].visibility)
        controls['offset'].visibility.hide()

        if requires_joint:
            root_joint = self.skeleton_layer().joint('world')
            root_motion_control = controls['rootMotion']
            control_panel.displayRootMotion.connect(root_motion_control.visibility)
            root_motion_control.visibility.hide()
            _, parent_constraint_extra_nodes = api.build_constraint(
                root_joint,
                drivers={
                    'targets': ((root_motion_control.fullPathName(partial_name=True, include_namespace=False), root_motion_control),)},
                constraint_type='parent', maintainOffset=True
            )
            rig_layer.add_extra_nodes(parent_constraint_extra_nodes)
            _, scale_constraint_extra_nodes = api.build_constraint(
                root_joint,
                drivers={
                    'targets': ((root_motion_control.fullPathName(partial_name=True, include_namespace=False),
                                 root_motion_control),)},
                constraint_type='scale', maintainOffset=True
            )
            rig_layer.add_extra_nodes(scale_constraint_extra_nodes)

    @override
    def post_setup_rig(self, parent_node: crit.Joint | api.DagNode | None = None):
        output_layer = self.output_layer()
        rig_layer = self.rig_layer()
        outputs = output_layer.find_output_nodes('world', 'offset', 'rootMotion')
        controls = rig_layer.find_controls('world', 'offset', 'rootMotion')
        for i, output_ctrl in enumerate(zip(outputs, controls)):
            output, control = output_ctrl
            if control is None:
                continue
            if i == 0:
                _, matrix_constraint_extra_nodes = api.build_constraint(
                    output,
                    drivers={
                        'targets': ((control.fullPathName(partial_name=True, include_namespace=False), control),)},
                    constraint_type='matrix', maintainOffset=False
                )
                rig_layer.add_extra_nodes(matrix_constraint_extra_nodes)
            else:
                control.attribute('matrix').connect(output.offsetParentMatrix)
                output.resetTransform()

        super().post_setup_rig(parent_node=parent_node)
