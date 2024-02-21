from __future__ import annotations

from typing import List

import maya.cmds as cmds

from tp.core import log
from tp.maya import api

from tp.libs.rig.noddle.functions import naming, nodes

logger = log.rigLogger


def joint_chain(start_joint: api.Joint, end_joint: api.Joint | None = None) -> List[api.Joint]:
    """
    Returns the joint chain from the given start joint.

    :param api.Joint start_joint: start joint of the chain.
    :param api.Joint end_joint: end joint of the chain.
    :return: list of joints from given start joint to end joint.
    :rtype: List[api.DagNode]
    """

    if not start_joint:
        return []

    if start_joint == end_joint:
        return [start_joint]

    chain = [start_joint] + list(start_joint.iterateChildren(node_types=(api.OpenMaya.MFn.kJoint,)))
    if not end_joint:
        return chain

    cut_chain = []
    for joint in chain:
        if joint.name() in end_joint.fullPathName().split('|'):
            cut_chain.append(joint)

    return cut_chain


def create_along_curve(
        curve: api.DagNode, amount: int, joint_name: str = 'joint', joint_side: str = 'c', joint_suffix: str = 'jnt',
        delete_curve: bool = False, attach_to_curve: bool = False) -> List[api.Joint]:
    """
    Creates new joints along given curve.

    :param api.DagNode curve: curve to create joints following it.
    :param int amount:
    :param str joint_name: name part for the new joints names.
    :param str joint_side: side part fo the new joints names.
    :param str joint_suffix: suffix part for the new joints names.
    :param bool delete_curve: whether to delete curve after creating the joints.
    :param bool attach_to_curve: whether to attach joints to the curve.
    :return: newly created joints.
    :rtype: List[api.Joint]
    """

    joints = []
    for i in range(amount):
        param = float(i) / float(amount - 1)
        point = cmds.pointOnCurve(curve.fullPathName(), pr=param, top=1)
        jnt = api.node_by_name(cmds.createNode('joint', n=naming.generate_name(joint_name, joint_side, joint_suffix)))
        jnt.setTranslation(api.Vector(*point), space=api.kWorldSpace)
        joints.append(jnt)

    if attach_to_curve:
        pt_on_curve_info = nodes.create('pointOnCurveInfo', joint_name, joint_side, suffix='ptcrv')
        curve.worldSpace[0].connect(pt_on_curve_info.inputCurve)
        pt_on_curve_info.parameter.set(param)
        pt_on_curve_info.turnOnPercentage.set(True)
        pt_on_curve_info.result.position.connect(jnt.translate)

    if delete_curve:
        curve.delete()

    return joints


def create_chain(joint_list: List[api.Joint] | None = None, reverse: bool = False) -> List[api.Joint]:
    """
    Creates joint hierarchy from a list of given joints.

    :param List[api.Joint] or None joint_list: joint to use to create the joint hierarchy.
    :param bool reverse: whether to reverse joint hierarchy.
    :return: joint hierarchy.
    :rtype: List[api.Joint]
    """

    joint_list = joint_list or []
    if reverse:
        joint_list.reverse()
    for i in range(1, len(joint_list)):
        joint_list[i].setParent(joint_list[i - 1])

    return joint_list


def reverse_chain(joint_list: List[api.Joint] | None = None):
    """
    Reverses the given joint chain.

    :param List[api.Joint] or None joint_list: joint hierarchy to reverse.
    """

    joint_list = joint_list or []
    for jnt in joint_list:
        jnt.setParent(None)
    joint_list.reverse()
    create_chain(joint_list)


def validate_rotations(joint_chain: List[api.Joint]) -> bool:
    """
    Returns whether all joints of the given chain have no rotations.

    :param List[api.Joint] joint_chain: list of joints to validate.
    :return: True if all joints are valid; False otherwise.
    :rtype: bool
    """

    is_valid = True
    for joint in joint_chain:
        if joint.rotateX.asFloat() > 0.0:
            logger.warning(f'Non zero rotationX on joint {joint}')
            is_valid = False
        if joint.rotateY.asFloat() > 0.0:
            logger.warning(f'Non zero rotationY on joint {joint}')
            is_valid = False
        if joint.rotateZ.asFloat() > 0.0:
            logger.warning(f'Non zero rotationZ on joint {joint}')
            is_valid = False

    return is_valid


def duplicate_chain(
        new_joint_name: str | List[str], new_joint_side: str, new_joint_suffix: str = 'jnt',
        original_chain: List[api.Joint] | None = None, start_joint: api.Joint | None = None,
        end_joint: api.Joint | None = None, new_parent: api.DagNode | None = None) -> List[api.Joint]:
    """
    Duplicates given joint chain.

    :param str new_joint_name:
    :param str new_joint_side:
    :param str new_joint_suffix:
    :param List[api.Joint] original_chain:
    :param api.Joint or None start_joint:
    :param api.Joint or None end_joint:
    :param api.DagNode or None new_parent:
    :return: duplicated joint chain.
    :rtype: List[api.Joint]
    """

    original_chain = original_chain or joint_chain(start_joint, end_joint=end_joint)
    new_chain = cmds.duplicate([jnt.fullPathName() for jnt in original_chain], po=True, rc=True)
    new_chain = [api.node_by_name(name) for name in new_chain]

    for new_joint in new_chain:
        new_joint.rename(naming.generate_name(new_joint_name, new_joint_side, new_joint_suffix))

    if new_parent:
        new_chain[0].setParent(None if new_parent.name(include_namespace=False) == 'world' else new_parent)

    return new_chain


def create_root_joint(
        name: str = 'root', side: str = 'c', suffix: str = 'jnt', children: List[api.Joint] | None = None,
        parent: api.DagNode | None = None) -> api.Joint:
    """
    Creates root joint.

    :param str name: name part of the joint name.
    :param str side: side part of the joint name.
    :param str suffix: suffix part of the joint name.
    :param List[api.Joint] or None children: optional children joints to parent the root joint.
    :param api.Joint or None parent: optional root joint parent.
    :return: newly created root joint.
    :rtype: api.Joint
    """

    root = api.node_by_name(cmds.createNode('joint', n=naming.generate_name(name, side, suffix)))
    if parent:
        root.setParent(parent)
    for child in children or []:
        child.setParent(root)

    return root


def pole_vector_locator(joint_chain: List[api.Joint]) -> api.DagNode:
    """
    Calculates position vector where the pole vector for the given joint chain should be located,
    creates a new locator and places in the previously calculated pole vector position.

    :param List[api.Joint] joint_chain: joint chain to get pole vector position for.
    :return: pole vector locator.
    :rtype: api.DagNode
    """

    root_jnt_vec = joint_chain[0].translation(space=api.kWorldSpace)
    end_jnt_vec = joint_chain[-1].translation(space=api.kWorldSpace)

    if len(joint_chain) % 2:
        mid_index = (len(joint_chain) - 1) // 2
        mid_jnt_vec = joint_chain[mid_index].translation(space=api.kWorldSpace)
    else:
        prev_jnt_index = len(joint_chain) // 2
        next_jnt_index = prev_jnt_index + 1
        prev_jnt_vec = joint_chain[prev_jnt_index].getTranslation(space=api.kWorldSpace)
        next_jnt_vec = joint_chain[next_jnt_index].getTranslation(space=api.kWorldSpace)
        # find mid-point between joints with close to mid
        mid_jnt_vec = (next_jnt_vec + prev_jnt_vec) * 0.5

    # calculate projection vector
    line = end_jnt_vec - root_jnt_vec
    point = mid_jnt_vec - root_jnt_vec
    scale_value = (line * point) / (line * line)
    project_vec = line * scale_value + root_jnt_vec

    # retrieve chain length
    root_to_mid_len = (mid_jnt_vec - root_jnt_vec).length()
    mid_to_end_len = (end_jnt_vec - mid_jnt_vec).length()
    total_len = root_to_mid_len + mid_to_end_len

    pol_vec_pos = (mid_jnt_vec - project_vec).normal() * total_len + mid_jnt_vec
    pole_locator = api.node_by_name(cmds.spaceLocator(n='polevector_loc')[0])
    pole_locator.setTranslation(pol_vec_pos, space=api.kWorldSpace)

    return pole_locator
