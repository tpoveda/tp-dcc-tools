from __future__ import annotations

import typing

from tp.core import log
from tp.maya import api
from tp.maya.meta import base
from tp.maya.libs.triggers import api as triggers

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import errors

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.core.component import Component
    from tp.libs.rig.crit.meta.component import CritComponent


logger = log.rigLogger


def component_from_node(node: api.DGNode, rig: Rig | None = None) -> Component | None:
    """
    Tries to find and returns the attached components class of the node.

    :param api.DGNode node: node to find component from.
    :param Rig rig: optional rig instance to find searches of. If not given, all rigs within current scene will be
        checked.
    :return: found component.
    :rtype: Component or None
    :raises errors.MissingRigForNode: cannot find a meta node or the meta node is not a valid CRIT node.
    """

    # Import here to avoid cyclic imports
    from tp.libs.rig.noddle.functions import rigs

    rig = rig or rigs.rig_from_node(node)
    if not rig:
        raise errors.NoddleMissingRigForNode(node.fullPathName())

    return rig.component_from_node(node)


def components_from_nodes(nodes: list[api.DGNode]) -> dict[Component, list[api.DGNode]]:
    """
    Returns dictionaries that matches the found component instances with the scene nodes linked to that component.

    :param list[DGNode] nodes: list of nodes to get components for.
    :return: dictionary with the found components and its related scene nodes.
    :rtype: dict[Component, list[api.DGNode]]
    """

    found_components = {}
    for node in nodes:
        try:
            found_component = component_from_node(node)
        except errors.NoddleMissingMetaNode:
            continue
        found_components.setdefault(found_component, []).append(node)

    return found_components


def components_from_selected() -> dict[Component, list[api.DGNode]]:
    """
    Returns dictionaries that matches the found component instances with the selected scene nodes linked to that
    component.

    :return: dictionary with the found components and its related selected scene nodes.
    :rtype: dict[Component, list[api.DGNode]]
    """

    return components_from_nodes(api.selected())


def component_meta_node_from_node(node: api.DGNode) -> CritComponent | base.MetaBase | None:
    """
    Returns to retrieve the component meta node instance from given node by walking the DG downstream of the given node.

    :param api.DGNode node: node to get meta node instance from.
    :return: component meta node instance.
    :rtype: CritComponent or None
    :raises ValueError: if given node is not attached to any meta node.
    """

    meta_nodes = base.connected_meta_nodes(node) if not base.is_meta_node(node) else [base.MetaBase(node.object())]
    if not meta_nodes:
        raise ValueError('No meta node attached to given node!')

    actual = meta_nodes[0]
    if actual.hasAttribute(consts.NODDLE_COMPONENT_TYPE_ATTR):
        return actual

    for meta_parent in actual.iterate_meta_parents():
        if meta_parent.hasAttribute(consts.NODDLE_COMPONENT_TYPE_ATTR):
            return meta_parent

    return None


def create_triggers(node: api.DGNode, layout_id: str):
    """
    Creates contextual menu trigger into given node and attaches the given contextual menu layout ID to it.

    :param api.DGNode node: node to attach contextual menu trigger to.
    :param str layout_id: ID of the contextual menu layout to set.
    """

    found_trigger = triggers.as_trigger_node(node)
    if found_trigger is not None:
        found_trigger.delete_triggers()

    new_trigger = triggers.create_trigger_for_node(node, 'triggerMenu')
    new_trigger.command.set_menu(layout_id)


def setup_space_switches(components: list[Component]):
    """
    Loops over given components and setup space switches.

    :param list[Component] components: list of components to set up space switches for.
    """

    for component in components:
        with api.namespace_context(component.namespace()):
            container = component.container()
            if container is not None:
                container.makeCurrent(True)
            try:
                component.setup_space_switches()
            finally:
                if container is not None:
                    container.makeCurrent(False)


def cleanup_space_switches(rig: Rig, component: Component):
    """
    Removes all space switch drivers which use the given component as a driver.

    :param Rig rig: rig component belongs to.
    :param Component component: component instance which will be deleted.
    """

    logger.debug('Updating space switching.')

    old_token = component.serialized_token_key()
    for found_component in rig.iterate_components():
        if found_component == component:
            continue
        requires_save = False
        for space in found_component.descriptor.space_switching:
            new_drivers = []
            for driver in list(space.drivers):
                driver_name = driver.driver
                if old_token not in driver_name:
                    new_drivers.append(driver)
                else:
                    requires_save = True
            space.drivers = new_drivers

        if requires_save:
            found_component.save_descriptor(found_component.descriptor)
