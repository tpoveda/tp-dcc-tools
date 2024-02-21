from __future__ import annotations

import maya.cmds as cmds

from tp.core import log
from tp.common.python import helpers
from tp.maya import api
from tp.maya.meta import base, metaproperty
from tp.maya.cmds.nodes import helpers

from tp.libs.rig.freeform import consts
from tp.libs.rig.freeform.meta import character, properties, skeleton

logger = log.rigLogger


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


def setup_joint(joint: api.Joint, joints: skeleton.FreeformJoints):
    """
    Connects the given joint to the joints meta node and adds an Export Property, adds bind attributes, sets values
    to the current translation and rotation values and enforces [1.0, 1.0, 1.0] scale bind pose.

    :param api.Joint joint: Maya scene joint node to set up.
    :param FreeformJoints joints: freeform joints meta node instance.
    """

    joint.connect('message', joints.attribute(consts.JOINTS_ATTR).nextAvailableDestElementPlug())
    metaproperty.add_property(joint, properties.ExportProperty)
    if not joint.hasAttribute(consts.BIND_TRANSLATE_ATTR):
        joint.addAttribute(consts.BIND_TRANSLATE_ATTR, type=api.kMFnNumeric3Double)
    if not joint.hasAttribute(consts.BIND_ROTATE_ATTR):
        joint.addAttribute(consts.BIND_ROTATE_ATTR, type=api.kMFnNumeric3Double)
    joint.attribute(consts.BIND_TRANSLATE_ATTR).set(joint.attribute('translate').value())
    joint.attribute(consts.BIND_ROTATE_ATTR).set(joint.attribute('rotate').value())
    if not joint.attribute('scale').isLocked:
        joint.attribute('scale').set([1.0, 1.0, 1.0])


def setup_joints(characer_node: character.FreeformCharacter):
    """
    Runs through all joints in the given character skeleton to find any joints that are not part of the character
    network, adding any new ones and adding default markup to them.

    :param FreeformCharacter characer_node: freeform character rig meta node instance.
    """

    character_node = base.create_meta_node_from_node(characer_node)
    print('gogogogo', character_node)


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


def skeleton_dict(joint: api.Joint) -> dict:
    """
    Creates a dictionary of all region markup chains on a skeleton, using the direct connection from Regions meta node
    that exist on the skeleton, otherwise it will search every joint for the RigMarkupProperty.

    :param api.Joint joint: Maya scene joint that is part of a skeleton.
    :return: all joints marked up by RigMarkupProperties organized by region and side.
    :rtype: dict
    """

    joints_group = base.find_meta_node_from_node(joint, check_type=skeleton.FreeformJoints)
    character_node = base.find_meta_node_from_node(
        joints_group, check_type=character.FreeformCharacter, attribute=base.MPARENT_ATTR_NAME) if joints_group else None
    if not character_node:
        logger.warning('No character node found')
        return {}

    result = {}
    regions_node = character_node.upstream(skeleton.FreeformRegions)		# type: skeleton.FreeformRegions

    if regions_node:
        for region_markup_node in regions_node.markup_nodes():
            side = region_markup_node.attribute(consts.SIDE_ATTR).value()
            result.setdefault(side, {})
            result[side].setdefault(region_markup_node.attribute(consts.REGION_ATTR).value()), {}
            result[side][region_markup_node.attribute(consts.REGION_ATTR).value()][region_markup_node.attribute(
                consts.TAG_ATTR).value()] = cmds.listConnections(f'{region_markup_node.fullPathName()}.message', type='joint')[0]
    else:
        root_jnt = root_joint(joint)
        joints = [root_jnt] + list(root_jnt.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kJoint,)))
        for joint in joints:
            property_dict = metaproperty.properties_dict(joint)
            rig_markup_property_list = property_dict.get(properties.RegionMarkupProperty)
            if rig_markup_property_list:
                for rig_markup in rig_markup_property_list:
                    side = rig_markup.data()[consts.SIDE_ATTR]
                    result.setdefault(side, {})
                    result[side].setdefault(rig_markup.data()[consts.REGION_ATTR], {})
                    result[side][rig_markup.data()[consts.REGION_ATTR][rig_markup.data()[consts.TAG_ATTR]]] = joint

        clean_skeleton_dict(result)

    return result


def clean_skeleton_dict(skeleton_dict_to_clean: dict):
    """
    Validates that all regions have both a root and end, removing any orphaned entries and associated markup properties
    that do not.

    :param dict[str, str] skeleton_dict_to_clean: a skeleton dictionary created by skeleton_dict() function.
    """

    items_to_remove = {}
    for side, side_dict in skeleton_dict_to_clean.items():
        for region, region_dict in side_dict.items():
            root_jnt = region_dict.get('root')
            end_joint = region_dict.get('end')
            if not (root_jnt and end_joint):
                items_to_remove[side] = region
                orphan_joint = root_jnt if root_jnt else end_joint
                property_dict = metaproperty.properties_dict(orphan_joint)
                rig_markup_list = property_dict.get(properties.RegionMarkupProperty)
                for rig_markup in rig_markup_list:
                    if rig_markup.get('side') == side and rig_markup.get('region') == region:
                        rig_markup.node.delete()

    for side, region in items_to_remove.items():
        del skeleton_dict_to_clean.get(side)[region]
