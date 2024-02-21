from __future__ import annotations

import typing

from tp.maya import api
from tp.libs.rig.noddle.functions import curves

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.nodes import ControlNode
    from tp.libs.rig.noddle.descriptors.nodes import TransformDescriptor
    from tp.libs.rig.noddle.meta.layers import NoddleRigLayer


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
    :param api.Plug curve_visibility_control_attribute: plug that will be used to control the visibilite of the newly
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
