from __future__ import annotations

import typing
from typing import Iterator

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.crit.core.rig import Rig


def unique_name_for_rig(rigs: Iterator[Rig], name: str) -> str:
    """
    Returns a unique name for a rig.

    :param Iterator[Rig] rigs: list of rig instances to compare names with.
    :param str name: new name for the rig.
    :return: unique name for the rig based on the comparison with the names of the list of rigs.
    :rtype: str
    """

    new_name = name
    current_names = [i.name() for i in rigs]
    index = 1
    while new_name in current_names:
        new_name = name + str(index).zfill(3)
        index += 1

    return new_name


def unique_name_for_component_by_rig(rig: Rig, name: str, side: str) -> str:
    """
    Returns a unique name for the component using based on the given rig instance.

    :param Rig rig: rig instance to use as the filter.
    :param str name: name for the component.
    :param str side: side for the component.
    :return: unique name for the component within the rig.
    :rtype: str
    """

    current_name = ':'.join([name, side])
    current_names = [':'.join([i.name(), i.side()]) for i in rig.iterate_components()]
    index = 1
    while current_name in current_names:
        current_name = ':'.join([name + str(index).zfill(3), side])
        index += 1

    return current_name.split(':')[0]


def compose_rig_names_for_layer(name_manager: NameManager, rig_name: str, layer_type: str) -> tuple[str, str]:
    """
    Composes and returns the resolved node names for the layer root hierarchy and meta nodes.

    :param NameManager name_manager: naming manager instance used to resolve the name.
    :param str rig_name: rig name.
    :param str layer_type: layer type.
    :return: tuple with the root hierarchy name and the meta node name.
    :rtype: tuple[str, str]
    """

    hierarchy_name = name_manager.resolve('layerHrc', {'rigName': rig_name, 'layerType': layer_type, 'type': 'hrc'})
    meta_name = name_manager.resolve('layerMeta', {'rigName': rig_name, 'layerType': layer_type, 'type': 'meta'})

    return hierarchy_name, meta_name


def compose_component_root_names(
        name_manager: NameManager, component_name: str, component_side: str) -> tuple[str, str]:
    """
    Composes and returns the resolved node names for the component root hierarchy and meta nodes.

    :param NameManager name_manager: naming manager instance used to resolve the name.
    :param str component_name: component name.
    :param str component_side: component side.
    :return: tuple with the root hierarchy name and the meta node name.
    :rtype: tuple[str, str]
    """

    hierarchy_name = name_manager.resolve(
        'componentHrc', {'componentName': component_name, 'side': component_side, 'type': 'hrc'})
    meta_name = name_manager.resolve(
        'componentMeta', {'componentName': component_name, 'side': component_side, 'type': 'meta'})

    return hierarchy_name, meta_name


def compose_names_for_layer(
        name_manager: NameManager, component_name: str, component_side: str, layer_type: str) -> tuple[str, str]:
    """
    Composes and returns the resolved node names for the layer root hierarchy and meta nodes.

    :param tp.common.naming.manager.NameManager name_manager: naming manager instance used to resolve the name.
    :param str component_name: component name.
    :param str component_side: component side.
    :param str layer_type: type of layer.
    :return: tuple with the root hierarchy name and the meta node name.
    :rtype: tuple[str, str]
    """

    hierarchy_name = name_manager.resolve(
        'layerHrc', {'componentName': component_name, 'side': component_side, 'type': 'hrc', 'layerType': layer_type})
    meta_name = name_manager.resolve(
        'layerMeta', {'componentName': component_name, 'side': component_side, 'type': 'meta', 'layerType': layer_type})

    return hierarchy_name, meta_name


def compose_container_name(name_manager: NameManager, component_name: str, component_side: str) -> str:
    """
    Composes and returns the resolved node names for the component asset container node.

    :param NameManager name_manager: naming manager instance used to resolve the name.
    :param str component_name: component name.
    :param str component_side: component side.
    :return: resolved name for the container.
    :rtype: str
    """

    return name_manager.resolve(
        'containerName', {
            'componentName': component_name, 'side': component_side, 'section': 'root', 'type': 'container'})


def compose_connectors_group_name(name_manager: NameManager, component_name: str, component_side: str) -> str:
    """
    Composes and returns the resolved node names for the connectors group transform node.

    :param tp.common.naming.manager.NameManager name_manager: naming manager instance used to resolve the name.
    :param str component_name: component name.
    :param str component_side: component side.
    :return: resolved name for the connectors group transform node.
    :rtype: str
    """

    return name_manager.resolve(
        'connectorsGrp', {'componentName': component_name, 'side': component_side, 'type': 'connectorsGroup'})


def compose_settings_name(name_manager: NameManager, component_name: str, component_side: str, section: str) -> str:
    """
    Composes and returns the resolved node names for a setting node.

    :param tp.common.naming.manager.NameManager name_manager: naming manager instance used to resolve the name.
    :param str component_name: component name.
    :param str component_side: component side.
    :param str section: unique setting section name.
    :return: resolved name for the setting node.
    :rtype: str
    """

    return name_manager.resolve(
        'settingsName', {'componentName': component_name, 'side': component_side, 'section': section, 'type': 'settings'})
