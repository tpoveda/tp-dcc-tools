from __future__ import annotations

import typing
from typing import Iterator

from tp.core import log
from tp.libs.rig.crit.core import errors
from tp.libs.rig.crit.descriptors import component

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.core.component import Component
    from tp.libs.rig.crit.descriptors.component import ComponentDescriptor
    from tp.libs.rig.crit.core.config import Configuration

logger = log.rigLogger


def update_and_merge_component_descriptor_from_template(
        template: dict, configuration: Configuration) -> Iterator[ComponentDescriptor]:
    """
    Returns the template as a dictionary containing all updated/merged component descriptors.

    :param dict template: CRIT template data structure.
    :param Configuration configuration: rig configuration instance.
    :return: updated/merged dictionary.
    :rtype: Iterator[ComponentDescriptor]
    """

    for component_data in template.get('components', []):
        component_type = component_data['type']
        component_descriptor = configuration.initialize_component_descriptor(component_type)
        migrated_descriptor = component.migrate_to_latest_version(
            component_data, original_descriptor=component_descriptor)
        component_descriptor.update(migrated_descriptor)
        yield component_descriptor


def update_rig_connections(components: dict[str, Component]):
    """
    Remaps parents and constraints for given list of components.

    :param dict[str, Component] components: components to remap connections of.
    """

    for comp in components.values():
        component_descriptor = comp.descriptor
        parent = component_descriptor.parent
        connections: dict = component_descriptor.connections
        remap_parent_name: str | None = None
        if parent is not None:
            parent_component = components.get(parent)
            if parent_component:
                remap_parent_name = parent_component.serialized_token_key()
                comp.set_parent(parent_component)
            else:
                connections = {}
        component_descriptor.parent = remap_parent_name

        for constraint in connections.get('constraints', []):
            remap_targets = []
            for target in constraint['targets']:
                target_label, target_id = target
                component_name, component_side, component_id = target_id.split(':')
                target_key = ':'.join((component_name, component_side))
                parent_component = components.get(target_key)
                if parent_component:
                    remap_targets.append(
                        [target_label, ':'.join((parent_component.serialized_token_key(), component_id))])
            constraint['targets'] = remap_targets


def load_from_template(template: dict, rig: Rig) -> dict[str, Component]:
    """
    Loads the CRIT template on the given rig.

    :param dict template: CRIT template data structure.
    :param Rig rig:  existing rig instance.
    :return: dictionary of newly created components.
    :rtype: dict[str, Component]
    :raises errors.CritTemplateMissingComponents: if template has no components.
    """

    template_components = template.get('components')
    if not template_components:
        logger.error(f'No component saved in template: {template["name"]}!')
        raise errors.CritTemplateMissingComponents(template['name'])

    logger.debug('Creating components from template')
    new_components: dict[str, Component] = {}
    for component_descriptor in update_and_merge_component_descriptor_from_template(template, rig.configuration):
        descriptor_name = ':'.join((component_descriptor.name, component_descriptor.side))
        new_component = rig.create_component(
            component_descriptor['type'], component_descriptor['name'], component_descriptor['side'],
            descriptor=component_descriptor)
        new_components[descriptor_name] = new_component

    update_rig_connections(new_components)

    return new_components
