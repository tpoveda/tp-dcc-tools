from __future__ import annotations

from typing import Sequence

import maya.cmds as cmds

from tp.core import log
from tp.maya.cmds import gui
from tp.maya.cmds.nodes import attributes

logger = log.tpLogger


def joints(nodes: list[str], children: bool = True) -> list[str]:
    """
    Filters all joints from given list of nodes without duplicates.

    :param list[str] nodes: list of nodes to filter joints from.
    :param bool children: whether to also return children joints of filtered joints.
    :return: list of joints.
    :rtype: list[str]
    """

    found_joints = cmds.ls(nodes, type='joint', long=True)
    if children:
        child_joints = cmds.listRelatives(nodes, children=True, type='joint', fullPath=True, allDescendents=True)
        if child_joints:
            found_joints = list(set(found_joints).union(set(child_joints)))

    return found_joints


def selected_joints(children: bool = True) -> list[str]:
    """
    Returns all selected joints.

    :param bool children: whether to also return children joints of selected joints.
    :return: list of selected joints.
    :rtype: list[str]
    """

    found_joints = cmds.ls(selection=True, long=True)
    return joints(found_joints, children=children)


def joint_chains(
        joint_names: list[str], ignore_connected_joints: bool = True,
        filter_type: str = 'joint') -> tuple[list[list[str]], list[str]]:
    """
    Checks the given list of joints for chans and returns a list of chains, each branch being a separated chain.

    :param list[str] joint_names: list of Maya joint full path names.
    :param bool ignore_connected_joints: whether to skip any joints with keyframes, connections, constraints or locked
        attributes
    :param str filter_type: type of node to filter by ('transform' or 'joint').
    :return: list containing a list for each joint chain found.
    :rtype: tuple[list[list[str]], list[str]]
    ..note:: each member of the joint chains must be in the given list of nodes.
    """

    joints_to_ignore: list[str] = []
    chain_lists: list[list[str]] = []
    end_joints: list[str] = []
    already_recorded_joints: list[str] = []

    if ignore_connected_joints:
        joints_to_ignore = attributes.locked_connected_attributes_for_nodes(
            joint_names, attributes=attributes.MAYA_TRANSFORM_ATTRS, keyframes=True, constraints=True)[0]
        if joints_to_ignore:
            joint_names = [x for x in joint_names if x not in joints_to_ignore]

    # Retrieve all joints.
    for joint in joint_names:
        end = True
        child_joints = cmds.listRelatives(joint, children=True, type=filter_type, fullPath=True)
        if child_joints:
            for child_joint in child_joints:
                if child_joint in joint_names:
                    end = False
        if not child_joints or end:
            end_joints.append(joint)

    # Loop backward all joints.
    for end_joint in end_joints:
        joints_chain: list[str] = [end_joint]
        already_recorded_joints.append(end_joint)
        last_joint_parent = cmds.listRelatives(end_joint, parent=True, type=filter_type, fullPath=True)\

        # Next chain has no parent.
        if not last_joint_parent:
            chain_lists.append(joints_chain)
            continue

        # Next chain parent is not in the joints list.
        last_joint_parent = last_joint_parent[0]
        if last_joint_parent not in joint_names:
            chain_lists.append(joints_chain)
            continue

        while last_joint_parent:
            joints_chain.append(last_joint_parent)
            already_recorded_joints.append(last_joint_parent)
            parent_joint = cmds.listRelatives(last_joint_parent, parent=True, type=filter_type, fullPath=True)
            if parent_joint:
                parent_joint = parent_joint[0]
            if not parent_joint:
                last_joint_parent = None
            elif parent_joint not in joint_names or parent_joint in already_recorded_joints:
                last_joint_parent = None
            else:
                last_joint_parent = parent_joint

        chain_lists.append(joints_chain)

    for chain in chain_lists:
        chain.reverse()

    return chain_lists, joints_to_ignore


def filter_child_joints(joint_names: list[str]) -> list[str]:
    """
    Retrieve all child joints under the given list of joints in the hierarchy.

    :param list[str] joint_names: list of joints to get child joints from.
    :return: list of the given joints with all their child joints (without duplicates).
    :rtype: list[str]
    """

    all_joints: list[str] = []
    for joint in joint_names:
        all_joints.append(joint)
        all_joints.extend(cmds.listRelatives(joint, allDescendents=True, type='joint', fullPath=True) or [])

    return list(set(all_joints))


def align_joint_to_parent(joint: str):
    """
    Aligns given joint to its parent.
    Uses orient constraint (while temporally un-parenting children) to re-orient the joint to match parent orientation.
    Freezes joint transforms before re-parenting children.

    :param str joint: joint to orient to its parent.
    """

    children = cmds.listRelatives(joint, children=True, fullPath=True)
    parent = cmds.listRelatives(joint, parent=True, fullPath=True)
    if children:
        children = cmds.parent(children, world=True)
    cmds.delete(cmds.orientConstraint(parent[0], joint, maintainOffset=False))
    cmds.makeIdentity(joint, apply=True, r=True)
    if children:
        cmds.parent(children, joint)


def align_joints_to_parent(joint_names: list[str]):
    """
    Aligns given joints to its parent.
    Uses orient constraint (while temporally un-parenting children) to re-orient the joint to match parent orientation.
    Freezes joint transforms before re-parenting children.

    :param list[str] joint_names: list of joints to orient to their parents.
    """

    [align_joint_to_parent(joint) for joint in joint_names]


def align_selected_joints_to_parent():
    """
    Aligns selected joints to its parent.
    Uses orient constraint (while temporally un-parenting children) to re-orient the joint to match parent orientation.
    Freezes joint transforms before re-parenting children.
    """

    current_selected_joints = cmds.ls(selection=True, exactType='joint', long=True)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    align_joints_to_parent(current_selected_joints)
    cmds.select(current_selected_joints, replace=True)

    logger.debug('Joints aligned to their parent successfully!')


def edit_component_lra(flag: bool = True):
    """
    Makes the local rotation axis editable/no editable in component mode.

    :param bool flag: If True, local rotation axis is editable in component mode; if False, disables it and exit to
        object mode.
    """

    if flag:
        cmds.selectMode(component=True)
        cmds.selectType(localRotationAxis=True)
        current_panel = gui.panel_under_pointer_or_focus(viewport3d=True, message=False)
        cmds.modelEditor(current_panel, edit=True, handles=True)
    else:
        cmds.selectType(localRotationAxis=False)
        cmds.selectMode(object=True)


def zero_joints_rotation_axis(joint_names: list[str], zero_children: bool = True):
    """
    Zeroes out the joint rotation of given joints.

    :param list[str] joint_names: list of joints.
    :param bool zero_children: whether to zero out also rotation axis of child joints.
    """

    if zero_children:
        joint_names = filter_child_joints(joint_names)
    for joint in joint_names:
        cmds.joint(joint, edit=True, zeroScaleOrient=True)


def zero_selected_joints_rotation_axis(zero_children: bool = True):
    """
    Zeroes out the joint rotation of selected joints.

    :param bool zero_children: whether to zero out also rotation axis of child joints.
    """

    current_selected_joints = cmds.ls(selection=True, exactType='joint', long=True)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    zero_joints_rotation_axis(current_selected_joints, zero_children=zero_children)
    cmds.select(current_selected_joints, replace=True)

    logger.debug('Joints rotations axis zeroed successfully!')


def rotate_joint_local_rotation_axis(
        joint: Sequence[str], rotation: Sequence[float, float, float]):
    """
    Rotates the local rotation axis of given `joint` by given `rotation`.

    :param str joint: joint to rotate local rotation axis of.
    :param Sequence[float, float, float] rotation: XYZ rotationa in degrees.
    """

    cmds.rotate(rotation[0], rotation[1], rotation[2], f'{joint}.rotateAxis', objectSpace=True, forceOrderXYZ=True)
    if cmds.objectType(joint) == 'joint':
        cmds.joint(joint, edit=True, zeroScaleOrient=True)


def rotate_joints_local_rotation_axis(
        joint_names: Sequence[str], rotation: Sequence[float, float, float]):
    """
    Rotates the local rotation axis of given `joints` by given `rotation`.

    :param Sequence[str] joint_names: joints to rotate local rotation axis of.
    :param Sequence[float, float, float] rotation: XYZ rotationa in degrees.
    """

    for joint in joint_names:
        rotate_joint_local_rotation_axis(joint, rotation)


def rotate_selected_joints_local_rotation_axis(rotation: Sequence[float, float, float], include_children: bool = True):
    """
    Rotates the local rotation axis of current selected joints by given `rotation`.

    :param Sequence[float, float, float] rotation: XYZ rotation in degrees.
    :param bool include_children: whether to include joints hierarchy.
    """

    current_selected_joints = selected_joints(children=include_children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    rotate_joints_local_rotation_axis(current_selected_joints, rotation)


def set_joints_draw_style_to_bone(joint_names: list[str]):
    """
    Sets given joints draw style to `Bone` (default mode).

    :param list[str] joint_names: list of joints to set draw style of.
    """

    for joint in joint_names:
        cmds.setAttr(f'{joint}.drawStyle', 0)


def set_selected_joints_draw_style_to_bone(children: bool = True):
    """
    Sets selected joints draw style to `Bone` (default mode).

    :param bool children: whether to also change draw style of children joints.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    set_joints_draw_style_to_bone(current_selected_joints)


def set_joints_draw_style_to_multi_box(joint_names: list[str]):
    """
    Sets given joints draw style to `Multi-Child Box` (default mode).

    :param list[str] joint_names: list of joints to set draw style of.
    """

    for joint in joint_names:
        cmds.setAttr(f'{joint}.drawStyle', 1)


def set_selected_joints_draw_style_to_multi_box(children: bool = True):
    """
    Sets selected joints draw style to `Multi-Child Box` (default mode).

    :param bool children: whether to also change draw style of children joints.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    set_joints_draw_style_to_multi_box(current_selected_joints)


def set_joints_draw_style_to_none(joint_names: list[str]):
    """
    Sets given joints draw style to `None` (default mode).

    :param list[str] joint_names: list of joints to set draw style of.
    """

    for joint in joint_names:
        cmds.setAttr(f'{joint}.drawStyle', 2)


def set_selected_joints_draw_style_to_none(children: bool = True):
    """
    Sets selected joints draw style to `None` (default mode).

    :param bool children: whether to also change draw style of children joints.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    set_joints_draw_style_to_none(current_selected_joints)


def set_joints_draw_style_to_joint(joint_names: list[str]):
    """
    Sets given joints draw style to `Joint` (default mode).

    :param list[str] joint_names: list of joints to set draw style of.
    """

    for joint in joint_names:
        cmds.setAttr(f'{joint}.drawStyle', 3)


def set_selected_joints_draw_style_to_joint(children: bool = True):
    """
    Sets selected joints draw style to `Joint` (default mode).

    :param bool children: whether to also change draw style of children joints.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return

    set_joints_draw_style_to_joint(current_selected_joints)


def set_joints_local_rotation_axis_display(joint_names: list[str], display: bool, children: bool = True):
    """
    Shows/Hides local rotation axis of selected joints.

    :param list[str] joint_names: list of joints to set local rotation axis visibility of.
    :param bool display: whether to show/hide selected joints.
    :param bool children: whether to also set local rotation visibility of children joints.
    """

    if not joint_names:
        logger.warning('No joints given.')
        return
    if children:
        joint_names = filter_child_joints(joint_names)
    for joint in joint_names:
        cmds.setAttr(f'{joint}.displayLocalAxis', display)
    logger.debug(f'Joints local rotation axis visibility set to "{display}"')


def set_selected_joints_local_rotation_axis_display(display: bool, children: bool = True):
    """
    Shows/Hides local rotation axis of selected joints.

    :param bool display: whether to show/hide selected joints.
    :param bool children: whether to also set local rotation visibility of children joints.
    """

    current_selected_joints = cmds.ls(selection=True, long=True, exactType='joint')
    set_joints_local_rotation_axis_display(current_selected_joints, display, children=children)

    # Make sure handles are visible in current view panel.
    current_panel = gui.panel_under_pointer_or_focus(viewport3d=True, message=False)
    cmds.modelEditor(current_panel, edit=True, handles=True)


def mirror_joint(joint_name: str, axis: str, search_replace: tuple[list[str]] = (['_L', '_R'], ['_lft', '_rgt']),
                 mirror_behavior: bool = True) -> list[str]:
    """
    Mirror given joint along given axis.

    :param str joint_name: name of the Maya joint to mirror.
    :param str axis: axis to mirror across ('X', 'Y' or 'Z').
    :param tuple[list[str]] search_replace: tuple with list of names to search and replace mirror joint names with.
    :param bool mirror_behavior: whether to mirror joint with a mirror behavior.
    :return: list of mirrored joints.
    :rtype: list[str]
    """

    joints_to_mirror = [joint_name]
    joints_to_mirror.extend(cmds.listRelatives(joint_name, allDescendents=True, type='joint') or [])

    search_list: list[str, str] = ['', '']
    for mirror_map in search_replace:
        for joint_to_mirror in joints_to_mirror:
            if mirror_map[0] in joint_name:
                search_list = mirror_map
                break
            elif mirror_map[1] in joint_name:
                mirror_map.reverse()
                search_list = mirror_map
                break

    axis = axis.lower()
    if axis == 'x':
        mirrored_joints = cmds.mirrorJoint(
            joint_name, mirrorYZ=True, mirrorBehavior=mirror_behavior, searchReplace=search_list)
    elif axis == 'y':
        mirrored_joints = cmds.mirrorJoint(
            joint_name, mirrorXZ=True, mirrorBehavior=mirror_behavior, searchReplace=search_list)
    else:
        mirrored_joints = cmds.mirrorJoint(
            joint_name, mirrorXY=True, mirrorBehavior=mirror_behavior, searchReplace=search_list)

    return mirrored_joints


def mirror_joints(joint_names: list[str], axis: str,
                  search_replace: tuple[list[str]] = (['_L', '_R'], ['_lft', '_rgt']),
                  mirror_behavior: bool = True) -> list[str]:
    """
    Mirror given joints along give axis.

    :param list[str] joint_names: name of the Maya joints to mirror.
    :param str axis: axis to mirror across ('X', 'Y' or 'Z').
    :param tuple[list[str]] search_replace: tuple with list of names to search and replace mirror joint names with.
    :param bool mirror_behavior: whether to mirror joint with a mirror behavior.
    :return: list of mirrored joints.
    :rtype: list[str]
    """

    mirrored_joints: list[str] = []
    for joint_name in joint_names:
        mirrored_joints.extend(
            mirror_joint(joint_name, axis, search_replace=search_replace, mirror_behavior=mirror_behavior))

    return mirrored_joints


def mirror_selected_joints(
        axis: str, search_replace: tuple[list[str]] = (['_L', '_R'], ['_lft', '_rgt']),
        mirror_behavior: bool = True) -> list[str]:
    """
    Mirrors selected joints along give axis.

    :param str axis: axis to mirror across ('X', 'Y' or 'Z').
    :param tuple[list[str]] search_replace: tuple with list of names to search and replace mirror joint names with.
    :param bool mirror_behavior: whether to mirror joint with a mirror behavior.
    :return: list of mirrored joints.
    :rtype: list[str]
    """

    current_selected_joints = cmds.ls(sl=True, type='joint', long=True)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return []

    return mirror_joints(current_selected_joints, axis, search_replace=search_replace, mirror_behavior=mirror_behavior)


def selected_joints_scale_compensate(compensate: bool = True, children: bool = False):
    """
    Turns the segment scale compensate on or off for the selected joints.

    :param bool compensate: True to enable scale compensate; False to disable it.
    :param bool children: whether to affect children.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return []

    for joint_name in current_selected_joints:
        cmds.setAttr(f'{joint_name}.segmentScaleCompensate', compensate)


def set_selected_joints_radius(radius: float, children: bool = False):
    """
    Sets the joint radius for selected joints.

    :param float radius: joint radius.
    :param bool children: whether to include all child joints while adjusting the radius.
    """

    current_selected_joints = selected_joints(children=children)
    if not current_selected_joints:
        logger.warning('No joints found. Please select some joints.')
        return []

    for joint_name in current_selected_joints:
        cmds.setAttr(f'{joint_name}.radius', radius)
