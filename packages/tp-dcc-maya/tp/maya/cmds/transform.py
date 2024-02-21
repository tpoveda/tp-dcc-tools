#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related with transforms
"""

from __future__ import annotations

import random

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log, dcc
from tp.common.python import helpers, name
from tp.common.math import scalar, bbox, vec3
from tp.maya.cmds import exceptions, attribute, node, component, name as name_utils

logger = log.tpLogger

TRANSFORM_SIDES = {
    'end': {
        'short': [('_L', '_R'), ('_l', '_r'), ('left', 'right'), ('Left', 'Right')],
        'long': [('_left', '_right'), ('left', 'right'), ('Left', 'Right')],
    },
    'mid': {
        'short': [('_L_', '_R_'), ('_l_', '_r_')],
        'long': [('_left_', '_right_')]
    },
    'start': {
        'short': [('L_', 'R_'), ('l_', 'r_'), ('left', 'right'), ('Left', 'Right')],
        'long': [('left_', 'right_'), ('left', 'right'), ('Left', 'Right')]
    }
}

TRANSFORM_BASE_ATTRS = (
    '.tx', '.ty', '.tz',
    '.rx', '.ry', '.rz',
    '.sx', '.sy', '.sz',
    '.v'
)


def check_transform(node_name: str):
    """
    Checks if a node is a valid transform and raise and exception if the transform is not valid.
    
    :param str node_name: Name of the node to be checked.
    :raises exceptions.TransformException: if given node name is not a valid transform node.
    """

    if not is_transform(node_name):
        raise exceptions.TransformException(node_name)


def is_transform(node_name: str) -> bool:
    """
    Check whether the specified object is a valid transform node.

    :param str node_name: object to check as a transform node
    :return: True if given node name is a transform node; False otherwise.
    :rtype: bool
    """

    if not cmds.objExists(node_name):
        return False

    if not cmds.objectType(node_name, isAType='transform'):
        return False

    return True


def is_transform_default(transform_node_name: str) -> bool:
    """
    Returns whether given transforms has the default values (identity matrix).
        - translate = [0, 0, 0]
        - rotate = [0, 0, 0]
        - scale = [1, 1, 1]

    :param str transform_node_name: str, transform to check
    :return: True if given transform node has default values in its transform attributes.
    :rtype: bool
    """

    attrs = ['translate', 'rotate']
    for attr in attrs:
        for axis in 'XYZ':
            value = cmds.getAttr('{}.{}{}'.format(transform_node_name, attr, axis))
            if value < -0.00001 or value > 0.00001:
                return False

    for axis in 'XYZ':
        if cmds.getAttr('{}.scale{}'.format(transform_node_name, axis)) != 1:
            return False

    return True


def is_rotate_default(transform):
    """
    Returns whether given transform has the default rotation values
    :param transform: str
    :return: bool
    """

    attributes = ['rotate']
    for attr in attributes:
        for axis in 'XYZ':
            value = maya.cmds.getAttr('{}.{}{}'.format(transform, attr, axis))
            if value < -0.00001 or value > 0.00001:
                return False

    return True


def is_rotate_scale_default(transform):
    """
    Returns whether given transform has the default rotation and scale values
    :param transform: str
    :return: bool
    """

    attributes = ['rotate']
    for attr in attributes:
        for axis in 'XYZ':
            value = maya.cmds.getAttr('{}.{}{}'.format(transform, attr, axis))
            if value < -0.00001 or value > 0.00001:
                return False

    for axis in 'XYZ':
        if maya.cmds.getAttr('{}.scale{}'.format(transform, axis)) != 1:
            return False

    return True


def get_non_default_transforms():
    """
    Returns transforms in the scene that do not have default values
    :return: list(str)
    """

    from tp.maya.cmds import shape as shape_lib

    found = list()
    skip_types = ['joint', 'aimConstraint', 'pointConstraint', 'orientConstraint', 'parentConstraint', 'ikHandle']

    transforms = maya.cmds.ls(type='transform')
    for transform in transforms:
        if maya.cmds.nodeType(transform) in skip_types:
            continue
        elif shape_lib.has_shape_of_type(transform, 'camera'):
            continue
        elif not is_transform_default(transform):
            found.append(transform)

    return found


def match(transform, target):
    """
    Matches given transform to target transform (by matching transform matrices)
    :param transform: str, transform to set
    :param target: str, target transform to match to
    """

    check_transform(transform)
    check_transform(target)

    target_matrix = maya.cmds.xform(target, q=True, ws=True, matrix=True)

    maya.cmds.xform(transform, ws=True, matrix=target_matrix)


def snap(transform, target, snap_pivot=False):
    """
    Snaps given source to target
    :param transform: str, transform to set
    :param target:  str, target transform to match to
    :param snap_pivot: bool, Whether to snap pivot or not
    """

    if snap_pivot:
        pivot = maya.cmds.xform(target, query=True, pivots=True, worldSpace=True)
        maya.cmds.xform(transform, worldSpace=True, pivots=(pivot[0], pivot[1], pivot[2]))
    else:
        pos = maya.cmds.xform(target, query=True, worldSpace=True, translation=True)
        rp_a = maya.cmds.xform(target, query=True, rotatePivot=True)
        rp_b = maya.cmds.xform(transform, query=True, rotatePivot=True)
        maya.cmds.xform(transform, worldSpace=True, translation=(
            pos[0] + rp_a[0] - rp_b[0], pos[1] + rp_a[1] - rp_b[1], pos[2] + rp_a[2] - rp_b[2]))


def get_position(point):
    """
    Returns the position of any point or transform
    :param point: variant, str || list, tuple, point to return position for
    :return: list<int, int, int>
    """

    pos = list()

    if type(point) == list or type(point) == tuple:
        if len(point) < 3:
            logger.exception('Invalid point value supplied! Not enough list/tuple elements!')
            return
        pos = point[0:3]
    elif helpers.is_string(point):
        mobj = node.get_mobject(node_name=point)
        if mobj.hasFn(maya.api.OpenMaya.MFn.kTransform):
            try:
                pos = maya.cmds.xform(point, query=True, worldSpace=True, rotatePivot=True)
            except Exception:
                pass
        if not pos:
            try:
                pos = maya.cmds.pointPosition(point)
            except Exception:
                pass
        if not pos:
            logger.exception(
                'Invalid point value supplied! Unable to determine type of point "{0}"!'.format(str(point)))
            return
    else:
        logger.exception('Invalid point value supplied! Invalid argument type!')
        return

    return pos


def get_mpoint(point):
    """
    Returns the position of any point or transform as an MPoint object
    :param point: variant, str || list || tuple, point to return MPoint position for
    :return: MPoint
    """

    if type(point) == maya.api.OpenMaya.MPoint:
        return point

    pos = get_position(point=point)
    mpoint = maya.api.OpenMaya.MPoint(pos[0], pos[1], pos[2], 1.0)

    return mpoint


def get_matrix(transform, world_space=True, time=None, as_list=False):
    """
    Returns world/local matrix of given transform
    :param transform: str, transform object to get world matrix from
    :param world_space: bool, Whether to get world space matrix or local space matrix
    :param time: int || float, frame to get the transform world matrix for. If is None, will use the current frame
    :param as_list: bool, whether to return matrix as OpenMaya.MMatrix object or as a list
    :return: MMatrix or list
    """

    from tp.maya.cmds import matrix

    if not maya.cmds.objExists(transform):
        exceptions.NodeExistsException(transform)

    # Get matrix attribute definition
    matrix_attr = 'worldMatrix[0]'
    if not world_space:
        matrix_attr = 'matrix'

    # Get time
    if time is not None:
        mat = maya.cmds.getAttr(transform + '.' + matrix_attr, t=time)
    else:
        mat = maya.cmds.getAttr(transform + '.' + matrix_attr)

    if as_list:
        return mat

    # Build matrix
    xform_matrix = matrix.build_matrix(
        translate=(mat[12], mat[13], mat[14]),
        x_axis=(mat[0], mat[1], mat[2]),
        y_axis=(mat[4], mat[5], mat[6]),
        z_axis=(mat[8], mat[9], mat[10]))

    return xform_matrix


def get_translation(transform_name, world_space=True):
    """
    Returns translation of given transform node
    :param transform_name: str, name of a transform node
    :param world_space: bool,  Whether to get the translation on object space or world space. By default, world space
    :return: list<float, float, float>
    """

    if world_space:
        return maya.cmds.xform(transform_name, q=True, t=True, ws=True)

    return maya.cmds.xform(transform_name, q=True, t=True, os=True)


def set_translation(transform_name, translate_vector, world_space=True):
    """
    Set the translation of the given transform node
    :param transform_name: str, name of the node we want to set transform to
    :param translate_vector: list<float, float, float>, new translation vector of the transform node
    :param world_space: bool,  Whether to set the translation on object space or world space. By default, world space
    """

    if world_space:
        return maya.cmds.xform(transform_name, t=translate_vector, ws=True)

    return maya.cmds.xform(transform_name, t=translate_vector, os=True)


def get_rotation(transform_name, world_space=True):
    """
    Returns rotation of given transform node
    :param transform_name: str, name of a transform node
    :param world_space: bool,  Whether to get the rotation on object space or world space. By default, world space
    :return: list<float, float, float>
    """

    if world_space:
        return maya.cmds.xform(transform_name, q=True, ro=True, ws=True)

    return maya.cmds.xform(transform_name, q=True, ro=True, os=True)


def set_rotation(transform_name, rotation_vector, world_space=True):
    """
    Set the rotation of the given transform node
    :param transform_name: str, name of the node we want to set transform to
    :param rotation_vector: list<float, float, float>, new rotation vector of the transform node
    :param world_space: bool,  Whether to set the translation on object space or world space. By default, world space
    """

    if world_space:
        maya.cmds.xform(transform_name, ro=rotation_vector, ws=True)

    maya.cmds.xform(transform_name, ro=rotation_vector, os=True)


def get_rotate_pivot(transform_name, world_space=False):
    """
    Returns the rotate pivot of the given transform node
    :param transform_name: str, name of a transform node
    :param world_space: bool, Whether to get the rotate pivot on object space or world space. By default, object space
    :return: list<float, float, float>
    """

    if world_space:
        return maya.cmds.xform(transform_name, q=True, rp=True, ws=True)

    return maya.cmds.xform(transform_name, q=True, rp=True, os=True)


def set_rotate_pivot(transform_name, rotate_pivot_vector, world_space=False):
    """
    Set the rotation pivot of the given transform node
    :param transform_name: str, name of the node we want to set transform to
    :param rotate_pivot_vector: list<float, float, float>, new rotation pivot vector of the transform node
    :param world_space: bool,  Whether to set the translation on object space or world space. By default, object space
    """

    if world_space:
        return maya.cmds.xform(transform_name, rp=rotate_pivot_vector, ws=True)

    return maya.cmds.xform(transform_name, rp=rotate_pivot_vector, os=True)


def get_scale_pivot(transform_name, world_space=False):
    """
    Returns the scale pivot of the given transform node
    :param transform_name: str, name of a transform node
    :param world_space: bool, Whether to get the scale pivot on object space or world space. By default, object space
    :return: list<float, float, float>
    """

    if world_space:
        return maya.cmds.xform(transform_name, q=True, sp=True, ws=True)

    return maya.cmds.xform(transform_name, q=True, sp=True, os=True)


def set_scale_pivot(transform_name, scale_pivot_vector, world_space=False):
    """
    Set the scale pivot of the given transform node
    :param transform_name: str, name of the node we want to set transform to
    :param scale_pivot_vector: list<float, float, float>, new scale pivot vector of the transform node
    :param world_space: bool,  Whether to set the translation on object space or world space. By default, object space
    """

    if world_space:
        maya.cmds.xform(transform_name, sp=scale_pivot_vector, ws=True)

    maya.cmds.xform(transform_name, sp=scale_pivot_vector, os=True)


def match_scale(target, source):
    """
    Matches target transform scale to source transform scale
    :param target: str, transform we want to match scale to source
    :param source: source transform
    """

    for axis in 'xyz':
        source_scale = maya.cmds.getAttr('{}.scale{}'.format(source, axis.upper()))
        maya.cmds.setAttr('{}.scale{}'.format(target, axis.upper()), source_scale)


def match_translation(target, source):
    """
    Matches target translation to source one
    :param target: str, transform we want to match
    :param source: str, source transform
    """

    scale_pivot_vector = get_scale_pivot(transform_name=source, world_space=False)
    rotate_pivot_vector = get_rotate_pivot(transform_name=source, world_space=False)
    translate_vector = get_translation(transform_name=source, world_space=True)
    set_scale_pivot(transform_name=target, scale_pivot_vector=scale_pivot_vector, world_space=False)
    set_rotate_pivot(transform_name=target, rotate_pivot_vector=rotate_pivot_vector, world_space=False)
    set_translation(transform_name=target, translate_vector=translate_vector, world_space=True)


def match_rotation(target, source):
    """
    Matches target rotation to source one
    :param target: str, transform we want to match
    :param source: str, source transform
    """

    rotation_vector = get_rotation(transform_name=source, world_space=True)
    set_rotation(transform_name=target, rotation_vector=rotation_vector, world_space=True)


def match_translation_rotation(target, source):
    """
    Matches target translation and rotation to source ones
    :param target: str, transform we want to match
    :param source: str, source transform
    """

    match_translation(target=target, source=source)
    match_rotation(target=target, source=source)


def match_translation_to_rotate_pivot(target, source):
    """
    Matches target translation to the source transform rotate pivot
    :param target: str, transform we want to match
    :param source: str, source transform
    """

    translate_vector = get_rotate_pivot(transform_name=source, world_space=True)
    set_translation(transform_name=target, translate_vector=translate_vector, world_space=True)


def match_rotate_scale_pivot_to_translation(target, source):
    """
    Matches the rotation and scale pivot of target transform to the translation of source
    :param target: str, transform we want to match
    :param source: str, source transform
    """

    position = get_translation(transform_name=source, world_space=True)
    maya.cmds.move(position[0], position[1], position[2], '{}.scalePivot'.format(target),
                   '{}.rotatePivot'.format(target), a=True)


def match_rotate_pivot(target, source, world_space=False):
    """
    Matches target transform rotate pivot to source one in object space
    :param target: str, transform we want to match rotate pivot to source
    :param source: str, source transform
    :param world_space: bool, Whether to match rotate pivot in object space or world space. By default, in object space
    """

    source_rotate_pivot = get_rotate_pivot(transform_name=source, world_space=world_space)
    set_rotate_pivot(transform_name=target, rotate_pivot_vector=source_rotate_pivot, world_space=world_space)


def match_scale_pivot(target, source, world_space=False):
    """
    Matches target transform scale pivot to source one in object space
    :param target: str, transform we want to match scale pivot to source
    :param source: str, source transform
    :param world_space: bool, Whether to match scale pivot in object space or world space. By default, in object space
    """

    source_scale_pivot = get_scale_pivot(transform_name=source, world_space=world_space)
    set_scale_pivot(transform_name=target, scale_pivot_vector=source_scale_pivot, world_space=world_space)


def match_orient(target, source):
    """
    Matches target orientation using an orientation constraint
    :param target: str, transform we want to match scale pivot to source
    :param source: str, source transform
    """

    maya.cmds.delete(maya.cmds.orientConstraint(source, target, mo=False))


def match_point(target, source):
    """
    Matches target position using a position constraint
    :param target: str, transform we want to match scale pivot to source
    :param source: str, source transform
    """

    maya.cmds.delete(maya.cmds.pointConstraint(source, target, mo=False))


def match_orient_point(target, source):
    """
    Matches target position and orientation using position and orientation constraints
    :param target: str, transform we want to match scale pivot to source
    :param source: str, source transform
    """

    maya.cmds.delete(maya.cmds.orientConstraint(source, target, mo=False))
    maya.cmds.delete(maya.cmds.pointConstraint(source, target, mo=False))


def get_distance(source_transform, target_transform):
    """
    Get the distance between source and target transforms
    :param source_transform: str, name of a transform node
    :param target_transform: str, name of a transform node
    :return: float
    """

    v1 = maya.cmds.xform(source_transform, q=True, rp=True, ws=True)
    if maya.cmds.nodeType(target_transform) == 'mesh':
        v2 = maya.cmds.xform(target_transform, q=True, t=True, ws=True)
    else:
        v2 = maya.cmds.xform(target_transform, q=True, rp=True, ws=True)

    return vec3.get_distance_between_vectors(v1, v2)


def create_group_in_plane(transform1, transform2, transform3):
    """
    Creates a group that is located in the triangle plane defined by 3 transforms
    :param transform1: str, name of a transform node
    :param transform2: str, name of a transform node
    :param transform3: str, name of a transform node
    :return: str, name of new group that is located in triangle plane (good place to place pole vectors)
    """

    pole_group = maya.cmds.group(empty=True)
    match_translation_rotation(target=pole_group, source=transform1)
    maya.cmds.aimConstraint(transform3, pole_group, offset=[0, 0, 0], weight=1, aimVector=[1, 0, 0], upVector=[0, 1, 0],
                            worldUpType='object', worldUpObject=transform2)

    pole_group_2 = maya.cmds.group(empty=True, n='pole_{}'.format(transform1))
    match_translation_rotation(target=pole_group_2, source=transform2)

    maya.cmds.parent(pole_group_2, pole_group)
    maya.cmds.makeIdentity(pole_group_2, apply=True, t=True, r=True)
    maya.cmds.parent(pole_group_2, w=True)

    maya.cmds.delete(pole_group)

    return pole_group_2


def get_pole_vector(transform1, transform2, transform3, offset=1):
    """
    Given 3 transform (such as arm, elbow, wrist), returns a position where pole vector should be located
    :param transform1: str, name of a transform node
    :param transform2: str, name of a transform node
    :param transform3: str, name of a transform node
    :param offset: float, offset value for the final pole vector position
    :return: list(float, float, float), pole vector with offset
    """

    dst = get_distance(transform1, transform3)
    grp = create_group_in_plane(transform1, transform2, transform3)
    maya.cmds.move(0, offset * dst, 0, grp, r=True, os=True)
    final_pos = maya.cmds.xform(grp, q=True, rp=True, ws=True)
    maya.cmds.delete(grp)

    return final_pos


def mirror_toggle(transform, flag):
    """
    Mirrors attribute value that handles the mirror functionality
    :param transform: str
    :param flag: bool
    """

    if not maya.cmds.objExists('{}.mirror'.format(transform)):
        maya.cmds.addAttr(transform, ln='mirror', at='bool', k=True)

    maya.cmds.setAttr('{}.mirror'.format(transform), flag)


def mirror_transform(
        prefix=None, suffix=None, string_search=None, create_if_missing=False, transforms=None, left_to_right=True):
    """
    Mirrors the position of all transforms that match the given search strings
    :param prefix:str, prefix to search for
    :param suffix: str, suffix to search for
    :param string_search: str, search for a name containing string search
    :param create_if_missing: bool
    :param transforms: list(str)
    :param left_to_right: bool
    :return:
    """

    from tp.maya.cmds import shape as shape_lib

    if transforms is None:
        transforms = list()
    else:
        transforms = transforms[:]

    scope_joints = list()
    scope_transforms = list()
    joints = list()
    skip_search = False

    if transforms:
        skip_search = True
        temp_transforms = list(transforms)
        for temp_xform in temp_transforms:
            node_type = maya.cmds.nodeType(temp_xform)
            if node_type == 'joint':
                joints.append(temp_xform)
            if node_type == 'transform':
                transforms.append(temp_xform)

    if not skip_search:
        # If not prefix or suffix given we store all selected joints and transforms
        if not prefix and not suffix and not string_search:
            joints = maya.cmds.ls(type='joint')
            transforms = maya.cmds.ls(type='transform')

        # If prefix is given we store objects matching that prefix
        if prefix:
            joints = maya.cmds.ls('{}*'.format(prefix, type='joint'))
            transforms = maya.cmds.ls('{}*'.format(prefix), type='transform')
        scope_joints += joints
        scope_transforms += transforms

        # If suffix is given we store objects matching that prefix
        if suffix:
            joints = maya.cmds.ls('*{}'.format(prefix, type='joint'))
            transforms = maya.cmds.ls('*{}'.format(prefix), type='transform')
        scope_joints += joints
        scope_transforms += transforms

        if string_search:
            joints = maya.cmds.ls('*{}*'.format(string_search, type='joint'))
            transforms = maya.cmds.ls('*{}*'.format(string_search, type='transform'))

    # Get list of elements to mirror
    scope_joints += joints
    scope_transforms += transforms
    scope = list(set(scope_joints + scope_transforms))
    if not scope:
        logger.warning('No objects to mirror!')
        return

    other_parents = dict()
    fixed = list()
    created = False

    for xform in scope:

        if maya.cmds.objExists('{}.inMesh'.format(xform)):
            continue

        if left_to_right:
            other = find_transform_right_side(xform, check_if_exists=False)
        else:
            other = find_transform_left_side(xform, check_if_exists=False)

        if not other:
            continue
        if xform in fixed:
            continue
        if attribute.is_translate_rotate_connected(other, ignore_keyframe=True):
            continue

        shape_type = shape_lib.get_shape_node_type(xform)
        if not maya.cmds.objExists(other) and create_if_missing:
            node_type = maya.cmds.nodeType(xform)
            if not node_type == 'joint':
                if shape_type:
                    other_node = maya.cmds.createNode(shape_type)
                    if shape_lib.is_a_shape(other_node):
                        other_node = maya.cmds.listRelatives(other_node, p=True, f=True)
                        other = maya.cmds.rename(other_node, other)
            elif node_type == 'joint':
                other = maya.cmds.duplicate(xform, po=True, n=other)[0]
                if shape_type:
                    other_shape = maya.cmds.createNode(shape_type)
                    if shape_lib.is_a_shape(other_shape):
                        temp_parent = maya.cmds.listRelatives(other_shape, p=True, f=True)
                        maya.cmds.parent(other_shape, other, r=True, s=True)
                        maya.cmds.rename(other_shape, '{}Shape'.format(other))
                        maya.cmds.delete(temp_parent)

            created = True
            parent = maya.cmds.listRelatives(xform, p=True)
            if parent:
                if left_to_right:
                    other_parent = find_transform_right_side(parent[0], check_if_exists=False)
                else:
                    other_parent = find_transform_left_side(parent[0], check_if_exists=False)
                if other_parent:
                    other_parents[other] = other_parent

        if maya.cmds.objExists(other):
            if maya.cmds.objExists('{}.mirror'.format(other)):
                mirror = maya.cmds.getAttr('{}.mirror'.format(other))
                if not mirror:
                    logger.debug('{} was not mirrored because its mirror attribute is set off!'.format(other))
                    continue

            lock_state = attribute.LockTransformState(other)
            lock_state.unlock()

            new_xform = maya.cmds.xform(xform, query=True, ws=True, t=True)

            # Mirror locator
            if shape_type == 'locator':
                local_position = maya.cmds.getAttr('{}.localPosition'.format(xform))[0]
                local_scale = maya.cmds.getAttr('{}.localScale'.format(xform))[0]
                maya.cmds.setAttr('{}.localPosition'.format(other), *local_position, type='float3')
                maya.cmds.setAttr('{}.localScale'.format(other), *local_scale, type='float3')

            # Mirror Joint
            if maya.cmds.nodeType(other) == 'joint':
                radius = maya.cmds.getAttr('{}.radius'.format(xform))
                if not node.is_referenced(other):
                    var = attribute.NumericAttribute('radius')
                    var.set_node(other)
                    var.set_value(radius)
                if not maya.cmds.getAttr('{}.radius'.format(other), lock=True):
                    maya.cmds.setAttr('{}.radius'.format(other), radius)
                maya.cmds.move(
                    new_xform[0] * -1, new_xform[1], new_xform[2],
                    '{}.scalePivot'.format(other), '{}.rotatePivot'.format(other), a=True)

            # Mirror Transform
            if maya.cmds.nodeType(other) == 'transform':
                pos = (new_xform[0] * -1, new_xform[1], new_xform[2])
                maya.cmds.xform(other, ws=True, t=pos)
                pivot = maya.cmds.xform(xform, query=True, ws=True, rp=True)
                maya.cmds.move((pivot[0] * -1), pivot[1], pivot[2], '{}.scalePivot'.format(other),
                               '{}.rotatePivot'.format(other), a=True)
                if maya.cmds.objExists('{}.localPosition'.format(xform)):
                    fix_locator_shape_position(xform)
                if maya.cmds.objExists('{}.localPosition'.format(other)):
                    fix_locator_shape_position(other)

            children = maya.cmds.listRelatives(xform, type='transform')
            if not children:
                rotate = maya.cmds.getAttr('%s.rotate' % xform)[0]
                scale = maya.cmds.getAttr('%s.scale' % xform)[0]
                rotate = helpers.force_list(rotate)
                scale = helpers.force_list(scale)
                rotate[1] *= -1
                rotate[2] *= -1
                maya.cmds.setAttr('%s.rotate' % other, *rotate, type='float3')
                maya.cmds.setAttr('%s.scale' % other, *scale, type='float3')

                lock_state.restore_initial()

            fixed.append(other)

    if create_if_missing:
        for other in other_parents.keys():
            parent = other_parents[other]
            if maya.cmds.objExists(parent) and maya.cmds.objExists(other):
                maya.cmds.parent(other, parent)

    if create_if_missing:
        if created:
            return True
        else:
            return False
    else:
        if fixed:
            return True
        else:
            return False


def find_transform_right_side(transform, check_if_exists=True):
    """
    Try to find the right side of a transform
    :param transform: str, name of a transform
    :param check_if_exists: bool, Whether to return transform if mirror does not exists or not
    :return: str
    """

    other = ''

    for side in TRANSFORM_SIDES['end']['short']:
        if transform.endswith(side[0]):
            other = name.replace_string_at_end(transform, side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['end']['long']:
        if transform.find(side[0]) > -1:
            for end_side in TRANSFORM_SIDES['end']['short']:
                if transform.endswith(end_side[1]):
                    continue
            for start_side in TRANSFORM_SIDES['start']['short']:
                if transform.startswith(start_side[1]):
                    continue
            if not other:
                continue
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['mid']['short']:
        if side[0] in transform:
            other = transform.replace(side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['mid']['long']:
        if side[0] in transform:
            other = transform.replace(side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for i, side in enumerate(TRANSFORM_SIDES['start']['short']):
        if transform.startswith(side[0]) and not transform.endswith(TRANSFORM_SIDES['end']['short'][i][1]):
            other = name.replace_string_at_start(transform, side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['start']['long']:
        if transform.find(side[0]) > -1:
            for end_side in TRANSFORM_SIDES['end']['short']:
                if transform.endswith(end_side[1]):
                    continue
            for start_side in TRANSFORM_SIDES['start']['short']:
                if transform.startswith(start_side[1]):
                    continue

            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    return ''


def find_transform_left_side(transform, check_if_exists=True):
    """
    Try to find the left side of a transform
    :param transform: str, name of a transform
    :param check_if_exists: bool, Whether to return transform if mirror does not exists or not
    :return: str
    """

    other = ''

    for side in TRANSFORM_SIDES['end']['short']:
        if transform.endswith(side[1]):
            other = name.replace_string_at_end(transform, side[1], side[0])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['end']['long']:
        if transform.find(side[1]) > -1:
            for end_side in TRANSFORM_SIDES['end']['short']:
                if transform.endswith(end_side[0]):
                    continue
            for start_side in TRANSFORM_SIDES['start']['short']:
                if transform.startswith(start_side[0]):
                    continue

            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['mid']['short']:
        if side[0] in transform:
            other = transform.replace(side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['mid']['long']:
        if side[0] in transform:
            other = transform.replace(side[0], side[1])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for i, side in enumerate(TRANSFORM_SIDES['start']['short']):
        if transform.startswith(side[1]) and not transform.endswith(TRANSFORM_SIDES['start']['short'][i][0]):
            other = name.replace_string_at_start(transform, side[1], side[0])
            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    for side in TRANSFORM_SIDES['start']['long']:
        if transform.find(side[1]) > -1:
            for end_side in TRANSFORM_SIDES['end']['short']:
                if transform.endswith(end_side[0]):
                    continue
            for start_side in TRANSFORM_SIDES['start']['short']:
                if transform.startswith(start_side[0]):
                    continue

            if (maya.cmds.objExists(other) and check_if_exists) or not check_if_exists:
                return other

    return ''


def zero_transform_channels(xform):
    """
    Zero out the translate and rotate. Set scale to 1
    :param xform: str, name of a transform node
    """

    for channel in 'tr':
        for axis in 'xyz':
            try:
                maya.cmds.setAttr('{}.{}{}'.format(xform, channel, axis), 0)
            except Exception:
                pass

    for axis in 'xyz':
        try:
            maya.cmds.setAttr('{}.scale{}'.format(xform, axis))
        except Exception:
            pass


def get_transforms(shapes_list, full_path=True):
    """
    Returns all transforms from a list of shape nodes
    :param shapes_list: list(str), list of shape nodes to retrieve transform nodes from
    :param full_path: bool, Whether to return full path of shape nodes or not
    :return: list(str)
    """

    transform_list = list()
    for shape_node in shapes_list:
        parent = maya.cmds.listRelatives(shape_node, parent=True, fullPath=full_path)[0]
        if maya.cmds.objectType(parent, isType='transform'):
            transform_list.append(parent)

    return list(set(transform_list))


def fix_locator_shape_position(locator_name):
    """
    Function used to fix the position shape location when doing mirror operations
    :param locator_name: str, name of the locator
    """

    pivot_pos = maya.cmds.xform(locator_name, query=True, os=True, rp=True)
    for i, axis in enumerate('XYZ'):
        maya.cmds.setAttr('{}.localPosition{}'.format(locator_name, axis), pivot_pos[i])


def parent_in_hierarchy(transform, parent):
    """
    Checks if the transform has given parent transform in its hierarchy
    :param transform: str, name of the transform
    :param parent: str, name of the parent transform
    :return: bool
    """

    long_xform = maya.cmds.ls(transform, long=True)
    if not long_xform:
        return

    long_xform = long_xform[0]
    split_long = long_xform.split('|')

    # TODO: Check if we need to compare the long name of the parent or the base name
    parent = name_utils.get_basename(parent)
    if parent in split_long:
        return True

    return False


def transfer_relatives(source_node, target_node, reparent=False):
    """
    Reparent the children of source_node under target_node
    If reparent, move the target_node uner the parent of the source_node
    :param source_node: str, name of a transform to take relatives from
    :param target_node: str, name of a transform to transfer relatives to
    :param reparent: bool, Whether to reparent target_node under source_node after transfering relatives
    """

    parent = None
    if reparent:
        parent = maya.cmds.listRelatives(source_node, p=True)
        if parent:
            parent = parent[0]

    children = maya.cmds.listRelatives(source_node, c=True, type='transform')
    if children:
        maya.cmds.parent(children, target_node)

    if parent:
        maya.cmds.parent(target_node, parent)


def get_upstream_nodes(n):
    """
    Return a list with all upstream nodes of the given Maya node
    :param n: str, name of the node
    :return: list(str)
    """

    upstream_nodes = list()
    upstream_nodes.append(n)
    incoming_nodes = maya.cmds.listConnections(n, source=True, destination=False)
    if incoming_nodes:
        for n in incoming_nodes:
            upstream_nodes.extend(get_upstream_nodes(n))
        return upstream_nodes
    else:
        return upstream_nodes


def delete_all_incoming_nodes(node_name):
    """
    Delete all incoming nodes from the given Maya node
    :param node_name: str
    """

    upstream_nodes = list()
    upstream_nodes_clean = list()
    connections = maya.cmds.listConnections(node_name, source=True, destination=False)
    if connections:
        for n in connections:
            upstream_nodes.extend(get_upstream_nodes(n))

        for n in upstream_nodes:
            if n not in upstream_nodes_clean:
                upstream_nodes_clean.append(n)

        for n in upstream_nodes_clean:
            maya.cmds.delete(n)


def create_buffer_group(node_name, buffer_name=None, suffix='buffer', use_duplicate=False, copy_scale=False):
    """
    Creates a group above a transform that matches transformation of the transform
    Used to zeroing transform values of the node
    :param node_name: str, name of the transform to match
    :param buffer_name: str, name of the buffer
    :param suffix: str, suffix to add to the matching group
    :param use_duplicate: bool, If True, matching happens by duplication instead of changing transform values
    :param copy_scale:
    :return: str, name of the new group
    """

    parent = maya.cmds.listRelatives(node_name, p=True, f=True)
    basename = name_utils.get_basename(node_name)
    full_name = buffer_name
    if not full_name:
        full_name = '{}_{}'.format(basename, suffix)

    orig_scale = maya.cmds.getAttr('{}.scale'.format(node_name))
    if copy_scale:
        try:
            maya.cmds.setAttr('{}.scaleX'.format(node_name), 1)
            maya.cmds.setAttr('{}.scaleY'.format(node_name), 1)
            maya.cmds.setAttr('{}.scaleZ'.format(node_name), 1)
        except Exception:
            pass

    if use_duplicate:
        buffer_grp = maya.cmds.duplicate(node_name, po=True)[0]
        attribute.remove_user_defined_attributes(buffer_grp)
        buffer_grp = maya.cmds.rename(buffer_grp, name_utils.find_unique_name(full_name))
    else:
        buffer_grp = maya.cmds.group(name=name_utils.find_unique_name(full_name), empty=True)
        match_xform = MatchTransform(source_transform=node_name, target_transform=buffer_grp)
        match_xform.translation_rotation()
        if copy_scale:
            match_xform.scale()
        if parent:
            maya.cmds.parent(buffer_grp, parent[0])

    maya.cmds.parent(node_name, buffer_grp)

    if copy_scale:
        maya.cmds.setAttr('{}.scaleX'.format(buffer_grp, orig_scale[0]))
        maya.cmds.setAttr('{}.scaleY'.format(buffer_grp, orig_scale[1]))
        maya.cmds.setAttr('{}.scaleZ'.format(buffer_grp, orig_scale[2]))

    node_name_split = node_name.split('|')
    if len(node_name_split) == 1:
        attribute.connect_group_with_message(buffer_grp, node_name, suffix)
    else:
        node_root_name = '|'.join(node_name_split[:-1])
        buffer_node_name = '{}|{}|{}'.format(node_root_name, buffer_grp, node_name_split[-1])
        attribute.connect_group_with_message(buffer_grp, buffer_node_name, suffix)

    return buffer_grp


def get_buffer_group(node_name, suffix='buffer'):
    """
    Returns buffer group above given node
    :param node_name: str
    :param suffix: str, suffix given when creating buffer group
    :return: str
    """

    attr_name = 'group_{}'.format(suffix)
    node_and_attr = '{}.{}'.format(node_name, attr_name)
    if not maya.cmds.objExists(node_and_attr):
        return
    input_node = attribute.attribute_input(node_and_attr, node_only=True)

    return input_node


def get_shape_bounding_box(shape):
    """
    Returns the bounding box of a shape
    :param shape: str
    :return: BoundingBox
    """

    x_min, y_min, z_min, x_max, y_max, z_max = maya.cmds.exactWorldBoundingBox(shape)
    return bbox.BoundingBox([x_min, y_min, z_min], [x_max, y_max, z_max])


def get_axis_vector(transform, axis_vector):
    """
    Returns the vector matrix product
    If you give a vector [1, 0, 0], it will return the transform's X point
    If you give a vector [0, 1, 0], it will return the transform's Y point
    If you give a vector [0, 0, 1], it will return the transform's Z point
    :param transform: str, name of a transforms. Its matrix will be checked
    :param axis_vector: list<int>, A vector, X = [1,0,0], Y = [0,1,0], Z = [0,0,1]
    :return: list<int>, the result of multiplying the vector by the matrix
    Useful to get an axis in relation to the matrix
    """

    # TODO: This is not working properly. Check why ...
    # from tpRigToolkit.maya.lib import api
    #
    # xform = api.TransformFunction(transform)
    # new_vector = xform.get_vector_matrix_product(axis_vector)
    #
    # return new_vector

    vector_node = maya.cmds.createNode('vectorProduct')
    new_group = maya.cmds.group(empty=True)
    maya.cmds.connectAttr('{}.worldMatrix'.format(transform), '{}.matrix'.format(vector_node))
    for i, axis in enumerate(['X', 'Y', 'Z']):
        maya.cmds.setAttr('{}.input1{}'.format(vector_node, axis), axis_vector[i])

    maya.cmds.setAttr('{}.operation'.format(vector_node), 4)
    maya.cmds.connectAttr('{}.output'.format(vector_node), '{}.translate'.format(new_group))
    new_vector = maya.cmds.getAttr('{}.translate'.format(new_group))[0]
    maya.cmds.delete(vector_node)
    maya.cmds.delete(new_group)

    return new_vector


def get_vector_axis_letter(vector):
    """
    Returns the axis letter of the given vector
    :param vector: list(float, float, float)
    :return: str
    """

    if vector == [1, 0, 0]:
        return 'X'
    if vector == [0, 1, 0]:
        return 'Y'
    if vector == [0, 0, 1]:
        return 'Z'
    if vector == [-1, 0, 0]:
        return '-X'
    if vector == [0, -1, 0]:
        return '-Y'
    if vector == [0, 0, -1]:
        return '-Z'


def get_axis_aimed_at_child(transform):
    """
    Returns the axis that is pointing to the given transform
    :param transform: str, name of a transform node
    :return:
    """

    children = maya.cmds.listRelatives(transform, type='transform')
    if not children:
        return

    all_axis = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]
    aim_axis = [0, 0, 0]
    current_result = 0

    pos_1 = maya.cmds.xform(transform, q=True, ws=True, t=True)
    pos_2 = maya.cmds.xform(children[0], q=True, ws=True, t=True)
    pos_2 = vec3.vector_sub(pos_2, pos_1)

    for axis in all_axis:
        axis_vector = get_axis_vector(transform, axis_vector=axis)
        axis_vector = vec3.vector_sub(axis_vector, pos_1)
        vector_1 = vec3.Vector3(axis_vector)
        vector_2 = vec3.Vector3(pos_2)
        result = vec3.get_dot_product(vector_1, vector_2)
        if result > current_result:
            aim_axis = axis
            current_result = result

    return aim_axis


def get_axis_letter_aimed_at_child(transform):
    """
    Returns the axis letter that is poinitng to the given transform
    :param transform: str, name of a transform
    :return: str
    """

    vector = get_axis_aimed_at_child(transform)
    return get_vector_axis_letter(vector)


def get_closest_transform(source_xform, targets):
    """
    Given the list of target transforms, find the closest to the source transform
    :param source_xform: str, name of the transform to test distance to
    :param targets: list<str>, list of targets to test distance against
    :return: str, name of the target in targets that is closest to source transform
    """

    least_distant = 1000000.0
    closest_target = None

    for target in targets:
        dst = get_distance(source_xform, target)
        if dst < least_distant:
            least_distant = dst
            closest_target = target

    return closest_target


def get_middle_transform(transform_list):
    """
    Given a list of transforms, find the middle index. If the list is even, then find the midpoint between the middle
    two indices
    :param transform_list: list<str>, list of transforms in order. Transforms should make a hierarchy or a sequence,
    where the order of the list matches the order in space
    :return: list<x, y, z>, midpoint
    """

    count = len(transform_list)
    total_division = count / 2

    if count == 0:
        return

    if (total_division + total_division) == count:
        mid_point = vec3.get_mid_point(transform_list[total_division - 1], transform_list[total_division])
    else:
        mid_point = maya.cmds.xform(transform_list[total_division], q=True, t=True, ws=True)

    return mid_point


def get_bounding_box_size(transform):
    """
    Returns the bounding box size of a selection (components or transforms)
    :param transform: str, name of a maya node
    :return: float
    """

    components = component.get_components_in_hierarchy(transform)
    if components:
        transform = components

    bounding_box = BoundingBox(transform)
    return bounding_box.get_size()


def get_center(transform):
    """
    Returns the center of a selection (components or transforms)
    :param transform: str, name of a maya node
    :return: list(float, float, float)
    """

    objs = helpers.force_list(transform)
    components = list()
    for obj in objs:
        if maya.cmds.nodeType(transform) == 'transform' or maya.cmds.nodeType(transform) == 'joint':
            sub_components = component.get_components_in_hierarchy(transform)
            if sub_components and type(sub_components) == list:
                components += sub_components

        if obj.find('.') > -1:
            components.append(obj)

    if components:
        transform = components

    bounding_box = BoundingBox(transform)

    return bounding_box.get_center()


def get_top_center(transform):
    """
    Returns the top center of a selection (components or transforms)
    :param transform: str, name of a a maya node
    :return: list(float, float, float)
    """

    components = component.get_components_in_hierarchy(transform)
    if components:
        transform = components

    bounding_box = BoundingBox(transform)
    return bounding_box.get_ymax_center()


def get_bottom_center(transform):
    """
    Returns the bottom center of a selection (components or transforms)
    :param transform: str, name of a a maya node
    :return: list(float, float, float)
    """

    components = component.get_components_in_hierarchy(transform)
    if components:
        transform = components

    bounding_box = BoundingBox(transform)
    return bounding_box.get_ymin_center()


def get_ordered_distance_and_transform(source_transform, transform_list):
    """
    Returns:
        - List of distance based on how far each transform in transform_list is from source_transform
        - Distance dictionary with each distance key returning the corresponding transform
        - List with the original distance order has fed in from transform_list
    :param source_transform: str, name of a maya transform node
    :param transform_list: list(str), list of maya transform nodes distances from source_transform will be calculated of
    :return: list(str)
    """

    distance_list = list()
    distance_dict = dict()

    for xform in transform_list:
        distance = get_distance(source_transform, xform)
        distance_list.append(distance)
        if distance in distance_dict:
            distance_dict[distance].append(xform)
        else:
            distance_dict[distance] = [xform]

    original_distance_order = list(distance_list)
    distance_list.sort()

    return distance_list, distance_dict, original_distance_order


def get_transform_list_from_distance(source_transform, transform_list):
    """
    Returns a list of distances that corresponds to the transform_list
    :param source_transform: str, name of a maya transform node
    :param transform_list: list(str), list of maya transform nodes distances from source_transform will be calculated of
    :return: list(str)
    """

    distance_list, distance_dict, original = get_ordered_distance_and_transform(source_transform, transform_list)
    found = list()
    for dst in distance_list:
        found.append(distance_dict[dst][0])

    return found


def delete_history(transform):
    """
    Deletes the construction history of the given node
    :param transform: str
    """

    return maya.cmds.delete(transform, constructionHistory=True)


def freeze_transforms(
        transform, translate=True, rotate=True, scale=True, normal=False, preserve_normals=True, clean_history=False):
    """
    Freezes the transformations of the given node and its children
    :param transform: bool
    :param translate: bool
    :param rotate: bool
    :param scale: bool
    :param normal: bool
    :param preserve_normals: bool
    :param clean_history: bool, When applying to transforms with history, a transformGeometry node is
        created in history. Pass True, to clean history before applying the freeze transforms
    """

    if clean_history:
        delete_history(transform)

    return maya.cmds.makeIdentity(
        transform, apply=True,
        translate=translate, rotate=rotate, scale=scale, normal=normal, pn=preserve_normals
    )


def inverse_transform(source_node, target_node, translate=True, rotate=True, scale=True):
    """
    Applies the inverse of a given transform to another target transform
    :param source_node: str, source transform
    :param target_node: str, target transform that in which we are going to apply the inverse transformation
    :param translate: bool, apply inverse translation to target transform
    :param rotate: bool, apply inverse rotation to target transform
    :param scale: bool, apply inverse scale to target transform
    :return:
    """

    if not maya.cmds.objExists(source_node):
        raise Exception('Transform "{}" does not exists!'.format(source_node))
    if not maya.cmds.objExists(target_node):
        raise Exception('Transform "{}" does not exists!'.format(target_node))

    # Load decomposeMatrix plugin if necessary
    if not maya.cmds.pluginInfo('decomposeMatrix', query=True, loaded=True):
        try:
            maya.cmds.loadPlugin('decomposeMatrix')
        except Exception:
            raise Exception('Unable to laod "decomposeMatrix" Maya plugin!')

    decompose_node = maya.cmds.createNode('decomposeMatrix', n='{}_decomposeMatrix'.format(source_node))
    maya.cmds.connectAttr('{}.invsereMatrix'.format(source_node), '{}.inputMatrix'.format(decompose_node), f=True)
    if translate:
        maya.cmds.connectAttr('{}.outputTranslate'.format(decompose_node), '{}.translate'.format(target_node), f=True)
    if rotate:
        maya.cmds.connectAttr('{}.outputRotate'.format(decompose_node), '{}.rotate'.format(target_node), f=True)
    if scale:
        maya.cmds.connectAttr('{}.outputScale'.format(decompose_node), '{}.scale'.format(target_node), f=True)

    return decompose_node


def set_translate_x_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the translate X of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -1 if min_value is None else min_value
    max_value = 1 if min_value is None else max_value

    maya.cmds.transformLimits(transform, tx=[min_value, max_value], etx=[min_bool, max_bool])


def set_translate_y_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the translate Y of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -1 if min_value is None else min_value
    max_value = 1 if min_value is None else max_value

    maya.cmds.transformLimits(transform, ty=[min_value, max_value], ety=[min_bool, max_bool])


def set_translate_z_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the translate Z of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -1 if min_value is None else min_value
    max_value = 1 if min_value is None else max_value

    maya.cmds.transformLimits(transform, tz=[min_value, max_value], etz=[min_bool, max_bool])


def set_rotate_x_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the rotate X of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -45 if min_value is None else min_value
    max_value = 45 if min_value is None else max_value

    maya.cmds.transformLimits(transform, rx=[min_value, max_value], erx=[min_bool, max_bool])


def set_rotate_y_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the rotate Y of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -45 if min_value is None else min_value
    max_value = 45 if min_value is None else max_value

    maya.cmds.transformLimits(transform, ry=[min_value, max_value], ery=[min_bool, max_bool])


def set_rotate_z_limit(transform, min_value=None, max_value=None):
    """
    Sets the maximum value a transform node accepts for the rotate Z of its transform
    :param transform: str
    :param min_value: float or None
    :param max_value: float or None
    """

    min_bool = 0 if min_value is None else 1
    max_bool = 0 if max_value is None else 1
    min_value = -45 if min_value is None else min_value
    max_value = 45 if min_value is None else max_value

    maya.cmds.transformLimits(transform, rz=[min_value, max_value], erz=[min_bool, max_bool])


def randomize_transform(translate=None, rotate=None, scale=None, transforms=None):
    """
    Generates random transforms taking into account the given amounts
    :param translate: list(float, float, float), positive and negative amount values used to generate random translation
    :param rotate: list(float, float, float), positive and negative amount values used to generate random rotation
    :param scale: list(float, float, float), positive and negative amount values used to generate random scale
    :param transforms: list(list(float, float, float), transforms to apply randomization. If not given, current
        viewport selected transforms will be randomized
    """

    translate = translate or [0.1, 0.1, 0.1]
    rotate = rotate or [1, 1, 1]
    scale = scale or [0.1, 0.1, 0.1]

    transforms = transforms if transforms else maya.cmds.ls(sl=True, type='transform')
    for xform in transforms:
        maya.cmds.move(
            random.uniform(-translate[0], translate[0]),
            random.uniform(-translate[1], translate[1]),
            random.uniform(-translate[2], translate[2]),
            xform, relative=True)

        maya.cmds.rotate(
            random.uniform(-rotate[0], rotate[0]),
            random.uniform(-rotate[1], rotate[1]),
            random.uniform(-rotate[2], rotate[2]),
            xform, ocp=True, relative=True)

        scale_x_invert = 1 - scale[0]
        scale_y_invert = 1 - scale[1]
        scale_z_invert = 1 - scale[2]

        maya.cmds.scale(
            random.uniform(scale_x_invert, (1 + scale[0])),
            random.uniform(scale_y_invert, (1 + scale[1])),
            random.uniform(scale_z_invert, (1 + scale[2])),
            xform)


def create_locators_along_curve(curve, count, description, attach=True):
    """
    Crates new locators on given curve
    :param curve: str, name of the curve
    :param count: int, number of joints to create
    :param description: str, description to give to the created locators
    :param attach: bool, Whether ot attach or not the joints on the curve
    :return: list(str), list of created locators
    """

    from tp.maya.cmds import curve as curve_utils

    maya.cmds.select(clear=True)

    locators = list()
    current_length = 0
    percent = 0
    segment = 1.0 / count

    total_length = maya.cmds.arclen(curve)
    part_length = total_length / (count - 1)

    for i in range(count):
        param = curve_utils.get_parameter_from_curve_length(curve, current_length)
        position = curve_utils.get_point_from_curve_parameter(curve, param)
        if attach:
            maya.cmds.select(clear=True)
        locator = maya.cmds.spaceLocator(n=name_utils.find_unique_name('locator_{}'.format(description)))
        maya.cmds.xform(locator, ws=True, t=position)
        maya.cmds.addAttr(locator, ln='param', at='double', dv=param)
        if attach:
            curve_utils.attach_to_curve(locator, curve, parameter=param)
        current_length += part_length
        locators.append(locator)
        percent += segment

    return locators


def duplicate_transform_without_children(transform_node, node_name='', delete_shapes=False, delete_shape_type=''):
    """
    Duplicates given transform node without their children and keeping the shape node intact
    NOTE: During this process, the original shapes nodes are temporally parented out of the original transform
    NOTE: User attributes are lost because transform is rebuilt from scratch
    :param transform_node: str, transform node we want to duplicate
    :param node_name: str, name of the new transform node
    :param delete_shapes: bool, whether to delete the shape nodes of the original transform node
    :param delete_shape_type: str, only shapes of the given types will be duplicated. If not given, all shapes
        will be duplicated onto the new transform
    :return: str, name of the duplicated transform
    """

    # Import here to avoid cyclic imports
    from tp.maya.cmds import shape as shape_utils

    # Create temporal group and matches original transform offset
    rot_offset = list()

    if maya.cmds.objectType(transform_node) == 'transform':
        rot_offset = maya.cmds.getAttr('{}.rotatePivot'.format(transform_node))[0]
    node_short_name = name_utils.get_short_name(transform_node)
    temp_node = maya.cmds.group(empty=True, name='{}_tempNode'.format(node_short_name))
    maya.cmds.matchTransform([temp_node, transform_node], pos=True, rot=True, scl=True, piv=False)

    # Parent all shapes node of the original node to the temporal group
    if delete_shape_type:
        shapes_list = maya.cmds.listRelatives(transform_node, shapes=True, type=delete_shape_type, fullPath=True)
    else:
        shapes_list = maya.cmds.listRelatives(transform_node, shapes=True, fullPath=True)
    if shapes_list:
        for i, shape in enumerate(shapes_list):
            shapes_list[i] = maya.cmds.parent(shape, temp_node, shape=True, relative=True)[0]
    shapes_list = maya.cmds.listRelatives(temp_node, shapes=True, fullPath=True)

    if not delete_shapes:
        temp_dup = maya.cmds.duplicate(temp_node, name='{}_duplicate'.format(node_short_name), renameChildren=True)[0]
        if shapes_list:
            for i, shape in enumerate(shapes_list):
                shapes_list[i] = maya.cmds.parent(shape, transform_node, shape=True, relative=True)[0]
        maya.cmds.delete(temp_node)
    else:
        temp_dup = temp_node
        if not node_name:
            temp_dup = maya.cmds.rename(temp_dup, '{}_duplicate'.format(node_short_name))

    if rot_offset and (rot_offset[0] or rot_offset[1] or rot_offset[2]):
        maya.cmds.move(-rot_offset[0], -rot_offset[1], rot_offset[2], temp_dup, relative=True, objectSpace=True)
        maya.cmds.matchTransform([temp_dup, node], pos=False, rot=False, scl=False, piv=True)

    if node_name:
        temp_dup = maya.cmds.rename(temp_dup, name_utils.get_basename(node_name))

    shape_utils.rename_shapes(temp_dup)

    return temp_dup


def parent_transforms_shapes(
        target_transform, transform_nodes_to_parent, delete_original=False, rename_shapes=True, delete_shape_type=''):
    """
    Parents all shapes of the given transform nodes to the given target transform node
    :param target_transform: str
    :param transform_nodes_to_parent: list(str)
    :param delete_original: bool
    :param rename_shapes: bool
    :param delete_shape_type: str
    :return:
    """

    # Import here to avoid cyclic imports
    from tp.maya.cmds import shape as shape_utils

    transform_nodes_to_parent = helpers.force_list(transform_nodes_to_parent)
    use_locked_attr_parent = False
    obj_parents = node.get_all_parents(transform_nodes_to_parent[-1])
    for obj in transform_nodes_to_parent[:-1]:
        obj_unsettable_attrs = attribute.get_locked_and_connected_attributes(obj)
        if obj_unsettable_attrs:
            use_locked_attr_parent = True
            break
        if obj in obj_parents:
            use_locked_attr_parent = True
            break
        if maya.cmds.listRelatives(obj, children=True, type='transform'):
            use_locked_attr_parent = True
            break

    if use_locked_attr_parent:
        for i, obj in enumerate(transform_nodes_to_parent[:-1]):
            new_obj = duplicate_transform_without_children(obj, delete_shapes=True)
            if not maya.cmds.listRelatives(obj, children=True):
                maya.cmds.delete(transform_nodes_to_parent[i])
            transform_nodes_to_parent[i] = new_obj

    if delete_original:
        if delete_shape_type:
            shapes_to_delete = maya.cmds.listRelatives(
                target_transform, shapes=True, fullPath=True, type=delete_shape_type)
        else:
            shapes_to_delete = maya.cmds.listRelatives(target_transform, shapes=True, fullPath=True)
        if shapes_to_delete:
            maya.cmds.delete(shapes_to_delete)

    for transform_node in transform_nodes_to_parent:
        transform_node = maya.cmds.parent(transform_node, target_transform)
        maya.cmds.makeIdentity(transform_node, apply=True, translate=True, rotate=True, scale=True)
        transform_node = maya.cmds.parent(transform_node, world=True)
        source_shapes = maya.cmds.listRelatives(transform_node, shapes=True, fullPath=True)
        if source_shapes:
            for shape in source_shapes:
                maya.cmds.parent(shape, target_transform, s=True, r=True)
            maya.cmds.delete(transform_node)

    if rename_shapes:
        shape_utils.rename_shapes(target_transform)

    return target_transform


def axis_world_position(transform_node, axis):
    """
    Returns the axis world position of the given transform node
    :param transform_node: str
    :param axis: list(int)
    :return: list(float)
    """

    transform1 = maya.cmds.createNode('transform', name='transform1')
    try:
        transform1 = maya.cmds.parent(transform1, transform_node, r=True)[0]
        maya.cmds.setAttr('{}.t'.format(transform1), *axis)
        maya.cmds.setAttr('{}.r'.format(transform1), 0, 0, 0)
        maya.cmds.setAttr('{}.s'.format(transform1), 1, 1, 1)
        return maya.cmds.xform(transform1, query=True, ws=True, piv=True)
    finally:
        maya.cmds.delete(transform1)


def get_mirror_axis(transform_node, mirror_plane):
    """
    Returns mirror axis of the given node name
    :param transform_node: str
    :param mirror_plane: str, mirror plane ("YZ", "XY", "XZ")
    :return: str
    """

    result = [1, 1, 1]
    transform0 = maya.cmds.createNode('transform', name='transform0')
    try:
        transform0 = maya.cmds.parent(transform0, transform_node, r=True)[0]
        transform0 = maya.cmds.parent(transform0, w=True)[0]
        maya.cmds.setAttr('{}.t'.format(transform0), 0, 0, 0)
        t1 = axis_world_position(transform0, [1, 0, 0])
        t2 = axis_world_position(transform0, [0, 1, 0])
        t3 = axis_world_position(transform0, [0, 0, 1])
        t1 = '%.3f' % t1[0], '%.3f' % t1[1], '%.3f' % t1[2]
        t2 = '%.3f' % t2[0], '%.3f' % t2[1], '%.3f' % t2[2]
        t3 = '%.3f' % t3[0], '%.3f' % t3[1], '%.3f' % t3[2]
        if mirror_plane == dcc.MirrorPlane.YZ:
            x = [t1[0], t2[0], t3[0]]
            i = scalar.max_index(x)
            result[i] = -1
        if mirror_plane == dcc.MirrorPlane.XZ:
            y = [t1[1], t2[1], t3[1]]
            i = scalar.max_index(y)
            result[i] = -1
        if mirror_plane == dcc.MirrorPlane.XY:
            z = [t1[2], t2[2], t3[2]]
            i = scalar.max_index(z)
            result[i] = -1
    finally:
        maya.cmds.delete(transform0)

    return result


def is_axis_mirrored(source_transform, target_transform, axis, mirror_plane):
    """
    Returns whether given nodes axis are mirrored
    :param source_transform: str
    :param target_transform: str
    :param axis: list(int)
    :param mirror_plane: str
    :return: bool
    """

    old1 = maya.cmds.xform(source_transform, q=True, ws=True, piv=True)
    old2 = maya.cmds.xform(target_transform, q=True, ws=True, piv=True)
    new1 = axis_world_position(source_transform, axis)
    new2 = axis_world_position(target_transform, axis)
    mp = mirror_plane
    v1 = mp[0] * (new1[0] - old1[0]), mp[1] * (new1[1] - old1[1]), mp[2] * (new1[2] - old1[2])
    v2 = new2[0] - old2[0], new2[1] - old2[1], new2[2] - old2[2]

    total_distance = sum(p * q for p, q in zip(v1, v2))
    if total_distance >= 0.0:
        return False

    return True


class PinTransform:
    """
    Class that allows to pin a transform so its parent and children are not affected by any edits
    """

    def __init__(self, transform_name):
        self.transform = transform_name
        self.delete_later = list()
        self.lock_state = dict()

    def pin(self):
        """
        Creates the pin constraints on parent and children
        """

        from tp.maya.cmds import name

        self.lock_state = dict()
        parent = maya.cmds.listRelatives(self.transform, p=True, f=True)
        if parent:
            parent = parent[0]
            pin = maya.cmds.duplicate(parent, po=True, n=name.find_unique_name('pin1'))[0]
            pin_parent = maya.cmds.listRelatives(pin, p=True)
            if pin_parent:
                maya.cmds.parent(pin, w=True)

            cns = maya.cmds.parentConstraint(pin, parent, mo=True)[0]
            self.delete_later.append(cns)
            self.delete_later.append(pin)

        children = maya.cmds.listRelatives(self.transform, f=True)
        if not children:
            return

        for child in children:
            if not is_transform(child):
                continue

            pin = maya.cmds.duplicate(child, po=True, n=name.find_unique_name('pin1'))[0]

            try:
                maya.cmds.parent(pin, w=True)
            except Exception:
                pass

            lock_state_inst = attribute.LockAttributesState(node=child)
            self.lock_state[child] = lock_state_inst
            lock_state_inst.unlock()

            cns = maya.cmds.parentConstraint(pin, child, mo=True)[0]
            self.delete_later.append(cns)
            self.delete_later.append(pin)

    def unpin(self):
        """
        Removes the pin
        :return:
        """

        if self.delete_later:
            maya.cmds.delete(self.delete_later)
            for lock_state in self.lock_state:
                self.lock_state[lock_state].restore_initial()

    def get_pin_nodes(self):
        """
        Returns list of nodes involved in the pinning (constraints and empty groups)
        :return: list<str>
        """

        return self.delete_later


class MatchTransform:
    """
    Class used to match transformations between two transform nodes
    """

    def __init__(self, source_transform, target_transform):
        """
        Constructor
        :param source_transform: source transform node
        :param target_transform: transform node we want to match to source
        """
        self.source = source_transform
        self.target = target_transform

    def translation(self):
        """
        Matches target translation to source one
        """

        self._set_translation()
        self._set_scale_pivot()
        self._set_rotate_pivot()

    def rotation(self):
        """
        Matches target rotation to source one
        """

        self._set_rotation()

    def translation_rotation(self):
        """
        Matches target translation and rotation to source ones
        """

        self._set_translation()
        self._set_scale_pivot()
        self._set_rotate_pivot()
        self._set_rotation()

    def translation_to_rotate_pivot(self):
        """
        Matches target translation to the source transform rotate pivot
        """

        translate_vector = self._get_world_rotate_pivot()
        self._set_translation(translate_vector)

    def rotate_scale_pivot_to_translation(self):
        """
        Matches the rotation and scale pivot of target transform to the translation of source
        """

        match_rotate_scale_pivot_to_translation(target=self.target, source=self.source)

    def pivots(self):
        """
        Matches the pivots of target transform to the source transform ones in object space
        """

        self._set_rotate_pivot()
        self._set_scale_pivot()

    def world_pivots(self):
        """
        Matches the pivots of target transform  to the source transform ones in world space
        """

        self._set_world_rotate_pivot()
        self._set_world_scale_pivot()

    def scale(self):
        """
        Matches target transform scale to source transform scale
        """

        match_scale(target=self.target, source=self.source)

    def _get_translation(self):
        """
        Return the translation in world space of the source transform
        :return: list<float, float, float>
        """

        return get_translation(transform_name=self.source, world_space=True)

    def _get_rotation(self):
        """
        Returns rotation in world space of the source transform
        :return: list<float, float, float>
        """

        return get_rotation(transform_name=self.source, world_space=True)

    def _get_rotate_pivot(self):
        """
        Get rotate pivot in object space of the source transform
        :return: list<float, float, float>
        """

        return get_rotate_pivot(transform_name=self.source, world_space=False)

    def _get_scale_pivot(self):
        """
        Returns scale pivot in object space of the source transform
        :return: list<float, float, float>
        """

        return get_scale_pivot(transform_name=self.source, world_space=False)

    def _get_world_rotate_pivot(self):
        """
        Get rotate pivot in world space of the source transform
        :return: list<float, float, float>
        """

        return get_rotate_pivot(transform_name=self.source, world_space=True)

    def _get_world_scale_pivot(self):
        """
        Returns scale pivot in world space of the source transform
        :return: list<float, float, float>
        """

        return get_scale_pivot(transform_name=self.source, world_space=True)

    def _set_translation(self, translate_vector=None):
        """
        Set the target transform position in world space
        :param translate_vector: list<float, float, float>, translation vector to apply to target
        transform in world space. If not given, target will be match to source position
        """

        if not translate_vector:
            translate_vector = self._get_translation()

        set_translation(transform_name=self.target, translate_vector=translate_vector, world_space=True)

    def _set_rotation(self, rotation_vector=None):
        """
        Set the target transform rotation in world space
        :param rotation_vector: list<float, float, float>, rotation vector to apply to target
        transform in world space. If not given, target will be match to source rotation
        """

        if not rotation_vector:
            rotation_vector = self._get_rotation()

        set_rotation(transform_name=self.target, rotation_vector=rotation_vector, world_space=True)

    def _set_rotate_pivot(self, rotate_pivot_vector=None):
        """
        Set the target transform rotation pivot in object space
        :param rotate_pivot_vector: list<float, float, float>, rotation pivot vector to apply to target
        transform rotation pivot in object space. If not given, target will be match to source rotation pivot
        """

        if not rotate_pivot_vector:
            rotate_pivot_vector = self._get_rotate_pivot()

        set_rotate_pivot(transform_name=self.target, rotate_pivot_vector=rotate_pivot_vector, world_space=False)

    def _set_scale_pivot(self, scale_pivot_vector=None):
        """
        Set the target transform scale pivot in object space
        :param scale_pivot_vector: list<float, float, float>, scale pivot vector to apply to target
        transform scale pivot in object space. If not given, target will be match to source scale pivot
        """

        if not scale_pivot_vector:
            scale_pivot_vector = self._get_scale_pivot()

        set_scale_pivot(transform_name=self.target, scale_pivot_vector=scale_pivot_vector, world_space=False)

    def _set_world_rotate_pivot(self, rotate_pivot_vector=None):
        """
        Set the target transform rotation pivot in world space
        :param rotate_pivot_vector: list<float, float, float>, rotation pivot vector to apply to target
        transform rotation pivot in world space. If not given, target will be match to source rotation pivot
        """

        if not rotate_pivot_vector:
            rotate_pivot_vector = self._get_rotate_pivot()

        set_rotate_pivot(transform_name=self.target, rotate_pivot_vector=rotate_pivot_vector, world_space=True)

    def _set_world_scale_pivot(self, scale_pivot_vector=None):
        """
        Set the target transform scale pivot in world space
        :param scale_pivot_vector: list<float, float, float>, scale pivot vector to apply to target
        transform scale pivot in world space. If not given, target will be match to source scale pivot
        """

        if not scale_pivot_vector:
            scale_pivot_vector = self._get_scale_pivot()

        set_scale_pivot(transform_name=self.target, scale_pivot_vector=scale_pivot_vector, world_space=True)


class BoundingBox(bbox.BoundingBox):
    """
    Util class to work with bounding box
    """

    def __init__(self, transform_node=None):
        """
        Constructor
        :param transform_node: str, name of a transform in Maya. If given, bounding box is automatically created from it
        """

        self._node = transform_node

        x_min, y_min, z_min, x_max, y_max, z_max = maya.cmds.exactWorldBoundingBox(transform_node)
        super(BoundingBox, self).__init__([x_min, y_min, z_min], [x_max, y_max, z_max])

    def get_shapes_bounding_box(self):
        """
        Returns bounding box of the transform shapes
        :return: BoundingBox
        """

        from tp.maya.cmds import shape as shape_lib
        shapes = shape_lib.get_shapes(self._node, intermediates=False, full_path=True)
        if shapes:
            x_min, y_min, z_min, x_max, y_max, z_max = maya.cmds.exactWorldBoundingBox(shapes)
            return bbox.BoundingBox([x_min, y_min, z_min], [x_max, y_max, z_max])

        return None


class DuplicateHierarchy:
    """
    Duplicate the hierarchy of a transform
    """

    def __init__(self, transform_name):
        """
        Constructor
        :param transform_name:  str
        """
        self._top_transform = transform_name
        self._duplicates = list()
        self._replace_old = None
        self._replace_new = None
        self._stop = False
        self._stop_at_transform = None
        self._only_these_transform = None
        self._only_joints = False

    def create(self):
        """
        Creates the duplicate hierarchy
        """

        maya.cmds.refresh()
        self._duplicate_hierarchy(self._top_transform)

        return self._duplicates

    def only_these(self, list_of_transforms):
        """
        Only transforms of the given list will be duplicated
        :param list_of_transforms: list<str>
        """

        self._only_joints = list_of_transforms

    def stop_at(self, xform):
        """
        Hierarchy duplication will be stop at the given transform
        :param xform: str
        """

        relative = maya.cmds.listRelatives(xform, type='transform')
        if relative:
            self._stop_at_transform = relative[0]

    def set_replace(self, old, new):
        """
        Replace the naming in the duplicate
        :param old: str, string in the duplicate name to replace
        :param new: str, string in the duplicate to replace with
        """

        self._replace_old = old
        self._replace_new = new

    def _get_children(self, xform):
        """
        Internal function used to return all children of the given transforms
        Without taking into account constraint nodes
        :param xform: str
        :return: list<str>
        """

        children = maya.cmds.listRelatives(xform, children=True, type='transform')
        found = list()
        if children:
            for child in children:
                if maya.cmds.nodeType(child).find('Constraint') > - 1:
                    continue
                found.append(child)

        return found

    def _duplicate(self, xform):
        new_name = xform
        if self._replace_old and self._replace_new:
            replace_old = helpers.force_list(self._replace_old)
            replace_new = helpers.force_list(self._replace_new)
            for old_name, replace_name in zip(replace_old, replace_new):
                if old_name in new_name:
                    new_name = xform.replace(old_name, replace_name)
                    break
                else:
                    if new_name == xform:
                        new_name = '{}_{}'.format(xform, replace_name)
            new_name = name_utils.get_basename(new_name)

        duplicate = maya.cmds.duplicate(xform, po=True)[0]
        attribute.remove_user_defined_attributes(duplicate)
        duplicate = maya.cmds.rename(duplicate, name_utils.find_unique_name(new_name))
        self._duplicates.append(duplicate)

        return duplicate

    def _duplicate_hierarchy(self, xform):
        if xform == self._stop_at_transform:
            self._stop = True
        if self._stop:
            return

        top_duplicate = self._duplicate(xform)
        children = self._get_children(xform)
        if children:
            duplicates = list()
            for child in children:
                if self._only_these_transform and child not in self._only_these_transform:
                    continue
                if self._only_joints:
                    if not maya.cmds.nodeType(child) == 'joint':
                        continue
                duplicate = self._duplicate_hierarchy(child)
                if not duplicate:
                    break
                duplicates.append(duplicate)

                if maya.cmds.nodeType(top_duplicate) == 'joint' and maya.cmds.nodeType(duplicate) == 'joint':
                    if maya.cmds.isConnected('{}.scale'.format(xform), '{}.inverseScale'.format(duplicate)):
                        maya.cmds.disconnectAttr('{}.scale'.format(xform), '{}.inverseScale'.format(duplicate))
                        maya.cmds.connectAttr('{}.scale'.format(top_duplicate), '{}.inverseScale'.format(duplicate))

            if duplicates:
                maya.cmds.parent(duplicates, top_duplicate)

        return top_duplicate
