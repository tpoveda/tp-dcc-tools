from __future__ import annotations

import typing
from typing import Iterator

import maya.cmds as cmds

from tp.core import log
from tp.maya import api
from tp.maya.meta import base
from tp.common.python import helpers

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import asset, rig, nodes, errors

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.rig import NoddleRig

logger = log.rigLogger


def list_controls() -> dict[str, nodes.ControlNode]:
    """
    Generator function that yields all controls of current asset rig.

    :return: iterated rig controls.
    :rtype: dict[str, nodes.ControlNode]
    """

    build_rig = get_build_rig()
    if not build_rig:
        return

    found_controls: dict[str, nodes.ControlNode] = {}
    for component in build_rig.iterate_components():
        rig_layer = component.rig_layer()
        if not rig_layer:
            continue
        for control in rig_layer.iterate_controls(recursive=True):
            found_controls[f'{component.name()}:{component.side()}:{control.id()}'] = control

    return found_controls


def get_build_rig() -> rig.Rig | None:
    """
    Returns the rig of current build asset.

    :return: build rig.
    :rtype: rig.Rig or None
    """

    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No asset set')
        return None

    found_rig: rig.Rig | None = None
    asset_name = current_asset.name if current_asset else None
    for iterated_rig in iterate_scene_rigs():
        if iterated_rig.name() == asset_name:
            found_rig = iterated_rig
            break

    if found_rig is None:
        logger.error(f'Failed to find build rig with name "{asset_name}"!')

    return found_rig


def param_control_locator(
        side: str, anchor_transform: api.DagNode, move_axis: str = 'x', multiplier: float = 1.0) -> api.DagNode:
    """
    Returns the position where the parameters control should be located and creates a locator in that position.

    :param str side: side where the param control is located.
    :param api.DagNode anchor_transform: anchor node where the param locator will be placed initially.
    :param str move_axis: axis to move param locator along.
    :param float multiplier: optional position multipler along given axis.
    :return: newly created param control locator.
    :rtype: api.DagNode
    """

    current_rig = get_build_rig()
    clamped_size = current_rig.clamped_size() if current_rig else 1.0

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


def iterate_scene_rig_meta_nodes() -> Iterator[NoddleRig]:
    """
    Generator function that iterates over all rig meta node instances within the current scene.

    :return: iterated scene rig meta node instances.
    :rtype: Iterator[NoddleRig]
    """

    for found_meta_rig in base.find_meta_nodes_by_class_type(consts.RIG_TYPE):
        yield found_meta_rig


def iterate_scene_rigs() -> Iterator[rig.Rig]:
    """
    Generator function that iterates over all rig instances within the current scene.

    :return: iterated scene rig instances.
    :rtype: Iterator[rig.Rig]
    """

    for meta_rig in iterate_scene_rig_meta_nodes():
        rig_instance = rig.Rig(meta=meta_rig)
        rig_instance.start_session()
        yield rig_instance


def root_by_rig_name(name: str, namespace: str | None = None) -> NoddleRig | None:
    """
    Finds the root meta with the given name in the "name" attribute.

    :param str name: rig name to find meta node rig instance.
    :param str or None namespace: optional valid namespace to search for the rig meta node instance.
    :return: found root meta node instance with given name.
    :rtype: NoddleRig or None
    """

    meta_rigs: list[NoddleRig] = []
    meta_rig_names: list[str] = []

    found_meta_rig = None
    for meta_node in iterate_scene_rig_meta_nodes():
        meta_rigs.append(meta_node)
        meta_rig_names.append(meta_node.attribute(consts.NODDLE_NAME_ATTR).value())
    if not meta_rigs:
        return None
    if not namespace:
        dupes = helpers.duplicates_in_list(meta_rig_names)
        if dupes:
            raise errors.NoddleRigDuplicationError(dupes)
        for meta_rig in meta_rigs:
            if meta_rig.attribute(consts.NODDLE_NAME_ATTR).value() == name:
                return meta_rig
    if found_meta_rig is None and namespace:
        namespace = namespace if namespace.startswith(':') else f':{namespace}'
        for meta_rig in meta_rigs:
            rig_namespace = meta_rig.namespace()
            if rig_namespace == namespace and meta_rig.attribute(consts.NODDLE_NAME_ATTR).value() == name:
                found_meta_rig = meta_rig
                break

    return found_meta_rig


def rig_from_node(node: api.DGNode) -> rig.Rig | None:
    """
    Returns rig from given node.

    :param DGNode node: scene node to find rig from.
    :return: found rig.
    :rtype: rig.Rig or None
    :raises errors.CritMissingMetaNode: if given node is not attached to a meta node.
    :raises errors.CritMissingMetaNode: if attached meta node is not a valid Noddle meta node instance.
    """

    meta_nodes = base.connected_meta_nodes(node)
    if not meta_nodes:
        raise errors.NoddleMissingMetaNode(f'No meta node attached to node: {node}')
    try:
        return parent_rig(meta_nodes[0])
    except AttributeError:
        raise errors.NoddleMissingMetaNode(f'Attached meta node is not a valid Noddle node')


def parent_rig(meta_node: base.MetaBase) -> rig.Rig | None:
    """
    Returns the meta node representing the parent rig of the given meta node instance.

    :param base.MetaBase meta_node: meta base class to get rig of.
    :return: rig instance found to be the parent of the given meta node instance.
    :rtype: rig.Rig or None
    """

    found_rig = None
    for parent in meta_node.iterate_meta_parents(recursive=True):
        crit_root_attr = parent.attribute(consts.NODDLE_IS_ROOT_ATTR)
        if crit_root_attr and crit_root_attr.value():
            found_rig = rig.Rig(meta=parent)
            found_rig.start_session()
            break

    return found_rig
