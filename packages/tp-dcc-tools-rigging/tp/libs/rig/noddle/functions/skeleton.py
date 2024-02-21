from __future__ import annotations

import time

import maya.cmds as cmds

from tp.core import log
from tp.maya import api
from tp.maya.meta import base, metaproperty
from tp.maya.cmds.nodes import helpers

from tp.preferences.interfaces import noddle
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import rig
from tp.libs.rig.noddle.meta import layers, properties, rig as meta_rig
from tp.libs.rig.noddle.functions import baking

logger = log.rigLogger


def characterize_skeleton(
        joint: api.Joint, name, freeze_skeleton: bool = True) -> rig.Rig | None:
    """
    Set up meta node graph for a character and loads all rigging necessary information into a skeleton within Maya scene.
    Zero translate and rotate values ar saved at this time and stored on custom attributes on each joint.

    :param api.Joint joint: Maya scene joint that is part of the skeleton hierarchy for a character.
    :param str or None name: name for the rig.
    :param bool freeze_skeleton:
    :return: rig node.
    :rtype: NoddleRig or None
    """

    start_time = time.perf_counter()
    prefs = noddle.noddle_interface()

    clean_skeleton(joint)

    found_meta_rig = None
    skeleton_layer = base.find_meta_node_from_node(joint, check_type=layers.NoddleSkeletonLayer)
    if skeleton_layer:
        found_meta_rig = base.find_meta_node_from_node(
            skeleton_layer, check_type=meta_rig.NoddleRig, attribute=base.MPARENT_ATTR_NAME)
    if found_meta_rig:
        logger.warning(
            f'This Skeleton is already characterized: {found_meta_rig.name()}')
        return rig.rig_from_node(found_meta_rig)

    logger.info(f'Characterizing "{name}" from "{joint.fullPathName(partial_name=True)}"')

    skeleton_root = root_joint(joint)
    replace_joints = replace_transforms_with_joints(
        [skeleton_root] + list(skeleton_root.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kTransform,))))
    if not skeleton_root.exists():
        skeleton_root = root_joint(replace_joints[-1])

    rig_namespace = skeleton_root.namespace()
    root_parent = skeleton_root.parent()

    rig_node = rig.Rig()
    rig_node.start_session(name=name, namespace=rig_namespace)

    if root_parent and is_animated([root_parent], filter_joints=False):
        skeleton_root.setParent(None)
        temp_constraint = cmds.parentConstraint(root_parent.fullPathName(), skeleton_root.fullPathName(), mo=False)
        baking.bake_objects(
            [skeleton_root], translate=True, rotate=True, scale=True, use_settings=False, simulation=False)
        cmds.delete(temp_constraint)

    # root_folder = path.dirname(cmds.file(query=True, sceneName=True))
    # if prefs.check_project():
    #     raise NotImplementedError
    # rig_node.attribute(consts.ROOT_PATH_ATTR).set(root_folder)

    rig_node.setup_skeleton(skeleton_root)

    joints = [skeleton_root] + list(skeleton_root.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kJoint,)))
    for joint in joints:
        setup_joint(joint)

    logger.info(f'Characterize completed in {time.perf_counter() - start_time} seconds')

    return rig_node


def root_joint(node: api.Joint) -> api.Joint:
    """
    Recursive function that traverse up the hierarchy until finding the first joint that does not have a joint parent.

    :param api.Joint node: Maya scene joint that is part of a skeleton hierarchy.
    :return: top level joint of a skeleton.
    :rtype: api.Joint
    """

    return api.node_by_name(helpers.root_node(node.fullPathName(), 'joint'))


def is_animated(nodes: list[api.DagNode | api.Joint], filter_joints: bool = True, recursive: bool = True):
    """
    Checks whether given joints are animated. Animated in this case means that the object is being moved by animation
    keys, constraints or any motion up in hierarchy.

    :param list[api.DagNode | api.Joint] nodes: DAG nodes to check.
    :param bool filter_joints: whether to only look at joint objecs in the given nodes.
    :param bool recursive: whether to recursively check hierarchy.
    :return: True if any of the joints are animated; False otherwise.
    :rtype: bool
    """

    if filter_joints:
        nodes = [x for x in nodes if x and x.apiType() == api.kNodeTypes.kJoint]
    for node in nodes:
        node_name = node.fullPathName()
        # TODO: do this check using OpenMaya
        if cmds.listConnections(node_name, type='animCurve') or cmds.listConnections(
                node_name, type='constraint', s=True, d=False) or cmds.listConnections(
            node_name, type='animLayer', s=False, d=True):
            return True
        else:
            if recursive:
                return is_animated([node.parent()])
            else:
                return False

    return False


def clean_skeleton(node: api.Joint):
    """
    Clean all connections to a skeleton to remove any links to meta node graph and set all scale values to 1.0

    :param api.Joint node: Maya scene joint that is part of a skeleton hierarchy.
    """

    root_jnt = root_joint(node)
    joints = [root_jnt] + list(root_jnt.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kJoint,)))
    for joint in joints:
        if not joint.attribute('scale').isLocked:
            joint.attribute('scale').set([1.0, 1.0, 1.0])
        joint_name = joint.fullPathName()
        for attr in cmds.listAttr(joint_name, ud=True) or []:
            attr_name = f'{joint_name}.{attr}'
            if not cmds.attributeQuery(attr, node=joint_name, exists=True):
                continue
            if not cmds.listConnections(attr_name, s=True, d=False, p=True):
                cmds.deleteAttr(attr_name)


def replace_transforms_with_joints(nodes: list[api.DagNode | api.Joint]) -> list[api.Joint]:
    """
    Runs through a list of scene objects and replaces any transforms with joint objects.

    :param list[api.DagNode] nodes: Maya scene objects to operate on.
    :return: copy of given nodes list with transforms replaced with the created joints.
    :rtype: list[api.Joint]
    """

    result = nodes
    for node in nodes:
        if not node.shapes():
            continue
        parent_node = node.parent()
        children = node.children(node_types=(api.kNodeTypes.kTransform,))
        name = node.name()
        cmds.select(clear=True)
        replace_joint = api.factory.create_dag_node('temp_joint', node_type='joint')
        replace_joint.setParent(parent_node)
        replace_joint.attribute('translate').set(node.attribute('translate').value())
        replace_joint.attribute('rotate').set(node.attribute('rotate').value())
        for child in children:
            child.setParent(child)
        node.delete()
        replace_joint.rename(name)
        result.remove(node)
        result.append(replace_joint)

    return result


def setup_joint(joint: api.Joint):
    """
    Connects the given joint to the joints meta node and adds an Export Property, adds bind attributes, sets values
    to the current translation and rotation values and enforces [1.0, 1.0, 1.0] scale bind pose.

    :param api.Joint joint: Maya scene joint node to set up.
    """

    metaproperty.add_property(joint, properties.ExportProperty)
    if not joint.hasAttribute(consts.NODDLE_BIND_TRANSLATE_ATTR):
        joint.addAttribute(consts.NODDLE_BIND_TRANSLATE_ATTR, type=api.kMFnNumeric3Double)
    if not joint.hasAttribute(consts.NODDLE_BIND_ROTATE_ATTR):
        joint.addAttribute(consts.NODDLE_BIND_ROTATE_ATTR, type=api.kMFnNumeric3Double)
    joint.attribute(consts.NODDLE_BIND_TRANSLATE_ATTR).set(joint.attribute('translate').value())
    joint.attribute(consts.NODDLE_BIND_ROTATE_ATTR).set(joint.attribute('rotate').value())
    if not joint.attribute('scale').isLocked:
        joint.attribute('scale').set([1.0, 1.0, 1.0])
