from __future__ import annotations

import json
import typing
import contextlib
from typing import Iterator

from tp.bootstrap import api as bootstrap
from tp.core import log, dcc
from tp.common.python import profiler
from tp.maya import api

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import errors, naming, config, component
from tp.libs.rig.crit.meta import rig
from tp.libs.rig.crit.functions import rigs, components, guides

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.maya.api import DagNode
    from tp.libs.rig.crit.core.component import Component
    from tp.libs.rig.crit.descriptors.component import ComponentDescriptor
    from tp.libs.rig.crit.meta.component import CritComponent
    from tp.libs.rig.crit.meta.layers import CritComponentsLayer, CritSkeletonLayer, CritGeometryLayer

logger = log.rigLogger


class Rig:
    """
    Main entry class for any given rig, which is composed by a root node and a meta node.
    This class handles the construction and destruction of rig components.
    """

    def __init__(self, rig_config: config.Configuration | None = None, meta: rig.CritRig | None = None):
        """
        Constructor.

        :param config.Configuration rig_config: local configuration to use for this rig.
        :param rig.CritRig meta: root CRIT meta node to use for this rig.
        """

        super().__init__()

        self._meta = meta
        self._components_cache: set[Component] = set()
        self._config = rig_config or config.Configuration()
        self._crit_version = ''
        self._application_version = dcc.version_name()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}> name:{self.name()}'

    def __bool__(self) -> bool:
        return self.exists()

    def __eq__(self, other: Rig) -> bool:
        return self._meta == other.meta

    def __ne__(self, other: Rig) -> bool:
        return self._meta != other.meta

    def __hash__(self):
        return hash(self._meta) if self._meta is not None else hash(id(self))

    def __len__(self) -> int:
        return len(self.components())

    def __contains__(self, item: Component) -> bool:
        return True if self.component(item.name(), item.side()) else False

    def __getattr__(self, item: str):
        if item.startswith('_'):
            return super().__getattribute__(item)
        splitter = item.split('_')
        if len(splitter) < 2:
            return super().__getattribute__(item)
        component_name = '_'.join(splitter[:-1])
        component_side = splitter[-1]
        component_found = self.component(component_name, component_side)
        if component_found is not None:
            return component_found

        return super().__getattribute__(item)

    @property
    def meta(self) -> rig.CritRig:
        """
        Getter method that returns the CRIT meta node instance for this rig.

        :return: rig meta node.
        :rtype: rig.CritRig
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

    @property
    def crit_version(self) -> str:
        """
        Getter method that returns CRIT version used for this rig.

        :return: CRIT version.
        :rtype: str
        """

        current_version = self._crit_version
        if current_version:
            return current_version

        crit_package = bootstrap.current_package_manager().resolver.package_by_name('tp-dcc-tools-crit')
        self._crit_version = str(crit_package.version)

        return self._crit_version

    @property
    def blackbox(self) -> bool:
        """
        Getter method that returns whether any rig component is set to blackbox.

        :return: True if any of the rig components are blackboxed; False otherwise.
        :rtype: bool
        """

        return any(i.blackbox for i in self.iterate_components())

    @blackbox.setter
    def blackbox(self, flag: bool):
        """
        Setter method that sets each component blackbox state attached tto this rig instance.

        :param bool flag: True to mark attached rig components as blackboxed; False otherwise.
        """

        for found_component in self.iterate_components():
            found_component.blackbox = flag

    @profiler.fn_timer
    def start_session(self, name: str | None = None, namespace: str | None = None) -> rig.CritRig:
        """
        Starts a rig session for the rig with given name.

        :param str or None name: optional rig name to initialize, if it does not exist, one will be created.
        :param namespace: optional rig namespace.
        :return: root meta node instance for this rig.
        :rtype: rig.CritRig
        """

        meta = self._meta
        if meta is None:
            meta = rigs.root_by_rig_name(name=name, namespace=namespace)
        if meta is not None:
            self._meta = meta
            logger.info(f'Found rig in scene, initializing rig "{self.name()}" for session')
            self.configuration.update_from_rig(self)
            return self._meta

        namer = self.naming_manager()
        meta = rig.CritRig(name=namer.resolve('rigMeta', {'rigName': name, 'type': 'meta'}))
        meta.attribute(consts.CRIT_NAME_ATTR).set(name)
        meta.attribute(consts.CRIT_ID_ATTR).set(name)
        meta.create_transform(namer.resolve('rigHrc', {'rigName': name, 'type': 'hrc'}))
        meta.create_selection_sets(namer)
        self._meta = meta

        return self._meta

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

    def rename(self, name: str) -> bool:
        """
        Renames this rig instance.

        :param str name: new rig name.
        :return: True if rename rig operation was successful; False otherwise.
        :rtype: bool
        """

        if not self.exists():
            return False

        naming_manager = self.naming_manager()

        self._meta.attribute(consts.CRIT_ID_ATTR).set(name)
        self._meta.attribute(consts.CRIT_NAME_ATTR).set(name)
        self._meta.rename(naming_manager.resolve('rigMeta', {'rigName': name, 'type': 'meta'}))
        self._meta.root_transform().rename(naming_manager.resolve('rigHrc', {'rigName': name, 'type': 'hrc'}))

        components_layer = self.components_layer()
        skeleton_layer = self.skeleton_layer()
        geometry_layer = self.geometry_layer()

        for meta_node, layer_type in zip(
                (components_layer, skeleton_layer, geometry_layer),
                (consts.COMPONENTS_LAYER_TYPE, consts.SKELETON_LAYER_TYPE, consts.GEOMETRY_LAYER_TYPE)):
            if meta_node is None:
                continue
            transform = meta_node.root_transform()
            hrc_name, meta_name = naming.compose_rig_names_for_layer(naming_manager, name, layer_type)
            if transform is not None:
                transform.rename(hrc_name)
            meta_node.rename(meta_name)

        sets = self._meta.selection_sets()
        for set_name, set_node in sets.items():
            if set_node is None:
                continue
            name_rule = 'rootSelectionSet' if set_name == 'root' else 'selectionSet'
            set_node.rename(naming_manager.resolve(
                name_rule, {'rigName': name, 'selectionSet': set_name, 'type': 'objectSet'}))

        return True

    def naming_manager(self) -> NameManager:
        """
        Returns the naming manager for the current rig instance.

        :return: naming manager.
        :rtype: NameManager
        """

        return self.configuration.find_name_manager_for_type('rig')

    def cached_configuration(self) -> dict:
        """
        Returns the configuration cached on the rigs meta node config attribute as a dictionary.

        :return: configuration dict.
        :rtype: dict
        """

        config_plug = self._meta.attribute(consts.CRIT_RIG_CONFIG_ATTR)
        try:
            config_data = config_plug.value()
            if config_data:
                return json.loads(config_data)
        except ValueError:
            pass

        return {}

    @profiler.fn_timer
    def save_configuration(self) -> dict:
        """
        Serializes and saves the configuration for this rig on the meta node instance.

        :return: saved serialized configuration.
        :rtype: dict
        """

        logger.debug('Saving CRIT rig configuration.')
        config_data = self.configuration.serialize(rig=self)
        if config_data:
            config_plug = self._meta.attribute(consts.CRIT_RIG_CONFIG_ATTR)
            config_plug.set(json.dumps(config_data))

        return config_data

    def root_transform(self) -> DagNode | None:
        """
        Returns the root transform node for this rig instance.

        :return: root transform instance.
        :rtype: DagNode or None
        """

        return self._meta.root_transform() if self.exists() else None

    def selection_sets(self) -> dict[str, api.ObjectSet]:
        """
        Returns rig selection sets.

        :return: selection sets with names as keys and instances as values.
        :rtype: dict[str, api.ObjectSet]
        """

        return self._meta.selection_sets() if self._meta else {}

    def components_layer(self) -> CritComponentsLayer | None:
        """
        Returns the components layer instance from this rig by querying the attached meta node.

        :return: components layer instance.
        :rtype: CritComponentsLayer or None
        """

        return self._meta.components_layer() if self._meta else None

    def get_or_create_components_layer(self) -> CritComponentsLayer:
        """
        Returns the components layer if it is attached to this rig or creates a new one and attaches it.

        :return: components layer instance.
        :rtype: CritComponentsLayer
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

    def skeleton_layer(self) -> CritSkeletonLayer | None:
        """
        Returns the skeleton layer instance from this rig by querying the attached meta node.

        :return: skeleton layer instance.
        :rtype: CritSkeletonLayer or None
        """

        return self._meta.skeleton_layer()

    def get_or_create_skeleton_layer(self) -> CritSkeletonLayer:
        """
        Returns the skeleton layer if it is attached to this rig or creates a new one and attaches it.

        :return: skeleton layer instance.
        :rtype: CritSkeletonLayer
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

    def geometry_layer(self) -> CritGeometryLayer | None:
        """
        Returns the geometry layer instance from this rig by querying the attached meta node.

        :return: geometry layer instance.
        :rtype: CritGeometryLayer or None
        """

        return self._meta.geometry_layer()

    def get_or_create_geometry_layer(self) -> CritGeometryLayer:
        """
        Returns the geometry layer if it is attached to this rig or creates a new one and attaches it.

        :return: geometry layer instance.
        :rtype: CritGeometryLayer
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
            descriptor: ComponentDescriptor | None = None) -> Component:
        """
        Adds a new component instance to the rig and creates the root node structure for that component.

        :param str component_type: component type (which is the class name of the component to create).
        :param str name: name of the new component.
        :param str side: side of the new component.
        :param ComponentDescriptor descriptor: optional component descriptor.
        :return: new instance of the created component.
        :rtype: Component
        :raises errors.CritMissingComponentType: if not component with given type is registered.
        """

        if descriptor:
            component_type = component_type or descriptor['type']
            name = name or descriptor['name']
            side = side or descriptor['side']
        else:
            descriptor = self.configuration.initialize_component_descriptor(component_type)

        component_class = self.configuration.components_manager().find_component_by_type(component_type)
        if not component_class:
            raise errors.CritMissingComponentType(component_type)

        name = name or descriptor['name']
        side = side or descriptor['side']
        unique_name = naming.unique_name_for_component_by_rig(self, name, side)
        components_layer = self.get_or_create_components_layer()

        descriptor['side'] = side
        descriptor['name'] = unique_name
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
        visited_meta: set[CritComponent] = set()

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
                logger.error('Failed to initialize component: {}'.format(component_metanode.name()), exc_info=True)
                raise errors.CritInitializeComponentError(component_metanode.name())

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

        :param str component_type: CRIT component type name.
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
            component_name = component_metanode.attribute(consts.CRIT_NAME_ATTR).asString()
            component_side = component_metanode.attribute(consts.CRIT_SIDE_ATTR).asString()
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
            raise errors.CritMissingMetaNode(node.fullPathName())

        return self.component(
            meta_node.attribute(consts.CRIT_NAME_ATTR). value(), meta_node.attribute(consts.CRIT_SIDE_ATTR).value())

    def clear_components_cache(self):
        """
        Clears the components cache which stores component class instances on this rig instance.
        """

        self._components_cache.clear()

    def build_state(self) -> int:
        """
        Returns the current build state which is determined by the very first component.

        :return: build state constant.
        :rtype: int
        """

        for found_component in self.iterate_components():
            if found_component.has_polished():
                return consts.POLISH_STATE
            elif found_component.has_rig():
                return consts.RIG_STATE
            elif found_component.has_skeleton():
                return consts.SKELETON_STATE
            elif found_component.has_guide_controls():
                return consts.CONTROL_VIS_STATE
            elif found_component.has_guide():
                return consts.GUIDES_STATE
            break

        return consts.NOT_BUILT_STATE

    @contextlib.contextmanager
    def build_script_context(self, build_script_type: str, **kwargs):
        """
        Executes all build scripts assigned in the buildScript configuration.

        :param str build_script_type:
        """

        pre_fn_name, post_fn_name = consts.BUILD_SCRIPT_FUNCTIONS_MAPPING.get(build_script_type)

        script_configuration = self.meta.build_script_configuration()
        if pre_fn_name:
            for script in self.configuration.build_scripts:
                if hasattr(script, pre_fn_name):
                    logger.info('Executing pre build script function: {}'.format(
                        '.'.join((script.__class__.__name__, pre_fn_name))))
                    script_properties = script_configuration.get(script.ID, dict())
                    script.rig = self
                    getattr(script, pre_fn_name)(properties=script_properties, **kwargs)
        yield
        if post_fn_name:
            for script in self.configuration.build_scripts:
                if hasattr(script, post_fn_name):
                    logger.info('Executing post build script function: {}'.format(
                        '.'.join((script.__class__.__name__, pre_fn_name))))
                    script_properties = script_configuration.get(script.ID, dict())
                    script.rig = self
                    getattr(script, pre_fn_name)(properties=script_properties, **kwargs)

    # @profiler.profile_it('~/tp/preferences/logs/crit/build_guides.profile')
    @profiler.fn_timer
    def build_guides(self, components_to_build: list[Component] | None = None) -> bool:
        """
        Builds all the guides for the current rig initialized components. If a component has guides already built it
        will be skipped.

        :param list[Component] or None components_to_build: list of components to build guides for.
            If None, all components guides for this rig instance will be built.
        :return: True if the build guides operation was successful; False otherwise.
        :rtype: bool
        """

        def _construct_unordered_list(_component):
            """
            Internal function that walks the component parent hierarchy gathering each component.

            :param component.Component _component: component to get parent hierarchy of.
            """

            _parent = child_parent_relationship[_component]
            if _parent is not None:
                _construct_unordered_list(_parent)
            unordered.append(_component)

        self.configuration.update_from_rig(self)
        child_parent_relationship = {_component: _component.parent() for _component in self.iterate_components()}
        components_to_build = components_to_build or list(child_parent_relationship.keys())

        unordered = []
        for found_component in components_to_build:
            _construct_unordered_list(found_component)

        with component.disconnect_components_context(unordered), self.build_script_context(consts.GUIDE_FUNCTION_TYPE):
            self._build_components(components_to_build, child_parent_relationship, 'build_guide')
            mod = api.DGModifier()
            for component_to_build in components_to_build:
                component_to_build.update_naming(layer_types=(consts.GUIDE_LAYER_TYPE,), mod=mod, apply=False)
            mod.doIt()
            self.set_guide_visibility(
                state_type=consts.GUIDE_LAYER_TYPE,
                control_value=self.configuration.guide_control_visibility,
                guide_value=self.configuration.guide_pivot_visibility)

        return True

    def set_guide_visibility(
            self, state_type: int, control_value: bool | None = None, guide_value: bool | None = None,
            include_root: bool = False):
        """
        Sets all components guides visibility.

        :param str state_type: state type to set visibility of.
        :param bool or None control_value: whether to set visibility of the control nodes.
        :param bool or None guide_value: whether to set visibility of the guide nodes.
        :param bool include_root: whether to set visibility of the root guide.
        """

        is_guide_type = state_type == consts.GUIDE_PIVOT_STATE or state_type == consts.GUIDE_PIVOT_CONTROL_STATE
        is_control_type = state_type == consts.GUIDE_CONTROL_STATE or state_type == consts.GUIDE_PIVOT_CONTROL_STATE
        if is_control_type is not None:
            self.configuration.guide_control_visibility = control_value
        if is_guide_type is not None:
            self.configuration.guide_pivot_visibility = guide_value

        self.save_configuration()

        modifier = api.DGModifier()
        for component_found in self.iterate_components():
            if not component_found.has_guide():
                continue
            guide_layer = component_found.guide_layer()
            root_transform = guide_layer.root_transform()
            if root_transform is not None:
                root_transform.setVisible(True, mod=modifier, apply=False)
            if is_control_type:
                guide_layer.set_guides_controls_visible(control_value)
            _include_root = (False if include_root is None else True) or component_found.has_parent()
            if is_guide_type:
                guide_layer.set_guides_visible(guide_value, include_root=include_root)
        modifier.doIt()

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

        with self.build_script_context(consts.SKELETON_FUNCTION_TYPE):
            guides.align_guides(self, components_to_build)
            self._meta.create_selection_sets(self.naming_manager())
            self._build_components(
                components_to_build, child_parent_relationship, 'build_skeleton', parent_node=parent_node)
            mod = api.DGModifier()
            for component_to_build in components_to_build:
                component_to_build.update_naming(layer_types=(consts.SKELETON_LAYER_TYPE,), mod=mod, apply=False)
            mod.doIt()

        return True

    # @profiler.profile_it('~/tp/preferences/logs/crit/build_rigs.profile')
    @profiler.fn_timer
    def build_rigs(self, components_to_build: list[Component] | None = None) -> bool:
        """
        Builds rigs for the given components. If not given, all initialized components rigs will be built.

        :param list[Component] or None components_to_build: optional list of components to build rig for.
        :return: True if the build rigs operation was successful; False otherwise.
        :rtype: bool
        """

        self._config.update_from_rig(self)
        self._meta.create_selection_sets(self.naming_manager())
        child_parent_relationship = {_component: _component.parent() for _component in self.iterate_components()}
        components_to_build = components_to_build or list(child_parent_relationship.keys())

        if not any(found_component.has_skeleton() for found_component in components_to_build):
            self.build_skeleton(components_to_build)

        with self.build_script_context(consts.RIG_FUNCTION_TYPE):
            success = self._build_components(
                components_to_build, child_parent_relationship, 'build_rig', parent_node=None)
            components.setup_space_switches(components_to_build)
            if success:
                self._handle_control_display_layer(components_to_build)
                return True

        return False

    # @profiler.profile_it('~/tp/preferences/logs/crit/polish.profile')
    def polish(self) -> bool:
        """
        Executers very component `polish` function. Used to do a final cleanup of the rig beforehand off to animation.

        :return: True if rig polish was successful; False otherwise.
        :rtype: bool
        """

        requires_rig: list[Component] = []
        for found_component in self.iterate_components():
            if not found_component.has_rig():
                requires_rig.append(found_component)
        if requires_rig:
            self.build_rigs(requires_rig)

        with self.build_script_context(consts.POLISH_FUNCTION_TYPE):
            success = False
            for found_component in self.iterate_components():
                component_success = found_component.polish()
                if component_success:
                    success = component_success

            return success

    @profiler.fn_timer
    def serialize_from_scene(self, rig_components: list[Component] | None = None) -> dict:
        """
        Runs through all current initialized rig components and serializes them.

        :param list[Component] or None rig_components: optional list of components to serialize. If not given, all rig
            components will be serialized.
        :return: serialized rig.
        :rtype: dict
        """

        output_components = rig_components or self.components()
        data = {'name': self.name(), 'critVersion': self.crit_version}
        count = len(output_components)
        serialized_components = [{}] * count
        for i in range(count):
            serialized_components[i] = output_components[i].serialize_from_scene().to_template()
        data['components'] = serialized_components
        saved_config = self.save_configuration()
        if 'guidePivotVisibility' in saved_config:
            del saved_config['guidePivotVisibility']
        if 'guideControlVisibility' in saved_config:
            del saved_config['guideControlVisibility']
        data['config'] = saved_config

        return data

    @profiler.fn_timer
    def duplicate_component(
            self, component_to_duplicate: Component | tuple[str, str], new_name: str, side: str) -> Component:
        """
        Duplicates the given component and adds it to this rig instance.

        :param Component or tuple[str, str] component_to_duplicate: component to duplicate. This can be a component
            instance or a tuple containing the name and the side of the component to duplicate.
        :param str new_name: new name for the duplicated component.
        :param str side: new side for the duplicated component.
        :return: new duplicated component.
        :rtype: Component
        :raises ValueError: if component with given name and side does not exist.
        """

        if isinstance(component_to_duplicate, tuple):
            name, current_side = component_to_duplicate
            component_to_duplicate = self.component(name, current_side)
            if component_to_duplicate is None:
                raise ValueError(f'Cannot find component with the given name: {name} and side: {current_side}')

        duplicated_component = component.duplicate(new_name, side=side)
        self._components_cache.add(duplicated_component)

        return duplicated_component

    @profiler.fn_timer
    def duplicate_components(self, component_data: list[dict]) -> dict[str, Component]:
        """
        Duplicates the given component data and returns the new components.

        :param list[dict] component_data: list of component data dictionaries containing the coponent, name and side
            of the components to duplicate.
        :return: dictionary of the new components keyed by the original name and side of the component.
        :rtype: dict[str, Component]
        """

        new_components: dict[str, Component] = {}
        has_skeleton = False
        has_rig = False

        for source in component_data:
            source_component: Component = source['component']
            if source_component.has_skeleton():
                has_skeleton = True
            if source_component.has_rig():
                has_rig = True
            new_component = self.duplicate_component(source_component, source['name'], source['side'])
            new_components[':'.join([source_component.name(), source_component.side()])] = new_component

        for new_component in new_components.values():
            connections = new_component.descriptor.connections
            new_constraints = []
            for constraint in connections.get('constraints', []):
                targets = []
                for target in constraint['targets']:
                    target_label, target_id_map = target
                    component_name, component_side, guide_id = target_id_map.split(':')
                    parent = new_components.get(':'.join((component_name, component_side)))
                    if parent is not None:
                        targets.append((target_label, ':'.join((parent.name(), parent.side(), guide_id))))
                        new_component.set_parent(parent)
                if targets:
                    constraint_data = {
                        'type': constraint['type'], 'kwargs': constraint['kwargs'],
                        'controller': constraint['controller'], 'targets': targets}
                    new_constraints.append(constraint_data)
            component_descriptor = new_component.descriptor
            component_descriptor['connections'] = {'id': 'root', 'constraints': new_constraints}
            new_component.save_descriptor(component_descriptor)

        self.build_guides(list(new_components.values()))
        if has_skeleton:
            self.build_skeleton(list(new_components.values()))
        if has_rig:
            self.build_rigs(list(new_components.values()))

        return new_components

    def mirror_components(self, component_data: list[dict]) -> dict:
        """
        Mirrors the given components. Mirror is done with the following steps:
            1. Gather connection info (constraints and un-parent).
            2. Do the mirror operation.
            3. Remap old connection info links to the new component.

        :param list[dict] component_data: a list of dictionaries containing component and metadata for mirroring.
        :return: dictionary containing the mirrored components and metadata for their transformation.
        :rtype: dict
        """

        skeletons_to_build: list[Component] = []
        rigs_to_build: list[Component] = []
        transform_data: list = []
        new_components: list[Component] = []
        connection_info: dict[str, dict] = {}
        visited: set[Component] = set()
        existing_connections_cache = {}
        naming_manager = self.naming_manager()

        # Gather the connection info and un-parent components which will not be duplicated.
        # This avoids affecting the components children during the mirroring of the parent.
        for info in component_data:
            component_to_mirror: Component = info['component']
            connections = component_to_mirror.serialize_component_guide_connections()
            existing_connections_cache[component_to_mirror.serialized_token_key()] = connections
            if not info['duplicate']:
                component_to_mirror.remove_all_parents()

        for info in component_data:
            component_to_mirror: Component = info['component']
            if component_to_mirror in visited:
                continue
            visited.add(component_to_mirror)
            connections = existing_connections_cache[component_to_mirror.serialized_token_key()]
            side = info['side']
            mirror_info = components.mirror_component(
                self, component_to_mirror, side, info['translate'], info['rotate'], duplicate=info['duplicate'])
            new_component: Component = mirror_info['component']
            if mirror_info['duplicated']:
                if mirror_info['has_skeleton']:
                    skeletons_to_build.append(new_component)
                if mirror_info['has_rig']:
                    rigs_to_build.append(new_component)
                new_components.append(new_component)

            transform_data.extend(mirror_info['transform_data'])
            token_key = ':'.join((component_to_mirror.name(), new_component.side()))
            connection_info[token_key] = {'component': new_component, 'connections': connections}

        # Reapply constraints (remap the side value if needed)
        symmetry_field = naming_manager.token('sideSymmetry')
        for new_connection in connection_info.values():
            new_original_component: Component = new_connection['component']
            connections = new_connection[consts.CONNECTIONS_DESCRIPTOR_KEY]

            parent: Component | None = None
            for constraint in connections.get('constraints', []):
                for index, target in enumerate(constraint['targets']):
                    target_label, target_id_map = target
                    comp_name, original_component_side, guide_id = target_id_map.split(':')
                    comp_side = symmetry_field.value_for_key(original_component_side) or original_component_side
                    token_key = ':'.join((comp_name, comp_side))
                    mirrored_parent = connection_info.get(token_key)
                    parent = mirrored_parent['component'] if mirrored_parent else self.component(comp_name, comp_side)
                    if parent is not None:
                        comp_name = parent.name()
                        constraint['targets'][index] = (target_label, ':'.join([comp_name, comp_side, guide_id]))
                    else:
                        # Fall back to the existing parent, case when we mirror without duplication.
                        parent = self.component(comp_name, comp_side)
            if parent is not None:
                new_original_component.set_parent(parent)

            component_descriptor = new_original_component.descriptor
            component_descriptor[consts.CONNECTIONS_DESCRIPTOR_KEY] = new_connection[consts.CONNECTIONS_DESCRIPTOR_KEY]
            new_original_component.save_descriptor(component_descriptor)
            new_original_component.deserialize_component_connections(consts.GUIDE_LAYER_TYPE)

        if skeletons_to_build:
            self.build_skeleton(skeletons_to_build)
        if rigs_to_build:
            self.build_rigs(rigs_to_build)

        return {'new_components': new_components, 'transform_data': transform_data}

    def control_display_layer(self) -> api.DGNode | None:
        """
        Returns the display layer for the controls.

        :return: controls display layer instance.
        :rtype: api.DGNode or None
        """

        return self.meta.attribute(consts.CRIT_CONTROL_DISPLAY_LAYER_ATTR).sourceNode()

    def delete_control_display_layer(self) -> bool:
        """
        Deletes the current display for this rig instance.

        :return: Ture if delete control display layer was deleted successfully; False otherwise.
        :rtype: bool
        """

        return self._meta.delete_control_display_layer()

    @profiler.fn_timer
    def delete_guides(self):
        """
        Deletes all guides from this rig.
        """

        with self.build_script_context(consts.DELETE_GUIDE_LAYER_FUNCTION_TYPE):
            for found_component in self.iterate_components():
                found_component.delete_guide()

    @profiler.fn_timer
    def delete_skeleton(self):
        """
        Deletes all component skeletons.
        """

        with self.build_script_context(consts.DELETE_SKELETON_LAYER_FUNCTION_TYPE):
            for found_component in self.iterate_components():
                found_component.delete_skeleton()

    @profiler.fn_timer
    def delete_rigs(self):
        """
        Deletes all component rigs.
        """

        with self.build_script_context(consts.DELETE_RIG_LAYER_FUNCTION_TYPE):
            for found_component in self.iterate_components():
                found_component.delete_rig()
            self.delete_control_display_layer()

    @profiler.fn_timer
    def delete_components(self):
        """
        Deletes all components for this rig instance.
        """

        with self.build_script_context(consts.DELETE_COMPONENTS_FUNCTION_TYPE):
            for found_component in self.iterate_components():
                component_name = found_component.name()
                try:
                    found_component.delete()
                except Exception as err:
                    logger.error(f'Failed to delete component: {component_name}: {err}', exc_info=True)

        self.clear_components_cache()

    @profiler.fn_timer
    def delete_component(self, name: str, side: str) -> bool:
        """
        Deletes component with given name and side from this rig.

        :param str name: name of the component to delete.
        :param str side: side of the component to delete.
        :return: True if the component deletion operation was successful; False otherwise.
        :rtype: bool
        """

        found_component = self.component(name, side)
        if not found_component:
            logger.warning(f'No component found by the name: {":".join((name, side))}')
            return False

        with self.build_script_context(consts.DELETE_COMPONENT_FUNCTION_TYPE, component=found_component):
            components.cleanup_space_switches(self, found_component)
            found_component.delete()
            try:
                self._components_cache.remove(found_component)
            except KeyError:
                return False

            return True

    @profiler.fn_timer
    def delete(self) -> bool:
        """
        Deletes full rig from the scene.

        :return: Ture if rig was deleted successfully; False otherwise.
        :rtype: bool
        """

        self.delete_components()

        with self.build_script_context(consts.DELETE_RIG_FUNCTION_TYPE):
            root = self._meta.root_transform()
            self.delete_control_display_layer()
            for layer in self._meta.layers():
                layer.delete()
            root.delete()
            self._meta.delete()

        return True

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

        def _process_component(_component, _parent_component):

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
            except errors.CritBuildComponentUnknownError:
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

        display_layer_plug = self.meta.attribute(consts.CRIT_CONTROL_DISPLAY_LAYER_ATTR)
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
