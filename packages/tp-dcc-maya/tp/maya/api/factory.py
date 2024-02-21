from __future__ import annotations

from typing import Any

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.maya.api import consts, base, contexts, curves
from tp.maya.om import factory


def create_dag_node(
        name: str, node_type: str, parent: base.DagNode | None = None, mod: OpenMaya.MDagModifier | None = None,
        apply: bool = True) -> base.DagNode:
    """
    Creates a new DAG node and if a parent is specified, then parent the new node.

    :param str name: name of the DAG node to create.
    :param str node_type: type of the DAG node to create.
    :param base.DagNode or None parent:
    :param OpenMaya.MDagModifier or None mod: optional Maya modifier to apply.
    :param bool apply: whether to apply modifier immediately.
    :return: newly created Maya object instance.
    :rtype: base.DagNode
    """

    parent_node = parent.object() if parent else None
    return base.node_by_object(
        factory.create_dag_node(name=name, node_type=node_type, parent=parent_node, mod=mod, apply=apply))


def create_dg_node(
        name: str, node_type: str, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> base.DGNode | Any:
    """
    Creates a dependency graph node and returns the node Maya object.

    :param str name: new name of the node.
    :param str node_type: Maya node type to create.
    :param OpenMaya.MDGModifier or None mod: optional Maya modifier to apply.
    :param bool apply: whether to apply modifier immediately.
    :return: newly created Maya object instance.
    :rtype: base.DGNode
    """

    return base.node_by_object(factory.create_dg_node(name=name, node_type=node_type, mod=mod, apply=apply))


def create_mult_matrix(name: str, inputs: list[base.Plug], output: base.Plug | None) -> base.DGNode:
    """
    Creates a multMatrix node.

    :param str name: name of the node.
    :param list[base.Plug] inputs: input plugs.
    :param base.Plug or None output: output plug.
    :return: created multMatrix node.
    :rtype: base.DGNode
    """

    mult_matrix = create_dg_node(name, 'multMatrix')
    compound = mult_matrix.matrixIn
    for i in range(1, len(inputs)):
        _input = inputs[i]
        if isinstance(_input, base.Plug):
            _input.connect(compound.element(i))
            continue
        compound.element(i).set(_input)
    _input = inputs[0]
    if isinstance(_input, base.Plug):
        _input.connect(compound.element(0))
    else:
        compound.element(0).set(_input)
    if output is not None:
        mult_matrix.matrixSum.connect(output)

    return mult_matrix


def create_decompose(
        name: str, destination: base.DGNode, translate_values: tuple[bool, bool, bool] = (True, True, True),
        rotation_values: tuple[bool, bool, bool] = (True, True, True),
        scale_values: tuple[bool, bool, bool] = (True, True, True),
        input_matrix_plug: base.Plug | None = None) -> base.DGNode:
    """
    Creates decompose node and connects it to the given destination node.

    :param str name: name of the node.
    :param base.DGNode destination: node to connect to.
    :param tuple[bool, bool, bool] translate_values: X, Y, Z to apply for the translation channel.
    :param tuple[bool, bool, bool] rotation_values: X, Y, Z to apply for the rotation channel.
    :param tuple[bool, bool, bool] scale_values: X, Y, Z to apply for the scale channel.
    :param base.Plug or None input_matrix_plug: optional input matrix plug to connect from.
    :return: created decompose node.
    :rtype: base.DGNode
    """

    decompose = create_dg_node(name, 'decomposeMatrix')

    if input_matrix_plug is not None:
        input_matrix_plug.connect(decompose.inputMatrix)

    if destination:
        decompose.outputTranslate.connect(destination.translate, children=translate_values)
        decompose.outputRotate.connect(destination.rotate, children=rotation_values)
        decompose.outputScale.connect(destination.scale, children=scale_values)

    return decompose


def create_reverse(name: str, inputs: base.Plug | list[base.Plug], outputs: base.Plug | list[base.Plug]):
    """
    Creates a reverse node.

    :param str name: name for the reverse node.
    :param base.Plug or list[base.Plug] inputs: input compound plug or list of plugs.
    :param base.Plug or list[base.Plug] outputs: output compound plug or list of plugs.
    :return: created reverse node.
    :rtype: base.DGNode
    :raises ValueError: if only one input is passed and input plug is not a compound attribute.
    :raises ValueError: if only one output is passed and output plug is not a compound attribute.
    """

    reverse_node = create_dg_node(name, 'reverse')
    in_plug = reverse_node.input
    out_plug = reverse_node.output

    if isinstance(inputs, base.Plug):
        if inputs.isCompound:
            inputs.connect(in_plug)
            return reverse_node
        raise ValueError('inputs argument must be a compound when passing a single plug')
    elif isinstance(outputs, base.Plug):
        if outputs.isCompound:
            outputs.connect(out_plug)
            return reverse_node
        raise ValueError('outputs argument must be a compound when passing a single plug')

    for child_index in range(len(inputs)):
        in_a = inputs[child_index]
        if in_a is None:
            continue
        out_plug.child(child_index).connect(outputs[child_index])

    return reverse_node


def create_controller_tag(
        node: base.DagNode, name: str, parent: base.DGNode | None = None,
        visibility_plug: base.Plug | None = None) -> base.DGNode:
    """
    Creates a new Maya kControllerTag node into this control.

    :param base.DagNode node: node to tag.
    :param str name: name of the newly created controller tag.
    :param ControlNode parent: optional controller tag control parent.
    :param base.Plug visibility_plug: visibility plug to connect to.
    :return: newly created controller tag instance.
    :rtype: base.DGNode
    """

    new_controller = create_dg_node(name, 'controller')
    node.message.connect(new_controller.controllerObject)
    if visibility_plug is not None:
        visibility_plug.connect(new_controller.visibilityMode)
    if parent is not None:
        new_controller.attribute('parent').connect(parent.children.nextAvailableDestElementPlug())

    return new_controller


def create_display_layer(name):
    """
    Creates a new display layer with given name.

    :param str name: name of the display layer.
    :return: newly created display layer instance.
    :rtype: api.DGNode
    """

    return base.node_by_name(cmds.createDisplayLayer(name=name, empty=True))


def create_ik_handle(
        name: str, start_joint: base.Joint, end_joint: base.Joint, solver_type=consts.kIkRPSolveType,
        parent: base.DagNode | None = None, **kwargs) -> tuple[base.IkHandle, base.DagNode]:
    """
    Creates an IK handle and returns both, the IK handle and the IK effector.

    :param str name: name of the ik handle.
    :param base.Joint start_joint: start joint.
    :param base.Joint end_joint: end joint for the effector.
    :param str solver_type: solver type ('ikRPSolver' or 'ikSCsolver' or 'ikSplineSolver').
    :param api.DagNode or None parent: optional node to be the parent of the handle.
    :keyword str curve: full path to the curve.
    :keyword int priority: 1
    :keyword float weight: 1.0
    :keyword float positionWeight: 1.0
    :keyword bool forceSolver:
    :keyword bool snapHandleFlagToggle:
    :keyword bool sticky: False
    :keyword bool createCurve: True
    :keyword bool simplifyCurve: True
    :keyword bool rootOnCurve: True
    :keyword str twistType: "linear"
    :keyword bool createRootAxis: False
    :keyword bool parentCurve: True
    :keyword bool snapCurve: False
    :keyword int numSpans: 1
    :keyword bool rootTwistMode: False
    :return: tuple with the created IK handle and IK effector.
    :rtype: tuple[base.IkHandle, base.DagNode]
    """

    with contexts.namespace_context(OpenMaya.MNamespace.rootNamespace()):
        ik_nodes = cmds.ikHandle(
            sj=start_joint.fullPathName(), ee=end_joint.fullPathName(), solver=solver_type, n=name, **kwargs)
        handle, effector = map(base.node_by_name, ik_nodes)
        if parent:
            handle.setParent(parent)

    return handle, effector


def create_nurbs_curve_from_points(
        name: str, points: list[list[float, float, float], ...], shape_data: dict | None = None,
        parent: base.DagNode | None = None) -> tuple[base.DagNode, list[base.DGNode]]:
    """
    Creates a NURBS curve based on given world space points.

    :param str name: name of the curve node.
    :param list[list[float, float, float], ...] points: list of points for the curve in world space.
    :param dict or None shape_data: optional curve shape data.
    :param base.DagNode or None parent: optional parent for the curve transform node.
    :return: tuple containing the curve transform node and all its shapes.
    :rtype: tuple[base.DagNode, list[base.DGNode]]
    """

    spline_curve_transform, created_shapes = curves.create_curve_from_points(
        name=name, points=points, shape_dict=shape_data, parent=parent.object() if parent is not None else None)

    return (
        base.node_by_name(spline_curve_transform),
        [base.node_by_name(i) for i in created_shapes if i != spline_curve_transform]
    )
