from __future__ import annotations

import typing
from typing import Iterator

from tp.core import log
from tp.common.python import helpers, yamlio
from tp.maya.meta import base

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import errors
from tp.libs.rig.crit.core import config, rig, template as core_template

if typing.TYPE_CHECKING:
    from tp.maya.api import DGNode
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.core.component import Component
    from tp.libs.rig.crit.meta.rig import CritRig

logger = log.rigLogger


def iterate_scene_rig_meta_nodes() -> Iterator[CritRig]:
    """
    Generator function that iterates over all rig meta node instances within the current scene.

    :return: iterated scene rig meta node instances.
    :rtype: Iterator[CritRig]
    """

    for found_meta_rig in base.find_meta_nodes_by_class_type(consts.RIG_TYPE):
        yield found_meta_rig


def iterate_scene_rigs() -> Iterator[Rig]:
    """
    Generator function that iterates over all rig instances within the current scene.

    :return: iterated scene rig instances.
    :rtype: Iterator[Rig]
    """

    for meta_rig in iterate_scene_rig_meta_nodes():
        rig_instance = rig.Rig(meta=meta_rig)
        rig_instance.start_session()
        yield rig_instance


def root_by_rig_name(name: str, namespace: str | None = None) -> CritRig | None:
    """
    Finds the root meta with the given name in the "name" attribute.

    :param str name: rig name to find meta node rig instance.
    :param str or None namespace: optional valid namespace to search for the rig meta node instance.
    :return: found root meta node instance with given name.
    :rtype: CritRig or None
    """

    meta_rigs: list[CritRig] = []
    meta_rig_names: list[str] = []

    found_meta_rig = None
    for meta_node in iterate_scene_rig_meta_nodes():
        meta_rigs.append(meta_node)
        meta_rig_names.append(meta_node.attribute(consts.CRIT_NAME_ATTR).value())
    if not meta_rigs:
        return None
    if not namespace:
        dupes = helpers.duplicates_in_list(meta_rig_names)
        if dupes:
            raise errors.CritRigDuplicationError(dupes)
        for meta_rig in meta_rigs:
            if meta_rig.attribute(consts.CRIT_NAME_ATTR).value() == name:
                return meta_rig
    if found_meta_rig is None and namespace:
        namespace = namespace if namespace.startswith(':') else f':{namespace}'
        for meta_rig in meta_rigs:
            rig_namespace = meta_rig.namespace()
            if rig_namespace == namespace and meta_rig.attribute(consts.CRIT_NAME_ATTR).value() == name:
                found_meta_rig = meta_rig
                break

    return found_meta_rig


def parent_rig(meta_node: base.MetaBase) -> Rig | None:
    """
    Returns the meta node representing the parent rig of the given meta node instance.

    :param base.MetaBase meta_node: meta base class to get rig of.
    :return: rig instance found to be the parent of the given meta node instance.
    :rtype: Rig or None
    """

    found_rig = None
    for parent in meta_node.iterate_meta_parents(recursive=True):
        crit_root_attr = parent.attribute(consts.CRIT_IS_ROOT_ATTR)
        if crit_root_attr and crit_root_attr.value():
            found_rig = rig.Rig(meta=parent)
            found_rig.start_session()
            break

    return found_rig


def rig_from_node(node: DGNode) -> Rig | None:
    """
    Returns rig from given node.

    :param DGNode node: scene node to find rig from.
    :return: found rig.
    :rtype: Rig or None
    :raises errors.CritMissingMetaNode: if given node is not attached to a meta node.
    :raises errors.CritMissingMetaNode: if attached meta node is not a valid CRIT meta node instance.
    """

    meta_nodes = base.connected_meta_nodes(node)
    if not meta_nodes:
        raise errors.CritMissingMetaNode(f'No meta node attached to node: {node}')
    try:
        return parent_rig(meta_nodes[0])
    except AttributeError:
        raise errors.CritMissingMetaNode(f'Attached meta node is not a valid CRIT node')


def load_rig_from_template_file(
        file_path: str, name: str | None = None,
        rig_to_use: Rig | None = None) -> tuple[Rig, dict[str, Component]] | None:
    """
    Loads rig from given template file.

    :param str file_path: absolute path to the template rig file to load.
    :param str or None name: optional name for the new rig instance.
    :param Rig or None rig_to_use: optional rig to load the components from template on to. If not given, a new rig
        instance will be created.
    :return: rig instance.
    :rtype: tuple[Rig, dict[str, Component]]
    """

    template = yamlio.read_file(file_path)
    if not template:
        logger.error(f'Failed to read template file: {template}')
        return
    logger.debug(f'Loading template from path: {file_path}')
    return load_rig_from_template(template, name=name, rig_to_use=rig_to_use)


def load_rig_from_template(
        template: dict, name: str | None, rig_to_use: Rig | None = None) -> tuple[Rig, dict[str, Component]] | None:
    """
    Loads the CRIT template to a rig.

    :param dict template: CRIT template data structure.
    :param str or None name: optional name for the new rig instance.
    :param Rig or None rig_to_use: optional rig to load the components from template on to. If not given, a new rig
        instance will be created.
    :return: tuple containing the new or given rig instance and a list of newly created components.
    :rtype: tuple[Rig, dict[str, Component]]
    """

    if rig_to_use is None:
        config_data = template.get('config', [])
        build_scripts = config_data.get('buildScripts', {})
        rig_config = config.Configuration()
        rig_config.update_from_cache(config_data)
        rig_to_use = rig.Rig(rig_config=rig_config)
        has_created = rig_to_use.start_session(name or template['name'])
        try:
            rig_config.update_build_script_config(rig_to_use, {k: v for k, v in build_scripts})
        except ValueError:
            pass
        if not has_created:
            logger.error('Cannot create template with a name that already exists!')
            return None

    return rig_to_use, core_template.load_from_template(template, rig_to_use)
