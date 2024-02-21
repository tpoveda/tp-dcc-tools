#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related to nodes
"""

from __future__ import annotations

import re
import uuid
from typing import Sequence

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.common.python import helpers, name, color
from tp.maya.cmds import exceptions, color as maya_color, namespace as namespace_utils

logger = log.tpLogger


def is_a_shape(node_name):
    """
    Returns whether a given node name is a shape node
    :param node_name: str, name of a Maya node
    :return: bool
    """

    if cmds.objectType(node_name, isAType='shape'):
        return True

    return False


def is_a_transform(node_name):
    """
    Check if the specified object is a valid transform node
    :param node_name: str, object to check as a transform node
    :return: bool
    """

    if not cmds.objExists(node_name):
        return False

    if not cmds.objectType(node_name, isAType='transform'):
        return False

    return True


def is_referenced(node_name):
    """
    Returns whether a given node name is referenced or not
    :param node_name: str, name of a Maya node
    :return: bool
    """

    if not node_name:
        return False
    if not cmds.objExists(node_name):
        return False
    is_node_referenced = cmds.referenceQuery(node_name, isNodeReferenced=True)

    return is_node_referenced


def is_empty(node_name, no_user_attributes=True, no_connections=True):
    """
    Returns whether a given node is an empty one (is not referenced, has no child transforms,
    has no custom attributes and has no connections)
    :param node_name: str, name of a Maya node
    :param no_user_attributes: bool
    :param no_connections: bool
    :return: bool
    """

    if is_referenced(node_name=node_name):
        return False

    if is_a_transform(node_name=node_name):
        relatives = cmds.listRelatives(node_name)
        if relatives:
            return False

    if no_user_attributes:
        attrs = cmds.listAttr(node_name, userDefined=True, keyable=True)
        if attrs:
            return False

    default_nodes = ['defaultLightSet', 'defaultObjectSet', 'initialShadingGroup', 'uiConfigurationScriptNode',
                     'sceneConfigurationScriptNode']
    if node_name in default_nodes:
        return False

    if no_connections:
        connections = cmds.listConnections(node_name)
        if connections != ['defaultRenderGlobals']:
            if connections:
                return False

    return True


def is_undeletable(node_name):
    """
    Returns whether a given node is deletable or not
    :param node_name: str, name of a Maya node
    :return: bool
    """

    try:
        nodes = cmds.ls(undeletable=True)
        if node_name in nodes:
            return True
    except Exception:
        return False

    return False


def is_unique(node_name):
    """
    Returns whether a given node is unique or not
    :param node_name: str, name of Maya node
    :return: bool
    """

    scope = cmds.ls(node_name)
    count = len(scope)
    if count > 1:
        return False
    elif count == 1:
        return True

    return True


def root_node(node_name, node_type):
    """
    Recursively traverses up the hierarchy until finding the first object that does not have a parent.

    :param str node_name: node name to get root of.
    :param str node_type: node type for the root node.
    :return: found root node.
    :rtype: str
    """

    parent = helpers.first_in_list(cmds.listRelatives(node_name, parent=True, type=node_type))
    return root_node(parent, node_type) if parent else node_name


def node_types(nodes, return_shape_type=True):
    """
    Returns the Maya node type for the given nodes
    :param nodes: list<str>, list of nodes we want to check types of
    :param return_shape_type: bool, Whether to check shape type or not
    :return: dict<str>, [node_type_name], node dictionary of matching nodes
    """

    from tp.maya.cmds import shape

    nodes = helpers.force_list(nodes)

    found_type = dict()

    for n in nodes:
        node_type = cmds.nodeType(n)
        if node_type == 'transform':
            if return_shape_type:
                shapes = shape.shapes(n)
                if shapes:
                    node_type = cmds.nodeType(shapes[0])
        if node_type not in found_type:
            found_type[node_type] = list()

        found_type[node_type].append(n)

    return found_type


def update_uuid(node_name):
    """
    Updates the unique identifier of the given Maya node
    :param node_name: str
    :return:
    """

    ids = list()
    for attr in cmds.ls('*.uuid'):
        node_id = cmds.getAttr(attr)
        ids.append(node_id)

    uuid_attr = node_name + '.uuid'
    if not cmds.objExists(uuid_attr):
        cmds.addAttr(node_name, longName='uuid', dataType='string')
        new_id = str(uuid.uuid4())
        ids.append(new_id)
    else:
        existing_id = cmds.getAttr(uuid_attr)
        if existing_id not in ids:
            ids.append(existing_id)
            return
        new_id = str(uuid.uuid4())
    cmds.setAttr(uuid_attr, new_id, type='string')


def check_node(node):
    """
    Checks if a node is a valid node and raise and exception if the node is not valid
    :param node: str | MObject, name of the node to be checked or MObject to be checked
     :return: bool, True if the given node is valid
    """

    return cmds.objExists(node)


def is_type(node_name, node_type):
    """
    Checks if the input object has the specified node type
    :param node_name: str, Name of the node
    :param node_type: str, Node type
    :return: bool, True if the node is the same type of the passed type or False otherwise
    """

    if not cmds.objExists(node_name):
        return False
    if cmds.objectType(node_name) != node_type:
        return False
    return True


def verify_node(node, node_type):
    """
    Run standard checks on the specified node. Raise an exception if any checks fail
    :param node: str, Node name of the node to verify
    :param node_type: Node type
    :return: bool, True if the ndoe is valid or False otherwise
    """

    check_node(node)

    # Check node type
    obj_type = cmds.objectType(node)
    if obj_type != node_type:
        raise exceptions.NodeException(node, node_type)


def is_visible(node, check_lod_vis=True, check_draw_override=True):
    """
    Checks if a specified DAG node is visibility by checking visibility of all ancestor nodes
    :param node: str, Node name of the node to verify
    :param check_lod_vis: bool, Check LOD visibility
    :param check_draw_override: bool, Check drawing override visibility
    :return: bool, True if the node is visible or False otherwise
    """

    check_node(node)

    if not cmds.ls(node, dag=True):
        raise exceptions.DagNodeException(node)

    full_path = cmds.ls(node, long=True)[0]
    path_part = full_path.split('|')
    path_part.reverse()

    # Check visibility
    is_visible_ = True
    for part in path_part:

        # Skip unknown nodes
        if not part:
            continue
        if not cmds.objExists(part):
            logger.debug('Unable to find ancestor node {}!'.format(part))
            continue

        if not cmds.getAttr(part + '.visibility'):
            is_visible_ = False
        if check_lod_vis:
            if not cmds.getAttr(part + '.lodVisibility'):
                is_visible_ = False
        if check_draw_override:
            if cmds.getAttr(part + '.overrideEnabled'):
                if not cmds.getAttr(part + '.overrideVisibility'):
                    return False

        return is_visible_


def namespace(node_name, check_node=True, clean=False):
    """
    Returns namespace of the given node
    :param node_name: str
    :param check_node: bool
    :param clean: bool
    :return: str
    """

    if is_referenced(node_name):
        try:
            found_namespace = cmds.referenceQuery(node_name, namespace=True)
        except Exception as exc:
            found_namespace = namespace_utils.namespace(node_name, check_obj=check_node)
    else:
        found_namespace = namespace_utils.namespace(node_name, check_obj=check_node)
    if not found_namespace:
        return None

    if clean:
        if found_namespace.startswith('|') or found_namespace.startswith(':'):
            found_namespace = found_namespace[1:]

    return found_namespace


def mdag_path(node_name):
    """
    Takes an object name as a string and returns its MDAGPath.

    :param OpenMaya.MObject node_name: Maya object instance to get DAG path of.
    :return: DAG Path.
    :rtype: str
    """

    check_node(node_name)

    selection_list = OpenMaya.MGlobal.getSelectionListByName(node_name)
    dag_path = selection_list.getDagPath(0)

    return dag_path


def depend_node(node_name):
    """
    Returns the dependency node instance of the given node name.

    :param str node_name: name of the node.
    :return: Depend node instance.
    :rtype: OpenMaya.MFnDependencyNode
    """

    check_node(node_name)

    selection_list = OpenMaya.MSelectionList()
    selection_list.add(node_name)
    dep_node = selection_list.getDependNode(0)

    return dep_node


def plug(node_name, plug_name):
    """
    Get the plug of given Maya node name.

    :param str node_name: name of the node.
    :param str plug_name: name of the plug.
    :rtype: OpenMaya.MPlug
    """

    check_node(node_name)

    mobj = depend_node(node_name)
    dep_fn = OpenMaya.MFnDependencyNode()
    dep_fn.setObject(mobj)
    plug = dep_fn.findPlug(plug_name, False)

    return plug


def shape(node_name, intermediate=False):
    """
     Returns the shape node of a transform.

    :param str node_name: node name to get shape of.
    :param bool intermediate: whether to get intermediate shapes.
    :return: list of node shapes.
    :rtype: list(str)
    """

    if type(node_name) in [list, tuple]:
        node_name = node_name[0]

    check_node(node_name)

    if helpers.is_string(node_name):
        if cmds.nodeType(node_name) == 'transform':
            shapes = cmds.listRelatives(node_name, shapes=True, path=True)
            if not shapes:
                shapes = []
            for node_shape_name in shapes:
                is_intermediate = cmds.getAttr('{}.intermediateObject'.format(node_shape_name))
                if intermediate and is_intermediate and cmds.listConnections(node_shape_name, source=False):
                    return node_shape_name
                elif not intermediate and not is_intermediate:
                    return node_shape_name
            if shapes:
                return shapes[0]
        elif cmds.nodeType(node_name) in ['mesh', 'nurbsCurve', 'nurbsSurface']:
            is_intermediate = cmds.getAttr('{}.intermediateObject'.format(node_name))
            if is_intermediate and not intermediate:
                node_name = cmds.listRelatives(node_name, parent=True, path=True)[0]
                return shape(node_name)
            else:
                return node_name

    return node_name


def attribute_check(node_name, attribute):
    """
    Check an object for a given attribute.

    :param str node_name: node name to check attribute of.
    :param str attribute: name of an attribute.
    :return: True if the attribute exists; False otherwise.
    :rtype: bool
    """

    check_node(node_name)

    dep_node = depend_node(node_name)
    dep_fn = OpenMaya.MFnDependencyNode()
    dep_fn.setObject(dep_node)
    return dep_fn.hasAttribute(attribute)


def connect_nodes(parent_name, parent_plug, child_name, child_plug):
    """
    Connects two nodes using Maya API.

    :param str parent_obj: Maya node name to connect.
    :param str parent_plug: name of plug on parent node
    :param str child_name: Maya node name of the child node
    :param str child_plug: name of plug on child node
    """

    parent_plug = plug(parent_name, parent_plug)
    child_plug = plug(child_name, child_plug)
    mdg_mod = OpenMaya.MDGModifier()
    mdg_mod.connect(parent_plug, child_plug)
    mdg_mod.doIt()


def disconnect_nodes(parent_name, parent_plug, child_name, child_plug):
    """
    Disconnects two nodes using Maya API.

    :param str parent_name: Maya node name to disconnect.
    :param str parent_plug: name of plug on parent node.
    :param str child_name: Maya node name of the child node.
    :param str child_plug: name of plug on child node.
    """

    parent_plug = plug(parent_name, parent_plug)
    child_plug = plug(child_name, child_plug)
    mdg_mod = OpenMaya.MDGModifier()
    mdg_mod.disconnect(parent_plug, child_plug)
    mdg_mod.doIt()


def attr_message_value(node_name, attr):
    """
    Returns the connections to/from a message attribute.

    :param str node_name: node name with the desired attribute.
    :param str attr: name of source attribute.
    :return: list of message values.
    :rtype: list(Str)
    """

    check_node(node_name)

    dst_check = cmds.connectionInfo('{}.{}'.format(node_name, attr), isDestination=True)
    source_check = cmds.connectionInfo('{}.{}'.format(node_name, attr), isSource=True)
    if dst_check:
        attr_connection = cmds.connectionInfo('{}.{}'.format(node_name, attr), sourceFromDestination=True)
    elif source_check:
        attr_connection = cmds.connectionInfo('{}.{}'.format(node_name, attr), destinationFromSource=True)
    else:
        return None
    return attr_connection


def node_attr_destination(node_name, attr):
    """
    Returns the destination of an attribute on the given node.

    :param str node_name: node name with the desired attribute
    :param str attr: name of the source attribute
    :return: list containing the destination attribute and its node.
    :rtype: list
    """

    check_node(node_name)

    attr_connection = cmds.connectionInfo('{}.{}'.format(node_name, attr), destinationFromSource=True)
    if len(attr_connection) == 1:
        return attr_connection[0].split('.')
    elif len(attr_connection) > 1:
        return attr_connection
    else:
        return None


def node_attr_source(node_name, attr):
    """
    Returns the source of an attribute on the given node.

    :param str node_name: node name with the desired attribute
    :param str attr: name of source attribute
    :return: list containing the source attribute and its node.
    :rtype: list
    """

    check_node(node_name)

    attr_connection = cmds.connectionInfo('{}.{}'.format(node_name, attr), sourceFromDestination=True)
    if not attr_connection:
        return None
    elif isinstance(attr_connection, list):
        return attr_connection
    elif helpers.is_string(attr_connection):
        dest_info = attr_connection.split('.')
        return dest_info


def normalize_attribute_name(attr):
    """
    Removes invalid characters for attribute names from the provided string.

    :param str attr: string used as the name of an attribute
    :return: str
    """

    return re.sub(r'\W', '', attr)


def normalize_attribute_short_name(short_name, unique_on_obj=None):
    """
    Creates a shortName for the provided attribute name following:
        - Normalize attribute.
        - Adds the first character to any capital letters in the rest of the name.
        - Name is lowercase.

    If unique_on_obj is provided with an object, it will ensure the returned attribute name is
    unique by attaching a 3 digit padded number to it. It will be the lowest available number.

    :param str short_name: string used to generate the short name
    :param bool unique_on_obj: whether to ensure that the name is unique.
    :return: str
    """

    short_name = normalize_attribute_name(short_name)
    if len(short_name):
        short_name = short_name[0] + re.sub(r'[a-z]', '', short_name[1:])
    short_name = short_name.lower()
    if unique_on_obj:
        names = set(cmds.listAttr(short_name, shortNames=True))
        short_name = name.find_unique_name(short_name, names, inc_format='{name}{count}')

    return short_name


def has_attribute(node, attr_name):
    """
    Returns True if the OpenMaya.MObject has a specific attribute or False otherwise
    :param node: OpenMaya.MObject
    :param attr_name: str, attribute name to search for
    :return: bool
    """

    check_node(node)

    dep_node = depend_node(node)

    # TODO: hasAttribute fails when trying to check user defined non existent attributes
    # TODO: More info --> http://discourse.techart.online/t/getting-attribute-using-maya-api-in-python/1224/7
    try:
        return dep_node.hasAttribute(attr_name)
    except Exception:
        return False


def create_attribute(mobj, attribute_name, data_type=None, short_name=None, default=None):
    """
    Creates an attribute on the provided object.
    Returns the attribute name and shortName
    :param mobj: OpenMaya.MObject, MObject to create the attribute for
    :param attribute_name: str, name of the attribute
    :param data_type: Type of data to store in the attribute
    :param short_name: str, short name for the attribute
    :param default: default value assigned to teh attribute
    :return: (name, short name) As name and short name are normalized, this returns the actual names used for attribute
        names
    """

    # TODO: Reimplement this function so it can work on all cases (take the one that appears on the MetaData class)

    attribute_name = normalize_attribute_name(attribute_name)
    if data_type is None and default is not None:
        data_type = get_attribute_data_type(default)
        if data_type == maya.api.OpenMaya.MFnData.kInvalid:
            data_type = None
            logger.debug('Unable to determine the attribute type => {}'.format(str(default)))
        if data_type is None:
            data_type = maya.api.OpenMaya.MFnData.kAny

        try:
            if short_name is None:
                short_name = normalize_attribute_short_name(attribute_name, unique_on_obj=mobj)
            dep_node = maya.api.OpenMaya.MFnDependencyNode(mobj)
        except Exception as e:
            raise Exception('Error while getting dependency node from MObject "{}" - {}'.format(mobj, str(e)))

        s_attr = maya.api.OpenMaya.MFnTypedAttribute()
        if default:
            attr = s_attr.create(attribute_name, short_name, data_type, default)
        else:
            attr = s_attr.create(attribute_name, short_name, data_type)
        dep_node.addAttribute(attr)

        return attribute_name, short_name


def set_attribute(mobj, attr_name, value):
    """
    Sets the value of a current existing attribute of the passed node
    :param mobj: OpenMaya.MObject, MObject to set the attribute value to
    :param attr_name: str, name of the attribute to store the value in
    :param value: value to store in the attribute
    """

    plug = plug(mobj, attr_name)
    if isinstance(value, str):
        plug.setString(value)
    elif isinstance(value, bool):
        plug.setBool(value)
    elif isinstance(value, float):
        plug.setFloat(value)
    elif isinstance(value, int):
        plug.setInt(value)
    # elif isinstance(value, double):
    #     plug.setDouble(value)
    # elif isinstance(value, MAngle):
    #     plug.setMAngle(value)
    # elif isinstance(value, MDataHandle):
    #     plug.setMDataHandle(value)
    # elif isinstance(value, MDistance):
    #     plug.setMDistance(value)
    # elif isinstance(value, MObject):
    #     plug.setMObject(value)
    # elif isinstance(value, MPxData):
    #     plug.setMPxData(value)
    # elif isinstance(value, MTime):
    #     plug.setMTime(value)
    # elif isinstance(value, int):
    #     plug.setNumElements(value)
    # elif isinstance(value, ShortInt):
    #     plug.setShort(value)


def display_override(obj, override_enabled=False, override_display=0, override_lod=0, override_visibility=True,
                     override_shading=True):
    """
    Set display override attributes for the given object
    :param obj: str, object to set display overrides for
    :param override_enabled: bool, set the display override enable state for the given DAG object
    :param override_display: int, set the display override type for the given DAG object
        (0=normal, 1=template, 2=reference)
    :param override_lod: int, set the display override level of detail value for the given DAG object
        (0=full, 1=boundingBox)
    :param override_visibility: bool, set the display override visibility value for the given DAG object
    :param override_shading: bool, set the display override shading value for the given DAG object
    """

    if not cmds.objExists(obj):
        raise Exception('Object "{}" does not exists!'.format(obj))
    if not cmds.ls(obj, dag=True):
        raise Exception('Object "{}" is not a valid DAG node!'.format(obj))

    # Set the display override values
    cmds.setAttr('{}.overrideEnabled'.format(override_enabled))
    cmds.setAttr('{}.overrideDisplayType'.format(override_display))
    cmds.setAttr('{}.overrideLevelOfDetail'.format(override_lod))
    cmds.setAttr('{}.overrideVisibility'.format(override_visibility))
    cmds.setAttr('{}.overrideShading'.format(override_shading))


def get_input_attributes(node):
    """
    Returns a list with all input attributes of the given node
    :param node: str, node name we want to retrieve input attributes of
    :return: list<str>
    """

    if not cmds.objExists(node):
        raise Exception('Object "{}" does not exists!'.format(node))

    inputs = cmds.listConnections(
        node, connections=True, destination=False, source=True, plugs=True, skipConversionNodes=True)
    if inputs:
        inputs.reverse()
    else:
        inputs = list()

    return inputs


def get_output_attributes(node):
    """
    Returns a list with all outputs attributes of the given node
    :param node: str, node name we want to retrieve output attributes of
    :return: list<str>
    """

    if not cmds.objExists(node):
        raise Exception('Object "{}" does not exists!'.format(node))

    outputs = cmds.listConnections(
        node, connections=True, destination=True, source=False, plugs=True, skipConversionNodes=True)
    if not outputs:
        outputs = list()

    return outputs


def get_all_hierarchy_nodes(node, direction=None, object_type=None):
    """
    Returns a list with all nodes in the given node hierarchy
    :param node: str, node to retrieve hierarchy from
    :param direction: str
    :param object_type: str
    :return:
    """

    if direction is None:
        # if helpers.get_maya_version() > 2016:
        #     direction = maya.api.OpenMaya.MItDependencyGraph.kDownstream
        # else:
        #     direction = OpenMaya.MItDependencyGraph.kDownstream
        direction = maya.api.OpenMaya.MItDependencyGraph.kDownstream

    check_node(node)

    object_type = helpers.force_list(object_type)
    nodes = list()

    if type(node) == maya.api.OpenMaya.MObject:
        mobj = node
    else:
        sel_list = maya.api.OpenMaya.MSelectionList()
        sel_list.add(node)
        mobj = sel_list.getDependNode(0)

    mit_dependency_graph = maya.api.OpenMaya.MItDependencyGraph(
        mobj, direction, maya.api.OpenMaya.MItDependencyGraph.kPlugLevel)

    while not mit_dependency_graph.isDone():
        current_item = mit_dependency_graph.currentNode()
        depend_node_fn = maya.api.OpenMaya.MFnDependencyNode(current_item)
        node_name = depend_node_fn.name()
        if object_type:
            for o_type in object_type:
                if current_item.hasFn(o_type):
                    nodes.append(node_name)
                    break
        else:
            nodes.append(node_name)

        mit_dependency_graph.next()

    return nodes


def get_objects_of_mtype_iterator(object_type):
    """
    Returns an iterator of Maya objects filtered by object type
    :param object_type: enum value used to identify Maya objects
    :return: SceneObject:_abstract_to_native_object_type
    """

    object_type = helpers.force_list(object_type)
    for obj_type in object_type:
        obj_iter = OpenMaya.MItDependencyNodes(obj_type)
        while not obj_iter.isDone():
            yield obj_iter.thisNode()
            obj_iter.next()


def delete_nodes_of_type(node_type):
    """
    Delete all nodes of the given type
    :param node_type: varaiant, list<str> || str, name of node type (eg: hyperView, etc) or list of names
    """

    node_type = helpers.force_list(node_type)
    deleted_nodes = list()

    for node_type_name in node_type:
        nodes_to_delete = cmds.ls(type=node_type_name)
        for n in nodes_to_delete:
            if n == 'hyperGraphLayout':
                continue
            if not cmds.objExists(n):
                continue

            cmds.lockNode(n, lock=False)
            cmds.delete(n)
            deleted_nodes.append(n)

    return deleted_nodes


def get_index_color(node):
    """
    Returns the node color as Maya color index
    :param node: str
    :return: int or None, -1 if index not found because shape RGB mode color is enabled
    """

    if not node:
        return None

    if not cmds.getAttr('{}.overrideEnabled'.format(node)):
        return 0
    elif not cmds.getAttr('{}.overrideRGBColors'.format(node)):
        return cmds.getAttr('{}.overrideColor'.format(node))

    return -1


def rgb_color(
        node_name: str, linear: bool = True, limit_decimal_places: bool = False) -> tuple[float, float, float]:
    """
    Returns the color of the given node in RGB or HSV.

    :param str node_name: name of the shape node to retrieve RGB color of.
    :param bool linear: whether the RGB should be in linear space (matches viewport color).
    :param bool limit_decimal_places: whether decimal places should be limited to a maximum of 3.
    :return: tuple of floats representing an RGB color.
    :rtype: tuple[float, float, float]
    """

    if not cmds.getAttr(f'{node_name}.overrideEnabled'):
        rgb = maya_color.MAYA_COLORS_LINEAR_RGB[0] if linear else maya_color.MAYA_COLORS_SRGB[0]
    elif not cmds.getAttr(f'{node_name}.overrideRGBColors'):
        color_index = cmds.getAttr(f'{node_name}.overrideColor')
        rgb = maya_color.MAYA_COLORS_LINEAR_RGB[color_index] if linear else maya_color.MAYA_COLORS_SRGB[color_index]
    else:
        rgb = tuple([
            cmds.getAttr(f'{node_name}.overrideColorR'),
            cmds.getAttr(f'{node_name}.overrideColorG'),
            cmds.getAttr(f'{node_name}.overrideColorB')])
        if not linear:
            rgb = color.convert_color_linear_to_srgb(rgb)

    if limit_decimal_places:
        rgb = list(rgb)
        for i, value in enumerate(rgb):
            rgb[i] = float("{0:.3f}".format(value))
        return tuple(rgb)

    return rgb


def hsv_color(node_name, linear: bool = True) -> tuple[float, float, float]:
    """
    Returns the color of the given node in HSV.

    :param str node_name: name of the shape node to retrieve color of.
    :param bool linear: whether the RGB should be in linear space (matches viewport color).
    :return: tuple of floats in 0-1 range.
    :rtype: tuple[float, float, float]
    """

    return color.convert_rgb_to_hsv(rgb_color(node_name, linear=linear))


def set_color(nodes, value):
    """
    Sets the override color for the given nodes
    :param nodes: str or list(str), list of nodes to change override color of
    :param value: int, color index to set override color to
    """

    if isinstance(value, int):
        set_index_color(nodes, value)
    else:
        set_rgb_color(nodes, value)


def set_index_color(nodes, index):
    """
    Sets the override Maya index color of the given nodes
    :param nodes: str or list(str), list of nodes to change override color of
    :param index: int, Maya color index to apply (from 0 to 30)
    """

    nodes = helpers.force_list(nodes)
    for node in nodes:
        if helpers.is_string(index):
            index = maya_color.convert_maya_color_string_to_index(index)
        if index is not None:
            if cmds.objExists('{}.overrideRGBColors'.format(node)):
                cmds.setAttr('{}.overrideRGBColors'.format(node), False)
            cmds.setAttr('{}.overrideEnabled'.format(node), True)
            cmds.setAttr('{}.overrideColor'.format(node), index)

    return index


def set_index_color_as_rgb(node, index, linear=True):
    """
    Sets the override RGB color by the given Maya color index
    :param node: str or list(str)
    :param index: int or str, Maya index color or Maya nice name color
    :param linear: bool, Whether or not the RGB should be set in linear space (matches viewport color)
    """

    if helpers.is_string(index):
        index = maya_color.convert_maya_color_string_to_index(index)
    rgb_list = maya_color.convert_maya_color_index_to_rgb(index, linear=linear)
    set_rgb_color(node, rgb_list=rgb_list)


def set_rgb_color(node: str, rgb_list: Sequence[float, float, float], linear: bool = True, color_shapes: bool = True):
    """Sets the override RGB color of the given nodes.

    :param str node: node to set RGB color of.
    :param Sequence[float, float, float] rgb_list: RGB color for the node.
    :param bool linear: whether RGB should be set in linear space (matches viewport color).
    :param bool color_shapes: whether to apply color to the given node or its shapes.
    """

    from tp.maya.cmds import shape

    if not linear:
        rgb_list = color.convert_color_linear_to_srgb(rgb_list)

    nodes: list[str] = []
    if color_shapes:
        nodes.extend(shape.filter_shapes_in_list([node]))

    for node in nodes:
        if not cmds.objExists(
                '{}.overrideRGBColors'.format(node)) or not cmds.objExists('{}.overrideEnabled'.format(node)):
            continue

        cmds.setAttr('{}.overrideRGBColors'.format(node), True)
        cmds.setAttr('{}.overrideEnabled'.format(node), True)
        cmds.setAttr('{}.overrideColorR'.format(node), rgb_list[0])
        cmds.setAttr('{}.overrideColorG'.format(node), rgb_list[1])
        cmds.setAttr('{}.overrideColorB'.format(node), rgb_list[2])
        cmds.setAttr('{}.overrideColorRGB'.format(node), rgb_list[0], rgb_list[1], rgb_list[2])


def set_nodes_rgb_color(
        nodes: list[str], rgb_list: Sequence[float, float, float], linear: bool = True, color_shapes: bool = True):
    """Sets the override RGB color of the given nodes.

    :param Sequence[str] nodes: nodes to set RGB color of.
    :param list[float, float, float] rgb_list: RGB color for the node.
    :param bool linear: whether RGB should be set in linear space (matches viewport color).
    :param bool color_shapes: whether to apply color to the given node or its shapes.
    """

    for node in nodes:
        set_rgb_color(node, rgb_list, linear=linear, color_shapes=color_shapes)


def set_hsv_color(node, hsv, linear=True, color_shapes=True):
    """
    Sets the override color of the given node as HSV
    :param node: str or list(str)
    :param hsv: tuple(float, float, float), HSV color
    :param linear: bool, Whether or not the RGB should be set in linear space (matches viewport color)
    :param color_shapes: bool, Whether to apply color to the given node or its shapes
    """

    rgb = color.convert_hsv_to_rgb(hsv)
    set_rgb_color(node, rgb, linear=linear, color_shapes=color_shapes)


def filter_nodes_by_rgb_color(nodes_list, rgb_color, tolerance=0.05, query_shapes=True):
    """
    Returns nodes with the given color from the given list of nodes
    :param nodes_list: list(str), list of Maya nodes we want to to select
    :param rgb_color: tuple(float, float, float), color to find
    :param tolerance: float, margin for errors when comparing RGB float color values
    :param query_shapes: bool, Whether or not nodes shapes should be check to find color of
    :return: list(str), list of filtered nodes
    """

    # Import here to avoid cyclic imports
    from tp.maya.cmds import shape as shape_utils

    colored_nodes = list()
    for i, node in enumerate(nodes_list):
        nodes_to_check = [nodes_list[i]]
        if query_shapes:
            nodes_to_check = shape_utils.filter_shapes_in_list([node])
        if nodes_to_check:
            if color.compare_rgb_colors_tolerance(rgb_color(nodes_to_check[0]), rgb_color, tolerance=tolerance):
                colored_nodes.append(node)

    return colored_nodes


def select_nodes_by_rgb_color(nodes_list, rgb_color, tolerance=0.05, query_shapes=False):
    """
    Selects nodes with the given color from the given list of nodes
    :param nodes_list: list(str), list of Maya nodes we want to to select
    :param rgb_color: tuple(float, float, float), color to find
    :param tolerance: float, margin for errors when comparing RGB float color values
    :param query_shapes: bool, Whether or not nodes shapes should be check to find color of
    :return: list(str), list of filtered nodes
    """

    colored_nodes = filter_nodes_by_rgb_color(nodes_list, rgb_color, tolerance=tolerance, query_shapes=query_shapes)
    if not colored_nodes:
        return None
    cmds.select(colored_nodes, replace=True)

    return colored_nodes


def get_node_by_id(node_id, full_path=True):
    """
    Returns a node by its UUID (support starting from Maya 2016)
    :param node_id: str
    :param full_path: bool
    :return: str
    """

    if helpers.maya_version() >= 2016:
        maya_nodes = cmds.ls(node_id, long=full_path)
        if maya_nodes and len(maya_nodes) > 1:
            logger.warning('Multiple Maya nodes found with same IDs (this can happen when using heavy references')
        return maya_nodes[0]

    return None


def get_node_color_data(node):
    """
    Returns the color data in the given Maya node
    :param node: str or OpenMaya.MObject
    :return: dict
    """

    if helpers.is_string(node):
        node = get_mobject(node)

    return api_node.node_color_data(node)


def get_all_parents(node, full_path=True):
    """
    Returns all parents of the given node
    :param node: str, Maya DAG object name
    :param full_path: bool, Whether or not to return parent full names
    :return: list(str)
    """

    parents = cmds.ls(node, long=True)[0].split('|')[1:-1]
    if full_path:
        parents = ['|'.join(parents[:i]) for i in range(1, 1 + len(parents))]
        for i, obj in enumerate(parents):
            parents[i] = '|{}'.format(obj)

    return parents


def nodes_from_nodes_flag(nodes_flag='all', long_name=False):
    """
    Returns nodes based on the given nodes flag:
        - 'all': all nodes in scene.
        - 'selected': only selected nodes.
        - hierarchy': search selected hierarchy.
    
    :param str nodes_flag: nodes flag.
    :param bool long_name: whether to return long names. 
    :return: node names.
    :rtype: list(str)
    """
    
    found_nodes = list()
    if nodes_flag == 'all':
        found_nodes.extend(cmds.ls(dag=True, long=long_name))
    elif nodes_flag == 'selected':
        found_nodes.extend(cmds.ls(sl=True, long=long_name))
    elif nodes_flag == 'hierarchy':
        found_nodes.extend(cmds.ls(sl=True, long=long_name))
        if found_nodes:
            found_nodes.extend(cmds.listRelatives(found_nodes, allDescendents=True, fullPath=long_name))

    return found_nodes
