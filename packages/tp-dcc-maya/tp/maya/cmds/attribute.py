#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related with attributes
"""

from __future__ import annotations

import os
import re
import sys
import copy
import random
import string
import traceback

import maya.cmds as cmds

from tp.core import log, dcc
from tp.common.python import helpers, decorators, name as name_utils
from tp.common.math import scalar
from tp.maya.cmds import exceptions, node as node_utils, shape as shape_utils, name as maya_name_utils

logger = log.tpLogger


class AttributeTypes(object):
    Bool = str('bool')
    Int = str('int')
    Long = str('long')
    Long2 = str('long2')
    Long3 = str('long3')
    Short = str('short')
    Short2 = str('short2')
    Short3 = str('short3')
    Byte = str('byte')
    Char = str('char')
    Enum = str('enum')
    Float = str('float')
    Float2 = str('float2')
    Float3 = str('float3')
    Double = str('double')
    Double2 = str('double2')
    Double3 = str('double3')
    DoubleAngle = str('doubleAngle')
    DoubleLinear = str('doubleLinear')
    DoubleArray = str('doubleArray')
    String = str('string')
    StringArray = str('stringArray')
    Unicode = str('unicode')
    Message = str('message')
    MessageSimple = str('messageSimple')
    Time = str('time')
    Matrix = str('matrix')
    ReflectanceRGB = str('reflectanceRGB')
    SpectrumRGB = str('spectrumRGB')
    IntArray32 = str('IntArray32')
    VectorArray = str('vectorArray')
    PointArray = str('pointArray')
    NurbsCurve = str('nurbsCurve')
    NurbsSurface = str('nurbsSurface')
    NurbsTrimFace = str('trimFace')
    Sphere = str('sphere')
    Cone = str('cone')
    Mesh = str('mesh')
    Lattice = str('lattice')
    Complex = str('complex')


numeric_attrs = [
    AttributeTypes.Bool,
    AttributeTypes.Long,
    AttributeTypes.Short,
    AttributeTypes.Float,
    AttributeTypes.Double,
    AttributeTypes.DoubleLinear,
    AttributeTypes.DoubleAngle,
    AttributeTypes.Enum
]


keyable_attrs = [
    AttributeTypes.Long,
    AttributeTypes.Double,
    AttributeTypes.Bool,
    AttributeTypes.Enum,
    AttributeTypes.Double3
]


add_cmd_edit_flags = [
    'min',
    'minValue',
    'max',
    'maxValue',
    'defaultValue',
    'dv',
    'softMinValue',
    'smn',
    'softMaxValue',
    'smx',
    'enumName'
]


set_cmd_edit_flags = [
    'keyable',
    'k',
    'lock',
    'l',
    'channelBox',
    'cb'
]


attr_mapping = {
    AttributeTypes.Bool: {'at': 'bool'},
    AttributeTypes.Int: {'at': 'long'},
    AttributeTypes.Long: {'at': 'long'},
    AttributeTypes.Long2: {'at': 'long2'},
    AttributeTypes.Long3: {'at': 'long3'},
    AttributeTypes.Short: {'at': 'short'},
    AttributeTypes.Short2: {'at': 'short2'},
    AttributeTypes.Short3: {'at': 'short3'},
    AttributeTypes.Byte: {'at': 'byte'},
    AttributeTypes.Char: {'dt': 'string'},
    AttributeTypes.Enum: {'at': 'enum'},
    AttributeTypes.Float: {'at': 'double'},
    AttributeTypes.Float2: {'at': 'float2'},
    AttributeTypes.Float3: {'at': 'float3'},
    AttributeTypes.Double: {'at': 'double'},
    AttributeTypes.Double2: {'at': 'double2'},
    AttributeTypes.Double3: {'at': 'double3'},
    AttributeTypes.DoubleAngle: {'at': 'double'},
    AttributeTypes.DoubleLinear: {'at': 'double'},
    AttributeTypes.DoubleArray: {'dt': 'doubleArray'},
    AttributeTypes.String: {'dt': 'string'},
    AttributeTypes.Unicode: {'dt': 'string'},
    AttributeTypes.StringArray: {'dt': 'stringArray'},
    AttributeTypes.Message: {'at': 'message', 'm': True, 'im': True},
    AttributeTypes.MessageSimple: {'at': 'message', 'm': False},
    AttributeTypes.Time: {'at': 'double'},
    AttributeTypes.Matrix: {'dt': 'matrix'},
    AttributeTypes.ReflectanceRGB: {'dt': 'reflectanceRGB'},
    AttributeTypes.SpectrumRGB: {'dt': 'spectrumRGB'},
    AttributeTypes.IntArray32: {'dt': 'Int32Array'},
    AttributeTypes.VectorArray: {'dt': 'vectorArray'},
    AttributeTypes.PointArray: {'dt': 'pointArray'},
    AttributeTypes.NurbsCurve: {'dt': 'nurbsCurve'},
    AttributeTypes.NurbsSurface: {'dt': 'nurbsSurface'},
    AttributeTypes.NurbsTrimFace: {'dt': 'nurbsTrimface'},
    AttributeTypes.Sphere: {'dt': 'sphere'},
    AttributeTypes.Cone: {'dt': 'cone'},
    AttributeTypes.Mesh: {'dt': 'mesh'},
    AttributeTypes.Lattice: {'dt': 'lattice'},
    AttributeTypes.Complex: {'dt': 'string'}
}


def check_attribute(attr):
    """
    Checks if a attribute is valid and raise a exception if the attribute is not valid
    :param attr: str, name of the attribute to be checked
    :return:  bool, True if the given attribute is a valid one
    """

    if not is_attribute(attr):
        raise exceptions.AttributeExistsException(attr)


def is_attribute(attr):
    """
    Checks if the given attribute is the name of valid attribute
    :param attr: str, attribute to query
    :return: bool
    """

    if not cmds.objExists(attr):
        return False

    split = attr.split('.')
    if len(split) == 1:
        return False

    if len(split) > 1 and not split[1]:
        return False

    return True


def is_attribute_numeric(attr):
    """
    Checks if given attribute exists and is numeric
    :param attr: str, attribute to query
    :return: bool
    """

    if not is_attribute(attr):
        return False

    attr_type = cmds.getAttr(attr, type=True)
    if attr_type not in numeric_attrs:
        return False

    return True


def has_attribute(node, attr):
    """
    Checks whether a given node has an attribute or not
    :param node: str, name of the node we want to check attribute of
    :param attr: str, name of the attribute we want to check
    :return: bool
    """

    return cmds.attributeQuery(attr, node=node, exists=True)


def validate_attribute_data_type(value):

    """
    Validates the attribute type
    :param value: variant, value to check type for
    :return: str, type string
    """

    python_types = [str, bool, int, float, dict, list, tuple]
    valid_types = ['string', 'bool', 'int', 'float', 'complex', 'complex', 'complex']
    if helpers.is_python2():
        python_types.append(unicode)
        valid_types.append('unicode')
    for py_type, valid_type in zip(python_types, valid_types):
        if issubclass(type(value), py_type):
            logger.debug('Value {0} is a "{1}" attribute'.format(py_type, valid_type))
            return valid_type


def node_and_attribute(attr):
    """
    Split a name between its node and its attribute
    :param attr: str, attribute name (node.attribute)
    :return:  list<str, str>, node_name, attribute]
    """

    split_attr = attr.split('.')
    if not split_attr:
        return None, None

    node = split_attr[0]
    attr = string.join(split_attr[1:], '.')

    return node, attr


def data_type(attr):
    """
    Returns the given attribute data type as a string value
    :param attr: str, attribute to return the data type for
    :return: str
    """

    check_attribute(attr)

    return cmds.getAttr(attr, type=True)


def is_locked(attr):
    """
    Returns whether the given attribute is locked or not
    :param attr: str, attribute to check if it is locked
    :return: bool
    """

    check_attribute(attr)

    return cmds.getAttr(attr, lock=True)


def is_connected(attr):
    """
    Returns whether the given attribute is connected or not
    :param attr: str, attribute to check if it is locked
    :return: bool
    """

    check_attribute(attr)

    input_value = attribute_input(attr)
    if input_value:
        return True

    return False


def is_keyable(attr):
    """
    Returns whether the given attribute is keyable or not
    :param attr: str, attribute to check if it is keyable
    :return: bool
    """

    check_attribute(attr)

    return cmds.getAttr(attr, keyable=True)


def is_settable(attr):
    """
    Returns whether the given attribute is settable.

    :param str attr: full name attribute to check.
    :return: True if attribute is settable; False otherwise.
    :rtype: bool
    """

    check_attribute(attr)

    return cmds.getAttr(attr, settable=True)


def is_hidden(attr):
    """
    Returns whether the given attribute is hidden or not
    :param attr: str, attribute to check if it is hidden
    :return: bool
    """

    check_attribute(attr)

    return cmds.getAttr(attr, cb=True)


def is_numeric(attr):
    """
    Returns whether the given attribute is a numeric one or not
    :param attr: str, attribute to check if it is numeric or not
    :return: bool
    """

    check_attribute(attr)

    if '.' in attr:
        attr = attr.split('.')

    attr_value = attribute(obj=attr[0], attr=attr[1])
    attr_type = validate_attribute_data_type(attr_value)

    return attr_type in numeric_attrs


def attr_mplug(attr):
    """
    Returns the MPlug object for the given attribute
    :param attr: str, the attribute to return the MPlug for
    :return: MPlug
    """

    check_attribute(attr)

    attr_elem_list = attr.split('.')
    attr_obj = node_utils.get_mobject(node_name=attr_elem_list[0])
    attr_obj_fn = maya.api.OpenMaya.MFnDependencyNode(attr_obj)

    # Get attribute element components (name, index)
    attr_elem = re.findall(r'\w+', attr_elem_list[1])

    # Get MPlug to top level attribute
    attr_mplug = attr_obj_fn.findPlug(attr_elem[0], True)
    if len(attr_elem) == 2:
        attr_mplug = attr_mplug.elementByLogicalIndex(int(attr_elem[1]))

    # Traverse to lowest child attribute
    for i in range(2, len(attr_elem_list)):
        attr_elem = re.findall(r'\w+', attr_elem_list[i])
        for n in range(attr_mplug.numChildren()):
            child_plug = attr_mplug.child(n)
            logger.debug('Looking for "{}", found "{}"'.format(attr_elem[0], child_plug.partialName()))

    return attr_mplug


def attribute(obj, attr, *args, **kwargs):
    """
    This function overrides Maya getAttr method to get message objects and also
    parses double3 parameters as lists
    :param obj: str
    :param attr: str
    :param args:
    :param kwargs:
    :return: variant
    """

    try:
        combined = '{0}.{1}'.format(obj, attr)
        if not cmds.objExists(combined):
            return False
        else:
            if '[' in attr:
                logger.debug('Getting indexed attribute')
                connections = cmds.listConnections(combined) or list()
                if not connections:
                    return cmds.getAttr(combined)

            attr_type = cmds.getAttr(combined, type=True)
            if attr_type in ['TdataCompound']:
                return cmds.listConnections(combined)

            msg = cmds.attributeQuery(attr, node=obj, msg=True)
            if msg:
                connections = cmds.listConnections(combined)
                if connections is not None:
                    return connections[0]
                else:
                    return
            elif attr_type == 'double3':
                children_attrs = cmds.attributeQuery(attr, node=obj, listChildren=True)
                data_buffer = list()
                for child_attr in children_attrs:
                    data_buffer.append(cmds.getAttr('{0}.{1}'.format(obj, child_attr)))
                return data_buffer
            else:
                return cmds.getAttr('{0}.{1}'.format(obj, attr), *args, **kwargs)
    except Exception as e:
        raise Exception('Attribute Getter Failed! | obj: {0} | attr:{1} | {2}'.format(obj, attr, e))


def attribute_instance(attribute_name):
    """
    Instantiates a new Attribute object from the given attribute name
    :param attribute_name: str, variable we want to work with
    :return: Attribute
    """

    node, attr = node_and_attribute(attr=attribute_name)
    attr_type = None
    try:
        attr_type = cmds.getAttr(attribute_name, type=True)
    except Exception:
        pass

    if not attr_type:
        return

    attr = attribute_instance_of_type(attribute_name=attr, attribute_type=attr_type)
    attr.set_node(node)
    attr.refresh()

    return attr


def attribute_instance_of_type(attribute_name, attribute_type):
    """
    Instantiates a new Variable object from the given attribute name and the given type
    :param attribute_name: str, variable we want to work with
    :param attribute_type: str, variable type we want to create
    :return: variant
    """

    new_var = Attribute(attribute_name=attribute_name)
    if attribute_type in new_var in numeric_attrs:
        new_var = NumericAttribute(attribute_name=attribute_name)
    elif attribute_type == AttributeTypes.Enum:
        new_var = EnumAttribute(attribute_name=attribute_name)
    elif attribute_type == AttributeTypes.String:
        new_var = StringAttribute(attribute_name=attribute_name)

    new_var.set_variable_type(attribute_type=attribute_type)

    return new_var


def attribute_name(node_and_attribute):
    """
    For a given string node_name.attribute_name, returns the attribute portion
    :param node_and_attribute: str, node_name.attribute_name to find an input into
    :return: str
    """

    split = node_and_attribute.split('.')
    attr = ''
    if split and len(split) > 1:
        attr = string.join(split[1:], '.')

    return attr


def attribute_input(node_and_attribute, node_only=False):
    """
    Returns the input into given attribute
    :param node_and_attribute: str, node_name.attribute_name to find an input into
    :param node_only: bool, Whether to return the node name or the node name + attribute (node_name.attribute)
    :return: str, attribute that inputs into given node
    """

    if cmds.objExists(node_and_attribute):
        connections = cmds.listConnections(
            node_and_attribute, plugs=True, connections=False, destination=False, source=True, skipConversionNodes=True)
        if connections:
            if not node_only:
                return connections[0]
            else:
                return connections[0].split('.')[0]


def attribute_outputs(node_and_attribute, node_only=False):
    """
    Get the outputs from the given attribute
    :param node_and_attribute: str, node_name.attribute name to find outputs
    :param node_only: bool, Whether to return the node name or the node name + attribute (node_name.attribute)
    :return: str, nodes that node_and_attribute connect into
    """

    if cmds.objExists(node_and_attribute):
        plug = True
        if node_only:
            plug = False

        return cmds.listConnections(
            node_and_attribute, plugs=plug, connections=False, destination=True, source=False, skipConversionNodes=True)


def add_attribute(node, attr, value=None, attr_type=None, hidden=False, **kwargs):
    """
    Adds a new attribute to the given node
    :param node: str, node name we want to add attributo into
    :param attr: str, name of the attribute we want to add
    :param value: variant, value of the attribute
    :param attr_type: str, attribute type as string
    :param hidden: boo, Whether the attribute should be hidden in the channel box or not
    :return:  bool, True if the attribute was added successfully; False otherwise
    """

    logger.debug('|Adding Attribute| >> node: {0} | attr: {1} | attrType: {2}'.format(node, attr, attr_type))

    added = False

    if attr_type and attr_type == 'enum' and 'enumName' not in kwargs:
        raise ValueError('enum attribute type must be passed with "enumName" keyword in args')

    add_kwargs_to_edit = dict()
    set_kwargs_to_edit = dict()
    if kwargs:
        for kw, v in kwargs.items():
            if kw in add_cmd_edit_flags:
                add_kwargs_to_edit[kw] = v
            elif kw in set_cmd_edit_flags:
                set_kwargs_to_edit[kw] = v

    # ===================================================================  IF ATTR EXISTS, EDIT ATTR
    if has_attribute(node=node, attr=attr):
        logger.debug('"{0}" : Attr already exists on the node'.format(attr))
        try:
            if kwargs:
                if add_kwargs_to_edit:
                    cmds.addAttr('{0}.{1}'.format(node, attr), edit=True, **add_kwargs_to_edit)
                    logger.debug('addAttr Edit flags run : {0} = {1}'.format(attr, add_kwargs_to_edit))
                if set_kwargs_to_edit:
                    try:
                        if not node_utils.is_referenced(node):
                            cmds.setAttr('{0}.{1}'.format(node, attr), **set_kwargs_to_edit)
                            logger.debug('setAttr Edit flags run : {0} = {1}'.format(attr, set_kwargs_to_edit))
                    except Exception:
                        logger.debug(
                            'node is referenced and the setEditFlags are therefore invalid (lock, keyable, channelBox)')
        except Exception:
            if node_utils.is_referenced(node_name=node):
                logger.debug('{0} : Trying to modify an attr on a reference node'.format(attr))

        if value:
            if not attr_type:
                attr_type = validate_attribute_data_type(value)

            if 'dt' in attr_mapping[attr_type]:
                cmds.setAttr(
                    '{0}.{1}'.format(node, attr), value, edit=True, **{'typ': attr_mapping[attr_type]['dt']})
            else:
                cmds.setAttr('{0}.{1}'.format(node, attr), value, edit=True)

        return

    # ===================================================================  IF ATTR NOT EXISTS, CREATE ATTR
    else:
        try:
            if not attr_type:
                attr_type = validate_attribute_data_type(value)

            string_value = ''
            if attr_type == AttributeTypes.String:
                string_value = add_kwargs_to_edit['dv']
                add_kwargs_to_edit.pop('dv')
            attr_mapping[attr_type].update(add_kwargs_to_edit)

            logger.debug(
                'addAttr : {0} : value_type : {1} > data_type keywords: {2}'.format(
                    attr, attr_type, attr_mapping[str(attr_type)]))

            cmds.addAttr(node, longName=attr, **attr_mapping[str(attr_type)])

            if attr_type == AttributeTypes.String:
                cmds.setAttr('{}.{}'.format(node, attr), string_value, edit=True, typ='string')

            if attr_type == 'double3' or attr_type == 'float3':
                if attr_type == 'double3':
                    sub_type = 'double'
                else:
                    sub_type = 'float'
                attr_list = []
                for i, axis in enumerate(['X', 'Y', 'Z']):
                    attr_list.append('{0}{1}'.format(attr, axis))
                    cmds.addAttr(node, longName=attr_list[i], at=sub_type, parent=attr, **kwargs)
                if attr_type in keyable_attrs and not hidden:
                    for at in attr_list:
                        cmds.setAttr('{0}.{1}'.format(node, at), edit=True, keyable=True)
            elif attr_type == 'doubleArray':
                cmds.setAttr('{0}.{1}'.format(node, attr), [], type='doubleArray')
            else:
                if attr_type in keyable_attrs and not hidden:
                    cmds.setAttr('{0}.{1}'.format(node, attr), edit=True, keyable=True)

            # Allow add_attribute to set any secondary kwargs via the setAttr call
            if set_kwargs_to_edit:
                cmds.setAttr('{0}.{1}'.format(node, attr), **set_kwargs_to_edit)
                logger.debug('setAttr Edit flags run : {0} = {1}'.format(attr, set_kwargs_to_edit))

            added = True
        except Exception:
            logger.error(traceback.format_exc())

    return added


def multi_index_list(attr):
    """
    Returns a list of the existing index elements of the given multi attribute
    :param attr: str, attribute to get the index list for
    :return: list<int>
    """

    check_attribute(attr)

    attr_mplug = attr_mplug(attr)

    if not attr_mplug.isArray():
        raise exceptions.InvalidMultiAttribute(attr)

    # Check existing indices
    ex_index_list = attr_mplug.getExistingArrayAttributeIndices()

    return list(ex_index_list)


def connection_index(attr, as_source=True, connected_to=None):
    """
    Return the index of the connection
    :param attr: name, attribute we want to check connection index of
    :param as_source: bool, Whether to check source connection
    :param connected_to:
    :return: int
    """

    attr_plug = attr_mplug(attr)

    # Get connectced plugs
    attr_plug_connections = maya.api.OpenMaya.MPlugArray()
    connected = attr_plug.connectedTo(attr_plug_connections, not as_source, as_source)
    if not connected:
        connection_type = 'outgoinhg' if as_source else 'incoming'
        raise Exception('No {} connections found for attribute "{}"'.format(connection_type, attr))

    # Get connected index
    for i in range(len(attr_plug_connections)):
        connected_plug = attr_plug_connections[i]
        connected_node = connected_plug.partialName(True, False, False, False, False).split('.')[0]
        if connected_to and not connected_to == connected_node:
            continue
        return connected_plug.logicalIndex()

    return -1


def connected_nodes(attr, as_source=True, connected_to=None):
    """
    Returns a list of all connected nodes to given attribute
    :param attr: str
    :param as_source: bool
    :param connected_to: str or None
    :return: list(str)
    """

    connected_nodes = list()

    attr_plug = attr_mplug(attr)
    attr_plug_connections = maya.api.OpenMaya.MPlugArray()
    connected = attr_plug.connectedTo(attr_plug_connections, not as_source, as_source)
    if not connected:
        return connected_nodes

    num_connections = len(attr_plug_connections)
    for i in range(num_connections):
        connected_plug = attr_plug_connections[i]
        connected_node = connected_plug.partialName(True, False, False, False, False)
        if connected_to and not connected_to == connected_node:
            continue
        connected_nodes.append(connected_node)

    return connected_nodes


def next_available_multi_index(attr, start=0, use_connected_only=True, max_index=10000000):
    """
    Returns the index of the first available index (no incoming connection) element of the given attribute
    :param attr: str, attribute to find next available index for
    :param start: int, multi index to start the connection check from
    :param use_connected_only: bool, Whether the existing indices are based in incoming connection only.
        Otherwise, any existing indices will be considered unavailable
    :param max_index: int, maximum index search value
    :return: int
    """

    next_index = -1
    if use_connected_only:
        for i in range(start, max_index):
            cnt = cmds.connectionInfo('{}[{}]'.format(attr, str(i)), sourceFromDestination=True)
            if not cnt:
                next_index = 1
                break
    else:
        existing_index_list = multi_index_list(attr)
        index_count = len(existing_index_list)
        if index_count:
            next_index = list(existing_index_list)[-1] + 1
        else:
            next_index = 0

    return next_index


def indices(attribute):
    """
    Returns the index values of a multi attribute
    :param attribute: str, node.attribute name of a multi attribute (Exp: bShp1.inputTarget)
    :return: dict, dict of integers that correspond to multi attribute indices
    """

    multi_attrs = cmds.listAttr(attribute, multi=True)
    indices = dict()
    if not multi_attrs:
        return indices

    for multi_attr in multi_attrs:
        index = re.findall(r'\d+', multi_attr)
        if index:
            index = int(index[-1])
            indices[index] = None

    indices = list(indices.keys())
    indices.sort()

    return indices


def slots(attribute):
    """
    Given a multi attribute, get all the slots currently made
    :param attribute: str, node.attribute name of a multi attribute (Exp: bShp1.inputTarget)
    :return: list<str>, index slots that are open returned as strings
    """

    slots = cmds.listAttr(attribute, multi=True)
    found_slots = list()
    if not slots:
        return found_slots

    for slot in slots:
        index = re.findall(r'\d+', slot)
        if index:
            found_slots.append(index[-1])

    return found_slots


def slots_count(attribute):
    """
    Returns the number of created slots in a multi attribute
    :param attribute: str, node.attribute name of a multi attribute (Exp: bShp1.inputTarget)
    :return: int, number of open slots in the multi attribute
    """

    current_slots = slots(attribute)
    if not current_slots:
        return 0

    return len(current_slots)


def available_slot(attribute):
    """
    Find the next available slot in a multi attribute
    :param attribute: str, node.attribute name of a multi attribute (Exp: bShp1.inputTarget)
    :return: int
    """

    current_slots = slots(attribute)
    if not current_slots:
        return 0

    return int(current_slots[-1]) + 1


def default(attr):
    """
    Returns the default value for the given attribute
    :param attr: str, the attribute to query the default value for
    :return: variant
    """

    check_attribute(attr)

    # Get object from attribute
    obj = cmds.ls(attr, o=True)[0]
    at = attr.replace(obj + '.', '')

    # Build default attribute list
    xform_attr_list = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
    xform_attr_list.extend(['tx', 'tx', 'tx', 'rx', 'rx', 'rx'])
    scale_attr_list = ['scaleX', 'scaleY', 'scaleZ']
    scale_attr_list.extend(['sx', 'sx', 'sx'])
    vis_attr_list = ['visibility', 'v']

    # Query attribute default value
    if xform_attr_list.count(at):
        return 0.0
    if scale_attr_list.count(at):
        return 1.0
    if vis_attr_list.count(at):
        return 1.0

    # Query default for user defined attribute
    val = cmds.addAttr(attr, q=True, dv=True)

    return val


def distribute_attr_value(target_list, target_attr, range_start=0.0, range_end=1.0, smooth_step=0.0):
    """
    Distribute a range of attribute values across list of target objects
    :param target_list: list<str>, list of target objects to distribute the attribute values across
    :param target_attr: str, target attribute that the distributed values will be applied to
    :param range_start: float, distribution range minimum value
    :param range_end: float, distribution range maximum value
    :param smooth_step: float, amount of value smoothing to apply to the distribution
    """

    for i in range(len(target_list)):
        if not cmds.objExists(target_list[i]):
            raise Exception('Object "{}" does not exists!'.format(target_list[i]))
        if not cmds.objExists(target_list[i] + '.' + target_attr):
            raise Exception('Object "{}" has no ".{}" attribute!'.format(target_list[i], target_attr))

    value_list = scalar.distribute_value(
        samples=len(target_list), spacing=1.0, range_start=range_start, range_end=range_end)

    for i in range(len(target_list)):
        val = value_list[i]
        if smooth_step:
            val = scalar.smooth_step(value=val, range_start=range_start, range_end=range_end, smooth=smooth_step)
        cmds.setAttr('{}.{}'.format(target_list[i], target_attr), val)


def randomize_attr_values(object_list, attr, min_value=0.0, max_value=1.0):
    """
    Randomize attribute values on a list of objects
    :param object_list:  list<str>, list of objects to randomize attributes on
    :param attr: str, attribute to randomize
    :param min_value: float, minimum value to randomize (default is 0)
    :param max_value: float, maximum value to randomize (default is 1)
    """

    if type(object_list) == str:
        object_list = [object_list]

    for i in range(len(object_list)):
        obj_attr = '{}.{}'.format(object_list[i], attr)
        if not cmds.objExists(obj_attr):
            raise Exception('Attribute "{}" does not exists!'.format(obj_attr))

        rnd = random.random()
        attr_val = min_value + (max_value - min_value) * rnd

        cmds.setAttr(obj_attr, attr_val)


def delete_user_attrs(obj, attrs_list=None, keep_if_connected=False):
    """
    Deletes user define attributes from a given object
    :param obj: str, source objects to delete user attributes from
    :param attrs_list: list<str>, a list of attributes to delete. If None, all user attributes will be deleted
    :param keep_if_connected:  bool, Whether is the attribue should not be deleted if has a connection
    """

    if not cmds.objExists(obj):
        raise Exception('Object "{}" does not exists!'.format(obj))

    if not attrs_list:
        attr_list = cmds.listAttr(obj, ud=True)
    if not attr_list:
        attr_list = list()

    for attr in attr_list:
        if cmds.objExists('{}.{}'.format(obj, attr)):
            if keep_if_connected:
                cns = cmds.listConnections('{}.{}'.format(obj, attr), s=True, d=True)
                if cns:
                    continue

            try:
                cmds.setAttr('{}.{}'.format(obj, attr), lock=False)
                cmds.deleteAttr(obj, at=attr)
            except Exception:
                logger.warning(
                    'Problem removing attribute "{}.{}". Skipping to he next attribute ...'.format(obj, attr))

    return attr_list


def rename_attr(attr, new_name):
    """
    Renames given attribute
    :param attr: str, attribute we want to rename
    :param new_name: str, new name of the attribute
    :return: str, new name of the attribute
    """

    check_attribute(attr)

    result = cmds.aliasAttr(new_name, attr)

    return result


def break_connection(obj, attr=None):
    """
    Breaks a connection of an attribute if exists
    :param obj: str
    :param attr: str
    :return: variant, str || False
    """

    if '.' in obj:
        split = return_object_attr_split(obj)
        if split:
            obj = split[0]
            attr = split[1]
        else:
            return False

    assert cmds.objExists('{0}.{1}'.format(obj, attr)) is True, '"{0}.{1}" does not exists!'.format(obj, attr)
    combine = '{0}.{1}'.format(obj, attr)

    family = dict()

    if cmds.connectionInfo(combine, isDestination=True):
        source_connections = cmds.listConnections(
            combine, skipConversionNodes=False, destination=False, source=True, plugs=False)
        if not source_connections:
            family = return_family_dict(obj, attr)
            source_connections = cmds.connectionInfo(combine, sourceFromDestination=True)
        else:
            source_connections = source_connections[0]

        if not source_connections:
            return logger.warning('No source for "{0}.{1} found!'.format(obj, attr))

        try:
            logger.debug('Source Connections: {}'.format(source_connections))
            driven_attr = '{0}.{1}'.format(obj, attr)
            if family and family.get('parent'):
                logger.debug('Family: {}'.format(family))
                driven_attr = '{0}.{1}'.format(obj, family.get('parent'))

            logger.debug('Breaking {0} to {1}'.format(source_connections, driven_attr))

            driven_lock = False
            if cmds.getAttr(driven_attr, lock=True):
                driven_lock = True
                cmds.setAttr(driven_attr, lock=False)
            source_lock = False
            if cmds.getAttr(source_connections, lock=True):
                source_lock = True
                cmds.setAttr(source_connections, lock=False)

            cmds.disconnectAttr(source_connections, driven_attr)

            if driven_lock:
                cmds.setAttr(driven_attr, lock=True)
            if source_lock:
                cmds.setAttr(source_connections, lock=True)

            return source_connections
        except Exception as e:
            raise Exception('Break Connection failed | {}'.format(e))

    return False


def connect_attribute(from_attr, to_attr, force_lock=False, transfer_connection=False):
    """
    Connects attributes. Handles locks on source or end automatically
    :param from_attr: str
    :param to_attr: str
    :param force_lock: bool
    :param transfer_connection: bool, Whether you want to transfer the existing connection or or not
    """

    # TODO: Add checks to check that node|attr are valid through cmds.objExist and cmds.attributeQuery functions

    assert from_attr != to_attr, 'Cannot connect an attribute to itself'

    # Checks
    was_locked = False
    if cmds.objExists(to_attr):
        if cmds.getAttr(to_attr, lock=True):
            was_locked = True
            cmds.setAttr(to_attr, lock=False)

        buffer_connection = return_driver_attribute(to_attr)
        attr_buffer = return_object_attr_split(to_attr)
        if not attr_buffer:
            return False

        break_connection(attr_buffer[0], attr_buffer[1])
        cmds.connectAttr(from_attr, to_attr)

        if transfer_connection:
            if buffer_connection:
                cmds.connectAttr(buffer_connection, to_attr)

    if was_locked or force_lock:
        cmds.setAttr(to_attr, lock=True)


def disconnect_attribute(attr):
    """
    Disconnects an attribute. Find its inputs automatically and disconnects it
    :param attr: str, name of an attribute that has a connection
    """

    connection = attribute_input(attr)
    if connection:
        cmds.disconnectAttr(connection, attr)


def disconnect_scale(transform_node):
    """
    Disconnect scale attributes of the given transform node
    :param transform_node: str, transform node we want disconnect scale attributes of
    """

    disconnect_attribute('{}.scale'.format(transform_node))
    disconnect_attribute('{}.scaleX'.format(transform_node))
    disconnect_attribute('{}.scaleY'.format(transform_node))
    disconnect_attribute('{}.scaleZ'.format(transform_node))


def unlock_disconnect_attributes(node_name: str, attr_names: list[str]):
    """
    Unlocks and disconnects keys in all given attributes of the given node.

    :param str node_name: name of the node.
    :param list[str] attr_names: list of attributes to unlock and disconnect.
    """

    for attr_name in attr_names:
        combined_attr = f'{node_name}.{attr_name}'
        cmds.setAttr(combined_attr, lock=False)
        remove_keys_from_attribute(node_name, attr_name)
        disconnect_attribute(combined_attr)


def remove_keys_from_attribute(node_name: str, attr_name: str, time_range: tuple[int, int] = (-10000, 10000)):
    """
    Deletes all the keys on the given attribute within the given range.

    :param str node_name: name of the node to remove key attributes from.
    :param str attr_name: name of the attribute.
    :param tuple[int, int] time_range: time range we want to delete keys from.
    """

    if cmds.keyframe(node_name, attribute=attr_name, selected=False, query=True):
        cmds.cutKey(node_name, time=time_range, attribute=attr_name)


def safe_delete_attribute(node_name: str, attr_name: str) -> bool:
    """
    Checks whether attributes exists and if it does, removes the attribute.

    :param str node_name: name of the node whose attribute we want to delete.
    :param str attr_name: name of the attribute to delete.
    """

    if not cmds.attributeQuery(attr_name, node=node_name, exists=True):
        return False

    parent_attrs = cmds.attributeQuery(attr_name, node=node_name, listParent=True)
    if parent_attrs:
        attr_name = parent_attrs[0]
        child_attrs = cmds.attributeQuery(attr_name, node=node_name, listChildren=True)
        if child_attrs:
            unlock_disconnect_attributes(node_name, child_attrs)
    else:
        unlock_disconnect_attributes(node, [attr_name])

    cmds.deleteAttr(f'{node_name}.{attr_name}')

    return True


def set_non_keyable(node_name, attributes):
    """
    Sets the given attributes of the given node name as a non keyale attributes
    :param node_name: str, name of a Maya node
    :param attributes: list<str>, list of attributes in the node that we want to set as non keyable attributes
    """

    attributes = helpers.force_list(attributes)
    for attr in attributes:
        name = '{}.{}'.format(node_name, attr)
        cmds.setAttr(name, k=False, cb=True)
        if cmds.getAttr(name, type=True) == 'double3':
            attributes.append('{}X'.format(attr))
            attributes.append('{}Y'.format(attr))
            attributes.append('{}Z'.format(attr))


def connect_visibility(attr_name, target_node, default_value=True):
    """
    Connect the visibility of the target node into an attribute
    :param attr_name: str, node.attribute name of a node. If it does not exist, it will ber created
    :param target_node: str, target node to connect its visibility into the attribute
    :param default_value: bool, Whether you want the visibility on/off by default
    """

    nodes = helpers.force_list(target_node)

    if not cmds.objExists(attr_name):
        split_name = attr_name.split('.')
        cmds.addAttr(split_name[0], ln=split_name[1], at='bool', dv=default_value, k=True)
        set_non_keyable(node_name=split_name[0], attributes=[split_name[1]])

    for n in nodes:
        if is_connected('{}.visibility'.format(n)):
            logger.warning('"{}" and "{}".visibility are already connected!'.format(attr_name, n))
        else:
            cmds.connectAttr(attr_name, '{}.visibility'.format(n))


def return_message_object(storage_object, message_attr):
    """
    Returns the object linked to the message attribute
    :param storage_object: str, object holding the message attribute
    :param message_attr: str, name of the message attribute
    :return:  str
    """

    combined = '{0}.{1}'.format(storage_object, message_attr)
    if cmds.objExists(combined):
        if cmds.addAttr(combined, query=True, m=True):
            logger.warning('"{} is a multi message attribute. Use return_message_data instead'.format(combined))
            return False

        message_obj = cmds.listConnections(combined)
        if message_obj is not None:
            if cmds.objExists(message_obj[0]) and not cmds.objectType(message_obj[0]) == 'reference':
                return message_obj[0]
            else:
                return repair_message_to_reference_target(storage_object, message_attr)
        else:
            return False
    else:
        return False


def return_message_data(storage_object, message_attr, long_names=True):
    """
    Return object linked to the multi message attribute
    :param storage_object: str, object holding the message attribute
    :param message_attr: str, name of the message attribute
    :param long_names: bool, True if you want to get long names
    :return: str
    """

    combined = '{0}.{1}'.format(storage_object, message_attr)
    if cmds.objExists(combined):
        msg_links = cmds.listConnections(combined, destination=True, source=True)
        return_list = list()
        if msg_links:
            for msg in msg_links:
                if long_names:
                    return_list.append(str(cmds.ls(msg, long=True)[0]))
                else:
                    return_list.append(str(cmds.ls(msg, shortNames=True)[0]))
            return return_list
        else:
            return False
    else:
        return False


def store_object_name_to_message(obj, storage_obj):
    """
    Adds the given object name as a message attribute to the storage object
    :param obj: str, object to store
    :param storage_obj: str, object to store info into
    """

    combined = '{0}.{1}'.format(storage_obj, obj)
    if cmds.objExists(combined):
        logger.debug(combined + ' already exists')
    else:
        cmds.addAttr(storage_obj, ln=obj, at='message')
        cmds.connectAttr(obj + '.message', storage_obj + '.' + obj)


def store_objects_list_name_to_message(objects_list, storage_obj):
    """
    Adds the objects names as message attributes to the storage object
    :param objects_list: list<str>, list of objects to store
    :param storage_obj: str, object to store info into
    """

    for obj in objects_list:
        store_object_name_to_message(obj, storage_obj)


def store_object_to_message(obj, storage_obj, message_name):
    """
    Adds the object name as a message attribute to the storage object with a custom
    message attribute name
    :param obj: str, object to store
    :param storage_obj: str, object to store the info to
    :param message_name: str, message name to store it as
    :return: bool, True if the operation was successful or False otherwise
    """

    # Check that given Maya objects are valid
    assert cmds.objExists(obj) is True, '"{}" does not exists'.format(obj)
    assert cmds.objExists(storage_obj) is True, '"{}" does not exists'.format(storage_obj)

    combined = storage_obj + '.' + message_name
    obj_long = cmds.ls(obj, long=True)
    if len(obj_long) > 1:
        logger.warning('Cannot find long name for object, found "{}"'.format(obj_long))
        return False
    obj_long = obj_long[0]

    storage_long = cmds.ls(storage_obj, long=True)
    if len(storage_long) > 1:
        logger.warning('Cannot find long name for storage, found "{}"'.format(obj_long))
        return False
    storage_long = storage_long[0]

    try:
        if cmds.objExists(combined):
            if cmds.attributeQuery(
                    message_name, node=storage_obj, msg=True) and not cmds.addAttr(combined, query=True, m=True):
                if return_message_object(storage_object=storage_obj, message_attr=message_name) != obj:
                    logger.debug('{} already exists. Adding it to existing message node'.format(combined))
                    break_connection(combined)
                    connect_attribute('{}.message'.format(obj), '{0}.{1}'.format(storage_obj, message_name))
                    return True
                else:
                    logger.debug('"{0}" already stored to "{1}.{2}"'.format(obj, storage_obj, message_name))
            else:
                connections = return_driven_attribute(combined)
                if connections:
                    for cnt in connections:
                        break_connection(cnt)

                logger.debug('"{}" already exists. Not a message attribute, converting it!'.format(combined))
                safe_delete_attribute(storage_obj, message_name)

                buffer = cmds.addAttr(storage_obj, ln=message_name, at='message')
                connect_attribute('{}.message'.format(obj), '{0}.{1}'.format(storage_obj, message_name))

                return True
        else:
            cmds.addAttr(storage_obj, ln=message_name, at='message')
            connect_attribute('{}.message'.format(obj), '{0}.{1}'.format(storage_obj, message_name))

            return True
    except Exception as exc:
        logger.warning(exc)
        return False


def store_objects_to_message(objects, storage_obj, message_name):
    """
    Adds the object names as a multi message attribute to the storage object with a custom
    message attribute name
    :param objects: list, objects to store
    :param storage_obj: str, object to store the info to
    :param message_name: str, message name to store it as
    :return: bool, True if the operation was successful or False otherwise
    """

    # Check that given Maya objects are valid
    for obj in objects:
        assert cmds.objExists(obj) is True, '"{}" does not exists'.format(obj)
    assert cmds.objExists(storage_obj) is True, '"{}" does not exists'.format(storage_obj)

    combined = '{0}.{1}'.format(storage_obj, message_name)
    objects = helpers.return_list_without_duplicates(objects)

    try:
        if cmds.objExists(combined):
            logger.debug(combined + ' already exists. Adding to existing message node')
            safe_delete_attribute(storage_obj, message_name)
            cmds.addAttr(storage_obj, ln=message_name, at='message', m=True, im=False)
            for obj in objects:
                cmds.connectAttr(
                    '{}.message'.format(obj), '{0}.{1}'.format(storage_obj, message_name), nextAvailable=True)
            cmds.setAttr(combined, lock=True)
            return True
        else:
            cmds.addAttr(storage_obj, ln=message_name, at='message', m=True, im=False)
            for obj in objects:
                cmds.connectAttr(
                    '{}.message'.format(obj), '{0}.{1}'.format(storage_obj, message_name), nextAvailable=True)
            cmds.setAttr(combined, lock=True)
            return True
    except Exception:
        logger.error('Storing "{0}" to "{1}.{2}" failed!'.format(objects, storage_obj, message_name))
        return False


def store_world_matrix_to_attribute(transform, attribute_name='origMatrix', skip_if_exists=False):
    """
    Stores world matrix of given transform into an attribute in the same transform
    :param transform: str
    :param attribute_name: str
    :param skip_if_exists: bool
    """

    world_matrix = cmds.getAttr('{}.worldMatrix'.format(transform))
    if cmds.objExists('{}.{}'.format(transform, attribute_name)):
        if skip_if_exists:
            return
        cmds.setAttr('{}.{}'.format(transform, attribute_name), lock=False)
        cmds.deleteAttr('{}.{}'.format(transform, attribute_name))
    cmds.addAttr(transform, ln=attribute_name, at='matrix')
    cmds.setAttr('{}.{}'.format(transform, attribute_name), *world_matrix, type='matrix', lock=True)


def repair_message_to_reference_target(obj, attr):
    """
    Fix message connection in both directions
    To work properly:
        1) Target attribute must be a message attribute
        2) Target is connected to a reference node
    :param obj: str
    :param attr: str
    :return: bool
    """

    target_attr = '{0}.{1}'.format(obj, attr)
    assert cmds.attributeQuery(attr, node=obj, msg=True), '"{}" is not a message attribute!'.format(target_attr)

    obj_test = cmds.listConnections(target_attr, p=1)
    assert cmds.objectType(obj_test[0]) == 'reference', '"{}" is not returning a reference!'.format(target_attr)

    ref = obj_test[0].split('RN.')[0]
    logger.info('Reference connection found, attempting to fix ...')

    message_connections_out = cmds.listConnections('{}.message'.format(obj), p=1)
    if message_connections_out and ref:
        for plug in message_connections_out:
            if ref in plug:
                logger.info('Checking "{}"'.format(plug))
                match_obj = plug.split('.')[0]
                connect_attribute('{}.message'.format(match_obj, target_attr))
                logger.info('"{0}" restored to "{1}"'.format(target_attr, match_obj))

                if len(message_connections_out) > 1:
                    logger.warning(
                        "Found more than one possible connection. Candidates are:'%s'" % "','".join(
                            message_connections_out))
                    return False
                return match_obj

    logger.warning('No message connections and reference found')
    return False


def connect_message(input_node, target_node, attr, force=False):
    """
    Connects the message attribute of the input_node into a custom message attribute on target_node
    :param input_node: str, name of a node
    :param target_node: str, name of a node
    :param attr: str, name of the message attribute to create and connect into. If already exists, just connect
    :param force: bool, whether force the connection of the message attribute
    """

    if not input_node or not cmds.objExists(input_node):
        logger.warning('No input node to connect message')
        return

    current_index = name_utils.get_last_number(attr)
    if current_index is None:
        current_index = 2

    test_attr = attr
    while cmds.objExists('{}.{}'.format(target_node, test_attr)):
        input_value = attribute_input('{}.{}'.format(target_node, test_attr))
        if not input_value:
            break
        test_attr = attr + str(current_index)
        current_index += 1
        if current_index == 1000:
            break

    if not cmds.objExists('{}.{}'.format(target_node, test_attr)):
        cmds.addAttr(target_node, ln=test_attr, at='message')

    if not cmds.isConnected('{}.message'.format(input_node), '{}.{}'.format(target_node, test_attr)):
        cmds.connectAttr('{}.message'.format(input_node), '{}.{}'.format(target_node, test_attr), force=force)


def connect_group_with_message(input_node, target_node, attr):
    """
    Connects given input node to the group_+(target_node.attr) attribute
    :param input_node: str, node we want to connect through message
    :param target_node: str, target node
    :param attr: str, base name of the attribute
    """

    if not attr.startswith('group_'):
        attr = 'group_' + attr

    connect_message(input_node, target_node, attr)


def return_object_attr_split(attr):
    """
    Splits given attribute returning a pair list with (obj ,attr)
    :param attr: str
    :return: list<obj, attr>
    """

    assert cmds.objExists(attr) is True, '"{}" does not exists!'.format(attr)
    return_buffer = list()

    if '.' in list(attr):
        split = attr.split('.')
        if split >= 2:
            return_buffer = [split[0], '.'.join(split[1:])]

        if return_buffer:
            return return_buffer

    return False


def return_driver_attribute(attr, skip_conversion_nodes=False, long_names=True):
    """
    Returns the driver attribute of an attribute if it exists
    :param attr: str
    :param skip_conversion_nodes: bool
    :param long_names: bool
    :return: variant, str || bool
    """

    if cmds.connectionInfo(attr, isDestination=True):
        source_connections = cmds.listConnections(
            attr, skipConversionNodes=skip_conversion_nodes, destination=False, source=True, plugs=True)
        if not source_connections:
            source_connections = [cmds.connectionInfo(attr, sourceFromDestination=True)]
        if source_connections:
            if long_names:
                return str(cmds.ls(source_connections[0], long=True)[0])
            else:
                return str(cmds.ls(source_connections[0], shortNames=True)[0])
        return False

    return False


def return_driver_object(attr, skip_conversion_nodes=False, long_names=True):
    """
    Returns the driver object of an attribute if it exists
    :param attr: str
    :param skip_conversion_nodes: bool
    :param long_names: bool
    :return: str
    """

    source_objects = cmds.listConnections(
        attr, skipConversionNodes=skip_conversion_nodes, destination=False, source=True, plugs=False)
    if not source_objects:
        return False

    if long_names:
        return str(cmds.ls(source_objects[0], long=True)[0])
    else:
        return str(cmds.ls(source_objects[0], shortNames=True)[0])


def return_driven_attribute(attr, skip_conversion_nodes=False, long_names=True):
    """
    Return the driven attribute of an attribute if it exists
    :param attr: str
    :param skip_conversion_nodes: bool
    :param long_names: bool
    :return: variant, list<str> || bool
    """

    if cmds.connectionInfo(attr, isSource=True):
        dst_connections = cmds.listConnections(
            attr, skipConversionNodes=skip_conversion_nodes, destination=True, source=False, plugs=True)
        if not dst_connections:
            dst_connections = cmds.connectionInfo(attr, destinationFromSource=True)
        if dst_connections:
            return_list = list()
            for dst in dst_connections:
                if long_names:
                    return_list.append(str(cmds.ls(dst, long=True)[0]))
                else:
                    return_list.append(str(cmds.ls(dst, shortNames=True)[0]))
            return return_list
        return False

    return False


def return_driven_object(attr, skip_conversion_nodes=False, long_names=True):
    """
    Returns the driven object of an attribute if it exists
    :param attr: str
    :param skip_conversion_nodes: bool
    :param long_names: bool
    :return: str
    """

    dst_connections = cmds.listConnections(
        attr, skipConversionNodes=skip_conversion_nodes, destination=True, source=False, plugs=False)
    if not dst_connections:
        return False
    if attr in dst_connections:
        dst_connections.remove(attr)

    return_list = list()
    for dst in dst_connections:
        if long_names:
            return_list.append(str(cmds.ls(dst, long=True)[0]))
        else:
            return_list.append(str(cmds.ls(dst, shortNames=True)[0]))

    return return_list


def return_user_attributes(obj, *args, **kwargs):
    """
    Returns user created attribuets of an object
    :param obj:  str, object to check
    :param args:
    :param kwargs:
    :return: list of [[attr_name, target], [..], [..]]
    """

    attrs = cmds.listAttr(obj, userDefined=True)
    if attrs > 0:
        return attrs

    return False


def return_message_objects(obj):
    """
    Return all objects linked to the messages of the given object
    :param obj:  str, object with message attributes
    :return: str
    """

    obj_list = list()
    obj_attrs = cmds.listAttr(obj, userDefined=True)
    if obj_attrs is not None:
        for attr in obj_attrs:
            msg = cmds.attributeQuery(attr, node=obj, msg=True)
            if msg:
                connections = cmds.listConnections('{0}.{1}'.format(obj, attr))
                if connections is not None:
                    obj_list.append(connections[0])
        return obj_list

    return False


def return_message_attrs(obj):
    """
    Returns list with pair ([attr_name, target], [..], [..]) with all message objects linked to the given object
    :param obj: str, object with message attributes
    :return: dict
    """

    msg_dict = dict()
    obj_attrs = cmds.listAttr(obj, userDefined=True)
    if obj_attrs is not None:
        for attr in obj_attrs:
            msg = cmds.attributeQuery(attr, node=obj, msg=True)
            if msg:
                connections = cmds.listConnections('{0}.{1}'.format(obj, attr))
                if connections is not None:
                    msg_dict[attr] = connections[0]
        return msg_dict

    return False


def return_family_dict(obj, attr):
    """
    Returns a dictionary of parent, children, siblings of the given attribute or False if nothing is found
    :param obj: str
    :param attr: str
    """

    assert cmds.objExists('{0}.{1}'.format(obj, attr)) is True, '"{0}.{1}" does not exists!'.format(obj, attr)

    return_dict = dict()
    attrs = cmds.attributeQuery(attr, node=obj, listParent=True)
    if attrs is not None:
        return_dict['parent'] = attrs[0]
    attrs = cmds.attributeQuery(attr, node=obj, listChildren=True)
    if attrs is not None:
        return_dict['children'] = attrs
    attrs = cmds.attributeQuery(attr, node=obj, listSiblings=True)
    if attrs is not None:
        return_dict['siblings'] = attrs

    if return_dict:
        return return_dict

    return False


def is_translate_rotate_connected(transform, ignore_keyframe=False):
    """
    Returns whether the given transform translate and rotate attributes are connected or not
    :param transform: str, name of a transform
    :param ignore_keyframe: bool
    :return: bool
    """

    for attr in 'tr':
        for axis in 'xyz':
            name = '{}.{}{}'.format(transform, attr, axis)
            input_value = attribute_input(name)
            if not input_value:
                return False
            if ignore_keyframe:
                if cmds.nodeType(input_value).find('animCurve') > -1:
                    return False

            return True


def create_axis_attribute(name, node, value=0, positive_axes=True, negative_axis=True, none_value=True):
    """
    Adds an axis attribute to the given node
    :param name: str, name of the attribute
    :param node: str, node to add attribute into
    :param value: int, default axis value
    :param positive_axes: bool, Whether to add positive axis (+X, +Y, +Z)
    :param negative_axis: bool, Whether to add negative axis (-X, -Y, -Z)
    :param none_value: str, bool, Whether to add none value (none)
    :return: EnumAttribute
    """

    axis_attr = EnumAttribute(name, value=value)
    axes_values = list()
    if positive_axes:
        for axis in ['X', 'Y', 'Z']:
            axes_values.append(axis)
    if negative_axis:
        for axis in ['-X', '-Y', '-Z']:
            axes_values.append(axis)
    if none_value:
        axes_values.append('none')
    axis_attr.set_enum_names(axes_values)
    axis_attr.set_locked(False)
    axis_attr.create(node=node)

    return axis_attr


def create_triangle_attribute(name, node, value=None):
    """
    Adds a triangle attribute to the given node
    :param name: str, name of the attribute
    :param node: str, node to add attribute into
    :param value: int, default enum value
    """

    triangle_attr = EnumAttribute(name, value=value)
    triangle_attr.set_enum_names(['grandParent', 'parent', 'self', 'child', 'grandChild'])
    triangle_attr.create(node)

    return triangle_attr


def create_title(node, name, name_list=None):
    """
    Creates an enum title attribute on given node
    :param node: str, name of a node
    :param name: str, name of the title
    :param name_list: list<str>, enums list
    """

    if not cmds.objExists(node):
        logger.warning('{} does not exists to create title on'.format(node))

    name = name.replace(' ', '')
    title = EnumAttribute(name)
    if name_list:
        title.set_enum_names(name_list)

    title.create(node)


def inputs(node, node_only=True):
    """
    Returns all the inputs attributes of the given node
    :param node: str, name of the node
    :param node_only: bool, Whether to return the node name or the node name + attribute
    :return: list<str>, list of input attributes
    """

    plugs = not node_only

    return cmds.listConnections(
        node, connections=False, destination=False, source=True, plugs=plugs, skipConversionNodes=True)


def outputs(node, node_only=True):
    """
    Returns all the outputs attributes of the given node
    :param node: str, name of the node
    :param node_only: bool, Whether to return the node name or the node name + attribute
    :return: list<str>, list of input attributes
    """

    plugs = not node_only

    return cmds.listConnections(
        node, connections=plugs, destination=TransferAttributes, source=False, plugs=plugs, skipConversionNodes=True)


def transfer_output_connections(source_node, target_node):
    """
    Transfer outputs connections from source_node to target_node
    :param source_node: str, node to take outputs connections from
    :param target_node: str, node to transfer output connections to
    """

    outs = cmds.listConnections(source_node, plugs=True, connections=True, destination=True, source=False)
    if not outs:
        return

    for i in range(len(outs), 2):
        new_attr = outs[i].replace(source_node, target_node)
        cmds.disconnectAttr(outs[i], outs[i + 1])
        cmds.connectAttr(new_attr, outs[i + 1], f=True)


def hide_attributes(node, attributes, skip_visibility=False):
    """
    Lock and hide the attributes given
    NOTE: Only should work in individual attributes (such as translateX, not translate)
    :param node: str, name of a node
    :param attributes: list<str>, list of attributes on node to lock and hide
    :param skip_visibility: bool, Whether or not skip visibility attribute hide
        (just name of the attribute, such as translateX
    """

    attrs = helpers.force_list(attributes)
    for attr in attrs:
        if attr == 'visibility' and skip_visibility:
            continue
        current_attr = ['{}.{}'.format(node, attr)]
        if not cmds.objExists(current_attr[0]):
            logger.warning('Impossible to lock attribute {} because it does not exists!'.format(current_attr[0]))
            return

        if cmds.getAttr(current_attr, type=True) == 'double3':
            current_attr = list()
            for axis in 'XYZ':
                current_attr.append('{}.{}{}'.format(node, attr, axis))

        for sub_attr in current_attr:
            cmds.setAttr(sub_attr, l=True, k=False, cb=False)


def hide_keyable_attributes(node, skip_visibility=False):
    """
    Hide keyable attributes on given node
    :param node: str, name of a node
    """

    attrs = cmds.listAttr(node, k=True)
    if attrs:
        return hide_attributes(node, attrs, skip_visibility=skip_visibility)
    if cmds.getAttr('{}.rotateOrder'.format(node), cb=True):
        hide_rotate_order(node)


def show_rotate_order(node, value=None):
    """
    Hides rotate order attributes of the given node
    :param node: str
    :param value:
    """

    if value is None:
        cmds.setAttr('{}.rotateOrder'.format(node), k=True)
    else:
        cmds.setAttr('{}.rotateOrder'.format(node), value, k=True)


def hide_rotate_order(node):
    """
    Hides rotate order attributes of the given node
    :param node: str
    """

    cmds.setAttr('{}.rotateOrder'.format(node), k=False, l=False)
    cmds.setAttr('{}.rotateOrder'.format(node), cb=False)


def lock_keyable_attributes(node, hide=True):
    """
    Locks attributes on given node
    :param node: str
    :param hide: bool
    """

    attrs = cmds.listAttr(node, k=True)
    return lock_attributes(node, attrs, lock=True, hide=hide)


def hide_translate(node_name):
    """
    Hide translate attributes of the given node
    :param node_name: str, name of Maya node
    """

    return hide_attributes(node_name, 'translate')


def hide_rotate(node_name):
    """
    Hide rotate attributes of the given node
    :param node_name: str, name of Maya node
    """

    return hide_attributes(node_name, 'rotate')


def hide_scale(node_name):
    """
    Hide scale attributes of the given node
    :param node_name: str, name of Maya node
    """

    return hide_attributes(node_name, 'scale')


def hide_visibility(node_name):
    """
    Hide visibility attribute of the given node
    :param node_name: str, name of Maya node
    """

    return hide_attributes(node_name, 'visibility')


def color_to_rgb(color_index):
    """
    Converts given Maya color index into RGB
    :param color_index: int
    :return: list(int, int, int)
    """

    values = list()
    if color_index > 0:
        values = cmds.colorIndex(color_index, query=True)

    return values


def color(shape_node):
    """
    Returns color of given node
    :param shape_node: str, name of node to retrieve color of
    :return: list(int, int, int)
    """

    if not cmds.objExists('{}.overrideColor'.format(shape_node)):
        return 0

    if not cmds.getAttr('{}.overrideRGBColors'.format(
            shape_node)) or not cmds.objExists('{}.overrideRGBColors'.format(shape_node)):
        color = cmds.getAttr('{}.overrideColor'.format(shape_node))

        return color

    if cmds.getAttr('{}.overrideRGBColors'.format(shape_node)):
        color = list(cmds.getAttr('{}.overrideColorRGB'.format(shape_node))[0])

        color[0] = color[0] if color[0] > 1 else (color[0] * 255)
        color[1] = color[1] if color[1] > 1 else (color[1] * 255)
        color[2] = color[2] if color[2] > 1 else (color[2] * 255)

        return color


def set_color(nodes, color, color_transform=False, short_range=False):
    """
    Set the override color for the given nodes
    :param nodes: list<str>, list of nodes to change the override color
    :param color: variant, list || int, color index to set override color to or color RGB list
    :param color_transform: bool, whether to override the shapes of the color or the transform itself
    :param short_range: bool, Whether color calculations are made using short range (values between 0 and 1)
        or long range (values between 0 and 255)
    """

    from Qt.QtGui import QColor

    nodes = helpers.force_list(nodes)

    maya_version = int(cmds.about(version=True))
    use_rgb_color = type(color) in [list, tuple] or isinstance(color, QColor)
    if type(color) in [list, tuple]:

        if not short_range and all(i <= 1.0 for i in color):
            short_range = True

        if short_range:
            color = QColor.fromRgbF(*color)
        else:
            color = QColor.fromRgb(*color)
    else:
        if color < 0 or color > 31:
            logger.warning('Maximum color index is 31. Using 31 value instead of {}!'.format(color))
            color = 31

    if use_rgb_color and maya_version < 2015:
        logger.warning('Current Maya version "{}" does not support RGB colors'.format(maya_version))
        return

    if color_transform:
        for node in nodes:
            if cmds.attributeQuery('overrideEnabled', node=node, exists=True):
                cmds.setAttr(node + '.overrideEnabled', True)
                if not use_rgb_color:
                    if cmds.attributeQuery('overrideRGBColors', node=node, exists=True):
                        cmds.setAttr(node + '.overrideRGBColors', False)
                    if cmds.attributeQuery('overrideColor', node=node, exists=True):
                        cmds.setAttr(node + '.overrideColor', color)
                else:
                    if cmds.attributeQuery('overrideRGBColors', node=node, exists=True):
                        cmds.setAttr(node + '.overrideRGBColors', True)
                        if cmds.attributeQuery('overrideColorRGB', node=node, exists=True):
                            cmds.setAttr(node + '.overrideColorRGB',
                                              color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)
    else:
        for node in nodes:
            shapes = list()
            if cmds.nodeType(node) == 'transform':
                shapes = cmds.listRelatives(node, type='shape')
            elif cmds.objectType(node, isAType='shape'):
                shapes = [node]
            if len(shapes) > 0:
                for shape in shapes:
                    if cmds.attributeQuery('overrideEnabled', node=shape, exists=True):
                        cmds.setAttr(shape + '.overrideEnabled', True)
                        if not use_rgb_color:
                            if cmds.attributeQuery('overrideRGBColors', node=shape, exists=True):
                                cmds.setAttr(shape + '.overrideRGBColors', False)
                            if cmds.attributeQuery('overrideColor', node=shape, exists=True):
                                cmds.setAttr(shape + '.overrideColor', color)
                        else:
                            if cmds.attributeQuery('overrideRGBColors', node=shape, exists=True):
                                cmds.setAttr(shape + '.overrideRGBColors', True)
                                if cmds.attributeQuery('overrideColorRGB', node=shape, exists=True):
                                    cmds.setAttr(shape + '.overrideColorRGB',
                                                      color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)


def attribute_values(node, keyable_only=True):
    """
    Get the values of the attributes of the given node
    :param node: str, node we want to retrieve attributes from
    :param keyable_only: bool, Whether to get only keyable attributes or not
    :return: dict<str, variant>
    """

    attrs = cmds.listAttr(node, k=keyable_only, v=True)
    values = dict()
    for attr in attrs:
        try:
            value = cmds.getAttr('{}.{}'.format(node, attr))
            values[attr] = value
        except Exception:
            continue

    return values


def set_attribute_values(node, values):
    """
    Set the given values from the [attr | attr_value] dict to the given node
    :param node: str, node we want to set attributes of
    :param values: dict<attr_name, attr_value>, attributes dict
    """

    for attr, attr_value in values.items():
        try:
            cmds.setAttr('{}.{}'.format(node, attr), attr_value)
        except Exception:
            pass


def transfer_attribute_values(source_node, target_node, keyable_only=True):
    """
    Transfers attributes fron one node to another
    :param source_node: str, node to get attributes from
    :param target_node: str, node to transfer attributes to
    :param keyable_only: bool, Whether to get only keyables attributes or not
    """

    attrs = cmds.listAttr(source_node, k=keyable_only)
    for attr in attrs:
        try:
            value = cmds.getAttr('{}.{}'.format(source_node, attr))
        except Exception:
            continue
        try:
            cmds.setAttr('{}.{}'.format(target_node, attr), value)
        except Exception:
            pass


def lock_attributes(node, attributes=None, lock=True, hide=False):
    """
    Lock attributes on a node
    :param node: str, name of the node
    :param lock: bool, Whether to lock the attributes or not
    :param attributes: list<str>, list of attributes to lock on node. If None, all keyable attributes will be lock
    :param hide: bool, Whether to lock ahd hide the attributes or only lock
    """

    if not attributes:
        attributes = cmds.listAttr(node, k=True)
    else:
        attributes = helpers.force_list(attributes)

    for attr in attributes:
        attr_name = '{}.{}'.format(node, attr)
        inputs = inputs(attr_name)
        if inputs:
            continue
        cmds.setAttr(attr_name, lock=lock)
        if hide:
            cmds.setAttr(attr_name, k=False)
            cmds.setAttr(attr_name, cb=False)


def unlock_attributes(node, attributes=None, only_keyable=False):
    """
    Unlock attributes on a node
    :param node: str, name of the node
    :param attributes: list<str>, list of attributes to lock on node. If None, unlock any that are locked
    :param only_keyable: bool, Whether to unlock only the keyable attributes
    """

    if not attributes:
        if only_keyable:
            attributes = cmds.listAttr(node, locked=True, k=True)
        else:
            attributes = cmds.listAttr(node, locked=True)

    if attributes:
        attributes = helpers.force_list(attributes)
        for attr in attributes:
            cmds.setAttr('{}.{}'.format(node, attr), lock=False, k=True, cb=True)
            cmds.setAttr('{}.{}'.format(node, attr), k=True)


def lock_translate_attributes(node, hide=True):
    """
    Lock translate attributes of the given nodes
    :param node: str, name of the node
    :param hide: bool, whether to hide attributes or not
    """

    lock_attributes(node, attributes=['translateX', 'translateY', 'translateZ'], hide=hide)


def lock_rotate_attributes(node, hide=True):
    """
    Lock rotate attributes of the given nodes
    :param node: str, name of the node
    :param hide: bool, whether to hide attributes or not
    """

    lock_attributes(node, attributes=['rotateX', 'rotateY', 'rotateZ'], hide=hide)


def lock_scale_attributes(node, hide=True):
    """
    Lock scale attributes of the given nodes
    :param node: str, name of the node
    :param hide: bool, whether to hide attributes or not
    """

    lock_attributes(node, attributes=['scaleX', 'scaleY', 'scaleZ'], hide=hide)


def unlock_translate_attributes(node):
    """
    Unlock translate attributes of the given nodes
    :param node: str, name of the node
    """

    unlock_attributes(node, attributes=['translateX', 'translateY', 'translateZ'])


def unlock_rotate_attributes(node):
    """
    Unlock rotate attributes of the given nodes
    :param node: str, name of the node
    """

    unlock_attributes(node, attributes=['rotateX', 'rotateY', 'rotateZ'])


def unlock_scale_attributes(node):
    """
    Unlock scale attributes of the given nodes
    :param node: str, name of the node
    """

    unlock_attributes(node, attributes=['scaleX', 'scaleY', 'scaleZ'])


def remove_user_defined_attributes(node):
    """
    Removes all user defined attributes from the given node
    :param node: str, name of the node
    """

    unlock_attributes(node)

    attrs = cmds.listAttr(node, ud=True)
    if not attrs:
        return

    for attr in attrs:
        try:
            unlock_attributes(node, attr)
            disconnect_attribute(attr)
            cmds.deleteAttr('{}.{}'.format(node, attr))
        except Exception:
            pass


def message_attributes(node, user_defined=True):
    """
    Returns all message attributes of the given node
    :param node: str, node to get message attributes from
    :param user_defined: bool, Whether to check for user defined message attributes or not
    :return: list<str>
    """

    attrs = cmds.listAttr(node, ud=user_defined)
    found = list()
    if attrs:
        for attr in attrs:
            attr_path = '{}.{}'.format(node, attr)
            if cmds.getAttr(attr_path, type=True) == 'message':
                found.append(attr)

    return found


def message_input(node, message):
    """
    Get the input value of a message attribute
    :param node: str, node to get message input from
    :param message: str, message attribute name we want to get input from
    :return: variant
    """

    input_msg_value = attribute_input('{}.{}'.format(node, message), node_only=True)

    return input_msg_value


def connect_vector_attributes(source_transform, target_transform, attribute, connect_type='plus'):
    """
    Connects an X, Y, Z attribute (suck as translate, rotate or scale)
    :param source_transform: str, name of a node
    :param target_transform: str, name of a node
    :param attribute: str, vector attribute we want to connect (eg: translate, rotate, scale)
    :param connect_type: str, 'plus' or 'multiply'
    """

    axis = ['X', 'Y', 'Z']
    nodes = list()

    for letter in axis:
        source_attr = '{}.{}{}'.format(source_transform, attribute, letter)
        target_attr = '{}.{}{}'.format(target_transform, attribute, letter)
        if connect_type == 'plus':
            node = connect_plus(source_attr, target_attr)
            nodes.append(node)
        elif connect_type == 'multiply':
            if node:
                cmds.connectAttr(source_attr, '{}.input1{}'.format(node, letter))
                cmds.connectAttr('{}.output{}'.format(node, letter), target_attr)
            else:
                node = connect_multiply(source_attr, target_attr)

    if not nodes:
        nodes = node

    return nodes


def connect_translate(source_transform, target_transform):
    """
    Connect translate attributes from source to target
    :param source_transform: str, name of a transform
    :param target_transform: str, name of a transform
    """

    connect_vector_attributes(source_transform, target_transform, 'translate')


def connect_rotate(source_transform, target_transform):
    """
    Connect rotate attributes from source to target
    :param source_transform: str, name of a transform
    :param target_transform: str, name of a transform
    """

    connect_vector_attributes(source_transform, target_transform, 'rotate')
    try:
        cmds.connectAttr('{}.rotateOrder'.format(source_transform), '{}.rotateOrder'.format(target_transform))
    except Exception:
        pass


def connect_scale(source_transform, target_transform):
    """
    Connect scale attributes from source to target
    :param source_transform: str, name of a transform
    :param target_transform: str, name of a transform
    """

    connect_vector_attributes(source_transform, target_transform, 'scale')


def connect_transforms(source_transform, target_transform):
    """
    Connects transltae, rotate and scale channels from source to target
    :param source_transform: str, name of a transform
    :param target_transform: str, name of a transform
    """

    connect_translate(source_transform, target_transform)
    connect_rotate(source_transform, target_transform)
    connect_scale(source_transform, target_transform)


def connect_translate_into_pivots(source_transform, target_transform):
    """
    Connect translate pivots from source to target
    :param source_transform: str, name of a transform
    :param target_transform: str, name of a transform
    """

    cmds.connectAttr('{}.translateX'.format(source_transform), '{}.rotatePivotX'.format(target_transform))
    cmds.connectAttr('{}.translateY'.format(source_transform), '{}.rotatePivotY'.format(target_transform))
    cmds.connectAttr('{}.translateZ'.format(source_transform), '{}.rotatePivotZ'.format(target_transform))

    cmds.connectAttr('{}.translateX'.format(source_transform), '{}.scalePivotX'.format(target_transform))
    cmds.connectAttr('{}.translateY'.format(source_transform), '{}.scalePivotY'.format(target_transform))
    cmds.connectAttr('{}.translateZ'.format(source_transform), '{}.scalePivotZ'.format(target_transform))


def connect_plus_and_value(source_attr, target_attr, value):
    """
    Connect plus attribute from source to target attr
    :param source_attr: str, node.attribute name of an attribute
    :param target_attr: str, node.attribute nome of an attribute
    :param value: int
    """

    target_attr_name = target_attr.replace('.', '_')
    plus = cmds.createNode('plusMinusAverage', n='plusMinusAverage_{}'.format(target_attr_name))
    cmds.connectAttr(source_attr, '{}.input1D[0]'.format(plus))
    cmds.setAttr('{}.input1D[1]'.format(plus), value)
    cmds.connectAttr('{}.output1D'.format(plus), target_attr, f=True)

    return plus


def connect_plus(source_attr, target_attr, respect_value=False):
    """
    Connects source_attr into target_attr with a plusMinusAverage inbetween
    :param source_attr: str, node.attribute name of an attribute
    :param target_attr: str, node.attribute nome of an attribute
    :param respect_value: bool, Whether to edit the input1D list to accomodate for values in the target attribute
    """

    if cmds.isConnected(source_attr, target_attr):
        return

    input_attr = attribute_input(target_attr)
    value = cmds.getAttr(target_attr)
    if not input_attr and not respect_value:
        cmds.connectAttr(source_attr, target_attr)
        return

    if input_attr:
        if cmds.nodeType(input_attr) == 'plusMinusAverage':
            plus = input_attr.split('.')[0]
            if cmds.getAttr('{}.operation'.format(plus)) == 1:
                slot = available_slot('{}.input1D'.format(plus))
                cmds.connectAttr(source_attr, '{}.input1D[{}]'.format(plus, slot))
                return plus

    target_attr_name = target_attr.replace('.', '_')
    plus = cmds.createNode('plusMinusAverage', n='plusMinusAverage_{}'.format(target_attr_name))
    cmds.connectAttr(source_attr, '{}.input1D[1]'.format(plus))
    if input_attr:
        cmds.connectAttr(input_attr, '{}.input1D[0]'.format(plus))
        new_value = cmds.getAttr(target_attr)
        if abs(new_value) - abs(value) > 0.01:
            cmds.setAttr('{}.input1D[2]'.format(plus), value)
    else:
        if respect_value:
            cmds.setAttr('{}.input1D[0]'.format(plus), value)

    cmds.connectAttr('{}.output1D'.format(plus), target_attr, f=True)

    return plus


def connect_multiply(source_attr, target_attr, value=0.1, skip_attach=False, plus=True, name=None):
    """
    Connects source_attr into target_attr with a multiplyDivide inbetween
    :param source_attr: str, node.attribute name of an attribute
    :param target_attr: str, node.attribute name of an attribute
    :param value: float, value of the mulitplyDivide
    :param skip_attach: bool, Whether to attach the input into target attribute
        (if there is one) into input2X of multiplyDivide
    :param plus: bool, Whether to fix input connections in target_attr to plug into a plusMinusAverage. This allow us
    not loosing their influence on that attribute while still multiplying by the source_attr
    :return: str, name of the multiplyDivide node
    """

    input_attr = attribute_input(target_attr)
    lock_state = LockState(target_attr)
    lock_state.unlock()

    multiply_name = name or 'multiplyDivide_{}'.format(
        target_attr.replace('.', '_').replace('[', '_').replace(']', '_'))

    source_attr_type = cmds.getAttr(source_attr, type=True)
    attr_type = cmds.getAttr(target_attr, type=True)

    multi = cmds.createNode('multiplyDivide', n=multiply_name)

    if attr_type == 'double3':
        if source_attr_type == 'double3':
            cmds.connectAttr(source_attr, '{}.input1'.format(multi))
        else:
            cmds.connectAttr(source_attr, '{}.input1X'.format(multi))
            cmds.connectAttr(source_attr, '{}.input1Y'.format(multi))
            cmds.connectAttr(source_attr, '{}.input1Z'.format(multi))

        cmds.setAttr('{}.input2X'.format(multi), value)
        cmds.setAttr('{}.input2Y'.format(multi), value)
        cmds.setAttr('{}.input2Z'.format(multi), value)

        if input_attr and not skip_attach:
            cmds.connectAttr(input_attr, '{}.input2'.format(multi))
        if plus:
            connect_plus('{}.output'.format(multi), target_attr)
        else:
            if not cmds.isConnected('{}.output'.format(multi), target_attr):
                cmds.connectAttr('{}.output'.format(multi), target_attr, f=True)
    else:
        cmds.connectAttr(source_attr, '{}.input1X'.format(multi))
        cmds.setAttr('{}.input2X'.format(multi), value)
        if input_attr and not skip_attach:
            cmds.connectAttr(input_attr, '{}.input2X'.format(multi))
        if plus:
            connect_plus('{}.outputX'.format(multi), target_attr)
        else:
            if not cmds.isConnected('{}.outputX'.format(multi), target_attr):
                cmds.connectAttr('{}.outputX'.format(multi), target_attr, f=True)

    lock_state.restore_initial()

    return multi


def connect_equal_condition(source_attr, target_attr, equal_value):
    """
    Connects source_attr into target_attr with a condition node inbetween
    :param source_attr: str, node.attribute name of an attribute
    :param source_attr: str, node.attribute name of an attribute
    :param equal_value: float, value the condition should be qual to, in order to pass 1; 0 otherwise
    Useful when hooking up enums to visibility
    :return: str, new condition node name
    """

    source_attr_name = source_attr.replace('.', '_')
    condition = cmds.createNode('condition', n='{}_condition'.format(source_attr_name))
    cmds.connectAttr(source_attr, '{}.firstTerm'.format(condition))
    cmds.setAttr('{}.secondTerm'.format(condition), equal_value)
    cmds.setAttr('{}.colorIfTrueR'.format(condition), 1)
    cmds.setAttr('{}.colorIfFalseR'.format(condition), 0)
    connect_plus('{}.outColorR'.format(condition), target_attr)

    return condition


def get_locked_and_connected_attributes(node, attributes=None):
    """
    Returns all the lock or connected attributes from all keyable attributes of an object is not attributes is given
    or for the given attributes.
    :param node: str, Maya object name to check attributes of
    :param attributes: list(str) or None, list of attributes to check
    :return: list(str), list of locked or connected attributes
    """

    locked_connected_attributes = list()

    if attributes:
        for attr in attributes:
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue
            if not cmds.getAttr('.'.join([node, attr]), settable=True):
                locked_connected_attributes.append('.'.join([node, attr]))
    else:
        for attr in cmds.listAttr(node, keyable=True):
            if not cmds.getAttr('.'.join([node, attr]), settable=True):
                locked_connected_attributes.append('.'.join([node, attr]))

    return locked_connected_attributes


def reset_nodes_attributes(node_names, skip_visibility=True):
    """
    Resets all keyable unlocked attributes on given nodes to their default values by filtering to channel box selection
    if there is one.

    :param list(str) node_names:  list of Maya node names.
    :param bool skip_visibility: whether to skip resetting visibility attribute.
    """

    selected_attributes = cmds.channelBox(
        'mainChannelBox', query=True, sma=True) or cmds.channelBox('mainChannelBox', query=True, sha=True)
    for node_name in node_names:
        attrs = cmds.listAttr(node_name, keyable=True, shortNames=True, unlocked=True)
        if not attrs:
            continue
        for attr in attrs:
            if skip_visibility and attr == 'visibility':
                continue
            if selected_attributes is not None and attr not in selected_attributes:
                continue
            default = 0
            try:
                default = cmds.attributeQuery(attr, n=node_name, listDefault=True)[0]
            except RuntimeError:
                pass
            attr_path = '.'.join([node_name, attr])
            if not cmds.getAttr(attr_path, settable=True):
                continue
            try:
                cmds.setAttr(attr_path, default, clamp=True)
            except RuntimeError:
                pass


def reset_node_attributes(node_name, skip_visibility=True):
    """
    Resets all keyable unlocked attributes on given nodes to their default values by filtering to channel box selection
    if there is one.

    :param str node_name:  Maya node name.
    :param bool skip_visibility: whether to skip resetting visibility attribute.
    """

    return reset_nodes_attributes([node_name], skip_visibility=skip_visibility)


def reset_selected_nodes_attributes(skip_visibility=True):
    """
    Resets all keyable unlocked attributes on selected nodes to their default values by filtering to channel box
    selection if there is one.

    :param bool skip_visibility: whether to skip resetting visibility attribute.
    """

    selected_nodes = cmds.ls(sl=True, type='transform')
    if not selected_nodes:
        logger.warning('No nodes selected, please select the objects to reset')
        return

    return reset_nodes_attributes(selected_nodes, skip_visibility=skip_visibility)


class AttributeValidator(object):
    """
    Static class with functionality to validate different types of attributes
    """

    @staticmethod
    def is_float_equivalent(lhs, rhs):
        """
        Returns True if both floats are with E (epsilon) of one another, where
        epsilon is the built-in system float point tolerance
        :param lhs: float
        :param rhs: float
        :return: bool
        """

        if not isinstance(lhs, (int, float)) or not isinstance(rhs, (int, float)):
            raise TypeError('Arguments must be "int" or "float"')

        return abs(lhs - rhs) <= sys.float_info.epsilon

    @staticmethod
    def is_string_equivalent(str1, str2):
        """
        Returns True if two strings are the same word regardless of case
        :param str1:
        :param str2:
        :return: bool
        """

        if str(str1).lower() == str(str2).lower():
            return True

        return False

    @staticmethod
    def bool_arg(arg=None, called_from=None):
        """
        Returns arg if args is a bool else returns False
        :param arg: variant, value to valid as a bool
        :param called_from: str
        :return: variant, arg || None
        """

        logger.debug('Attribute Validator | bool | arg = {}'.format(arg))

        fn_name = 'bool_arg'

        if called_from:
            fn_name = '{}.{}({})'.format(called_from, fn_name, arg)
        else:
            fn_name = '{}({})'.format(fn_name, arg)

        result = arg
        if isinstance(arg, int) and arg in [0, 1]:
            result = bool(arg)
        elif not isinstance(arg, bool):
            format_args = [arg, fn_name, type(arg).__name__]
            error_msg = 'Arg {} from function "{}" is type "{}", not "bool" or 0/1'.format(*format_args)
            raise TypeError(error_msg)

        return result

    @staticmethod
    def string_arg(arg=None, none_valid=True, called_from=None):
        """
        Returns arg if arg is a string else returns False
        :param arg: variant, value to validate as a string
        :param none_valid: bool, If True and arg is not string 'None' is returned; otherwise raise TypeError
        :return: variant, arg || None
        """

        logger.debug('Attribute Validator | string | arg = {}'.format(arg))

        fn_name = 'string_arg'

        if called_from:
            fn_name = '{}.{}({})'.format(called_from, fn_name, arg)
        else:
            fn_name = '{}({})'.format(fn_name, arg)

        if not arg:
            if none_valid:
                return False
            raise ValueError('Arg is None and not none_valid')

        if issubclass(type(arg), list or tuple):
            arg = arg[0]
        result = arg
        if not helpers.is_string(arg):
            if none_valid:
                result = False
            else:
                format_args = (arg, fn_name, type(arg).__name__)
                error_msg = 'Arg {} from function "{}" is type "{}", not str'
                raise TypeError(error_msg.format(*format_args))

        return result

    @staticmethod
    def list_arg(arg=None, types=None):
        """
        Returns list if possible and all items in that list are instances of given types else returns False
        If types is None (default), the type of each item is not tested
        :param arg: variant, value to validate as a list
        :param types: class or list of types and/or classes
        :return: list
        """

        logger.debug('Attribute Validator | list | arg = {}'.format(arg))

        result = isinstance(arg, (tuple, list))
        if not result:
            try:
                if arg is not None:
                    arg = [arg]
                    result = isinstance(arg, (tuple, list))
            except Exception as e:
                raise Exception('Failed to convert to list | error: {}'.format(e))

        if result:
            if types is not None:
                for a in arg:
                    if not isinstance(a, types):
                        result = False
                        break
                result = arg
            else:
                result = arg

        return result

    @classmethod
    def string_list_arg(cls, arg=None, none_valid=False, called_from=None):
        """
        Returns each argument in given arg if it is a string
        :param arg: variant, value to be validated as a list of strings
        :return: list
        """

        logger.debug('Attribute Validator | string list | arg = {} none_valid={}'.format(arg, none_valid))

        fn_name = 'string_list_arg'
        if called_from:
            fn_name = '{}.{}({})'.format(called_from, fn_name, arg)
        else:
            fn_name = '{}({})'.format(fn_name, arg)

        result = list()
        if arg is None:
            if none_valid:
                return False
            else:
                raise ValueError('Arg is None and none_valid!')
        if not isinstance(arg, (tuple, list)):
            arg = [arg]

        for a in arg:
            tmp = cls.string_arg(a, none_valid=none_valid)
            if helpers.is_string(tmp):
                result.append(tmp)
            else:
                logger.warning(
                    'Attr {0} from function "{}" is type {1} not str'.format(a, fn_name, type(a).__name__))

        return result

    @staticmethod
    def is_list_arg(arg=None, types=None):
        """
        Returns True if the given arg is a list and all items in that list are instances of given
        types ele returns False. If types is None (default), the type of each item is not tested
        :param arg: variant, value to validate as a list
        :param types: class or list of types and/or classes
        :return: bool
        """

        result = isinstance(arg, (tuple, list))
        if result and types is not None:
            for a in arg:
                if not isinstance(a, types):
                    result = False
                    break

        return result

    @staticmethod
    def get_data_type(data=None):
        """
        Returns the type of the given data
        :param data: variant
        :return:  variant
        """

        def simple_return(t):
            if t is int:
                return 'int'
            elif t is float:
                return 'float'
            elif helpers.is_string(t):
                return 'string'
            else:
                return False

        type_return = type(data)

        if type_return is list:
            if not data:
                return 'string'
            # If there is a single string in the data set, the rest of the list will be treated as a string set
            for o in data:
                if helpers.is_string(o):
                    return 'string'
            # Check for floats
            for o in data:
                if type(o) is float:
                    return 'float'
            if helpers.is_string(data[0]):
                return 'string'
            else:
                return simple_return(type(data[0]))
        else:
            return simple_return(type_return)

    @staticmethod
    def get_maya_type(node=None):
        """
        Returns Maya node type
        :param node: str, object to check
        :return: str
        """

        def simple_transform_shape_check(node=None):
            if AttributeValidator.is_shape(node):
                return cmds.objectType(node)
            shapes_list = cmds.listRelatives(node, shapes=True, fullPath=True) or list()
            shapes_len = len(shapes_list)
            if shapes_len == 1:
                return cmds.objectType(shapes_list[0])
            elif shapes_len > 1:
                logger.debug(
                    '|{}| >> node: {} has multiple shapes. Returning type for {}. Remaining shapes: {}'.format(
                        fn_name, node, shapes_list[0], shapes_list[1:]))
                shape_type = False
                for s in shapes_list:
                    s_type = cmds.objectType(s)
                    if not shape_type:
                        shape_type = s_type
                    elif shape_type != s_type:
                        logger.warning(
                            '|{}| >> node: {} has multiple shapes and all do not match. {} != {}'.format(
                                fn_name, node, shape_type, s_type))
                        return 'transform'
                return cmds.objectType(shapes_list[0])
            else:
                if cmds.listRelatives(node, children=True):
                    return 'group'
                return 'transform'

        fn_name = 'get_maya_type'
        node = AttributeValidator.string_arg(node, False, fn_name)

        logger.debug('|{}| >> node: {}'.format(fn_name, node))
        try:
            initial_check = cmds.objectType(node)
        except Exception:
            initial_check = False
        if initial_check in ['objectSet']:
            return initial_check

        if initial_check == 'transform':
            return simple_transform_shape_check(node)
        elif AttributeValidator.is_component(node):
            logger.debug('|{}| >> component mode...'.format(fn_name))
            split = node.split('[')[0].split('.')
            root = split[0]
            comp_type = split[1]
            logger.debug('|{}| >> split: {} | root: {} | comp: {}'.format(fn_name, split, root, comp_type))
            if 'vtx' == comp_type:
                return 'polyVertex'
            if 'cv' == comp_type:
                root = simple_transform_shape_check(root)
                if root == 'nurbsCurve':
                    return 'curveCV'
                elif root == 'nurbsSurface':
                    return 'surfaceCV'
                else:
                    logger.debug('|{}| >> Unknown CV root: {}'.format(fn_name, root))
                    return root

            if 'e' == comp_type:
                return 'polyEdge'
            elif 'f' == comp_type:
                return 'polyFace'
            elif 'map' == comp_type:
                return 'polyUV'
            elif 'uv' == comp_type:
                return 'surfacePoint'
            elif 'sf' == comp_type:
                return 'surfacePath'
            elif 'u' == comp_type or 'v' == comp_type:
                root_type = simple_transform_shape_check(root)
                if root_type == 'nurbsCurve':
                    return 'curvePoint'
                elif root_type == 'nurbsSurface':
                    return 'isoparm'
                else:
                    raise ValueError('Unexpected root_type: {}'.format(root_type))
            elif 'ep' == comp_type:
                return 'editPoint'
            raise RuntimeError('Should not have gotten here. Need another check for component type: {}'.format(node))

        return initial_check

    @staticmethod
    def is_transform(node=None):
        """
        Check if the given node is a valid Maya transform node
        :param node: variant, value to valid as a Maya transform node
        :return: bool
        """

        from tp.maya.cmds import transform as transform_utils

        fn_name = 'is_transform'

        node = AttributeValidator.string_arg(arg=node)
        logger.debug('|{}| >> node: "{}"'.format(fn_name, node))

        result = transform_utils.is_transform(node)
        if not result:
            return False

        for attr in ['translate', 'rotate', 'scale']:
            if not cmds.objExists('{0}.{1}'.format(node, attr)):
                return False
            return True

        if not cmds.objExists(node):
            logger.error('|{}| >> node "{}" does not exists!'.format(fn_name, node))

    @staticmethod
    def is_shape(node=None):
        """
        Check if the given node is a valid Maya shape node
        :param node: variant, value to valid as a Maya shape node
        :return: bool
        """

        node = AttributeValidator.string_arg(arg=node)
        logger.debug('|is_shape| >> node: "{}"'.format(node))

        result = shape_utils.is_shape(obj=node)
        if not result:
            return False

        node_shapes = cmds.ls(node, type='shape', long=True)
        if node_shapes:
            if len(node_shapes) == 1:
                if node_shapes[0] == maya_name_utils.get_long_name(obj=node):
                    return True

        return False

    @staticmethod
    def is_component(arg=None):
        """
        Returns whether given arg is a component or not
        :param arg: str
        :return: bool
        """

        fn_name = 'is_component'
        arg = AttributeValidator.string_arg(arg, False, fn_name)
        logger.debug('|{}| >> arg: {}'.format(fn_name, arg))

        if cmds.objExists(arg):
            if '.' in arg and '[' in arg and ']' in arg:
                return True

        return False

    @staticmethod
    def get_component(arg=None):
        """
        Check to sett if an arg is a component or not
        :param arg: str
        :return: [component, transform, component_type]
        """

        fn_name = 'get_component'
        if AttributeValidator.is_component(arg):
            logger.debug('|{}| >> component mode ...'.format(fn_name))
            split = arg.split('[')
            split_join = '[' + '['.join(split[1:])
            root_split = split[0].split('.')
            root = root_split[0]
            comp_type = root_split[1]
            logger.debug('|{}| >> split: {} | root: {} | comp: {}'.format(fn_name, split, root, comp_type))
            return ['{}{}'.format(comp_type, split_join), root, comp_type, AttributeValidator.get_maya_type(arg)]

        return False

    @staticmethod
    def obj_string(arg=None, maya_type=None, is_transform=None, none_valid=False, called_from=None, **kwargs):
        """
        Returns arg if arg is an existing uniquely named Maya object, meeting the given arguments of maya_type and
        is_transforms. Otherwise, return False if none_valid or raise an exception
        :param arg: str, name of the Maya object to be validated
        :param maya_type: variant, str || list<str>, one or more Maya types (arg must be in this list for
            the test to pass)
        :param is_transform: bool, test whether arg is a transform or not
        :param none_valid: bool, Returns False if arg does not pass rather than raise an exception
        :param called_from:
        :param kwargs:
        :return: variant, arg or False
        :raises:
            TypeError | if 'arg' is not a string
            NameError | if more than one object name 'arg' exists in the Maya scene
            NameError | if 'arg' does not exist in the Maya scene
            TypeError | if the Maya type of 'arg' is in the list 'mayaType' and noneValid is False
            TypeError | if isTransform is True, 'arg' is not a transform, and noneValid is False
        """

        logger.debug('MetaAttributeValidator.obj_string arg={}'.format(arg))
        fn_name = 'obj_string_list'
        if called_from:
            fn_name = '{}.{}({})'.format(called_from, fn_name, arg)
        else:
            fn_name = '{}({})'.format(fn_name, arg)

        result = None

        if issubclass(type(arg), list or tuple):
            arg = arg[0]

        if not helpers.is_string(arg):
            if none_valid:
                return False
            raise TypeError('{}: arg must be string'.format(fn_name))

        if len(cmds.ls(arg)) > 1:
            if none_valid:
                return False
            raise NameError('{}: More than object is named "{}"'.format(arg, fn_name))

        if result is None and not cmds.objExists(arg):
            if none_valid:
                result = False
            else:
                raise NameError('{}: "{}" does not exists!0'.format(arg, fn_name))

        if not result and maya_type is not None:
            maya_types_list = maya_type
            if helpers.is_string(maya_type):
                maya_types_list = [maya_type]
            arg_maya_type_str = AttributeValidator.get_maya_type(arg)
            if arg_maya_type_str not in maya_types_list:
                if none_valid:
                    result = False
                else:
                    maya_types_str_format = ', '.join(maya_types_list)
                    format_args = [arg, arg_maya_type_str, maya_types_str_format, fn_name]
                    raise TypeError("{3}: Arg {0} is type '{1}', expected '{2}'".format(*format_args))

        if result is None and is_transform:
            if not AttributeValidator.is_transform(arg):
                if none_valid:
                    result = False
                else:
                    arg_maya_type_str = AttributeValidator.get_maya_type(arg)
                    format_args = [arg, arg_maya_type_str, fn_name]
                    raise TypeError("{2}: 'Arg {0}' is type {1}, expected 'transform'".format(*format_args))

        if result is None:
            result = arg

        return result

    @staticmethod
    def obj_string_list(args_list=None, maya_type=None, none_valid=False, is_transform=False, called_from=None,
                        **kwargs):
        """
        Returns each item in args_list if that item exists as a Maya object with the given type and optional
        argumentes or None if does not exists. If nonve_valid and the object does not exists a exception is raised
        :param args_list:
        :param maya_type:
        :param none_valid:
        :param is_transform:
        :param called_from:
        :param kwargs:
        :return: list
        """

        logger.debug('MetaAttributeValidator.obj_string_list arg={}'.format(args_list))
        fn_name = 'obj_string_list'
        if called_from:
            fn_name = '{}.{}({})'.format(called_from, fn_name, args_list)
        else:
            fn_name = '{}({})'.format(fn_name, args_list)

        result = list()
        if args_list is None:
            if none_valid:
                return False
            else:
                raise ValueError('Arg is None and not none_valid!')

        if not isinstance(args_list, (list, tuple)):
            args_list = [args_list]

        for arg in args_list:
            try:
                arg = arg.meta_node
            except Exception:
                pass

            tmp = AttributeValidator.obj_string(
                arg=arg, maya_type=maya_type, is_transform=is_transform, none_valid=none_valid)
            if tmp:
                result.append(tmp)
            else:
                arg_maya_type_str = AttributeValidator.get_maya_type(arg)
                logger.warning(
                    'Arg {} from func {} is Maya type "{}", nos str'.format(arg, fn_name, arg_maya_type_str))

        return result

    @staticmethod
    def shape_arg(node=None, types=None, single_return=False):
        """
        Returns arg if args is a Maya shape node else returns shapes of given node
        :param node: variant, value to valid as a Maya shape node
        :param types: valid types if you want validation
        :param single_return: True if you only want to return first
        :return: bool
        """

        try:
            node = node.meta_node
        except Exception:
            pass

        node = AttributeValidator.string_arg(arg=node)

        if AttributeValidator.is_shape(node=node):
            result = [node]
        else:
            result = cmds.listRelatives(node, shapes=True, fullPath=True)

        if types:
            types = AttributeValidator.list_arg(arg=types)
            copy_result = copy.copy(result)
            result = list()
            for s in copy_result:
                maya_type = AttributeValidator.get_maya_type(node=s)
                if maya_type in types:
                    result.append(s)
                else:
                    logger.warning(
                        'Attribute Validator | Maya Shape | invalid type: {0} | {1} | shape: {2}'.format(
                            maya_type, types, s))

        if not result:
            return False

        if single_return:
            if len(result) > 1:
                logger.warning(
                    'Attribute Validator | Maya Shape | >> Too many shapes ({0}). Using first: {1}'.format(
                        len(result), result))
            return result[0]

        return result

    @staticmethod
    def kwargs_from_dict(arg=None, dic=None, none_valid=False, called_from=None):
        """
        Returns valid argument contained in given
        :param arg:
        :param dic: dictionary to get keywords from. Example: {'test':['TEST', 'test']...}
        :param none_valid: bool, Whether if False is returned an error should be raised or not
        :param called_from: str, calling function for error reporting
        :return:
        """

        fn_name = 'kwargs_from_dict'

        if called_from:
            fn_name = '{}calling {}'.format(called_from, fn_name)

        if arg is None or dic is None:
            if none_valid:
                return False
            raise ValueError('{}: Must have arg and cit arguments | arg: {} | dic: {}'.format(fn_name, arg, dic))
        if not isinstance(dic, dict):
            if none_valid:
                return False
            raise ValueError('{}: dic arg must be a dict | dic: {}'.format(fn_name, dic))

        for k in dic.keys():
            if AttributeValidator.is_string_equivalent(k, arg):
                return k
            list_arg = dic[k]
            if not AttributeValidator.is_list_arg(list_arg):
                raise ValueError('{}: Invalid list on dict key | k: {} | Not a list: {}'.format(fn_name, k, list_arg))
            for a in list_arg:
                if AttributeValidator.is_string_equivalent(a, arg):
                    return k

        if not none_valid:
            raise ValueError('{}: Invalid arg | arg: {} | options: {}'.format(fn_name, arg, dic))

        return arg

    @staticmethod
    def kwargs_from_list(arg=None, lst=None, index_callable=False, return_index=False, none_valid=False,
                         called_from=None):
        """
        Returns valid kwargs if it matches a list of possible options provided
        :param arg: str
        :param lst: list
        :param index_callable:, bool, Whether an index is an acceptable calling method
        :param return_index: bool, Whether you want index returned or the list value
        :param none_valid: bool, Whether if False is returned an error should be raised or not
        :param called_from: str, calling function for error reporting
        """

        fn_name = 'kwargs_from_list'

        if called_from:
            fn_name = '{} calling {}'.format(called_from, fn_name)

        if arg is None or lst is None:
            if none_valid:
                return False
            raise ValueError('{}: Mush ave arg and lst arguments | arg: {} | lst: {}'.format(fn_name, arg, lst))

        if not AttributeValidator.is_list_arg(lst):
            if none_valid:
                return False
            raise ValueError('{}: lst arg must be a list | lst: {} | type: {}'.format(fn_name, lst, type(lst)))

        if return_index:
            if type(arg) is int:
                if arg < len(lst):
                    return arg

        result = None
        for i, a in enumerate(lst):
            if a == arg:
                result = a
            if i == arg and index_callable:
                if return_index:
                    result = i
                else:
                    result = a
            if AttributeValidator.is_string_equivalent(a, arg):
                result = a

        if result is None and not none_valid:
            raise ValueError('{}: Invalid arg | arg: {} | options: {}'.format(fn_name, arg, lst))

        return result

    def file_path(self, file_path=None, file_mode=0, file_filter='Text files (*.txt)', start_dir=None):
        """
        Validates a given file path or generates one with dialog if necessary
        :param file_path: str
        :param file_mode: int (0: open, 1: save)
        :param file_filter: str, descriptor and starred prefix (Example: Text files (*.txt)
        :param start_dir: str, start diretory of the dialog
        """

        open_modes = {0: 'save', 1: 'open'}

        if file_path is None:
            if start_dir is None:
                start_dir = cmds.workspace(query=True, rootDirectory=True)
            file_path = cmds.fileDialog2(
                dialogStyle=2, fileMode=file_mode, startingDirectory=start_dir, fileFilter=file_filter)
            if file_path:
                file_path = file_path[0]

        result = False
        if file_path:
            if file_mode == 1:
                if os.path.exists(file_path):
                    logger.debug(
                        '{} mode | file path validated ... {}'.format(open_modes.get(file_mode), file_path))
                    result = file_path
                else:
                    logger.debug('Invalid file path ... {}'.format(file_path))
            elif file_mode == 0:
                logger.debug(
                    '{} mode | file path invalidated ... {}'.format(open_modes.get(file_mode), file_path))
                result = file_path

        return result


class Connection(object):
    """
    Class that wraps a native Maya Object and allows to work with connections easily
    """

    def __init__(self, node):
        """
        Constructor
        :param node: str, name of the Maya node
        """

        if type(node) != maya.api.OpenMaya.MObject:
            self._node = node_utils.get_mobject(node_name=node)
        else:
            self._node = node

        self.inputs = list()
        self.outputs = list()
        self.connections = list()

        self._store_connections()

    def get_node(self):
        return node_utils.get_name(self._node)

    node = property(get_node)

    def get(self):
        """
        Returns the stored connections (inputs + outputs)
        List is ordered as [[output, intput], ...]
        :return: list
        """

        return self.connections

    def get_inputs(self):
        """
        Returns all the inputs connections of the wrapped Maya object
        :return: list, [[external_output, node_input], ... ]
        """

        return node_utils.get_input_attributes(node=self.node)

    def get_outputs(self):
        """
        Returns all output connections of the wrapped Maya object
        :return: list, [[node_output, external_input], ... ]
        """

        return node_utils.get_output_attributes(node=self.node)

    def get_input_at(self, index):
        """
        Get connection that inputs into the node at given index
        :param index: int
        :return: list, [external_output, node_input]
        """

        return self.inputs[index]

    def get_output_at(self, index):
        """
        Get connection that the node outputs into at given index
        :param index: int
        :return: list, [node_output, external_input]
        """

        return self.outputs[index]

    def get_inputs_count(self):
        """
        Returns the number of input connections
        :return: int
        """

        return len(self.inputs)

    def get_outputs_count(self):
        """
        Returns the number of output connections
        :return: int
        """

        return len(self.outputs)

    def get_input_source(self, index):
        """
        Returns input source stored at the given index
        :param index: int
        :return: str
        """

        return '{}.{}'.format(self.node, self.inputs[index][0])

    def get_input_target(self, index):
        """
        Returns input target stored at the given index
        :param index: int
        :return: str
        """

        return '{}.{}'.format(self.inputs[index][1], self.inputs[index][2])

    def get_output_source(self, index):
        """
        Returns output source stored at the given index
        :param index: int
        :return: str
        """

        return '{}.{}'.format(self.outputs[index][1], self.outputs[index][2])

    def get_output_target(self, index):
        """
        Returns output target stored at the given index
        :param index: int
        :return: str
        """

        return '{}.{}'.format(self.node, self.outputs[index][0])

    def get_connections_input(self, connected_node):
        """
        Returns connections that input into the given node. Only inputs to the node will be returned
        :param connected_node: str, name of a connected node to filter with.
        :return: list, [[external_output, node_input], ...]
        """

        found = list()
        for i in range(len(self.inputs)):
            input = self.inputs[i]
            node = input[1]
            if node == connected_node:
                input_value = '{}.{}'.format(self.node, input[0])
                output_value = '{}.{}'.format(node, input[2])
                found.append([output_value, input_value])

        return found

    def get_connections_output(self, connected_node):
        """
        Returns connections that input into the given node. Only inputs to the node will be returned
        :param connected_node: str, name of a connected node to filter with.
        :return: list, [[external_output, node_input], ...]
        """

        found = list()
        for i in range(len(self.outputs)):
            output = self.outputs[i]
            node = output[1]
            if node == connected_node:
                output_value = '{}.{}'.format(self.node, output[0])
                input_value = '{}.{}'.format(node, output[2])
                found.append([output_value, input_value])

        return found

    def get_inputs_of_type(self, node_type):
        """
        Returns nodes of given type that connects into the wrapped node
        :param node_type: str, Maya node type
        :return: list<str>, list with the names of connected nodes matching given node type
        """

        found = list()
        for i in range(0, len(self.inputs)):
            node = self.inputs[i][1]
            if cmds.nodeType(node).startswith(node_type):
                found.append(node)

        return found

    def get_outputs_of_type(self, node_type):
        """
        Returns nodes of given type that output into the wrapped node
        :param node_type: str, Maya node type
        :return: list<str>, list with the names of connected nodes matching given node type
        """

        found = list()
        for i in range(0, len(self.outputs)):
            node = self.outputs[i][1]
            if cmds.nodeType(node).startswith(node_type):
                found.append(node)

        return found

    def disconnect(self):
        """
        Disconnect all connections of the current wrapped node
        """

        for i in range(0, len(self.connections), 2):
            if cmds.isConnected(self.connections[i], self.connections[i + 1], ignoreUnitConversion=True):
                lock_state = cmds.getAttr(self.connections[i + 1], lock=True)
                if lock_state:
                    cmds.setAttr(self.connections[i + 1], lock=False)
                    cmds.disconnectAttr(self.connections[i], self.connections[i + 1])
                if lock_state:
                    cmds.setAttr(self.connections[i + 1], lock=True)

    def connect(self):
        """
        Reconnects all the stored connections
        """

        for i in range(0, len(self.connections), 2):
            if not cmds.objExists(self.connections[i]) or not cmds.objExists(self.connections[i + 1]):
                continue

            if not cmds.isConnected(self.connections[i], self.connections[i + 1], ignoreUnitConversion=True):
                lock_state = cmds.getAttr(self.connections[i + 1], lock=True)
                if lock_state:
                    cmds.setAttr(self.connections[i + 1], lock=False)
                cmds.connectAttr(self.connections[i], self.connections[i + 1])
                if lock_state:
                    cmds.setAttr(self.connections[i + 1], lock=True)

    def refresh(self):
        """
        Refresh the stored connections
        """

        self._store_connections()

    def _store_output_connections(self, outputs):
        """
        Stores all node outputs into the list of outputs of the object
        :param outputs: list<str>, list with attribute tuples output values
        :return: list<list<str, str, str>>
        """

        output_values = list()
        for i in range(0, len(outputs), 2):
            split = outputs[i].split('.')
            output_attr = string.join(split[1:], '.')
            split_output = outputs[i + 1].split('.')
            node = split_output[0]
            node_attr = string.join(split_output[1:], '.')
            output_values.append([output_attr, node, node_attr])

        self.outputs = output_values

    def _store_input_connections(self, inputs):
        """
        Stores all node inputs into the list of outputs of the object
        :param inputs: list<str>, list with attribute tuples output values
        :return: list<list<str, str, str>>
        """

        input_values = list()
        for i in range(len(inputs, 2)):
            split = inputs[i].split('.')
            input_attr = string.join(split[1:], '.')
            split_input = inputs[i + 1].split('.')
            node = split_input[0]
            node_attr = string.join(split_input[1:], '.')
            input_values.append([input_attr, node, node_attr])

        self.inputs = input_values

    def _store_connections(self):
        """
        Reads node connections and store them for later use
        """

        self.inputs = list()
        self.outputs = list()

        inputs = self.get_inputs()
        outputs = self.get_outputs()

        if inputs:
            self._store_input_connections(inputs)
        if outputs:
            self._store_output_connections(outputs)

        self.connections = inputs + outputs


class Attribute(object):
    """
    Class that encapsulates the creation of attributes
    """

    def __init__(self, attribute_name, node=None, **kwargs):
        self.name = attribute_name
        self.node = node
        self.value = kwargs.pop('value', None)
        self.attribute_type = kwargs.pop('attribute_type', AttributeTypes.Short)
        self.nice_name = kwargs.pop('nice_name', None)
        self.short_name = kwargs.pop('short_name', None)
        self.minimum = kwargs.pop('minimum', None)
        self.maximum = kwargs.pop('maximum', None)
        self.keyable = kwargs.pop('keyable', True)
        self.readable = kwargs.pop('readable', True)
        self.storable = kwargs.pop('storable', True)
        self.writable = kwargs.pop('writable', True)
        self.hidden = kwargs.pop('hidden', False)
        self.locked = False

        self.default_value = self.value

        self._update_states()

    def __repr__(self):
        return self.get_full_name()

    def get_full_name(self):
        """
        Returns complete attribute name (node.attribute)
        :return: str
        """

        return '{}.{}'.format(self.node, self.name)

    def get_name(self):
        """
        Returns the attribute name
        :return: str
        """

        return self.name

    def get_value(self):
        """
        Returns the value of the attribute
        :return: variant
        """

        if not self.exists():
            return

        return attribute(self.node, self.name)

    def get_dict(self):
        """
        Returns a dictionary that stores the current state of the variable
        :return: dict
        """

        var_dict = {
            'value': self.get_value(),
            'type': self._get_data_type(),
            'key': self.is_keyable(),
            'lock': self.is_locked()
        }

        return var_dict

    def exists(self):
        """
        Returns whether the attribute exists or not
        :return: bool
        """

        return is_attribute(self.get_full_name())

    def is_locked(self):
        """
        Returns whether the attribute is locked or not
        :return: bool
        """

        if not self.exists():
            return self.locked

        return is_locked(self.get_full_name())

    def is_keyable(self):
        """
        Returns whether the attribute is keyable or not
        :return: bool
        """

        if not self.exists():
            return self.keyable

        return is_keyable(self.get_full_name())

    def is_hidden(self):
        """
        Returns whether the attribute is hidden or not
        :return: bool
        """

        if not self.exists():
            return self.hidden

        return is_hidden(self.get_full_name())

    def is_numeric(self):
        """
        Returns whether the attribute value is numeric or not
        :return: bool
        """

        if not self.exists():
            return False

        return is_numeric(self.get_full_name())

    def set_name(self, name):
        """
        Set the name of the variable
        :param name: str, name to give to the variable
        """

        var_name = self.get_full_name()

        try:
            if cmds.objExists(var_name):
                cmds.renameAttr(var_name, name)
        except Exception as e:
            logger.error('Error while renaming attribute "{}" to "{}" - {}'.format(var_name, name, str(e)))
            return

        self.name = name

    def set_node(self, name):
        """
        Set the node where the variable should live
        :param name: str, name of node
        """

        self.node = name

    def set_value(self, value):
        """
        Set the value of the variable
        :param value: variant
        """

        self.value = value
        self._set_value()

    def set_default_value(self):
        """
        Restores the attribute to its default value
        """

        if self.default_value is None:
            return

        self.set_value(self.default_value)

    def set_locked(self, lock):
        """
        Set the lock state of the variable
        :param lock: bool
        """

        self.locked = lock
        self._set_lock()

    def set_keyable(self, keyable):
        """
        Set the keyable state of the variable
        :param keyable: bool
        """

        self.keyable = keyable
        self._set_keyable()

    def set_hidden(self, hidden):
        """
        Set the hidden state of the variable
        :param hidden: bool
        """

        self.hidden = hidden
        self._set_hidden()

    def set_variable_type(self, attribute_type):
        """
        Set the variable type
        :param attribute_type: str, type of attribute
        """

        self.attribute_type = attribute_type

    def set_dict(self, var_dict):
        """
        Set variable values from a a dictionary that describes the variable
        :param var_dict: dict, a dictionary created from get_dict()
        """

        value = var_dict['value']
        type_value = var_dict['type']
        keyable = var_dict['key']
        lock = var_dict['lock']
        self.set_value(value)
        self.set_variable_type(type_value)
        self.set_keyable(keyable)
        self.set_locked(lock)

    def create(self, node=None):
        """
        Adds attribute in the given Maya node
        :param node: str, the node to add attribute into
        """

        if node and cmds.objExists(node):
            self.node = node

        value = self.value
        exists = self.exists()
        if exists:
            if value is not None:
                value = self.get_value()

        self._create_attribute()
        self._update_states()

        if exists:
            self.set_value(value)

    def delete(self, node=None):
        """
        Removes attribute from the given Maya node
        :param node: str, the node to remove attribute from
        """

        if node and cmds.objExists(node):
            self.node = node

        self.locked = False
        self._set_lock()

        safe_delete_attribute(node_name=self.node, attr_name=self.name)

    def connect_in(self, attr):
        """
        Connect the given attribute into this attribute
        :param attr: str, node.attribute
        """

        connect_attribute(attr, self.get_full_name())

    def connect_out(self, attr):
        """
        Connect the given attribute into the attribute
        :param attr: str, node.attribute
        """

        connect_attribute(self.get_full_name(), attr)

    def refresh(self):
        """
        Refresh the internal values
        """

        self.value = self.get_value()
        self.locked = self.is_locked()
        self.keyable = self.is_keyable()
        self.attribute_type = self._get_data_type()

    def _get_data_type(self):
        """
        Returns the data type of the attribute
        :return: str
        """

        return attr_mapping[self.attribute_type]

    def _set_value(self):
        """
        Internal function that set the value the attribute stores
        """

        if not self.exists():
            return

        locked_state = self.is_locked()
        hidden_state = self.is_hidden()

        add_attribute(node=self.node, attr=self.name, value=self.value)

        self.set_locked(locked_state)
        self.set_hidden(locked_state)

    def _set_data_type(self):
        """
        Internal function that set the data type stored by the attribute
        """

        if not self.exists():
            return

        self.attribute_type = data_type(self.get_full_name())

    def _set_lock(self):
        """
        Internal function to set the lock state depending the locked stored variable
        """
        if not self.exists():
            return

        cmds.setAttr(self.get_full_name(), lock=self.locked)

    def _set_keyable(self):
        """
        Internal function to set the keyable state depending the keyable stored variable
        """

        if not self.exists():
            return

        cmds.setAttr(self.get_full_name(), k=self.keyable)

    def _set_hidden(self):
        """
        Internal function to set the hidden state depending the hidden stored variable
        """

        if not self.exists():
            return

        cmds.setAttr(self.get_full_name(), cb=not self.hidden)

    def _create_attribute(self):
        """
        Internal function that is used to create attributes with the stored variables
        """

        logger.debug('creating with value: {}'.format(self.value))

        add_attribute(
            node=self.node,
            attr=self.name,
            dv=self.value,
            attr_type=self.attribute_type,
            hidden=self.hidden,
            keyable=self.keyable,
            locked=self.locked
        )

    def _update_states(self):
        """
        Internal function that updates all the stored info of the attribute
        """

        self._set_keyable()
        self._set_lock()
        self._set_value()
        self._set_data_type()


class NumericAttribute(Attribute, object):
    """
    Class to work with numeric attributes
    """

    def __init__(self, attribute_name, node=None, **kwargs):
        if kwargs.get('value') is None:
            kwargs['value'] = 0
        super(NumericAttribute, self).__init__(
            attribute_name, node=node, attribute_type=AttributeTypes.Double, **kwargs)

        self.min_value = None
        self.max_value = None

    def get_min_value(self):
        """
        Function that returns the minimum value of the integer attribute
        :return: int
        """

        if not self.exists():
            return

        # We need to use tyr/except because of scale attr
        # TODO: Check how to query if a double has ability for min and max
        try:
            return cmds.attributeQuery(self.name, node=self.node, minimum=True)[0]
        except Exception:
            return

    def get_max_value(self):
        """
        Function that returns the maximum value of the integer attribute
        :return: int
        """

        if not self.exists():
            return

        # We need to use tyr/except because of scale attr
        # TODO: Check how to query if a double has ability for min and max
        try:
            return cmds.attributeQuery(self.name, node=self.node, maximum=True)[0]
        except Exception:
            return

    def set_min_value(self, value):
        """
        Set the minimum value for the integer attribute
        :param value: int
        """

        self.min_value = value
        self._set_min_value()

    def set_max_value(self, value):
        """
        Set the maximum value for the integer attribute
        :param value: int
        """

        self.max_value = value
        self._set_max_value()

    def refresh(self):
        """
        Refresh the internal values
        """

        super(NumericAttribute, self).refresh()
        self.min_value = self.get_min_value()
        self.max_value = self.get_max_value()

    def _set_min_value(self):
        """
        Internal function that set the minimum value for the integer attribute
        """

        if not self.exists():
            return

        if not self.min_value:
            if cmds.attributeQuery(self.name, node=self.node, minExists=True):
                cmds.addAttr(self.get_full_name(), edit=True, hasMinValue=False)

        if self.min_value is not None:
            cmds.addAttr(self.get_full_name(), edit=True, hasMinValue=True)
            cmds.addAttr(self.get_full_name(), edit=True, minValue=self.min_value)

    def _set_max_value(self):
        """
        Internal function that set the maximum value for the integer attribute
        """

        if not self.exists():
            return

        if not self.max_value:
            if cmds.attributeQuery(self.name, node=self.node, maxExists=True):
                cmds.addAttr(self.get_full_name(), edit=True, hasMaxValue=False)

        if self.max_value is not None:
            cmds.addAttr(self.get_full_name(), edit=True, hasMaxValue=True)
            cmds.addAttr(self.get_full_name(), edit=True, maxValue=self.max_value)

    def _update_states(self):
        """
        Internal function that updates all the stored info of the attribute
        """

        self._set_min_value()
        self._set_max_value()
        super(NumericAttribute, self)._update_states()


class EnumAttribute(Attribute, object):
    """
    Class to work with enum attributes
    """

    def __init__(self, attribute_name, node=None, **kwargs):

        self.enum_names = ['----------']
        super(EnumAttribute, self).__init__(attribute_name, node, attribute_type=AttributeTypes.Enum, **kwargs)

    def set_enum_names(self, name_list):
        """
        Function that set the enun names used in the enum attribute
        :param name_list: list<str>, list of strings to define the enum names
        """

        self.enum_names = name_list

        self._set_enum_value()

    def _set_value(self):
        """
        Internal function that set the value the attribute stores
        """

        if not self.enum_names:
            return

        self._set_enum_value(set_value=False)
        super(EnumAttribute, self)._set_value()

    def _set_enum_value(self, set_value=True):
        """
        Internal function used to set the value of the enum
        :param set_value: bool, set the enum, optionally with the stored enum value
        """

        if not self.exists():
            return

        enum_name = string.join(self.enum_names, ':')
        if not enum_name:
            return

        value = self.get_value()
        cmds.addAttr(self.get_full_name(), edit=True, enumName=enum_name)

        if set_value:
            self.set_value(value)

    def _create_attribute(self):
        """
        Internal function that is used to create attributes with the stored variables
        """

        add_attribute(
            node=self.node,
            attr=self.name,
            value=self.value,
            attr_type=self.attribute_type,
            hidden=self.hidden,
            keyable=self.keyable,
            locked=self.locked,
            enumName=string.join(self.enum_names, '|')
        )

    def _update_states(self):
        """
        Internal function that updates all the stored info of the attribute
        """

        super(EnumAttribute, self)._update_states()

        self._set_enum_value()


class StringAttribute(Attribute, object):
    """
    Class to work with string attributes
    """

    def __init__(self, attribute_name, node=None, **kwargs):
        if kwargs.get('value') is None:
            kwargs['value'] = ''
        super(StringAttribute, self).__init__(attribute_name, node, attribute_type=AttributeTypes.String, **kwargs)


class LockState(object):
    """
    Class that saves the lock state of an attribute so it can be reset after editing
    """

    def __init__(self, attr):
        self.lock_state = cmds.getAttr(attr, lock=True)
        self.attribute = attr

    def unlock(self):
        """
        Unlock the attribute
        """

        try:
            cmds.setAttr(self.attribute, lock=False)
        except Exception as exc:
            logger.debug('Impossible to unlock: {} | {}'.format(self.attribute, exc))

    def lock(self):
        """
        Lock the attribute
        """

        try:
            cmds.setAttr(self.attribute, lock=True)
        except Exception as exc:
            logger.debug('Impossible to lock: {} | {}'.format(self.attribute, exc))

    def restore_initial(self):
        """
        Restore the initial lock state
        """

        try:
            cmds.setAttr(self.attribute, lock=self.lock_state)
        except Exception as exc:
            logger.debug('Impossible to restore initial lock status for {} | {}'.format(self.attribute, exc))


class LockAttributesState(LockState, object):
    """
    Class that stores the lock state of all attributes of a node so they can be reset after editing
    """

    def __init__(self, node):
        self.node = node
        self.attributes = cmds.listAttr(node)

        self.lock_state = dict()

        for attr in self.attributes:
            try:
                self.lock_state[attr] = cmds.getAttr('{}.{}'.format(node, attr), lock=True)
            except Exception:
                pass

    def unlock(self):
        """
        Unlock all the attributes
        """

        for attr in self.attributes:
            try:
                attr_name = '{}.{}'.format(self.node, attr)
                cmds.setAttr(attr_name, lock=False)
            except Exception:
                pass

    def lock(self):
        """
        Lock all the attributes
        """

        for attr in self.attributes:
            try:
                attr_name = '{}.{}'.format(self.node, attr)
                cmds.setAttr(attr_name, lock=True)
            except Exception:
                pass

    def restore_initial(self):
        """
        Restore the initial lock state
        """

        for attr in self.attributes:
            try:
                attr_name = '{}.{}'.format(self.node, attr)
                cmds.setAttr(attr_name, lock=self.lock_state[attr])
            except Exception:
                pass


class LockTransformState(LockAttributesState, object):
    def __init__(self, node):
        self.lock_state = dict()
        self.attributes = list()
        self.node = node

        for attr in ['translate', 'rotate', 'scale']:
            for axis in 'XYZ':
                attr_name = '{}{}'.format(attr, axis)
                self.attributes.append(attr_name)
                self.lock_state[attr_name] = cmds.getAttr('{}.{}'.format(node, attr_name), l=True)


class RemapAttributesToAttribute(object):
    """
    Class that creates a slider between multiple attributes
    Useful for setup up swithces attributes such as IK/FK or FK/IK attributes
    This will create the switch attribute if it does not already exists
    """

    def __init__(self, node, attr):
        """
        Constructor
        :param node: str, name of a node
        :param attr: str, attribute which should do the switching
        """

        self.node_attr = '{}.{}'.format(node, attr)
        self.node = node
        self.attr = attr
        self.attrs = list()
        self.keyable = True
        self._remaps = list()

    @property
    def remaps(self):
        return self._remaps

    def set_keyable(self, bool_value):
        """
        Whether the switch attribute should be keyable or not
        NOTE: Only works if the attribute does not exist prior to create()
        :param bool_value: bool
        """

        self.keyable = bool_value

    def create_attribute(self, node, attr):
        """
        Adds an attribute to be mapped. Save in a list for create()
        :param node: str, name of the node where the attributes live
        :param attr: str, the name of an attribute on the node to map to the switch
        """

        self.attrs.append([node, attr])

    def create_attributes(self, node, attrs):
        """
        Adds an attribute to be mapped. Save in a list for create()
        :param node: str, name of the node where the attributes live
        :param attrs: list<str>, list with names of an attributes on the node to map to the switch
        """

        for attr in attrs:
            self.create_attribute(node, attr)

    def create(self):
        """
        Creates switch attribute
        """

        self._create_attribute()
        length = len(self.attrs)
        if length <= 1:
            return

        for i in range(length):
            node = self.attrs[i][0]
            attr = self.attrs[i][1]

            input_min = i - 1
            input_max = i + 1
            if input_min < 0:
                input_min = 0
            if input_max > (length - 1):
                input_max = length - 1

            input_node = attribute_input(attr)
            if input_node:
                if cmds.nodeType(input_node) == 'remapValue':
                    split_name = input_node.split('.')
                    remap = split_name[0]
                if cmds.nodeType(input_node) != 'remapValue':
                    input_node = None

            if not input_node:
                remap_name = '{}_remapValue'.format(attr)
                if node and 'constraint' in dcc.node_type(node).lower():
                    # remap_name = '{}_{}_remapValue'.format(attr, dcc.node_type(node))
                    remap_name = '{}_{}_remapValue'.format(attr, node)
                remap = cmds.createNode('remapValue', n=remap_name)
                self._remaps.append(remap)

            cmds.setAttr('{}.inputMin'.format(remap), input_min)
            cmds.setAttr('{}.inputMax'.format(remap), input_max)

            if i == 0:
                cmds.setAttr('{}.value[0].value_FloatValue'.format(remap), 1)
                cmds.setAttr('{}.value[0].value_Position'.format(remap), 0)
                cmds.setAttr('{}.value[0].value_Interp'.format(remap), 1)
                cmds.setAttr('{}.value[1].value_FloatValue'.format(remap), 0)
                cmds.setAttr('{}.value[1].value_Position'.format(remap), 1)
                cmds.setAttr('{}.value[1].value_Interp'.format(remap), 1)

            if i == (length - 1):
                cmds.setAttr('{}.value[0].value_FloatValue'.format(remap), 0)
                cmds.setAttr('{}.value[0].value_Position'.format(remap), 0)
                cmds.setAttr('{}.value[0].value_Interp'.format(remap), 1)
                cmds.setAttr('{}.value[1].value_FloatValue'.format(remap), 1)
                cmds.setAttr('{}.value[1].value_Position'.format(remap), 1)
                cmds.setAttr('{}.value[1].value_Interp'.format(remap), 1)

            if i == 0 and i != (length - 1):
                for j in range(0, 3):
                    if j == 0:
                        position = 0
                        value = 0
                    if j == 1:
                        position = 0.5
                        value = 1
                    else:
                        position = 1
                        value = 0

                    cmds.setAttr('{}.value[{}].value_FloatValue'.format(remap, j), value)
                    cmds.setAttr('{}.value[{}].value_Position'.format(remap, j), position)
                    cmds.setAttr('{}.value[{}].value_Interp'.format(remap, j), 1)

            disconnect_attribute('{}.{}'.format(node, attr))
            cmds.connectAttr('{}.outValue'.format(remap), '{}.{}'.format(node, attr))

            disconnect_attribute('{}.inputValue'.format(remap))
            cmds.connectAttr(self.node_attr, '{}.inputValue'.format(remap))

    def _create_attribute(self):
        """
        Internal function sued to create proper variable
        """

        attr_count = len(self.attrs)
        if attr_count is None:
            attr_count = 1
        if attr_count == 1:
            attr_count += 1

        if cmds.objExists(self.node_attr):
            var = NumericAttribute(self.attr)
            var.set_node(self.node)
            var.set_min_value(0)
            var.set_max_value(attr_count - 1)
            var.create()
            return

        var = NumericAttribute(self.attr)
        var.set_variable_type(AttributeTypes.Double)
        var.set_node(self.node)
        var.set_min_value(0)
        var.set_max_value(attr_count - 1)
        var.set_keyable(self.keyable)
        var.create()


class TransferAttributes(object):
    def __init__(self):
        super(TransferAttributes, self).__init__()

    @staticmethod
    def transfer_control(source, target):
        """
        Transfers control attributes from one to another
        :param source: str, name of the control we want to transfer attributes from
        :param target: str, name of the control we want to transfer attributes to
        """

        attrs = list()
        xform_names = ['translate', 'rotate', 'scale']
        for xform_name in xform_names:
            for axis in 'XYZ':
                attr_name = '{}{}'.format(xform_name, axis)
                attrs.append(attr_name)
        attrs.append('visibility')

        user_attrs = cmds.listAttr(source, ud=True)
        if user_attrs:
            attrs.extend(user_attrs)

        for attr in attrs:
            attr_name = '{}.{}'.format(attr_name, attr)
            new_attr = attribute_instance(attribute_name=attr_name)
            if not new_attr:
                continue
            new_attr.create(node=target)


class TransferConnections(object):
    def __init__(self):
        super(TransferConnections, self).__init__()

    @staticmethod
    def transfer_keyable_connections(source_node, target_node, prefix=None):
        """
        Creates the keyable attributes on the target node found on source_node
        :param source_node: str, source node
        :param target_node: str, target node
        :param prefix: str, prefix to give
        """

        source_connections = Connection(node=source_node)
        outputs = source_connections.get_inputs()

        for i in range(len(outputs), 2):
            out_attr = outputs[i]
            in_attr = outputs[i + 1]

            if not cmds.getAttr(in_attr, k=True):
                continue
            if in_attr.find('[') > -1:
                continue

            new_attr = attribute_instance(attribute_name=in_attr)
            if prefix:
                create_title(node=target_node, name=prefix)
                new_attr.set_name('{}_{}'.format(prefix, new_attr.name))

            if not new_attr:
                continue

            new_attr.create(node=target_node)
            new_attr.connect_in(out_attr)


class MayaNode(object):
    """
    Class for managing specific Maya node related attributes
    """

    def __init__(self, name=None):
        self._node = None
        self._create_node(name)

    @property
    def node(self):
        return self._node

    @decorators.abstractmethod
    def _create_node(self, name):
        raise NotImplementedError('_create_node function in MayaNode not implemented!')


class MultiplyDivideNode(MayaNode, object):
    """
    Class for dealing witg multiply divide nodes
    """

    def __init__(self, name=None):
        if not name.startswith('multiplyDivide'):
            name = dcc.find_unique_name('multiplyDivide_{}'.format(name))
        super(MultiplyDivideNode, self).__init__(name)

    def _create_node(self, name):
        self._node = cmds.createNode('multiplyDivide', name=name)
        cmds.setAttr('{}.input2X'.format(self._node), 1)
        cmds.setAttr('{}.input2Y'.format(self._node), 1)
        cmds.setAttr('{}.input2Z'.format(self._node), 1)

    def set_operation(self, value):
        """
        Sets multiplyDivide node operation:
            0 = no operation
            1 = multiply (default)
            2 = divide
            3 = power
        :param value: int, operation index
        """

        cmds.setAttr('{}.operation'.format(self._node), value)

    def set_input1(self, value_x=None, value_y=None, value_z=None):
        """
        Sets input1 attribute values
        :param value_x: float
        :param value_y: float
        :param value_z: float
        """

        if value_x is not None:
            cmds.setAttr('{}.input1X'.format(self._node), value_x)
        if value_y is not None:
            cmds.setAttr('{}.input1Y'.format(self._node), value_y)
        if value_z is not None:
            cmds.setAttr('{}.input1Z'.format(self._node), value_z)

    def set_input2(self, value_x=None, value_y=None, value_z=None):
        """
        Sets input2 attribute values
        :param value_x: float
        :param value_y: float
        :param value_z: float
        """

        if value_x is not None:
            cmds.setAttr('{}.input2X'.format(self._node), value_x)
        if value_y is not None:
            cmds.setAttr('{}.input2Y'.format(self._node), value_y)
        if value_z is not None:
            cmds.setAttr('{}.input2Z'.format(self._node), value_z)

    def input1X_in(self, attribute):
        """
        Connects given attribute to input1X attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input1X'.format(self._node))

    def input1Y_in(self, attribute):
        """
        Connects given attribute to input1Y attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input1Y'.format(self._node))

    def input1Z_in(self, attribute):
        """
        Connects given attribute to input1Z attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input1Z'.format(self._node))

    def input2X_in(self, attribute):
        """
        Connects given attribute to input2X attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input2X'.format(self._node))

    def input2Y_in(self, attribute):
        """
        Connects given attribute to input2Y attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input2Y'.format(self._node))

    def input2Z_in(self, attribute):
        """
        Connects given attribute to input2Z attribute
        :param attribute: str, full attribute name (node.attribute) to connect in
        """

        cmds.connectAttr(attribute, '{}.input2Z'.format(self._node))

    def outputX_out(self, attribute):
        """
        Connects out from outputX to given attribute
        :param attribute: str, full attribute name (node.attribute) to connect out into
        """

        connect_plus('{}.outputX'.format(self._node), attribute)

    def outputY_out(self, attribute):
        """
        Connects out from outputY to given attribute
        :param attribute: str, full attribute name (node.attribute) to connect out into
        """

        connect_plus('{}.outputY'.format(self._node), attribute)

    def outputZ_out(self, attribute):
        """
        Connects out from outputZ to given attribute
        :param attribute: str, full attribute name (node.attribute) to connect out into
        """

        connect_plus('{}.outputZ'.format(self._node), attribute)
