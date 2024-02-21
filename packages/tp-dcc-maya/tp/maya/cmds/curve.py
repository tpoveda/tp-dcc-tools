# #! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility methods related to Maya Curves
"""

from __future__ import annotations

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.common.python import helpers, strings
from tp.common.math import scalar, vec3
from tp.maya import api
from tp.maya.api import curves as api_curves
from tp.maya.cmds import exceptions, transform, component, decorators, filtertypes, name as name_utils
from tp.maya.cmds import shape as shape_utils
from tp.maya.om import nodes

logger = log.tpLogger


def check_curve(curve):
    """
    Checks if a node is a valid curve and raise and exception if the curve is not valid
    :param curve: str, name of the node to be checked
    :return: bool, True if the given node is a curve node or False otherwise
    """

    if not is_curve(curve):
        raise exceptions.CurveException(curve)


def is_a_curve(curve):
    """
    Returns whether given node is curve or has a shape that is a curve
    :param curve: str
    :return: bool
    """

    if cmds.objExists('{}.cv[0]'.format(curve)) and not cmds.objExists('{}.cv[0][0]'.format(curve)):
        return True

    return False


def is_curve(curve):
    """
    Checks if the given object is a curve or transform parent of a curve
    :param curve: str, object to query
    :return: bool, True if the given object is a valid curve or False otherwise
    """

    if not cmds.objExists(curve):
        return False

    if cmds.objectType(curve) == 'transform':
        curve = cmds.listRelatives(curve, shapes=True, noIntermediate=True, pa=True)
    if cmds.objectType(curve) != 'nurbsCurve' and cmds.objectType(curve) != 'bezierCurve':
        return False

    return True


def is_cv_count_same(source_curve, target_curve):
    """
    Returns whether or not given curves have the same amount of CVs
    :param source_curve: str
    :param target_curve: str
    :return: bool
    """

    source_cvs = len(cmds.ls('{}.cv[*]'.format(source_curve)), flatten=True)
    target_cvs = len(cmds.ls('{}.cv[*]'.format(target_curve)), flatten=True)

    return source_cvs == target_cvs


def get_curve_fn(curve):
    """
    Creates an MFnNurbsCurve class object from the specified NURBS curve
    :param curve: str, curve to create function class for
    :return: MFnNurbsCurve function class initialized with the given curve object
    """

    check_curve(curve)

    if cmds.objectType(curve) == 'transform':
        curve = cmds.listRelatives(curve, shapes=True, noIntermediate=True)[0]

    curve_sel = OpenMaya.MGlobal.getSelectionListByName(curve)
    curve_path = curve_sel.getDagPath(0)
    curve_fn = OpenMaya.MFnNurbsCurve(curve_path)

    return curve_fn


def create_from_point_list(point_list, degree=3, name=''):
    """
    Build a NURBS curve from a list of world positions
    :param point_list:  list<int>, list of CV world positions
    :param degree: int, degree of the curve to create
    :param name: str, name prefix for newly created curves
    :return: name of the new created curve
    """

    cv_list = [transform.get_position(i) for i in point_list]

    crv = cmds.curve(p=cv_list, k=range(len(cv_list)), d=1)
    name = name or 'curve_from_points'
    crv = cmds.rename(crv, name)

    if degree > 1:
        crv = cmds.rebuildCurve(crv, d=degree, kcp=True, kr=0, ch=False, rpo=True)[0]

    return crv


def create_curve_from_mesh_edge_loop(
        mesh_edge_list, rebuild=False, rebuild_spans=0, form=2, keep_history=True, name=''):
    """
    Createsa a new from the given mesh edge loop
    :param mesh_edge_list: list(str), list of mesh edges to generate curve from
    :param rebuild: bool, Whether or not to rebuild curve to degree 3
    :param rebuild_spans: int, number of spans to rebuild the resulting curve to
    :param form: str, form of the resulting curve (0=open; 1=periodic; 2=best guess). Default is 2.
    :param keep_history: bool, Whether or not to maintain construction history
    :param name: str, name for new curve
    :return: str
    """

    if not mesh_edge_list:
        raise Exception('Invalid mesh edge list provided!')
    mesh_edge_list = cmds.ls(mesh_edge_list, flatten=True)

    if not name:
        name = '{}Curve'.format(strings.strip_suffix(mesh_edge_list[0].split('.')[0]))

    curve_degree = 3 if rebuild else 1
    new_curve = cmds.polyToCurve(form=form, degree=curve_degree, ch=keep_history)[0]
    if rebuild and rebuild_spans:
        new_curve = cmds.rebuildCurve(
            new_curve, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=1,
            s=rebuild_spans, d=3, tol=0.01, ch=keep_history)[0]
    new_curve = cmds.rename(new_curve, name or 'curveFromEdgeLoop')

    return new_curve

# TODO: Implement
# def create_curve_from_objects(transforms=None, extend=False):
#     """
#     Creates a curve using given objects as positions
#     :param transforms: list(str), list of objects to use positions to build the curve from.
#     :param extend: bool, Whether or not new curve should be extended after the last object.
#     :return: str, newly created curve
#     """
#
#     transforms = python.force_list(transforms or maya.cmds.ls(sl=True))
#     if len(transforms) < 2:
#         logger.warning('Impossible to create curve from objects. At least 2 should be given.')
#         return None
#     extend = extend if len(transforms) > 5 else True
#
#     positions = [maya.cmds.xform(node, query=True, ws=True, rp=True) for node in transforms]
#     if extend:
#         pass


def transforms_to_curve(transforms, spans=None, name='from_transforms'):
    """
    Creates a curve from a list of transforms. Each transform will define a curve CV
    Useful when creating a curve from a joint chain (spines/tails)
    :param transforms: list<str>, list of tranfsorms to generate the curve from. Positions will be used to place CVs
    :param spans: int, number of spans the final curve should have
    :param name: str, name for the curve
    :return: str name of the new curve
    """

    if not transforms:
        logger.warning('Impossible to create curve from transforms because no transforms given!')
        return None

    transform_positions = list()
    for xform in transforms:
        xform_pos = cmds.xform(xform, q=True, ws=True, rp=True)
        transform_positions.append(xform_pos)

    curve = cmds.curve(p=transform_positions, degree=1)
    if spans:
        cmds.rebuildCurve(
            curve, ch=False, rpo=True, rt=0, end=1, kr=False, kcp=False, kep=True,
            kt=False, spans=spans, degree=3, tol=0.01)
    curve = cmds.rename(curve, name_utils.find_unique_name(name))
    cmds.setAttr('{}.inheritsTransform'.format(curve), False)

    return curve


def get_closest_position_on_curve(curve, value_list):
    """
    Returns closes position on a curve from given vector
    :param curve: str, name of a curve
    :param value_list: list(float, float, float)
    :return: list(float, float, float)
    """

    curve_shapes = shape_utils.get_shapes(curve)
    curve = curve_shapes[0] if curve_shapes else curve
    curve = api.NurbsCurveFunction(curve)

    return curve.get_closest_position(value_list)


def get_closest_parameter_on_curve(curve, value_list):
    """
    Returns the closest parameter value (UV) on the curve given a vector
    :param curve: str, name of a curve
    :param value_list: list(int, int, int), vector from which to search for closest parameter
    :return: float
    """

    curve_shapes = shape_utils.get_shapes(curve)
    curve = curve_shapes[0] if curve_shapes else curve
    curve = api.NurbsCurveFunction(curve)
    new_point = curve.get_closest_position(value_list)

    return curve.get_parameter_at_position(new_point)


def get_parameter_from_curve_length(curve, length_value):
    """
    Returns the parameter value (UV) given the length section of a curve
    :param curve: str, name of a curve
    :param length_value: float, length along a curve
    :return: float, parameter value at the length
    """

    curve_shapes = shape_utils.get_shapes(curve)
    curve = curve_shapes[0] if curve_shapes else curve
    curve = api.NurbsCurveFunction(curve)

    return curve.get_parameter_at_length(length_value)


def get_curve_length_from_parameter(curve, parameter_value):
    """
    Returns a curve length at given parameter UV
    :param curve: str
    :param parameter_value:
    :return:
    """

    arc_node = cmds.arcLengthDimension('{}.u[{}]'.format(curve, parameter_value))
    length = cmds.getAttr('{}.arcLength'.format(arc_node))
    parent = cmds.listRelatives(arc_node, p=True)
    if parent:
        cmds.delete(parent[0])

    return length


def get_point_from_curve_parameter(curve, parameter):
    """
    Returns a position on a curve by giving a parameter value
    :param curve: str, name of a curve
    :param parameter: float, parameter value a curve
    :return: list(float, float, float), vector found at the parameter of the curve
    """

    return cmds.pointOnCurve(curve, pr=parameter, ch=False)


def get_curve_position_from_parameter(curve, parameter):
    """
    Returns a position on a curve by giving a parameter value
    :param curve: str, name of a curve
    :param parameter: float, parameter value a curve
    :return: list(float, float, float), vector found at the parameter of the curve
    """

    position = get_point_from_curve_parameter(curve, parameter)

    return position


def rebuild_curve(curve, spans=-1, degree=3):
    """
    Rebuilds a curve with given parameters (simplified version)
    :param curve: str, name of the curve to rebuild
    :param spans: int
    :param degree: int
    :return: str
    """

    if spans == -1:
        spans = cmds.getAttr('{}.spans'.format(curve))

    curve = cmds.rebuildCurve(curve, ch=False, rpo=True, rt=False, end=True, kr=False,
                                   kcp=False, kep=True, kt=False, s=spans, d=degree, tol=0.01)

    return curve


def rebulid_curve_at_distance(curve, min_length, max_length, min_spans=3, max_spans=10):
    """
    Rebuilds a curve with given parameter and in the given distance
    :param curve: str
    :param min_length: float
    :param max_length: float
    :param min_spans: int
    :param max_spans: int
    :return: str
    """

    curve_length = cmds.arcLen(curve, ch=False)
    spans = scalar.remap_value(curve_length, min_length, max_length, min_spans, max_spans)

    return rebuild_curve(curve, spans=spans, degree=3)


def evenly_position_curve_cvs(curve):
    """
    Given a curve, all its CVs will be evenly position along the given curve
    :param curve: str, name of the curve to evenly its CVs
    :return: str
    """

    cvs = cmds.ls('{}.cv[*}'.format(curve), flatten=True)

    return snap_transforms_to_curve(cvs, curve)


def snap_transforms_to_curve(transforms, curve):
    """
    Snaps the given transforms to the nearest position on the curve
    :param transforms: list(str)
    :param curve: str
    """

    count = len(transforms)
    total_length = cmds.arclen(curve)
    part_length = total_length / (count - 1)
    current_length = 0.0
    if count - 1 == 0:
        part_length = 0
    temp_curve = cmds.duplicate(curve)[0]

    for i in range(0, count):
        param = get_parameter_from_curve_length(temp_curve, current_length)
        pos = get_point_from_curve_parameter(temp_curve, param)
        xform = transforms[i]
        if cmds.nodeType(xform) == 'joint':
            cmds.move(
                pos[0], pos[1], pos[2], '{}.scalePivot'.format(xform), '{}.rotatePivot'.format(xform), a=True)
        else:
            cmds.xform(xform, ws=True, t=pos)

        current_length += part_length

    cmds.delete(temp_curve)


@decorators.undo_chunk
def snap_joints_to_curve(joints, curve=None, count=10):
    """
    Snap given joitns to the given curve
    If the given count is greater than the number of joints, new joints will be added to the curve
    :param joints: list(str(, list of joints to snap to curve
    :param curve: str, name of a curve. If no curve given a simple curve will be created based on the joints
    :param count: int, number of joints, if the joints list does not have the same number joints,
        new ones wil be created
    :return: list(str)
    """

    if not joints:
        return

    # List that will contain temporary objects that will be removed when the snapping process is over
    delete_after = list()

    if not curve:
        curve = transforms_to_curve(joints, spans=count, name='temp')
        delete_after.append(curve)

    joint_count = len(joints)
    if joint_count < count and count:
        missing_count = count - joint_count
        for i in range(missing_count):
            new_jnt = cmds.duplicate(joints[-1])[0]
            new_jnt = cmds.rename(new_jnt, name_utils.find_unique_name(joints[-1]))
            cmds.parent(new_jnt, joints[-1])
            joints.append(new_jnt)
    joint_count = len(joints)
    if not joint_count:
        return

    if count == 0:
        count = joint_count

    total_length = cmds.arclen(curve)
    part_length = total_length / (count - 1)
    current_length = 0.0
    if count - 1 == 0:
        part_length = 0

    for i in range(count):
        param = get_parameter_from_curve_length(curve, current_length)
        pos = get_point_from_curve_parameter(curve, param)
        cmds.move(
            pos[0], pos[1], pos[2], '{}.scalePivot'.format(joints[i]), '{}.rotatePivot'.format(joints[i], a=True))
        current_length += part_length

    if delete_after:
        cmds.delete(delete_after)


def attach_to_curve(transform, curve, maintain_offset=False, parameter=None):
    """
    Attaches the transform to the given curve using a point on curve
    :param transform: str, name of transform to attach to curve
    :param curve: str, name of curve
    :param maintain_offset: bool, Whether to attach to transform and maintain its offset from the curve
    :param parameter: float, parameter on the curve where the transform should attach
    :return: str, name of the pointOnCurveInfo node
    """

    position = cmds.xform(transform, query=True, ws=True, rp=True)
    if not parameter:
        parameter = get_closest_parameter_on_curve(curve, position)

    curve_info_node = cmds.pointOnCurve(curve, pr=parameter, ch=True)

    if maintain_offset:
        plus_node = cmds.createNode('plusMinusAverage', n='{}_subtract_offset'.format(transform))
        cmds.setAttr('{}.operation'.format(plus_node), 1)
        for axis in 'XYZ':
            value = cmds.getAttr('{}.position{}'.format(curve_info_node, axis))
            value_orig = cmds.getAttr('{}.translate{}'.format(transform, axis))
            cmds.connectAttr('{}.position{}'.format(curve_info_node, axis), '{}.input3D[0].input3D{}'.format(
                plus_node, axis.lower()))
            cmds.setAttr('{}.input3D[1].input3D{}'.format(plus_node, axis.lower()), -value)
            cmds.setAttr('{}.input3D[2].input3D{}'.format(plus_node, axis.lower()), value_orig)
            cmds.connectAttr(
                '{}.output3D{}'.format(plus_node, axis.lower()), '{}.translate{}'.format(transform, axis))
    else:
        for axis in 'XYZ':
            cmds.connectAttr(
                '{}.position{}'.format(curve_info_node, axis), '{}.translate{}'.format(transform, axis))

    return curve_info_node


def snap_curve_to_surface(curve, surface, offset=1, project=False):
    """
    Snaps curves CVs on given surface
    :param curve: str, name of the curve to snap onto surface
    :param surface: str, name of surface curve wil be snapped to
    :param offset: int, offset between curve and surface
    :param project: bool, Whether to snap or snap and project the curve into the surface
    """

    from tp.maya.cmds import mesh

    center = cmds.xform(curve, query=True, ws=True, rp=True)
    shapes = shape_utils.get_shapes(curve)
    for shape in shapes:
        cvs = cmds.ls('{}.cv[*]'.format(shape), flatten=True)
        for cv in cvs:
            pos = cmds.xform(cv, query=True, ws=True, t=True)
            if mesh.is_a_mesh(surface):
                mesh_fn = api.MeshFunction(surface)
                if project:
                    closest_point = mesh_fn.get_closest_intersection(pos, center)
                else:
                    closest_point = mesh_fn.get_closest_position(pos)
                cmds.xform(cv, ws=True, t=closest_point)
        cmds.scale(offset, offset, offset, cvs, r=True)


def snap_project_curve_to_surface(curve, surface, offset=1):
    """
    Projects curves CVs on given surface
   :param curve: str, name of the curve to snap onto surface
    :param surface: str, name of surface curve wil be snapped to
    :param offset: int, offset between curve and surface
    """

    return snap_curve_to_surface(curve=curve, surface=surface, offset=offset, project=True)


def curve_to_nurbs_surface(curve, description, spans=-1, offset_axis='X', offset_amount=1):
    """
    Creates a new NURBS surface given a curve
    :param curve: str
    :param description: str
    :param spans: int
    :param offset_axis: str
    :param offset_amount: float
    :return: str, newly created NURBS surface
    """

    curve1 = cmds.duplicate(curve)[0]
    curve2 = cmds.duplicate(curve)[0]
    offset_axis = offset_axis.upper()
    pos_move = vec3.get_axis_vector(offset_axis, offset_amount)
    neg_move = vec3.get_axis_vector(offset_axis, offset_amount * -1)
    cmds.move(pos_move[0], pos_move[1], pos_move[2], curve1)
    cmds.move(neg_move[0], neg_move[1], neg_move[2], curve2)
    curves = [curve1, curve2]

    if not spans == -1:
        for curve in curves:
            cmds.rebuildCurve(
                curve, ch=False, rpo=True, rt=0, end=1, kr=False,
                kcp=False, kep=True, kt=False, spans=spans, degree=3, tol=0.01)

    loft = cmds.loft(
        curve1, curve2, n=name_utils.find_unique_name(f'nurbsSurface_{description}'), ss=1, degree=1, ch=False)
    spans = cmds.getAttr('{}.spans'.format(curve1))
    cmds.rebuildSurface(
        loft, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=0, kc=0, su=1, du=1, sv=spans, dv=3, tol=0.01, fr=0, dir=2)
    cmds.delete(curve1, curve2)

    return loft[0]


def set_shapes_as_text_curve(transform, text_string):
    """
    Updates the shapes of the given transform with given text (as curves)
    :param transform: str, transform node we want to update shapes of
    :param text_string: str, text we want to add
    """

    shapes = shape_utils.get_shapes(transform)
    cmds.delete(shapes)
    text = cmds.textCurves(ch=False, f='Arial|w400|h-1', t=text_string)
    cmds.makeIdentity(text, apply=True, t=True)
    transforms = cmds.listRelatives(text, ad=True, type='transform')
    for text_transform in transforms:
        shapes = shape_utils.get_shapes(text_transform)
        if not shapes:
            continue
        for shape in shapes:
            cmds.parent(shape, transform, r=True, s=True)
    cmds.delete(text)
    shape_utils.rename_shapes(transform)


def get_curve_shape(curve, shape_index=0):
    """
    Returns the shape for a curve transform
    :param curve: str
    :param shape_index: int
    :return: str or None
    """

    if curve.find('.vtx'):
        curve = curve.split('.')[0]
    if cmds.nodeType(curve) == 'nurbsCurve':
        curve = cmds.listRelatives(curve, p=True)[0]

    shapes = shape_utils.get_shapes(curve)
    if not shapes:
        return
    if not cmds.nodeType(shapes[0]) == 'nurbsCurve':
        return

    shape_count = len(shapes)
    if shape_index < shape_count:
        return shapes[0]
    elif shape_index >= shape_count:
        logger.warning(
            'Curve {} does not have a shape count up to {}. Returning last shape'.format(curve, shape_index))
        return shapes[-1]

    return shapes[shape_index]


def get_curves_in_list(dg_nodes_list):
    """
    Given a list of DG nodes, returns any transform that has a curve shape node
    :param dg_nodes_list: list(str)
    :return: list(str)
    """

    found_curves = list()

    for dg_node in dg_nodes_list:
        if cmds.nodeType(dg_node) == 'nurbsCurve':
            found_curve = cmds.listRelatives(dg_node, p=True)
            found_curves.append(found_curve)
        if cmds.nodeType(dg_node) == 'transform':
            shapes = get_curve_shape(dg_node)
            if shapes:
                found_curves.append(dg_node)

    return found_curves


def get_selected_curves():
    """
    Returns all selected curves from current selection
    :return: list(str)
    """

    selection = cmds.ls(sl=True)

    return get_curves_in_list(selection)


def move_cvs(curves, position, pivot_at_center=False):
    """
    Moves given curves CVs together and maintaining their offset n world position
    :param curves: list(str)
    :param position:
    :param pivot_at_center: bool
    """

    curves = helpers.force_list(curves)
    for curve in curves:
        if curve.find('.cv[') > -1:
            curve_cvs = curve
            curve = component.get_curve_from_cv(curve)
        else:
            curve_cvs = '{}.cv[*]'.format(curve)
        if shape_utils.is_a_shape(curve):
            curve = cmds.listRelatives(curve, p=True)[0]
        if pivot_at_center:
            center_position = transform.get_center(curve_cvs)
        else:
            center_position = cmds.xform(curve, query=True, ws=True, rp=True)
        offset = vec3.vector_sub(position, center_position)
        cmds.move(offset[0], offset[1], offset[2], curve_cvs, ws=True, r=True)


def get_curve_line_thickness(curve_transform):
    """
    Returns the line thickness of the first curve shape under the given transform node
    :param curve_transform: str, transform we want to retrieve line width of
    :return: float, width of the given curve line
    """

    curve_shapes = filtertypes.filter_nodes_with_shapes(curve_transform, shape_type='nurbsCurve')
    if not curve_shapes:
        return 0

    return cmds.getAttr('{}.lineWidth'.format(curve_shapes[0]))


def set_curves_line_thickness(curve_transforms: list[str], line_width: int):
    """
    Sets the line width of the given curves.

    :param list[str] curve_transforms: curves we want to modify line width of.
    :param float line_width: new line width of the curves.
    """

    curve_shapes = filtertypes.filter_nodes_with_shapes(curve_transforms, shape_type='nurbsCurve')
    for curve in curve_shapes:
        cmds.setAttr(f'{curve}.lineWidth', line_width)


def get_curve_data(curve_shape, space=None):
    """
    Returns curve from the given shape node
    :param curve_shape: str, node that represents nurbs curve shape
    :param space:
    :return: dict
    """

    space = space or OpenMaya.MSpace.kObject

    if helpers.is_string(curve_shape):
        curve_shape = nodes.mobject(curve_shape)

    return api_curves.get_curve_data(curve_shape, space)


def find_shortest_path_between_curve_cvs(cvs_list):

    start = cvs_list[0]
    end = cvs_list[-1]
    curve = start.split('.')[0]

    obj_type = cmds.objectType(curve)
    if obj_type != 'nurbsCurve':
        return None

    numbers = [int(start.split("[")[-1].split("]")[0]), int(end.split("[")[-1].split("]")[0])]
    range_list = range(min(numbers), max(numbers) + 1)
    in_order = list()
    for i, num in enumerate(range_list):
        cv = '{}.cv[{}]'.format(curve, num)
        in_order.append(cv)
        if i == 0:
            continue

    return in_order
