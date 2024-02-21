#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related with Maya API curve nodes
"""

from __future__ import annotations

import copy
from typing import Dict

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.common.python import helpers
from tp.maya.om import plugs, nodes as om_nodes

SHAPE_INFO = {
    'cvs': (),
    'degree': 3,
    'form': 1,
    'knots': (),
    'matrix': (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    'outlinerColor': (0.0, 0.0, 0.0),
    'overrideColorRGB': (0.0, 0.0, 0.0),
    'overrideEnabled': False,
    'overrideRGBColors': False,
    'useOutlinerColor': False
}


class CurveCV(list):
    """
    Base class used to represent curve CVs
    """

    def ControlVWrapper(self):
        def wrapper(*args, **kwargs):
            f = self(*[a if isinstance(a, CurveCV) else CurveCV([a, a, a]) for a in args], **kwargs)
            return f
        return wrapper

    @ControlVWrapper
    def __mul__(self, other):
        return CurveCV([self[i] * other[i] for i in range(3)])

    @ControlVWrapper
    def __sub__(self, other):
        return CurveCV([self[i] - other[i] for i in range(3)])

    @ControlVWrapper
    def __add__(self, other):
        return CurveCV([self[i] + other[i] for i in range(3)])

    def __imul__(self, other):
        return self * other

    def __rmul__(self, other):
        return self * other

    def __isub__(self, other):
        return self - other

    def __rsub__(self, other):
        return self - other

    def __iadd__(self, other):
        return self + other

    def __radd__(self, other):
        return self + other

    @staticmethod
    def mirror_vector():
        return {
            None: CurveCV([1, 1, 1]),
            'None': CurveCV([1, 1, 1]),
            'XY': CurveCV([1, 1, -1]),
            'YZ': CurveCV([-1, 1, 1]),
            'ZX': CurveCV([1, -1, 1])
        }

    def reorder(self, order):
        """
        With a given order sequence CVs will be reordered (for axis order purposes)
        :param order: list(int)
        """

        return CurveCV([self[i] for i in order])


def get_curve_data(curve_shape, space=None, color_data=True, normalize: bool = True, parent=None):
    """
    Returns curve data from the given shape node.

    :param str or OpenMaya.MObject curve_shape: node that represents nurbs curve shape
    :param OpenMaya.MSpace space: MSpace, coordinate space to query the point data
    :param bool color_data: whether to include curve data.
    :param bool normalize: whether to normalize curve data, so it fits in first Maya grid quadrant.
    :param str or OpenMaya.MObject or None parent: optional parent for the curve.
    :return: curve data as a dictionary.
    :rtype: dict
    """

    if helpers.is_string(curve_shape):
        curve_shape = om_nodes.mobject(curve_shape)
    if parent and helpers.is_string(parent):
        parent = om_nodes.mobject(parent)

    space = space or OpenMaya.MSpace.kObject
    shape = OpenMaya.MFnDagNode(curve_shape).getPath()
    data = om_nodes.node_color_data(shape.node()) if color_data else dict()
    curve = OpenMaya.MFnNurbsCurve(shape)
    if parent:
        parent = OpenMaya.MFnDagNode(parent).getPath().partialPathName()

    curve_cvs = map(tuple, curve.cvPositions(space))
    curve_cvs = [cv[:-1] for cv in curve_cvs]       # OpenMaya returns 4 elements in the cvs, ignore last one

    if normalize:
        mx = -1
        for cv in curve_cvs:
            for p in cv:
                if mx < abs(p):
                    mx = abs(p)
        curve_cvs = [[p / mx for p in pt] for pt in curve_cvs]

    data.update({
        'knots': tuple(curve.knots()),
        'cvs': curve_cvs,
        'degree': int(curve.degree),
        'form': int(curve.form),
        'matrix': tuple(om_nodes.world_matrix(curve.object())),
        'shape_parent': parent
    })

    return data


def serialize_transform_curve(
        node: OpenMaya.MObject, space: OpenMaya.MSpace | None = None, color_data: bool = True,
        normalize: bool = True) -> Dict:
    """
    Serializes given transform shapes curve data and returns a dictionary with that data.

    :param OpenMaya.MObject node: object that represents the transform above the nurbsCurve shapes we want to serialize.
    :param OpenMaya.MSpace or None space: coordinate space to query the point data.
    :param bool color_data: whether to include or not color curve related data.
    :param bool normalize: whether to normalize curve data, so it fits in first Maya grid quadrant.
    :return: curve shape data.
    :rtype: Dict
    """

    space = space or OpenMaya.MSpace.kObject
    shapes = om_nodes.shapes(OpenMaya.MFnDagNode(node).getPath(), filter_types=OpenMaya.MFn.kNurbsCurve)
    data = dict()
    for shape in shapes:
        shape_dag = OpenMaya.MFnDagNode(shape.node())
        is_intermediate = shape_dag.isIntermediateObject
        if not is_intermediate:
            curve_data = get_curve_data(shape, space=space, color_data=color_data, normalize=normalize)
            curve_data['outlinerColor'] = tuple(curve_data.get('outlinerColor', ()))
            if len(curve_data['outlinerColor']) > 3:
                curve_data['outlinerColor'] = curve_data['outlinerColor'][:-1]
            curve_data['overrideColorRGB'] = tuple(curve_data.get('overrideColorRGB', ()))
            if len(curve_data['overrideColorRGB']) > 3:
                curve_data['overrideColorRGB'] = curve_data['overrideColorRGB'][:-1]
            data[OpenMaya.MNamespace.stripNamespaceFromName(shape_dag.name())] = curve_data

    return data


def iterate_curve_points(dag_path, count, space=None):
    """
    Generator function that iterates given DAG path pointing a curve shape node, containing the position, normal and
    tangent for the curve in the given point count.

    :param OpenMaya.MDagPATH dag_path: dagPath to the curve shape node
    :param int count: point count to generate
    :param OpenMaya.MSpace space: coordinate space to query the point data
    :return: position, normal and tangent of the curve points
    :rtype: tuple(MVector, MVector, MVector),
    """

    space = space or OpenMaya.MSpace.kObject
    curve_fn = OpenMaya.MFnNurbsCurve(dag_path)
    length = curve_fn.length()
    distance = length / float(count - 1)
    current = 0.001
    default_normal = [1.0, 0.0, 0.0]
    default_tangent = [0.0, 1.0, 0.0]
    max_param = curve_fn.findParamFromLength(length)
    for i in range(count):
        param = curve_fn.findParamFromLength(current)
        # Maya fails to get the normal when the param is the max param, so we sample with a slight offset
        if param == max_param:
            param = max_param - 0.0001
        point = OpenMaya.MVector(curve_fn.getPointAtParam(param, space=space))
        try:
            yield point, curve_fn.normal(param), curve_fn.tangent(param)
        except RuntimeError:
            # In flat curves (Y pointing completely up), exception is raised and normal is [1.0, 0.0, 0.0} and tangent
            # is [0.0, 1.0, 0.0
            yield point, default_normal, default_tangent
        current += distance


def mirror_curve_cvs(curve_obj, axis='x', space=None):
    """
    Mirrors the given curve transform shape CVs by the given axis.

    :param OpenMaya.MObject curve_obj: curve transform to mirror
    :param str axis: axis to mirror ('x', 'y' or 'z')
    :param OpenMaya.MSpace space: space to mirror (MSpace.kObject, MSpace.kWorld)
    :return:
    """

    space = space or OpenMaya.MSpace.kObject
    axis = axis.lower()
    axis_dict = {'x': 0, 'y': 1, 'z': 2}
    axis_to_mirror = set(axis_dict[ax] for ax in axis)

    for shape in om_nodes.iterate_shapes(OpenMaya.MFnDagNode(curve_obj).getPath()):
        curve = OpenMaya.MFnNurbsCurve(shape)
        cvs = curve.cvPositions(space)
        for i in cvs:
            for ax in axis_to_mirror:
                i[ax] *= -1
        curve.setCVPositions(cvs)
        curve.updateCurve()


def match_curves(driver, targets, space=None):
    """
    Matches the curves from the driver to the targets.

    :param OpenMaya.MObject driver: transform node of the shape to match
    :param list(MObject) or tuple(MObject) targets: list of transforms that will have the shapes replaced
    :param OpenMaya.MSpace space: coordinate space to query the point data
    :return: list of matched shapes.
    :rtype: list(MObject)
    """

    space = space or OpenMaya.MSpace.kObject
    driver_data = serialize_transform_curve(driver, space=space)
    shapes = list()
    for target in targets:
        target_shapes = [om_nodes.name(i.node()) for i in om_nodes.iterate_shapes(OpenMaya.MDagPath.getAPathTo(target))]
        if target_shapes:
            cmds.delete(target_shapes)
        shapes.extend(create_curve_shape(driver_data, parent=target, space=space)[1])

    return shapes


def create_curve_shape(
        curve_data: dict, parent: OpenMaya.MObject | None = None, space: int | None =None, curve_size: float = 1.0,
        translate_offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        scale_offset: tuple[float, float, float] = (1.0, 1.0, 1.0), axis_order: str = 'XYZ',
        color: tuple[float, float, float] | None = None,
        mirror: bool | None = None) -> tuple[OpenMaya.MObject, list[OpenMaya.MObject]]:
    """
    Creates a NURBS curve based on the given curve data.

    :param dict curve_data: data, {"shapeName": {"cvs": [], "knots":[], "degree": int, "form": int, "matrix": []}}
    :param str or OpenMaya.MObject parent: transform that takes ownership of the curve shapes. If not parent is given a new
        transform will be created
    :param int space: coordinate space to set the point data
    :param float curve_size: global curve size offset.
    :param tuple[float, float, float] translate_offset: translate offset for the curve.
    :param tuple[float, float, float] scale_offset: scale offset for the curve.
    :param str axis_order: axis order for the curve.
    :param tuple[float, float, float] or None color: curve color.
    :param bool or None mirror: whether curve should be mirrored.
    :return: tuple containing the parent MObject and the list of MObject shapes
    :rtype: tuple[OpenMaya.MObject, list[OpenMaya.MObject]]
    """

    parent_inverse_matrix = OpenMaya.MMatrix()
    if parent is None:
        parent = OpenMaya.MObject.kNullObj
    else:
        if helpers.is_string(parent):
            parent = om_nodes.mobject(parent)
        if parent != OpenMaya.MObject.kNullObj:
            parent_inverse_matrix = om_nodes.world_inverse_matrix(parent)

    translate_offset = CurveCV(translate_offset)
    scale = CurveCV(scale_offset)
    order = [{'X': 0, 'Y': 1, 'Z': 2}[x] for x in axis_order]

    curves_to_create: dict[str, str] = {}
    for shape_name, shape_data in curve_data.items():
        if not isinstance(shape_data, dict):
            continue
        curves_to_create[shape_name] = []
        shape_parent = shape_data.get('shape_parent', None)
        if shape_parent:
            if shape_parent in curves_to_create:
                curves_to_create[shape_parent].append(shape_name)

    created_curves: list[str] = []
    all_shapes: list[OpenMaya.MObject] = []
    created_parents: dict[str, OpenMaya.MObject] = {}

    # If parent already has a shape with the same name we delete it
    # TODO: We should compare the bounding boxes of the parent shape and the new one and scale it to fit new bounding
    # TODO: box to the old one
    parent_shapes = []
    if parent and parent != OpenMaya.MObject.kNullObj:
        parent_shapes = om_nodes.shapes(OpenMaya.MFnDagNode(parent).getPath())

    for shape_name, shape_children in curves_to_create.items():

        for parent_shape in parent_shapes:
            if parent_shape.partialPathName() == shape_name:
                if not om_nodes.is_valid_mobject(parent_shape.node()):
                    continue
                cmds.delete(parent_shape.fullPathName())
                break

        if shape_name not in created_curves:
            shape_name, parent, new_shapes, new_curve = _create_curve(
                shape_name, curve_data[shape_name], space, curve_size, translate_offset, scale, order, color,
                mirror, parent, parent_inverse_matrix)
            created_curves.append(shape_name)
            all_shapes.extend(new_shapes)
            created_parents[shape_name] = parent

        for child_name in shape_children:
            if child_name not in created_curves:
                to_parent = created_parents[shape_name] if shape_name in created_parents else parent
                child_name, child_parent, new_shapes, new_curve = _create_curve(
                    child_name, curve_data[child_name], space, curve_size, translate_offset, scale, order, color,
                    mirror, OpenMaya.MObject.kNullObj, parent_inverse_matrix)
                created_curves.append(child_name)
                all_shapes.extend(new_shapes)
                created_parents[child_name] = child_parent
                om_nodes.set_parent(new_curve.parent(0), to_parent)

    return parent, all_shapes


def create_curve_from_points(
        name: str, points: list[list[float, float, float], ...], shape_dict: dict | None = None,
        parent: OpenMaya.MObject | None = None) -> tuple[OpenMaya.MObject, tuple[OpenMaya.MObject]]:
    """
    Creates a new curve from the given points and the given data curve info
    :param str name: name of the curve to create.
    :param list[list[float, float, float], ...] points: list of points for the curve.
    :param dict or None shape_dict: optional shape data.
    :param parent: MObject
    :return: the newly created curve transform and their shapes.
    :rtype: tuple[OpenMaya.MObject, tuple[OpenMaya.MObject]]
    """

    shape_dict = shape_dict or copy.deepcopy(SHAPE_INFO)

    if not name.lower().endswith('shape'):
        name = name + 'Shape'

    degree = shape_dict.get('degree', 3)

    deg = shape_dict['degree']
    shape_dict['cvs'] = points
    knots = shape_dict.get('knots')
    if not knots:
        if degree == 1:
            shape_dict['knots'] = tuple(range(len(points)))
        elif deg == 3:
            total_cvs = len(points)
            # append two zeros to the front of the knot count, so it lines up with maya specs
            # (ncvs - deg) + 2 * deg - 1
            knots = [0, 0] + list(range(total_cvs))
            # remap the last two indices to match the third from last
            knots[-2] = knots[len(knots) - degree]
            knots[-1] = knots[len(knots) - degree]
            shape_dict['knots'] = knots

    return create_curve_shape({name: shape_dict}, parent)


def _create_curve(
        shape_name, shape_data, space, curve_size, translate_offset, scale, order, color, mirror,
        parent, parent_inverse_matrix):
    new_curve = OpenMaya.MFnNurbsCurve()
    new_shapes = []

    # transform cvs
    curve_cvs = shape_data['cvs']
    transformed_cvs = []
    cvs = [CurveCV(pt) for pt in copy.copy(curve_cvs)]
    for i, cv in enumerate(cvs):
        cv *= curve_size * scale.reorder(order)
        cv += translate_offset.reorder(order)
        cv *= CurveCV.mirror_vector()[mirror]
        cv = cv.reorder(order)
        transformed_cvs.append(cv)

    cvs = OpenMaya.MPointArray()
    for cv in transformed_cvs:
        cvs.append(cv)
    degree = shape_data['degree']
    form = shape_data['form']
    knots = shape_data.get('knots', None)
    if not knots:
        knots = tuple([float(i) for i in range(-degree + 1, len(cvs))])

    enabled = shape_data.get('overrideEnabled', False) or color is not None
    if space == OpenMaya.MSpace.kWorld and parent != OpenMaya.MObject.kNullObj:
        for i in range(len(cvs)):
            cvs[i] *= parent_inverse_matrix
    shape = new_curve.create(cvs, knots, degree, form, False, False, parent)
    om_nodes.rename(shape, shape_name)
    new_shapes.append(shape)
    if parent == OpenMaya.MObject.kNullObj and shape.apiType() == OpenMaya.MFn.kTransform:
        parent = shape
    if enabled:
        plugs.set_plug_value(
            new_curve.findPlug('overrideEnabled', False), int(shape_data.get('overrideEnabled', bool(color))))
        colors = color or shape_data['overrideColorRGB']
        outliner_color = shape_data.get('outlinerColor', None)
        use_outliner_color = shape_data.get('useOutlinerColor', False)
        om_nodes.set_node_color(
            new_curve.object(), colors, outliner_color=outliner_color, use_outliner_color=use_outliner_color)

    return shape_name, parent, new_shapes, new_curve
