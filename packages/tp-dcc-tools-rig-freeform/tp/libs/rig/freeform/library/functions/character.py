from __future__ import annotations

import time

import maya.cmds as cmds

from tp.core import log
from tp.common.python import path
from tp.preferences.interfaces import freeform
from tp.maya import api
from tp.maya.meta import base, metaproperty
from tp.libs.rig.freeform import consts

from tp.libs.rig.freeform.library.functions import skeleton, baking
from tp.libs.rig.freeform.meta import character, mesh, properties, rig as meta_rig, skeleton as meta_skeleton

logger = log.rigLogger


def characterize_skeleton(
        joint: api.Joint, name: str | None = None, update_ui: bool = True,
        freeze_skeleton: bool = True) -> character.FreeformCharacter | None:
    """
    Set up meta node graph for a character and loads all rigging necessary information into a skeleton within Maya scene.
    Zero translate and rotate values ar saved at this time and stored on custom attributes on each joint.

    :param api.Joint joint: Maya scene joint that is part of the skeleton hierarchy for a character.
    :param str or None name: optional name for the character, if not given the user will be prompted to enter one.
    :param bool update_ui:
    :param bool freeze_skeleton:
    :return: character node.
    :rtype: character.FreeformCharacter or None
    """

    # import here to avoid cyclic imports
    from tp.libs.rig.freeform.library.tools import rig

    start_time = time.perf_counter()
    prefs = freeform.freeform_interface()

    skeleton.clean_skeleton(joint)

    character_node = None
    joints_group = base.find_meta_node_from_node(joint, check_type=meta_skeleton.FreeformJoints)
    if joints_group:
        character_node = base.find_meta_node_from_node(
            joints_group, check_type=character.FreeformCharacter, attribute=base.MPARENT_ATTR_NAME)
    if character_node:
        logger.warning(
            f'This Skeleton is already characterized: {character_node.attribute(consts.CHARACTER_NAME_ATTR).value()}')
        return character_node

    if not name:
        result = cmds.promptDialog(title='Characterize Skeleton', message='Enter Name:', button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            name = cmds.promptDialog(query=True, text=True)
        else:
            return None

    logger.info(f'Characterizing "{name}" from "{joint.fullPathName(partial_name=True)}"')

    skeleton_root = skeleton.root_joint(joint)
    replace_joints = skeleton.replace_transforms_with_joints(
        [skeleton_root] + list(skeleton_root.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kTransform,))))
    if not skeleton_root.exists():
        skeleton_root = skeleton.root_joint(replace_joints[-1])

    character_namespace = skeleton_root.namespace()
    root_parent = skeleton_root.parent()

    character_node = character.FreeformCharacter(name=name)
    character_node.renameNamespace(character_namespace)
    character_node.root_transform().renameNamespace(character_namespace)

    root_folder = path.dirname(cmds.file(query=True, sceneName=True))
    if prefs.check_project():
        raise NotImplementedError
    character_node.attribute(consts.ROOT_PATH_ATTR).set(root_folder)

    character_rig = meta_rig.FreeformRig(
        name='rig_core', parent=character_node, character_group=character_node.root_transform())
    character_rig.renameNamespace(character_namespace)
    character_skeleton = meta_skeleton.FreeformSkeleton(name='skeleton_core', parent=character_node)
    character_skeleton.renameNamespace(character_namespace)
    character_joints = meta_skeleton.FreeformJoints(name='joints_core', parent=character_skeleton, root=skeleton_root)
    character_joints.renameNamespace(character_namespace)
    character_regions = meta_skeleton.FreeformRegions(name='regions_core', parent=character_node)
    character_regions.renameNamespace(character_namespace)
    character_meshes = mesh.FreeformMeshes(
        name='meshes_core', parent=character_node, group_name=f'{name}_meshes',
        character_group=character_node.root_transform())
    character_meshes.renameNamespace(character_namespace)

    if root_parent and skeleton.is_animated([root_parent], filter_joints=False):
        skeleton_root.setParent(None)
        temp_constraint = cmds.parentConstraint(root_parent.fullPathName(), skeleton_root.fullPathName(), mo=False)
        baking.bake_objects(
            [skeleton_root], translate=True, rotate=True, scale=True, use_settings=False, simulation=False)
        cmds.delete(temp_constraint)

    joints = [character_joints.root_joint] + list(character_joints.root_joint.iterateChildren(
        recursive=True, node_types=(api.kNodeTypes.kJoint,)))
    for joint in joints:
        skeleton.setup_joint(joint, character_joints)

    character_joints.root_joint.setParent(character_node.root_transform())

    auto_freeze_skeleton = prefs.auto_freeze_skeleton()
    if auto_freeze_skeleton and freeze_skeleton:
        freeze_time = time.perf_counter()
        rig.freeze_xform_rig(character_node)
        logger.info(f'Froze skeleton in {time.perf_counter() - freeze_time} seconds')

    logger.info(f'Characterize completed in {time.perf_counter() - start_time} seconds')

    return character_node


def delete_character(character_node: api.DGNode, move_namespace: str | None = None):
    """
    Deletes the given character from the Maya scene and clean up it's meta node graph.

    :param character.FreeformCharacter character_node: character meta node instance.
    :param str | None move_namespace:
    """

    found_character: character.FreeformCharacter = base.create_meta_node_from_node(character_node)
    character_group = found_character.root_transform()

    hik_property = metaproperty.property(character_node, properties.HIKProperty)
    if hik_property is not None:
        hik_property.delete()

    namespace = character_group.namespace()
    character_group.delete()
    if namespace:
        pass

    base.net


