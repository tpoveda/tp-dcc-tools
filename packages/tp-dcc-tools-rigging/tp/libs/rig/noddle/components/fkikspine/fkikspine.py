from __future__ import annotations

from overrides import override

import typing

import maya.cmds as cmds

from tp.maya import api
from tp.libs.rig.noddle.core import animcomponent, nodes
from tp.libs.rig.noddle.functions import curves

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.nodes import ControlNode
    from tp.libs.rig.noddle.meta.layers import NoddleRigLayer
    from tp.libs.rig.noddle.descriptors.nodes import TransformDescriptor


def create_spline_curve(
        layer: NoddleRigLayer, influences: list[TransformDescriptor], parent: api.DagNode, attribute_name: str,
        curve_name: str, curve_visibility_control_attribute: api.Plug) -> api.DagNode:
    """
    Creates a new spline NURBS curve and connects it to its rig layer.

    :param NoddleRigLayer layer: rig layer NURBS curve belongs to.
    :param list[TransformDescriptor] influences: list of transform descriptors that will be used to create the curve.
    :param api.DagNode parent: node curve will be parented under.
    :param str attribute_name: name of the attribute of the rig layer that curve will be connected into.
    :param str curve_name: name of the newly created curve transform node.
    :param api.Plug curve_visibility_control_attribute: plug that will be used to control the visibility of the newly
        created curve shapes.
    :return: newly created curve transform node.
    :rtype: api.DagNode
    """

    if not layer.hasAttribute(attribute_name):
        spline_attr = layer.addAttribute(attribute_name, type=api.kMFnMessageAttribute)
    else:
        spline_attr = layer.attribute(attribute_name)

    spline_curve_transform = spline_attr.sourceNode()
    if spline_curve_transform is None:
        points = [influence.translate for influence in influences]
        spline_curve_transform = curves.curve_from_points(curve_name, points=points)
        for shape in spline_curve_transform.iterateShapes():
            shape.template.set(True)
        spline_curve_transform.rename(curve_name)
        layer.connect_to_by_plug(spline_attr, spline_curve_transform)
        spline_curve_transform.setParent(parent)

    return spline_curve_transform


def create_ik_spline(
        name: str, parent: api.DagNode, up_vector_control: ControlNode, end_control: ControlNode, curve: api.DagNode,
        aim_vector, up_vector, ik_joints: list):

    ik_handle, ik_effector = api.factory.create_ik_handle(
        name, start_joint=ik_joints[0], end_joint=ik_joints[-1], solver_type=api.consts.kIkSplineSolveType,
        parent=parent, curve=curve.fullPathName(), parentCurve=False, rootOnCurve=True, simplifyCurve=False,
        createCurve=False)
    ik_handle.dTwistControlEnable.set(True)
    ik_handle.dWorldUpType.set(api.IkHandle.OBJECT_ROTATION_UP_START_END)

    ik_handle.dForwardAxis.set(ik_handle.vector_to_forward_axis_enum(aim_vector))
    ik_handle.dWorldUpAxis.set(ik_handle.vector_to_up_axis_enum(up_vector))
    # perpendicular = api.Vector(aim_vector) ^ api.Vector(up_vector)
    # ik_handle.dWorldUpVector.set(perpendicular)
    # ik_handle.dWorldUpVectorEnd.set(perpendicular)
    up_vector_control.attribute('worldMatrix')[0].connect(ik_handle.dWorldUpMatrix)
    end_control.attribute('worldMatrix')[0].connect(ik_handle.dWorldUpMatrixEnd)

    ik_handle.hide()

    return ik_handle, ik_effector


class FkIkSpineComponent(animcomponent.AnimComponent):

    ID = 'fkikspine'

    @override(check_signature=False)
    def setup_outputs(self, parent_node: nodes.Joint | api.DagNode):

        component_name, component_side = self.name(), self.side()
        naming = self.naming_manager()
        skeleton_layer_descriptor = self.descriptor.skeleton_layer
        output_layer_descriptor = self.descriptor.output_layer

        output_layer_descriptor.clear_outputs()
        for joint_descriptor in skeleton_layer_descriptor.iterate_joints():
            joint_id = joint_descriptor.id
            output_name = naming.resolve(
                'outputName',
                {'componentName': component_name, 'side': component_side, 'id': joint_id, 'type': 'output'})
            output_layer_descriptor.create_output(id=joint_id, name=output_name, parent=None)

        super().setup_outputs(parent_node=parent_node)

        output_layer = self.output_layer()
        skeleton_layer = self.skeleton_layer()
        joints: dict[str, nodes.Joint] = {joint.id(): joint for joint in skeleton_layer.joints()}
        for output in output_layer.iterate_outputs():
            driver_joint = joints.get(output.id())
            output.setWorldMatrix(driver_joint.worldMatrix())

    @override(check_signature=False)
    def setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        component_name, component_side = self.name(), self.side()
        naming = self.naming_manager()
        skeleton_layer_descriptor = self.descriptor.skeleton_layer
        skeleton_layer = self.skeleton_layer()
        rig_layer = self.rig_layer()
        rig_layer_root = rig_layer.root_transform()
        control_panel = rig_layer.control_panel()
        control_joints = list(skeleton_layer.iterate_joints())

        up_axis = 'y'

        # Build Ik curve
        ik_curve = create_spline_curve(
            layer=rig_layer, influences=list(skeleton_layer_descriptor.joints()),
            parent=rig_layer_root, attribute_name='splineIkCrv', curve_name='spineSpline_crv',
            curve_visibility_control_attribute=control_panel.attribute('showCurveTemplate'))
        # cmds.rebuildCurve(ik_curve.fullPathName(), d=3, kep=True, rpo=True, ch=False, tol=0.01, spans=4)

        # Build IK Controls
        control_locator = api.factory.create_dag_node(name='temp_control_loc', node_type='locator')
        control_locator.setTranslation(api.Vector(*cmds.pointOnCurve(ik_curve.fullPathName(), pr=0.0, top=True)))

        root_control = rig_layer.create_control(
            name=naming.resolve(
                'controlName',
                {'componentName': component_name, 'side': component_side, 'id': 'root', 'type': 'control'}),
            id='root', shape='root', not_locked_attributes='tr', color='red', orient_axis=up_axis,
            guide=control_locator, delete_guide=False)
        rig_layer.create_srt_buffer('root', '_'.join([root_control.name(False), 'srt']))

        hips_control = rig_layer.create_control(
            name=naming.resolve(
                'controlName',
                {'componentName': component_name, 'side': component_side, 'id': 'hips', 'type': 'control'}),
            id='hips', shape='circle_down_arrow', not_locked_attributes='tr', color=self.color(),
            guide=control_joints[0], delete_guide=False, parent=root_control)
        rig_layer.create_srt_buffer('hips', '_'.join([hips_control.name(False), 'srt']))

        control_locator.setTranslation(api.Vector(*cmds.pointOnCurve(ik_curve.fullPathName(), pr=0.5, top=True)))
        mid_control = rig_layer.create_control(
            name=naming.resolve(
                'controlName',
                {'componentName': component_name, 'side': component_side, 'id': 'mid', 'type': 'control'}),
            id='mid', shape='circle_up_arrow', not_locked_attributes='tr', color=self.color(), orient_axis=up_axis,
            guide=control_locator, delete_guide=False, parent=root_control)
        cmds.matchTransform(
            mid_control.fullPathName(), control_joints[0].fullPathName(), pos=False, rot=True, piv=False)
        rig_layer.create_srt_buffer('mid', '_'.join([mid_control.name(False), 'srt']))

        chest_control = rig_layer.create_control(
            name=naming.resolve(
                'controlName',
                {'componentName': component_name, 'side': component_side, 'id': 'chest', 'type': 'control'}),
            id='chest', shape='chest', not_locked_attributes='tr', color=self.color(), orient_axis=up_axis,
            guide=control_joints[-1], delete_guide=False, parent=root_control)
        rig_layer.create_srt_buffer('chest', '_'.join([chest_control.name(False), 'srt']))
        # cmds.delete(cmds.orientConstraint(
        #     chest_control.srt(0).fullPathName(), hips_control.srt(0).fullPathName(), mid_control.srt(0).fullPathName()))
        # cns, constraint_nodes = api.build_constraint(
        #     mid_control.srt(0),
        #     drivers={
        #         'targets': (
        #             (hips_control.fullPathName(partial_name=True, include_namespace=False), hips_control),
        #             (chest_control.fullPathName(partial_name=True, include_namespace=False), chest_control),
        #         )
        #     },
        #     constraint_type='parent', maintainOffset=True
        # )

        # rig_layer.add_extra_nodes(constraint_nodes)
        # control_panel.attribute('followHips').connect(cns.constraint_node.target[0].child(cns.CONSTRAINT_TARGET_INDEX))
        # control_panel.attribute('followChest').connect(cns.constraint_node.target[1].child(cns.CONSTRAINT_TARGET_INDEX))
        # # constraint_nodes[0].attribute('interpType').set(0)
        #
        # hips_control_joint = api.factory.create_dag_node(
        #     name=naming.resolve(
        #         'controlJointName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'hips', 'type': 'controlJoint'}),
        #     node_type='joint', parent=hips_control)
        # hips_control_joint.setVisible(False)
        # mid_control_joint = api.factory.create_dag_node(
        #     name=naming.resolve(
        #         'controlJointName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'mid', 'type': 'controlJoint'}),
        #     node_type='joint', parent=mid_control)
        # mid_control_joint.setVisible(False)
        # chest_control_joint = api.factory.create_dag_node(
        #     name=naming.resolve(
        #         'controlJointName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'chest', 'type': 'controlJoint'}),
        #     node_type='joint', parent=chest_control)
        # chest_control_joint.setVisible(False)
        # rig_layer.add_extra_nodes([hips_control_joint, mid_control_joint, chest_control_joint])
        #
        # # Skin IK curve to IK control joints
        # skin_cluster_name = naming.resolve(
        #     'object',
        #     {'componentName': component_name, 'side': component_side, 'section': 'spineSpline', 'type': 'skinCluster'})
        # skin_cluster = api.node_by_name(cmds.skinCluster(
        #     [hips_control_joint.fullPathName(), mid_control_joint.fullPathName(), chest_control_joint.fullPathName()],
        #     ik_curve.fullPathName(), n=skin_cluster_name)[0])
        # rig_layer.add_extra_node(skin_cluster)
        #
        # # We do this connection after applying the skin, otherwise Maya will fail.
        # for shape in ik_curve.iterateShapes():
        #     control_panel.attribute('showCurveTemplate').connect(shape.visibility)
        #
        # # Build Ik handle
        # spline_ik_name = naming.resolve(
        #     'object',
        #     {'componentName': component_name, 'side': component_side, 'section': 'splineIk', 'type': 'ikHandle'})
        # ik_handle, ik_effector = create_ik_spline(
        #     name=spline_ik_name, parent=rig_layer_root, up_vector_control=hips_control, end_control=chest_control,
        #     curve=ik_curve, aim_vector=[1.0, 0.0, 0.0], up_vector=[0.0, 1.0, 0.0], ik_joints=control_joints)
        # rig_layer.add_extra_nodes([ik_handle, ik_effector])

        # # Build FK controls
        # control_locator.setTranslation(api.Vector(*cmds.pointOnCurve(ik_curve.fullPathName(), pr=0.25, top=True)))
        # fk1_control = rig_layer.create_control(
        #     name=naming.resolve(
        #         'controlName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'fk1', 'type': 'control'}),
        #     id='fk1', shape='circle_up_arrow', not_locked_attributes='tr', color=self.color(), orient_axis=up_axis,
        #     guide=control_locator, delete_guide=False, parent=root_control)
        # rig_layer.create_srt_buffer('fk1', '_'.join([fk1_control.name(False), 'srt']))
        # cmds.delete(cmds.orientConstraint(
        #     hips_control.srt(0).fullPathName(), mid_control.srt(0).fullPathName(), fk1_control.srt(0).fullPathName()))
        #
        # control_locator.setTranslation(api.Vector(*cmds.pointOnCurve(ik_curve.fullPathName(), pr=0.75, top=True)))
        # fk2_control = rig_layer.create_control(
        #     name=naming.resolve(
        #         'controlName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'fk2', 'type': 'control'}),
        #     id='fk2', shape='circle_up_arrow', not_locked_attributes='tr', color=self.color(), orient_axis=up_axis,
        #     guide=control_locator, delete_guide=False, parent=root_control)
        # rig_layer.create_srt_buffer('fk2', '_'.join([fk2_control.name(False), 'srt']))
        # fk2_control_joint = api.factory.create_dag_node(
        #     name=naming.resolve(
        #         'controlJointName',
        #         {'componentName': component_name, 'side': component_side, 'id': 'fk2', 'type': 'controlJoint'}),
        #     node_type='joint', parent=fk2_control)
        # fk2_control_joint.setVisible(False)
        # rig_layer.add_extra_node(fk2_control_joint)
        #
        # _, parent_constraint_nodes = api.build_constraint(
        #     chest_control.srt(0),
        #     drivers={
        #         'targets': (
        #             (fk2_control_joint.fullPathName(partial_name=True, include_namespace=False), fk2_control_joint),
        #         )
        #     },
        #     constraint_type='parent', maintainOffset=True
        # )
        # rig_layer.add_extra_nodes(parent_constraint_nodes)

        scale_dict = {
            root_control: 0.4,
            hips_control: 0.35,
            mid_control: 0.3,
            chest_control: 0.30,
        #     fk1_control: 0.35,
        #     fk2_control: 0.35
        }
        self.scale_controls(scale_dict)

        hips_control.move_shapes(api.Vector(0.0, -5.0, 0.0))

    # @override
    # def post_setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
    #
    #     component_name, component_side = self.name(), self.side()
    #     naming = self.naming_manager()
    #     skeleton_layer = self.skeleton_layer()
    #     output_layer = self.output_layer()
    #
    #     bind_joints_map: dict[str, nodes.Joint] = {joint.id(): joint for joint in skeleton_layer.joints()}
    #
    #     for output_node in output_layer.iterate_outputs():
    #         source_node = bind_joints_map[output_node.id()]
    #         output_node.resetTransform()
    #         source_decompose_matrix = api.factory.create_dg_node(
    #             name=naming.resolve(
    #                 'object',
    #                 {'componentName': component_name, 'side': component_side, 'section': '',
    #                  'type': 'decomposeMatrix'}),
    #             node_type='decomposeMatrix')
    #         compose_matrix = api.factory.create_dg_node(
    #             name=naming.resolve(
    #                 'object',
    #                 {'componentName': component_name, 'side': component_side, 'section': '',
    #                  'type': 'composeMatrix'}),
    #             node_type='composeMatrix')
    #         source_node.attribute('worldMatrix')[0].connect(source_decompose_matrix.inputMatrix)
    #         source_decompose_matrix.outputTranslate.connect(compose_matrix.inputTranslate)
    #         source_decompose_matrix.outputRotate.connect(compose_matrix.inputRotate)
    #         source_decompose_matrix.outputTranslate.connect(compose_matrix.inputTranslate)
