from __future__ import annotations

import json
import typing
import contextlib
from typing import Iterator

from tp.core import log
from tp.common.python import profiler
from tp.maya import api
from tp.maya.meta import base
from tp.common.python import helpers
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.meta import rig as meta_rig
from tp.libs.rig.noddle.core import errors, config, component
from tp.libs.rig.noddle.functions import naming, components

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.noddle.meta.rig import NoddleRig
    from tp.libs.rig.noddle.meta.component import NoddleComponent
    from tp.libs.rig.noddle.meta.layers import NoddleComponentsLayer, NoddleSkeletonLayer, NoddleGeometryLayer
    from tp.libs.rig.noddle.core.component import Component
    from tp.libs.rig.noddle.descriptors.component import ComponentDescriptor

logger = log.rigLogger


def iterate_scene_rig_meta_nodes() -> Iterator[NoddleRig]:
    """
    Generator function that iterates over all rig meta node instances within the current scene.

    :return: iterated scene rig meta node instances.
    :rtype: Iterator[NoddleRig]
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
        rig_instance = Rig(meta=meta_rig)
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


def rig_from_node(node: api.DGNode) -> Rig | None:
    """
    Returns rig from given node.

    :param DGNode node: scene node to find rig from.
    :return: found rig.
    :rtype: Rig or None
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


def parent_rig(meta_node: base.MetaBase) -> Rig | None:
    """
    Returns the meta node representing the parent rig of the given meta node instance.

    :param base.MetaBase meta_node: meta base class to get rig of.
    :return: rig instance found to be the parent of the given meta node instance.
    :rtype: Rig or None
    """

    found_rig = None
    for parent in meta_node.iterate_meta_parents(recursive=True):
        crit_root_attr = parent.attribute(consts.NODDLE_IS_ROOT_ATTR)
        if crit_root_attr and crit_root_attr.value():
            found_rig = Rig(meta=parent)
            found_rig.start_session()
            break

    return found_rig


class Rig:
    """
    Main entry class for any given rig, which is composed by a root node and a meta node.
    This class handles the construction and destruction of rig components.
    """

    def __init__(
            self, rig_config: config.Configuration | None = None, meta: NoddleRig | base.MetaBase | None = None):
        """
        Constructor.

        :param config.Configuration rig_config: local configuration to use for this rig.
        :param rig.CritRig meta: root Noddle meta node to use for this rig.
        """

        super().__init__()

        self._meta = meta
        self._components_cache: set[Component] = set()
        self._config = rig_config or config.Configuration()

    @property
    def meta(self) -> NoddleRig:
        """
        Getter method that returns the Noddle meta node instance for this rig.

        :return: rig meta node.
        :rtype: rig.NoddleRig
        """

        return self._meta

    @property
    def configuration(self) -> config.Configuration:
        """
        Getter method that returns the local rig configuration for this instance.

        :return: rig local configuration.
        :rtype: config.Configuration
        """

        return self._config

    def exists(self) -> bool:
        """
        Returns whether this rig exists by checking the existing of the meta node.

        :return: True if rig exists within current scene; False otherwise.
        :rtype: bool
        """

        return self._meta is not None and self._meta.exists()

    def name(self) -> str:
        """
        Returns the name of the rig by accessing meta node data.

        :return: rig name.
        :rtype: str
        """

        return self._meta.rig_name() if self.exists() else ''

    @profiler.fn_timer
    def start_session(self, name: str | None = None, namespace: str | None = None) -> NoddleRig:
        """
        Starts a rig session for the rig with given name.

        :param str or None name: optional rig name to initialize, if it does not exist, one will be created.
        :param namespace: optional rig namespace.
        :return: root meta node instance for this rig.
        :rtype: rig.NoddleRig
        """

        meta = self._meta
        if meta is None:
            meta = root_by_rig_name(name=name, namespace=namespace)
        if meta is not None:
            self._meta = meta
            logger.info(f'Found rig in scene, initializing rig "{self.name()}" for session')
            self.configuration.update_from_rig(self)
            return self._meta

        namer = self.naming_manager()
        meta = meta_rig.NoddleRig(name=namer.resolve('rigMeta', {'rigName': name, 'type': 'meta'}))
        meta.attribute(consts.NODDLE_NAME_ATTR).set(name)
        meta.attribute(consts.NODDLE_ID_ATTR).set(name)
        meta.create_transform(namer.resolve('rigHrc', {'rigName': name, 'type': 'hrc'}))
        meta.create_selection_sets(namer)
        self._meta = meta

        return self._meta

    def cached_configuration(self) -> dict:
        """
        Returns the configuration cached on the rigs meta node config attribute as a dictionary.

        :return: configuration dict.
        :rtype: dict
        """

        config_plug = self._meta.attribute(consts.NODDLE_RIG_CONFIG_ATTR)
        try:
            config_data = config_plug.value()
            if config_data:
                return json.loads(config_data)
        except ValueError:
            pass

        return {}

    def naming_manager(self) -> NameManager:
        """
        Returns the naming manager for the current rig instance.

        :return: naming manager.
        :rtype: NameManager
        """

        return self.configuration.find_name_manager_for_type('rig')

    def components_layer(self) -> NoddleComponentsLayer | None:
        """
        Returns the components layer instance from this rig by querying the attached meta node.

        :return: components layer instance.
        :rtype: NoddleComponentsLayer or None
        """

        return self._meta.components_layer() if self._meta else None

    def get_or_create_components_layer(self) -> NoddleComponentsLayer:
        """
        Returns the components layer if it is attached to this rig or creates a new one and attaches it.

        :return: components layer instance.
        :rtype: NoddleComponentsLayer
        """

        components_layer = self.components_layer()
        if not components_layer:
            name_manager = self.naming_manager()
            hierarchy_name, meta_name = naming.compose_rig_names_for_layer(
                name_manager, self.name(), consts.COMPONENTS_LAYER_TYPE)
            components_layer = self._meta.create_layer(
                consts.COMPONENTS_LAYER_TYPE, hierarchy_name=hierarchy_name, meta_name=meta_name,
                parent=self._meta.root_transform())

        return components_layer

    def skeleton_layer(self) -> NoddleSkeletonLayer | None:
        """
        Returns the skeleton layer instance from this rig by querying the attached meta node.

        :return: skeleton layer instance.
        :rtype: NoddleSkeletonLayer or None
        """

        return self._meta.skeleton_layer()

    def get_or_create_skeleton_layer(self) -> NoddleSkeletonLayer:
        """
        Returns the skeleton layer if it is attached to this rig or creates a new one and attaches it.

        :return: skeleton layer instance.
        :rtype: NoddleSkeletonLayer
        """

        skeleton_layer = self.skeleton_layer()
        if not skeleton_layer:
            name_manager = self.naming_manager()
            hierarchy_name, meta_name = naming.compose_rig_names_for_layer(
                name_manager, self.name(), consts.SKELETON_LAYER_TYPE)
            skeleton_layer = self._meta.create_layer(
                consts.SKELETON_LAYER_TYPE, hierarchy_name=hierarchy_name, meta_name=meta_name,
                parent=self._meta.root_transform())

        return skeleton_layer

    def geometry_layer(self) -> NoddleGeometryLayer | None:
        """
        Returns the geometry layer instance from this rig by querying the attached meta node.

        :return: geometry layer instance.
        :rtype: NoddleGeometryLayer or None
        """

        return self._meta.geometry_layer()

    def get_or_create_geometry_layer(self) -> NoddleGeometryLayer:
        """
        Returns the geometry layer if it is attached to this rig or creates a new one and attaches it.

        :return: geometry layer instance.
        :rtype: NoddleGeometryLayer
        """

        geometry_layer = self.geometry_layer()
        if not geometry_layer:
            name_manager = self.naming_manager()
            hierarchy_name, meta_name = naming.compose_rig_names_for_layer(
                name_manager, self.name(), consts.GEOMETRY_LAYER_TYPE)
            geometry_layer = self._meta.create_layer(
                consts.GEOMETRY_LAYER_TYPE, hierarchy_name=hierarchy_name, meta_name=meta_name,
                parent=self._meta.root_transform())

        return geometry_layer

    @profiler.fn_timer
    def create_component(
            self, component_type: str | None = None, name: str | None = None, side: str | None = None,
            region: str | None = None, descriptor: ComponentDescriptor | None = None) -> Component:
        """
        Adds a new component instance to the rig and creates the root node structure for that component.

        :param str component_type: component type (which is the class name of the component to create).
        :param str name: name of the new component.
        :param str side: side of the new component.
        :param str region: region that defines which skeleton joints to use when building it.
        :param ComponentDescriptor descriptor: optional component descriptor.
        :return: new instance of the created component.
        :rtype: Component
        :raises errors.CritMissingComponentType: if not component with given type is registered.
        """

        if descriptor:
            component_type = component_type or descriptor['type']
            name = name or descriptor['name']
            side = side or descriptor['side']
            region = region or descriptor['region']
        else:
            descriptor = self.configuration.initialize_component_descriptor(component_type)

        component_class = self.configuration.components_manager().find_component_by_type(component_type)
        if not component_class:
            raise errors.NoddleMissingComponentType(component_type)

        name = name or descriptor['name']
        side = side or descriptor['side']
        region = region or descriptor['region']
        unique_name = naming.unique_name_for_component_by_rig(self, name, side)
        components_layer = self.get_or_create_components_layer()

        descriptor['side'] = side
        descriptor['name'] = unique_name
        descriptor['region'] = region
        init_component = component_class(rig=self, descriptor=descriptor)
        init_component.create(parent=components_layer)
        self._components_cache.add(init_component)

        return init_component

    def has_component(self, name: str, side: str = 'M') -> bool:
        """
        Returns whether a component with given name and side exists for this rig instance.

        :param str name: name of the component.
        :param str side: side of the component.
        :return: True if component with given name and side exists for this rig; False otherwise.
        :rtype: bool
        """

        for component_found in self.iterate_components():
            if component_found.name() == name and component_found.side() == side:
                return True

        return False

    def iterate_root_components(self) -> Iterator[Component]:
        """
        Generator function that iterates over all root components in this rig.

        :return: iterated root components.
        :rtype: Iterator[Component]
        """

        for found_component in self.iterate_components():
            if not found_component.has_parent():
                yield found_component

    def iterate_components(self) -> Iterator[Component]:
        """
        Generator function that iterates over all components in this rig.

        :return: iterated components.
        :rtype: Iterator[Component]
        :raises ValueError: if something happens when retrieving a component from manager instance.
        """

        found_components: set[Component] = set()
        visited_meta: set[NoddleComponent] = set()

        for cached_component in self._components_cache:
            if not cached_component.exists():
                continue
            found_components.add(cached_component)
            visited_meta.add(cached_component.meta)
            yield cached_component

        self._components_cache = found_components

        components_layer = self.components_layer()
        if components_layer is None:
            return

        components_manager = self.configuration.components_manager()
        for component_metanode in components_layer.iterate_components():
            try:
                if component_metanode in visited_meta:
                    continue
                found_component = components_manager.from_meta_node(rig=self,  meta=component_metanode)
                found_components.add(found_component)
                visited_meta.add(found_component.meta)
                yield found_component
            except ValueError:
                logger.error(f'Failed to initialize component: {component_metanode.name()}', exc_info=True)
                raise errors.NoddleInitializeComponentError(component_metanode.name())

    def components(self) -> list[Component]:
        """
        Returns a list of all component instances initialized within current scene for this rig.

        :return: list of components for this rig.
        :rtype: list[Component]
        """

        return list(self.iterate_components())

    def iterate_components_by_type(self, component_type: str) -> Iterator[Component]:
        """
        Generator function that yields all components of the given type name.

        :param str component_type: Noddle component type name.
        :return: iterated components of the given type.
        :rtype: Iterator[Component]
        """

        for found_component in self.iterate_components():
            if found_component.component_type == component_type:
                yield found_component

    def component(self, name: str, side: str = 'M') -> Component | None:
        """
        Tries to find the component by name and side by first check the component cache for this rig instance and
        after that checking the components via meta node network.

        :param str name: component name to find.
        :param str side: component side to find.
        :return: found component instance.
        :rtype: Component or None
        """

        for component_found in self._components_cache:
            if component_found.name() == name and component_found.side() == side:
                return component_found

        components_layer = self.components_layer()
        if components_layer is None:
            return None

        components_manager = self.configuration.components_manager()
        for component_metanode in components_layer.iterate_components():
            component_name = component_metanode.attribute(consts.NODDLE_NAME_ATTR).asString()
            component_side = component_metanode.attribute(consts.NODDLE_SIDE_ATTR).asString()
            if component_name == name and component_side == side:
                component_instance = components_manager.from_meta_node(rig=self, meta=component_metanode)
                self._components_cache.add(component_instance)
                return component_instance

        return None

    def component_from_node(self, node: api.DGNode) -> Component | None:
        """
        Returns the component for the given node if it is part of this rig.

        :param api.DGNode node: node to search for the component.
        :return: found component instance.
        :rtype: Component or None
        :raises errors.CritMissingMetaNode: if given node is not attached to any meta node.
        """

        meta_node = components.component_meta_node_from_node(node)
        if not meta_node:
            raise errors.NoddleMissingMetaNode(node.fullPathName())

        return self.component(
            meta_node.attribute(consts.NODDLE_NAME_ATTR). value(), meta_node.attribute(consts.NODDLE_SIDE_ATTR).value())

    def clear_components_cache(self):
        """
        Clears the components cache which stores component class instances on this rig instance.
        """

        self._components_cache.clear()

    @profiler.fn_timer
    def setup_skeleton(self, root_joint: api.Joint):
        """
        Setup rig skeleton based on the given root joint.

        :param api.Joint root_joint: skeleton root joint.
        """

        skeleton_layer = self.get_or_create_skeleton_layer()
        if root_joint not in skeleton_layer.joints():
            skeleton_layer.add_joint(root_joint, 'root')

        child_joints = list(root_joint.iterateChildren(recursive=True, node_types=(api.kNodeTypes.kJoint,)))
        for child_joint in child_joints:
            skeleton_layer.add_joint(child_joint, child_joint.fullPathName(partial_name=True, include_namespace=False))

        parent_node = skeleton_layer.root_transform()
        parent_node.show()
        root_joint.setParent(parent_node)

        self.get_or_create_geometry_layer()

        self._meta.create_selection_sets(self.naming_manager())

    # @profiler.profile_it('~/tp/preferences/logs/crit/build_skeleton.profile')
    @profiler.fn_timer
    def build_skeleton(self, components_to_build: list[Component] | None = None) -> bool:
        """
        Builds skeleton for the given components. If not given, all initialized components skeletons will be built.

        :param  list[Component] or None components_to_build: optional list of components to build skeleton for.
        :return: True if the build skeleton operation was successful; False otherwise.
        :rtype: bool
        """

        self._config.update_from_rig(self)
        child_parent_relationship = {_component: _component.parent() for _component in self.iterate_components()}
        components_to_build = components_to_build or list(child_parent_relationship.keys())

        parent_node = self.get_or_create_skeleton_layer().root_transform()
        parent_node.show()
        self.get_or_create_geometry_layer()

        self._meta.create_selection_sets(self.naming_manager())
        self._build_components(
            components_to_build, child_parent_relationship, 'build_skeleton', parent_node=parent_node)

        return True

    # @profiler.profile_it('~/tp/preferences/logs/noddle/build_rigs.profile')
    @profiler.fn_timer
    def build_rigs(self, components_to_build: list[Component] | None = None) -> bool:
        """
        Builds rigs for the given components. If not given, all initialized components rigs will be built.

        :param list[Component] or None components_to_build: optional list of components to build rig for.
        :return: True if the build rigs operation was successful; False otherwise.
        :rtype: bool
        """

        self.configuration.update_from_rig(self)
        self.meta.create_selection_sets(self.naming_manager())
        child_parent_relationship = {_component: _component.parent() for _component in self.iterate_components()}
        components_to_build = components_to_build or list(child_parent_relationship.keys())

        success = self._build_components(
            components_to_build, child_parent_relationship, 'build_rig', parent_node=None)
        if success:
            self._handle_control_display_layer(components_to_build)
            return True

        return False

    def _build_components(
            self, components_to_build: list[Component],
            child_parent_relationship: dict, build_fn_name: str, **kwargs) -> bool:
        """
        Internal function that handles the build of the component based on the given build function name.

        :param list[Component] components_to_build: list of components to build.
        :param dict child_parent_relationship: dictionary that maps each component with its parent component.
        :param str build_fn_name: name of the component build function to execute.
        :return: True if the build operation was successful; False otherwise.
        :rtype: bool
        """

        def _process_component(_component: Component, _parent_component: Component | None):

            # first build parent component if any
            if _parent_component is not None and _parent_component not in visited:
                _process_component(_parent_component, current_components[_parent_component])
            if _component in visited:
                return False
            visited.add(_component)

            _parent_descriptor = _component.descriptor.parent
            if _parent_descriptor:
                # this situation can happen when rebuilding a rig from a template for example, where it is likely that
                # parent has not been added, by they are defined within component descriptor, so we rebuild them if
                # possible.
                logger.debug('Component descriptor has parents defined, adding them...')
                _existing_component = self.component(*_parent_descriptor.split(':'))
                if _existing_component is not None:
                    _component.set_parent(_existing_component)

            try:
                logger.info('Building component: {}, with method: {}'.format(_component, build_fn_name))
                getattr(_component, build_fn_name)(**kwargs)
                return True
            except errors.NoddleBuildComponentUnknownError:
                logger.error('Failed to build for: {}'.format(_component))
                return False

        component_build_order = component.construct_component_order(components_to_build)
        current_components = child_parent_relationship
        visited: set[Component] = set()

        for child, parent in component_build_order.items():
            success = _process_component(child, parent)
            if not success:
                return False

        return True

    def _handle_control_display_layer(self, built_components: list[Component]):
        """
        Internal function that creates and renames the primary display layer for this rig and adds all controls from
        the components to the layer.

        :param list[Component] built_components: components whose controls we want to add into the rig display layer.
        """

        display_layer_plug = self.meta.attribute(consts.NODDLE_CONTROL_DISPLAY_LAYER_ATTR)
        layer = display_layer_plug.sourceNode()
        naming_manager = self.naming_manager()
        control_layer_name = naming_manager.resolve(
            'controlDisplayLayerSuffix', {'rigName': self.name(), 'type': 'controlLayer'})
        if layer is None:
            layer = api.factory.create_display_layer(control_layer_name)
            layer.hideOnPlayback.set(True)
            layer.message.connect(display_layer_plug)
        elif layer.name(include_namespace=False) != control_layer_name:
            layer.rename(control_layer_name)
        layer.playback = True
        for _component in built_components:
            for control in _component.rig_layer().iterate_controls():
                layer.drawInfo.connect(control.drawOverride)
