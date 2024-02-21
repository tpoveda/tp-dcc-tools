from __future__ import annotations

import typing

import maya.cmds as cmds

from tp.core import log
from tp.maya import api
from tp.maya.meta import base
from tp.libs.rig.noddle.core import control, asset

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.components.character import Character

logger = log.rigLogger


def list_controls():
    """
    Retrieves all controller nodes within current scene and returns them as control instances.

    :return: list of control nodes.

    """

    controllers = api.nodes_by_type_names('controller')
    transform_nodes = [controller.controllerObject.sourceNode() for controller in controllers]
    found_controls = []
    for transform_node in transform_nodes:
        if not transform_node:
            continue
        try:
            new_control = control.Control(node=transform_node.object())
        except Exception:
            logger.exception(f'Failed to create control instance from {transform_node}')
            continue
        found_controls.append(new_control)

    return found_controls


def get_build_character() -> Character | None:
    """
    Returns the character component of current build.

    :return: build character.
    :rtype: character.Character or None
    """

    from tp.libs.rig.noddle.maya.meta.components import character

    found_character = None
    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No asset set')
        return None

    character_name = current_asset.name if current_asset else None
    all_characters = base.find_meta_nodes_by_class_type(character.Character)

    for character_meta in all_characters:
        if character_meta.characterName.value() == character_name:
            found_character = character_meta
            break

    if found_character is None:
        logger.error(f'Failed to find build character with name "{character_name}"!')

    return found_character


def param_control_locator(
        side: str, anchor_transform: api.DagNode, move_axis: str = 'x', multiplier: float = 1.0) -> api.DagNode:
    """
    Returns the position where the parameters control should be loated and creates a locator in that position.

    :param str side: side where the param control is located.
    :param api.DagNode anchor_transform: anchor node where the param locator will be placed initially.
    :param str move_axis: axis to move param locator along.
    :param float multiplier: optional position multipler along given axis.
    :return: newly created param control locator.
    :rtype: api.DagNode
    """

    current_char = get_build_character()
    clamped_size = current_char.clamped_size() if current_char else 1.0

    new_locator = api.node_by_name(cmds.spaceLocator(n='param_loc')[0])
    end_joint_vec = anchor_transform.translation(api.kWorldSpace)
    side_multiplier = -1 if side.lower() == 'r' and move_axis else 1
    if 'x' in move_axis:
        end_joint_vec.x += clamped_size * 0.25 * side_multiplier * multiplier
    if 'y' in move_axis:
        end_joint_vec.y += clamped_size * 0.25 * multiplier
    if 'z' in move_axis:
        end_joint_vec.z += clamped_size * 0.25 * side_multiplier * multiplier
    new_locator.setTranslation(end_joint_vec, space=api.kWorldSpace)

    return new_locator
