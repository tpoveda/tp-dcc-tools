#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related to shapes
"""

from __future__ import annotations

from typing import Sequence

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.OpenMaya as OpenMaya1
import maya.api.OpenMayaAnim as OpenMayaAnim

from tp.core import log
from tp.common.python import helpers
from tp.maya.cmds import exceptions, filtertypes, node as node_utils, name as name_utils
from tp.maya.om import nodes

logger = log.tpLogger

TYPE_DICT = {
    'mesh': 'vtx',
    'nurbsCurve': 'cv',
    'nurbsSurface': 'cv',
    'lattice': 'pt',
    'subdiv': 'smp'
}

GEO_OUTPUT = {
    'mesh': ['.outMesh', '.worldMesh'],
    'nurbsCurve': ['.local', '.worldSpace'],
    'nurbsSurface': ['.local', '.worldSpace'],
    'lattice': ['.latticeOutput', '.worldLattice'],
    'subdiv': ['.outSubdiv', '.worldSubdiv']
}

ALL_GEO = [
    'mesh',
    'nurbsSurface',
    'subdiv'
]

GEO_INPUT = {
    'mesh': '.inMesh',
    'nurbsCurve': '.create',
    'nurbsSurface': '.create',
    'lattice': '.latticeInput',
    'subdiv': '.create'
}


def check_shape(shape):
    """
    Checks if a node is a valid shape and raise a exception if the shape is not valid
    :param shape: str, name of the node to be checked
    :return: bool, True if the given node is a shape node
    """

    if not is_shape(shape):
        raise exceptions.ShapeException(shape)


def is_a_shape(node):
    """
    Checks node type to determine if the given node is a shape or not
    :param node: str
    :return: bool
    """

    if not cmds.objectType(node, isAType='shape'):
        return False

    return True


def is_shape(obj):
    """
    Check if the specified object is a valid shape node
    :param obj: str, object to check as a shape node
    :return: bool
    """

    if not cmds.objExists(obj):
        return False

    if not cmds.objectType(obj, isAType='shape'):
        return False

    mobj = nodes.mobject(obj)
    if not mobj.hasFn(OpenMaya.MFn.kShape):
        return False

    return True


def get_shapes_types_with_color():
    """
    Returns a list Maya shapes types that can contain color
    :return: list(str)
    """

    shapes_with_color = ['nurbsCurve', 'locator', 'mesh', 'nurbsSurface', 'camera', 'light']
    shapes_with_color.extend(filtertypes.TYPE_FILTERS.get(filtertypes.DEFORMER_FILTER_TYPE, list()))

    return shapes_with_color


def has_intermediate(geo):

    """
    Checks if the specified geometry has any intermediate shapes
    :param geo: str, transform to check intermediate shapes for
    """

    return bool(len(list_intermediates(geo)))


def list_intermediates(geo):
    """
    Return a list of intermediate shapes under a transform parent
    :param geo: str, transform to list intermediate shapes for
    """

    if not cmds.objExists(geo):
        raise exceptions.NodeExistsException(geo)
    if is_shape(geo):
        geo = cmds.listRelatives(geo, parent=True, path=True)[0]

    # Get intermediate shapes
    shapes = cmds.listRelatives(geo, shapes=True, noIntermediate=True, path=True)
    all_shapes = cmds.listRelatives(geo, shapes=True, path=True)
    if not all_shapes:
        return []
    if not shapes:
        return all_shapes
    intermediate_shapes = list(set(all_shapes) - set(shapes))

    return intermediate_shapes


def get_first_shape(node):
    """
    Returns the first active shape on a given transform
    :param node: str, transform node to get shape from
    :return: str
    """

    shapes = get_shapes(node_name=node, non_intermediates=True, intermediates=False)
    if shapes:
        return shapes[0]

    return None


def get_shapes(node_name, non_intermediates=True, intermediates=True, full_path=True):
    """
    Returns a list of shapes under a transform parent
    :param node_name: str, transform to list parent for
    :param non_intermediates: bool, list non-intermediate shapes
    :param intermediates: bool, list intermediate shapes
    :param full_path: bool, Whether to return long names or not
    :return: list
    """

    if node_name is None or not cmds.objExists(node_name):
        raise exceptions.NodeExistsException(node_name)

    if is_shape(node_name):
        parent = cmds.listRelatives(node_name, parent=True, fullPath=full_path)
        return cmds.listRelatives(parent, shapes=True, fullPath=True, ni=non_intermediates)
        # node_name = cmds.listRelatives(node_name, parent=True, path=True)[0]

    # Get shapes
    shapes = list()
    if non_intermediates:
        non_intermediate_shapes = cmds.listRelatives(node_name, shapes=True, noIntermediate=True, path=True)
        if non_intermediate_shapes:
            shapes.extend(non_intermediate_shapes)
    if intermediates:
        shapes.extend(list_intermediates(node_name))

    return shapes


def get_shape_node_type(node_name):
    """
    Returns the node type of the given node
    :param node_name: str, name of a maya node
    :return: str
    """

    shapes = get_shapes(node_name)
    if shapes:
        return cmds.nodeType(shapes[0])


def get_shapes_of_type(node_name, shape_type=None, full_path=True, no_intermediate=False):
    """
    Returns a list of shapes under a transform parent
    :param node_name: str, transform to list parent for
    :param shape_type: str, shape type to get.
    :param bool full_path:
    :param bool no_intermediate: list non-intermediate shapes
    :return: list
    """

    if node_utils.is_a_shape(node_name):
        parent = cmds.listRelatives(node_name, p=True, f=full_path)
        return cmds.listRelatives(parent, s=True, f=full_path, ni=no_intermediate)

    if shape_type:
        return cmds.listRelatives(node_name, s=True, f=full_path, type=shape_type, ni=no_intermediate)
    else:
        return cmds.listRelatives(node_name, s=True, f=full_path, ni=no_intermediate)


def get_shapes_generator(mobj):
    """
    Returns a generator of all shape nodes for the provided transform node
    :param mobj: MObject, MObject to get teh shape nodes of
    :return: generator
    """

    # TODO: Make this function to work with OpenMaya2

    if not mobj.apiType() == OpenMaya.MFn.kTransform:
        return

    path = OpenMaya1.MDagPath.getAPathTo(mobj)
    num_shapes = OpenMaya1.MScriptUtil()
    num_shapes.createFromInt(0)
    num_shapes_ptr = num_shapes.asUintPtr()
    path.numberOfShapesDirectlyBelow(num_shapes_ptr)
    for index in range(OpenMaya1.MScriptUtil(num_shapes_ptr).asUint()):
        p = OpenMaya1.MDagPath.getAPathTo(mobj)
        p.extendToShapeDirectlyBelow(index)
        yield p.node()


def get_transform(mobj):
    """
    Returns the first transform node of the provided shape node
    If the mobj is already a transform node, its returned
    :param mobj: OpenMaya.MObject, MObject to get transform node of
    :return: OpenMaya.MObject
    """

    if not nodes.is_dag_node(mobj):
        return mobj

    path = OpenMaya.MDagPath.getAPathTo(mobj)
    new_ptr = path.transform()
    if new_ptr != mobj:
        return new_ptr

    return mobj


def rename(geo):
    """
    Rename shape nodes based on the parent transform node
    :param geo: str, transform to rename shapes for
    :return: list, renamed shapes
    """

    shapes = get_shapes(geo)
    if not shapes:
        return []

    # Rename shapes
    for i in range(len(shapes)):
        shape_type = cmds.objectType(shapes[i])

        # Rename temporary shapes so hash index (#) is accurate
        shapes[i] = cmds.rename(shapes[i], geo + 'ShapeTMP')

        if shape_type == 'nurbsCurve':
            shapes[i] = cmds.rename(shapes[i], geo + 'CrvShape#')
        elif shape_type == 'nurbsSurface':
            shapes[i] = cmds.rename(shapes[i], geo + 'SrfShape#')
        elif shape_type == 'mesh':
            shapes[i] = cmds.rename(shapes[i], geo + 'MeshShape#')
        else:
            shapes[i] = cmds.rename(shapes[i], geo + 'Shape#')

    return shapes


def shape_input_attr(shape):
    """
    Returns the shape input attribute
    :param shape:  str, shape node to find the shape input attribute for
    :return: str, attr
    """

    check_shape(shape)

    # Determine shape input plug
    shp_input_attr = ''
    shp_input_type = cmds.objectType(shape)
    shp_input_dict = {
        'mesh': 'inMesh',
        'nurbsCurve': 'create',
        'nurbsSurface': 'create',
        'lattice': 'latticeInput',
        'subdiv': 'create'
    }
    if shp_input_type in shp_input_dict:
        shp_input_attr = shp_input_dict[shp_input_type]
    else:
        raise Exception(shp_input_attr)

    return shp_input_attr


def shape_output_attr(shape, world_space=True):
    """
    Returns the shape output attribute
    :param shape: str, shape node to find the shape output attribute for
    :param world_space: bool, return world space output attribute if exists
    :return: attr, str
    """

    check_shape(shape)

    # Determine shae output plug
    shp_output_attr = ''
    shp_output_type = cmds.objectType(shape)
    shp_output_dict = {
        'mesh': ['outMesh', 'worldMesh'],
        'nurbsCurve': ['local', 'worldSpace'],
        'nurbsSurface': ['local', 'worldSpace'],
        'lattice': ['latticeOutput', 'worldLattice'],
        'subdiv': ['outSubdiv', 'worldSubdiv']
    }
    if shp_output_type in shp_output_dict:
        shp_output_attr = shp_output_dict[shp_output_type][int(world_space)]
    else:
        raise Exception(shp_output_attr)

    return shp_output_attr


def shape_input_source(shape):
    """
    Returns the shape input source plug. If not input exists, returns an empty string
    :param shape: str, shape node to find shape input source for
    :return: str
    """

    check_shape(shape)

    # Determine shape input plug and shape input source plug
    shape_in_attr = shape_input_attr(shape)
    shape_in_plug = ''
    shape_in_source = cmds.listConnections(shape + '.' + shape_in_attr, source=True, destination=False, plugs=True)
    if shape_in_source:
        shape_in_plug = shape_in_source[0]

    return shape_in_plug


def find_input_shape(obj, recursive=False, print_exceptions=False):
    """
    Returns the input shape for the specified shape node or transform
    :param obj: str, shape/transform node to find the corresponding input shape for
    :param recursive: bool, True if you want to change shape in a recursive way
    :param print_exceptions: bool, True if you want print exceptions while recursive searchhing
    :return: str
    """

    input_shape = None

    if not input_shape:
        try:
            input_shape = find_input_shape_1(obj)
        except Exception as e:
            if print_exceptions:
                logger.exception('Caught exception: {}'.format(str(e)))
    if not input_shape:
        try:
            input_shape = find_input_shape_2(obj)
        except Exception as e:
            if print_exceptions:
                logger.exception('Caught exception: {}'.format(str(e)))

    # Check if input shape is valid
    if not input_shape:
        raise exceptions.ShapeException(obj)

    # Do recursion if necessary
    # TODO: Limit the recursion to a maximum number of times to avoid infinit loops
    if recursive:
        while input_shape != find_input_shape(input_shape):
            input_shape = find_input_shape(input_shape)

    return input_shape


def find_input_shape_1(shape):
    """
    Returns the orig input shape (...ShapeOrig') for the specified shape node based on deformer data
    This function assumes that the specified shape is affected by at least one valid deformer
    :param shape: str, shape node to find the corresponding input shape for
    :return:  str
    """

    # Get MObject for shape
    shape_obj = nodes.mobject(shape)

    # Get inMesh connection attribute
    in_conn = cmds.listConnections(shape, source=True, destination=False)
    if not in_conn:
        return shape

    # Find connected deformer
    deformer_history = cmds.ls(cmds.listHistory(shape), type='geometryFilter')
    if not deformer_history:
        raise exceptions.ShapeValidDeformerAffectedException(shape)
    deformer_obj = nodes.mobject(deformer_history[0])

    # Get deformer function set
    deformer_fn = OpenMayaAnim.MFnGeometryFilter(deformer_obj)

    # Get input shape deformer
    geom_index = deformer_fn.indexForOutputShape(shape_obj)
    input_shape_obj = deformer_fn.inputShapeAtIndex(geom_index)

    return OpenMaya.MFnDagNode(input_shape_obj).partialPathName()


def find_input_shape_2(shape):
    """
    Determine the input shape for the specified geometry based on construction history
    :param shape: str, shape node to find the corresponding input shape for
    :return: str
    """

    transform = cmds.listRelatives(shape, parent=True, path=True) or []

    if node_utils.is_type(shape, 'transform'):
        transform = [shape]
        shapes = cmds.listRelatives(shape, shapes=True, noIntermediate=True, path=True)
        if not shapes:
            raise exceptions.ShapeFromTransformException(shape)
        shape = shapes[0]

    # Get all shapes and type
    all_shapes = cmds.listRelatives(transform[0], shapes=True, path=True)
    shape_type = cmds.objectType(shape)

    # Get shape history and check it
    shape_history = cmds.listRelatives(cmds.listHistory(shape), type=shape_type)
    if shape_history.count(shape):
        shape_history.remove(shape)
    if not shape_history:
        raise exceptions.ShapeHistoryException(shape)
    if len(shape_history) == 1:
        input_shape = shape_history[0]
    else:
        shape_input = list(set(shape_history).intersection(set(all_shapes)))
        if shape_input:
            input_shape = shape_input[0]
        else:
            input_shape = shape_history[0]

    return input_shape


def find_orig_shape(shape):
    """
    Returns the orig input shape (...ShapeOrig') for the specified shape node based on deformer data
    This function assumes that the specified shape is affected by at least one valid deformer
    :param shape: str, shape node to find the corresponding input shape for
    :return:  str
    """

    return find_input_shape_1(shape)


def get_components_from_shapes(shapes=None):
    """
    Get the components from a list of shapes
    NOTE: Only supports CV and Vertex Components
    :param shapes: list<str>, list of shapes to retrieve components from
    :return: list<str>, components of the given shapes
    """

    comps = list()
    if shapes:
        for shape in shapes:
            found_comps = None
            if cmds.nodeType(shape) == 'nurbsSurface':
                found_comps = '%s.cv[*]' % shape

            if cmds.nodeType(shape) == 'nurbsCurve':
                found_comps = '%s.cv[*]' % shape

            if cmds.nodeType(shape) == 'mesh':
                found_comps = '%s.vtx[*]' % shape

            if found_comps:
                comps.append(found_comps)

    return comps


def rename_shapes(transform_node=None):
    """
    Rename all shapes under the given transform to match the name of the transform
    :param transform_node: str, name of a transform
    """

    renamed_shapes = list()

    transform_node = helpers.force_list(transform_node or cmds.ls(sl=True, long=True))
    for node in transform_node:
        node_shapes = list()
        short_name = name_utils.get_short_name(node)
        shapes = get_shapes(node)
        if shapes:
            node_shapes.append(cmds.rename(shapes[0], '{}Shape'.format(short_name)))
            if len(shapes) > 1:
                i = 1
                for s in shapes[1:]:
                    node_shapes.append(cmds.rename(s, '{}Shape{}'.format(short_name, i)))
                    i += 1
            renamed_shapes.append(node_shapes)

    return renamed_shapes


def get_shapes_in_hierarchy(
        transform_node, shape_type='', return_parent=False, skip_first_relative=False,
        full_path=True, intermediate_shapes=False):
    """
    Get all the shapes in the child hierarchy excluding intermediates shapes
    :param transform_node: str, name of a transform
    :param shape_type: str, shape types we want to retrieve
    :param return_parent: bool, Whether to return parent node also or not
    :param skip_first_relative: bool
    :param full_path: str
    :param intermediate_shapes: bool
    :return: list<str, list of shape nodes
    """

    hierarchy = [transform_node]
    relatives = cmds.listRelatives(transform_node, ad=True, type='transform', f=full_path)
    if relatives:
        hierarchy.extend(relatives)
    if skip_first_relative:
        hierarchy = hierarchy[1:]

    shapes = list()

    for child in hierarchy:
        found_shapes = get_shapes_of_type(node_name=child, shape_type=shape_type)
        sifted_shapes = list()
        if not found_shapes:
            continue
        for found_shape in found_shapes:
            if not intermediate_shapes:
                if cmds.getAttr('{}.intermediateObject'.format(found_shape)):
                    continue
            if return_parent:
                found_shape = child
            sifted_shapes.append(found_shape)

        if sifted_shapes:
            shapes.extend(sifted_shapes)

    return shapes


def has_shape_of_type(node, shape_type):
    """
    Checks whether the given node has a shape of the given type
    :param node: str, name of a node
    :param shape_type: str, shape type (mesh, nurbsCurve or any Maya shape type)
    :return: bool
    """

    has_shape = None

    if cmds.objExists(node):
        has_shape = node

    if not cmds.objectType(node, isAType='shape'):
        shapes = get_shapes(node)
        if shapes:
            has_shape = shapes[0]

    if has_shape:
        if shape_type == cmds.nodeType(has_shape):
            return True

    return False


def scale_shapes(node, scale, use_pivot=True, relative=True):
    """
    Scales shapes of given transform node
    :param node:
    :param scale: variant, float || list<float, float, float>
    :param use_pivot:
    :param relative:
    :return:
    """

    shapes = get_shapes(node, intermediates=False, full_path=True)
    comps = get_components_from_shapes(shapes)
    if use_pivot:
        pivot = cmds.xform(node, query=True, rp=True, ws=True)
    else:
        from tp.maya.cmds import transform
        bounding_box = transform.BoundingBox(comps)
        pivot = bounding_box.get_center()

    if comps:
        if type(scale) in [list, tuple]:
            if relative:
                cmds.scale(scale[0], scale[1], scale[2], comps, pivot=pivot, r=True)
            else:
                cmds.scale(scale[0], scale[1], scale[2], comps, pivot=pivot, a=True)
        else:
            if relative:
                cmds.scale(scale, scale, scale, comps, pivot=pivot, r=True)
            else:
                cmds.scale(scale, scale, scale, comps, pivot=pivot, a=True)


def filter_shapes_in_list(nodes_list, shapes_node_type_list=None):
    """
    Filters given Maya nodes leaving only shapes and filtered by the given shapes_node_list
    :param nodes_list: list(str), list of Maya nodes list
    :param shapes_node_type_list: list(str), filtered shape nodes list
    :return: list(str)
    """

    shapes_list = list()
    if not nodes_list:
        return shapes_list

    shapes_node_type_list = shapes_node_type_list or get_shapes_types_with_color()
    shapes_child_list = cmds.listRelatives(nodes_list, shapes=True, type=shapes_node_type_list, fullPath=True)

    shapes_node_list = list()
    for node in nodes_list:
        node_type = cmds.nodeType(node)
        if node_type in shapes_node_type_list:
            shapes_node_list.append(node)

    if shapes_node_list:
        if shapes_child_list:
            all_nodes = list(set(shapes_node_list + shapes_child_list))
            shapes_list.extend(all_nodes)
        else:
            shapes_list.extend(shapes_node_list)
    elif shapes_child_list:
        shapes_list.extend(shapes_child_list)

    return shapes_list


def translate_shape_cvs(nurbs_shape: str, translate_list: Sequence[float, float, float]):
    """
    Translates given shape node by the given XYZ translation without affecting shape transform.

    :param str nurbs_shape: shape node name.
    :param Sequence[float, float, float] translate_list: XYZ translation as list.
    """

    return cmds.move(
        translate_list[0], translate_list[1], translate_list[2], '{}.cv[*]'.format(nurbs_shape),
        relative=True, objectSpace=True, worldSpaceDistance=True)


def rotate_shape_cvs(
        nurbs_shape: str, rotate_list: Sequence[float, float, float], relative: bool = True,
        object_center_pivot: bool = True):
    """
    Rotates given shape node by the given XYZ rotation without affecting shape transform.

    :param str nurbs_shape: shape node name.
    :param Sequence[float, float, float] rotate_list: XYZ rotation as list.
    :param bool relative: whether to rotate CVs relative to the object space.
    :param bool object_center_pivot: whether to rotate the objects with the pivot centered in the object or the world.
    """

    return cmds.rotate(
        rotate_list[0], rotate_list[1], rotate_list[2], '{}.cv[*]'.format(nurbs_shape),
        objectCenterPivot=object_center_pivot, relative=relative)


def scale_shape_cvs(nurbs_shape: str, scale_list: Sequence[float, float, float]):
    """
    Scales given node by the given XYZ scale without affecting shape transform.

    :param str nurbs_shape: shape node name.
    :param Sequence[float, float, float] scale_list: XYZ scale as list.
    """

    return cmds.scale(scale_list[0], scale_list[1], scale_list[2], '{}.cv[*]'.format(nurbs_shape))


def translate_nodes_cvs(node_names: list[str], translate_list: Sequence[float, float, float]):
    """
    Translates given node shape CVSs by the given XYZ translation without affecting shape transform.

    :param list[str] node_names: list of node names.
    :param Sequence[float, float, float] translate_list: XYZ translation as list.
    """

    shapes_list = filtertypes.filter_transforms_shapes(node_names, shape_type='nurbsCurve')
    for shape in shapes_list:
        translate_shape_cvs(shape, translate_list)


def rotate_nodes_cvs(
        node_names: list[str], rotate_list: Sequence[float, float, float], relative: bool = True,
        object_center_pivot: bool = True):
    """
    Rotates given node shape CVs by the given XYZ rotation without affecting shape transform.

    :param list[str] node_names: list of node names.
    :param Sequence[float, float, float] rotate_list: XYZ rotation as list.
    :param bool relative: whether to rotate CVs relative to the object space or not.
    :param bool object_center_pivot: whether to rotate the objects with the pivot centered in the object or the world.
    """

    shapes_list = filtertypes.filter_transforms_shapes(node_names, shape_type='nurbsCurve')
    for shape in shapes_list:
        rotate_shape_cvs(shape, rotate_list, relative=relative, object_center_pivot=object_center_pivot)


def scale_nodes_cvs(node_names: list[str], scale_list: Sequence[float, float, float]):
    """
    Scales given node shape CVs by the given XYZ scale without affecting shape transform.

    :param list[str] node_names: list of node names.
    :param Sequence[float, float, float] scale_list: XYZ scale as list.
    """

    shapes_list = filtertypes.filter_transforms_shapes(node_names, shape_type='nurbsCurve')
    for shape in shapes_list:
        scale_shape_cvs(shape, scale_list)


def translate_selected_nodes_cvs(translate_list: Sequence[float, float, float]):
    """
    Translates current selected nodes shapes CVSs by the given XYZ translation without affecting shape transform.

    :param Sequence[float, float, float] translate_list: XYZ translation as list.
    """

    selected_nodes = cmds.ls(sl=True, long=True)
    if not selected_nodes:
        return

    return translate_nodes_cvs(selected_nodes, translate_list)


def rotate_selected_nodes_cvs(
        rotate_list: Sequence[float, float, float], relative: bool = True, object_center_pivot: bool = True):
    """
    Rotates current selected nodes shapes CVs by the given XYZ rotation without affecting shape transform.

    :param Sequence[float, float, float] rotate_list: XYZ rotation as list.
    :param bool relative: whether to rotate CVs relative to the object space or not.
    :param bool object_center_pivot: whether to rotate the objects with the pivot centered in the object or the world.
    """

    selected_nodes = cmds.ls(sl=True, long=True)
    if not selected_nodes:
        return

    return rotate_nodes_cvs(
        selected_nodes, rotate_list, relative=relative, object_center_pivot=object_center_pivot)


def scale_selected_nodes_cvs(scale_list: Sequence[float, float, float]):
    """
    Scales current selected nodes shapes CVs by the given XYZ scale without affecting shape transform.

    :param Sequence[float, float, float] scale_list: XYZ scale as list.
    """

    selected_nodes = cmds.ls(sl=True, long=True)
    if not selected_nodes:
        return

    return scale_nodes_cvs(selected_nodes, scale_list)
