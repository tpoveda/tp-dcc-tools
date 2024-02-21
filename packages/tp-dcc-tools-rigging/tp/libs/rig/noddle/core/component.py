from __future__ import annotations

import copy
import json
import typing
import contextlib
from typing import Iterator, Iterable, Any

from tp.core import log
from tp.bootstrap import log
from tp.maya import api
from tp.maya.meta import base
from tp.maya.cmds import helpers as maya_helpers
from tp.common.python import profiler, decorators

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import errors, nodes
from tp.libs.rig.noddle.meta import layers, component as meta_component
from tp.libs.rig.noddle.descriptors import nodes as descriptor_nodes, component as descriptor_component
from tp.libs.rig.noddle.functions import naming, joints

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.noddle.core.rig import Rig
    from tp.libs.rig.noddle.core.config import Configuration
    from tp.libs.rig.noddle.core.namingpresets import Preset
    from tp.libs.rig.noddle.descriptors.nodes import InputDescriptor, OutputDescriptor

logger = log.rigLogger


def construct_component_order(components: list[Component]) -> dict[Component, Component]:
    """
    Handles the component order based on DG order. Parent components will be built before child components.

    :param list[Component] components: list of components to build.
    :return: list of components ordered by build order.
    :rtype: dict[Component, Component]
    """

    unsorted: dict[Component, Component] = {}
    for found_component in components:
        parent = found_component.parent()
        unsorted[found_component] = parent

    ordered: dict[Component, Component] = {}
    while unsorted:
        for child, parent in list(unsorted.items()):
            if parent in unsorted:
                continue
            else:
                del(unsorted[child])
                ordered[child] = parent

    return ordered


class Component:
    """
    Component class that encapsulates a single rigging component.
    """

    ID = ''
    DOCUMENTATION = ''
    REQUIRED_PLUGINS: list[str] = []

    def __init__(
            self, rig: Rig, descriptor: descriptor_component.ComponentDescriptor | None = None,
            meta: meta_component.NoddleComponent | None = None):
        super().__init__()

        self._rig = rig
        self._meta = meta
        self._descriptor: descriptor_component.ComponentDescriptor | None = None
        self._original_descriptor: descriptor_component.ComponentDescriptor | None = None
        self._container: api.ContainerAsset | None = None
        self._configuration = rig.configuration
        self._is_building_skeleton = False
        self._is_building_rig = False
        self._build_objects_cache: dict[str, Any] = dict()

        if descriptor is None and meta is not None:
            no_component_type = False
            component_type = meta.attribute(consts.NODDLE_COMPONENT_TYPE_ATTR).asString()
            if not component_type:
                no_component_type = True
                component_type = self.ID
            initialized_descriptor = self.configuration.initialize_component_descriptor(component_type)
            if no_component_type:
                meta.attribute(consts.NODDLE_COMPONENT_TYPE_ATTR).set(component_type)
            self._original_descriptor = self.configuration.components_manager().load_component_descriptor(
                component_type)
            scene_state = self._descriptor_from_scene()
            if scene_state:
                scene_data = descriptor_component.migrate_to_latest_version(
                    scene_state, original_descriptor=initialized_descriptor)
                initialized_descriptor.update(scene_data)
            self._descriptor = initialized_descriptor
        elif descriptor and meta:
            self._original_descriptor = copy.deepcopy(descriptor)
            self._descriptor = self._descriptor_from_scene()
        else:
            self._original_descriptor = descriptor
            self._descriptor = copy.deepcopy(descriptor)

        self.logger = log.get_logger('.'.join([__name__, '_'.join([self.name(), self.side()])]))

    @classmethod
    def load_required_plugins(cls):
        """
        Loads all required plugins for this component to work as expected.

        :raises Exception: if something went wrong while loading plugins.
        """

        for plugin_name in cls.REQUIRED_PLUGINS:
            if not maya_helpers.is_plugin_loaded(plugin_name):
                try:
                    logger.info(f'Loading plugin {plugin_name} required by {cls}')
                    maya_helpers.load_plugin(plugin_name, quiet=True)
                except Exception:
                    logger.exception(f'Failed to load plugin {plugin_name} required by {cls}')
                    raise

    @property
    def meta(self) -> meta_component.NoddleComponent:
        """
        Returns component meta node instance.

        :return: meta node instance.
        :rtype: meta_component.NoddleComponent
        """

        return self._meta

    @meta.setter
    def meta(self, value: meta_component.NoddleComponent):
        """
        Sets component meta node instance.

        :param meta_component.NoddleComponent value: meta node instance to set.
        """

        self._meta = value

    @property
    def configuration(self) -> Configuration:
        """
        Returns component configuration instance.

        :return: configuration instance.
        :rtype: Configuration
        """

        return self._configuration

    @property
    def component_type(self) -> str:
        """
        Returns the component type for this component instance.

        :return: component type name.
        :rtype: str
        """

        return self.__class__.__name__ if not self.exists() else self.meta.attribute(
            consts.NODDLE_COMPONENT_TYPE_ATTR).asString()

    @property
    def rig(self) -> Rig:
        """
        Returns the current rig instance this component belongs to.

        :return: rig instance.
        :rtype: Rig
        """

        return self._rig

    @property
    def descriptor(self) -> descriptor_component.ComponentDescriptor:
        """
        Returns the component descriptor instance.

        :return: component descriptor instance.
        :rtype: descriptor_component.ComponentDescriptor
        """

        return self._descriptor

    @descriptor.setter
    def descriptor(self, value: descriptor_component.ComponentDescriptor):
        """
        Sets the component descriptor.

        :param component.ComponentDescriptor value: component descriptor to set.
        """

        if type(value) == dict:
            value = descriptor_component.load_descriptor(value, self._original_descriptor)

        self._descriptor = value

    @property
    def blackbox(self) -> bool:
        """
        Returns whether this component asset container is blackboxed.

        :return: True if component asset container is blackboxed; False otherwise.
        :rtype: bool
        """

        container = self.container()

        return False if not container or not container.blackBox else True

    @blackbox.setter
    def blackbox(self, flag: bool):
        """
        Sets whether this component asset container is blackboxed.

        :param bool flag: True to blackbox component asset container; False otherwise.
        """

        container = self.container()
        if container:
            container.blackBox = flag

    @profiler.fn_timer
    def create(self, parent: layers.NoddleComponentsLayer | None = None, **kwargs) -> meta_component.NoddleComponent:
        """
        Creates the component within current scene.

        :param layers.NoddleComponentsLayer or None parent: optional rig parent layer which component will connect to
            via its meta node instance.
        :return: newly created component meta node instance.
        :rtype: meta_component.NoddleComponent
        """

        if not parent or not isinstance(parent, layers.NoddleComponentsLayer):
            parent = None

        self.logger.info(f'Building ({self.side()} - {self.name()}')
        self.load_required_plugins()

        self.logger.debug('Creating component stub in current scene...')
        descriptor = self.descriptor
        naming_manager = self.naming_manager()
        component_name, side, region = self.name(), self.side(), self.region()
        hierarchy_name, meta_name = naming.compose_component_root_names(naming_manager, component_name, side)
        self.logger.debug('Creating Component meta node instance...')
        meta_node = meta_component.NoddleComponent(name=meta_name, parent=parent)
        meta_node.attribute(consts.NODDLE_NAME_ATTR).set(component_name)
        meta_node.attribute(consts.NODDLE_SIDE_ATTR).set(side)
        meta_node.attribute(consts.NODDLE_REGION_NAME_ATTR).set(region)
        meta_node.attribute(consts.NODDLE_ID_ATTR).set(component_name)
        meta_node.attribute(consts.NODDLE_VERSION_ATTR).set(str(descriptor.get('version', '')))
        meta_node.attribute(consts.NODDLE_COMPONENT_TYPE_ATTR).set(descriptor.get('type', ''))
        notes = meta_node.attribute('notes')
        if notes is None:
            meta_node.addAttribute('notes', type=api.kMFnDataString, value=self.DOCUMENTATION)
        else:
            notes.set(self.DOCUMENTATION)
        parent_transform = parent.root_transform() if parent else None
        meta_node.create_transform(hierarchy_name, parent=parent_transform)
        self._meta = meta_node

        if parent and isinstance(parent, layers.NoddleComponentsLayer):
            meta_node.add_meta_parent(parent)

        return meta_node

    def save_descriptor(self, descriptor_to_save: descriptor_component.ComponentDescriptor | None = None):
        """
        Saves the given descriptor as the descriptor cache and bakes the descriptor into the component meta node
        instance.

        :param dict or descriptor_component.ComponentDescriptor descriptor_to_save: descriptor data to save.
        """

        descriptor_to_save = descriptor_to_save or self._descriptor

        if type(descriptor_to_save) == dict:
            descriptor_to_save = descriptor_component.load_descriptor(descriptor_to_save, self._original_descriptor)

        self._descriptor = descriptor_to_save
        self._meta.save_descriptor_data(descriptor_to_save.to_scene_data())

    def exists(self) -> bool:
        """
        Returns whether this component exists within current scene.

        :return: True if component meta node and its root transform node exist within current scene; False otherwise.
        :rtype: bool
        """

        try:
            return True if self._meta and self._meta.exists() else False
        except AttributeError:
            self.logger.warning(f'Component does not exist: {self.descriptor.name}', exc_info=True)

        return False

    def name(self) -> str:
        """
        Returns the name of the component from its descriptor.

        :return: component name.
        :rtype: str
        """

        return self.descriptor.name

    def side(self) -> str:
        """
        Returns the side of the component from its descriptor.

        :return: component side.
        :rtype: str
        """

        return self.descriptor.side

    def color(self) -> list[float, float, float]:
        """
        Returns the color of the component based on its side.

        :return: component color.
        :rtype: list[float, float, float]
        """

        return consts.SideColor[self.side().lower()[0]].value

    def region(self) -> str:
        """
        Returns the region of the component from its descriptor.

        :return: component region.
        :rtype: str
        """

        return self.descriptor.region

    def namespace(self) -> str:
        """
        Returns the current namespace for this component.

        :return: component namespace.
        :rtype: str
        """

        if self._meta is None:
            return ':'.join([api.OpenMaya.MNamespace.currentNamespace(), self.name()])

        name = api.OpenMaya.MNamespace.getNamespaceFromName(self._meta.fullPathName())
        root = api.OpenMaya.MNamespace.rootNamespace()
        if not name.startswith(root):
            name = root + name

        return name

    def parent_namespace(self) -> str:
        """
        Returns the parent namespace of this component namespace.

        :return: parent component namespace.
        :rtype: str
        """

        namespace = self.namespace()
        if not namespace:
            return api.OpenMaya.MNamespace.rootNamespace()

        current_namespace = api.OpenMaya.MNamespace.currentNamespace()
        api.OpenMaya.MNamespace.setCurrentNamespace(namespace)
        try:
            parent = api.OpenMaya.MNamespace.parentNamespace()
            api.OpenMaya.MNamespace.setCurrentNamespace(current_namespace)
        except RuntimeError:
            parent = api.OpenMaya.MNamespace.rootNamespace()

        return parent

    def rename_namespace(self, namespace: str) -> bool:
        """
        Renames the namespace which acts as the component name.

        :param str namespace: new namespace.
        :return: True if rename namespace operation was successful; False otherwise.
        :rtype: bool
        """

        component_namespace = self.namespace()
        if api.OpenMaya.MNamespace.namespaceExists(namespace):
            return False

        parent_namespace = self.parent_namespace()
        if parent_namespace == api.OpenMaya.MNamespace.rootNamespace():
            return False

        current_namespace = api.OpenMaya.MNamespace.currentNamespace()
        api.OpenMaya.MNamespace.setCurrentNamespace(parent_namespace)
        try:
            api.OpenMaya.MNamespace.renameNamespace(component_namespace, namespace)
            api.OpenMaya.MNamespace.setCurrentNamespace(current_namespace)
        except RuntimeError:
            self.logger.error(f'Failed to rename namespace: {component_namespace}-> {namespace}')
            return False

        return True

    def remove_namespace(self) -> bool:
        """
        Deletes the namespace of this component and moves all children to the root namespace.

        :return: True if the remove namespace operation was successful; False otherwise.
        :rtype: bool
        """

        namespace = self.namespace()
        if namespace:
            api.OpenMaya.MNamespace.moveNamespace(namespace, api.OpenMaya.MNamespace.rootNamespace(), True)
            api.OpenMaya.MNamespace.removeNamespace(namespace)
            return True

        return False

    def show(self) -> bool:
        """
        Shows the component by turning on the visibility on the root transform.

        :return: True if component was shown successfully; False otherwise.
        :rtype: bool
        """

        if not self.exists():
            return False

        return self._meta.root_transform().show()

    def hide(self) -> bool:
        """
        Hides the component by turning off the visibility on the root transform.

        :return: True if component was hidden successfully; False otherwise.
        :rtype: bool
        """

        if not self.exists():
            return False

        return self._meta.root_transform().hide()

    def current_naming_preset(self) -> Preset:
        """
        Returns the current naming convention preset instance for this component.

        :return: naming convention preset.
        :rtype: Preset
        """

        local_override = self.descriptor.get(consts.NAMING_PRESET_DESCRIPTOR_KEY)
        local_preset = self.configuration.name_presets_manager().find_preset(local_override) if local_override else None

        return local_preset if local_preset is not None else self.configuration.current_naming_preset

    def naming_manager(self) -> NameManager:
        """
        Returns the naming configuration for this component instance.

        :return: naming manager.
        :rtype: NameManager
        """

        naming_manager = self._build_objects_cache.get('naming')
        if naming_manager is not None:
            return naming_manager

        return self.configuration.find_name_manager_for_type(
            self.component_type, preset_name=self.current_naming_preset().name)

    def has_container(self) -> bool:
        """
        Returns whether this component has a container.

        :return: True if component has a container; False otherwise.
        :rtype: bool
        """

        return self.container() is not None

    def create_container(self) -> api.ContainerAsset | None:
        """
        Creates a new asset container if it is not already created and attaches it to this component instance.

        :return: newly created container asset instance.
        :rtype: api.ContainerAsset or None
        ..note:: this operation will not merge component nodes into the container.
        """

        if not self.configuration.use_containers:
            return None

        container = self.container()
        if container is not None:
            return container

        container = api.ContainerAsset()
        name, side = self.name(), self.side()
        container_name = naming.compose_container_name(self.naming_manager(), name, side)
        container.create(container_name)
        container.message.connect(self._meta.container)
        self._container = container

        return container

    def container(self) -> api.ContainerAsset | None:
        """
        Returns the container node which is retrieved from the meta node instance.

        :return: api.ContainerAsset or None
        """

        if not self._meta or not self._meta.exists() or not self.configuration.use_containers:
            return None

        source = self._meta.container.source()
        if source is not None:
            return api.ContainerAsset(source.node().object())

    def delete_container(self) -> bool:
        """
        Deletes the container of this component and all its contents.

        :return: True if the container deletion operation was successful; False otherwise.
        :rtype: bool
        """

        container = self.container()
        if not container:
            return False

        container.delete()

        return True

    def root_transform(self) -> api.DagNode | None:
        """
        Returns the root transform node for this component instance.

        :return: root transform instance.
        :rtype: api.DagNode or None
        """

        return self._meta.root_transform() if self.exists() else None

    def has_parent(self) -> bool:
        """
        Returns whether this component has a parent component.

        :return: True if this component has a parent component; False otherwise.
        :rtype: bool
        """

        if self._meta is None:
            return False

        for parent_meta in self._meta.iterate_meta_parents():
            if parent_meta.hasAttribute(consts.NODDLE_IS_COMPONENT_ATTR):
                return True

        return False

    def parent(self) -> Component | None:
        """
        Returns the parent component object for this component.

        :return: parent component.
        :rtype: Component or None
        """

        if self._meta is None:
            return None

        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get('parent')

        found_parent: Component | None = None
        for parent_meta in self._meta.iterate_meta_parents(recursive=False):
            if parent_meta.hasAttribute(consts.NODDLE_IS_COMPONENT_ATTR):
                found_parent = self._rig.component(
                    parent_meta.attribute(consts.NODDLE_NAME_ATTR).value(),
                    parent_meta.attribute(consts.NODDLE_SIDE_ATTR).value()
                )
                break

        return found_parent

    def set_parent(self, parent_component: Component | None, hook_id: str | None) -> bool:
        """
        Connects this component to the parent component.

        :param Component parent_component: parent component instance.
        :return: True if set parent component operation was successful; False otherwise.
        :rtype: bool
        """

        if parent_component == self:
            return False

        if parent_component is None:
            self.remove_all_parents()
            self._meta.add_meta_parent(self.rig.components_layer())
            return True

        did_set_parent = self._set_meta_parent(parent_component)
        if not did_set_parent:
            return False

        self.descriptor.parent = ':'.join([parent_component.name(), parent_component.side()])
        self.descriptor.hook = hook_id

        self.save_descriptor(self.descriptor)

        return True

    def remove_parent(self, parent_component: Component | None):
        """
        Removes parent relationship between this component and the parent component.

        :param Component or None parent_component: parent component to remove. If None, all parents will be removed.
        """

        if not self.exists():
            return

        parent = parent_component.meta if parent_component else None
        self._meta.remove_meta_parent(parent)
        self._meta.add_meta_parent(self._rig.components_layer())
        self.descriptor.parent = None
        self.descriptor.hook = ''
        self.descriptor.connections = {}
        self.save_descriptor(self.descriptor)

    def remove_all_parents(self):
        """
        Removes all parent components from the current component
        """

        if not self.exists():
            return

        parent_component = self.parent()
        if parent_component:
            self.remove_parent(parent_component)

    def iterate_children(self, depth_limit: int = 256) -> Iterator[Component]:
        """
        Generator function which iterates over all component children instances.

        :param int depth_limit: depth limit which to search within the meta network before stopping.
        :return: iterated component children instances.
        :rtype: Iterator[Component]
        """

        if not self.exists():
            return

        for child_meta in self._meta.iterate_meta_children(depth_limit=depth_limit):
            if child_meta.hasAttribute(consts.NODDLE_IS_COMPONENT_ATTR):
                child_component = self._rig.component(
                    child_meta.attribute(consts.NODDLE_NAME_ATTR).value(),
                    child_meta.attribute(consts.NODDLE_SIDE_ATTR).value())
                if child_component:
                    yield child_component

    def has_skeleton(self) -> bool:
        """
        Returns whether the skeleton for this component is already been built.

        :return: True if skeleton is already built; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.NODDLE_HAS_SKELETON_ATTR).value()

    def has_rig(self) -> bool:
        """
        Returns whether the rig for this component is already been built.

        :return: True if rig is already built; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.NODDLE_HAS_RIG_ATTR).value()

    def has_polished(self) -> bool:
        """
        Returns whether this component is already polished.

        :return: True if rig is already polished; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.NODDLE_HAS_POLISHED_ATTR).value()

    def find_layer(self, layer_type: str) -> layers.NoddleLayer | None:
        """
        Finds and returns the layer instance of given type for this component.

        :param str layer_type: layer type to get.
        :return: found layer meta node instance.
        :rtype: layers.NoddleLayer or None
        :raises ValueError: if given layer type is not supported.
        """

        if layer_type not in consts.LAYER_TYPES:
            raise ValueError('Unsupported layer type: {}, supported types: {}'.format(layer_type, consts.LAYER_TYPES))
        if not self.exists():
            return None

    def input_layer(self) -> layers.NoddleInputLayer | None:
        """
        Returns the input layer meta node instance for this component.

        :return: input layer meta node instance.
        :rtype: layers.NoddleInputLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.NoddleInputLayer.ID)

        return root.layer(consts.INPUT_LAYER_TYPE)

    def output_layer(self) -> layers.NoddleOutputLayer | None:
        """
        Returns the output layer meta node instance for this component.

        :return: output layer meta node instance.
        :rtype: layers.NoddleOutputLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.NoddleOutputLayer.ID)

        return root.layer(consts.OUTPUT_LAYER_TYPE)

    def skeleton_layer(self) -> layers.NoddleSkeletonLayer | None:
        """
        Returns skeleton layer meta node instance for this component.

        :return: skeleton layer meta node instance.
        :rtype: layers.CritSkeletonLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.NoddleSkeletonLayer.ID)

        return root.layer(consts.SKELETON_LAYER_TYPE)

    def rig_layer(self) -> layers.NoddleRigLayer | None:
        """
        Returns rig layer meta node instance for this component.

        :return: deform layer meta node instance.
        :rtype: layers.NoddleRigLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.NoddleRigLayer.ID)

        return root.layer(consts.RIG_LAYER_TYPE)

    def geometry_layer(self) -> layers.NoddleGeometryLayer | None:
        """
        Returns geometry layer meta node instance for this component.

        :return: geometry layer meta node instance.
        :rtype: layers.NoddleGeometryLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.NoddleGeometryLayer.ID)

        return root.layer(consts.GEOMETRY_LAYER_TYPE)

    def control_panel(self) -> nodes.SettingsNode | None:
        """
        Returns control panel instance for this rig layer instance.

        :return: control panel node from the scene.
        :rtype: nodes.SettingsNode or None
        """

        rig_layer = self.rig_layer()
        if not rig_layer:
            return None

        return rig_layer.control_panel()

    def id_mapping(self) -> dict:
        """
        Returns the guide ID -> layer node ID mapping acting as a lookup table.

        When live linking the joints with the guides this table is used to link the correct guide transform
        to deform joint. This table is used to figure out which joints should be deleted from the scene if the
        guide does not exist anymore.

        :return: layer ids mapping.
        :rtype: dict

        ..note:: this method can be overriden in subclasses, by default it maps the guide id as 1-1.
        """

        ids = {k.id: k.id for k in self.descriptor.skeleton_layer.iterate_joints()}
        return {
            consts.SKELETON_LAYER_TYPE: ids,
            consts.INPUT_LAYER_TYPE: ids,
            consts.OUTPUT_LAYER_TYPE: ids,
            consts.RIG_LAYER_TYPE: ids
        }

    @profiler.fn_timer
    def serialize_from_scene(self, layer_ids: Iterable[str] | None = None) -> descriptor_component.ComponentDescriptor:
        """
        Serializes the component from the root transform down using the individual layers.

        :param Iterable[str] layer_ids: optional iterable of CRIT layer IDs that should be serialized.
        :return: component descriptor.
        :rtype: descriptor_component.ComponentDescriptor
        """

        if not self.has_skeleton() and not self.has_rig():
            try:
                self._descriptor.update(descriptor_component.parse_raw_descriptor(self._meta.raw_descriptor_data()))
            except ValueError:
                self.logger.warning('Descriptor in scene is not valid, skipping descriptor update!')
            return self._descriptor

        descriptor = self._meta.serializeFromScene(layer_ids)
        parent_component = self.parent()
        descriptor['parent'] = ':'.join([parent_component.name(), parent_component.side()]) if parent_component else ''
        self._descriptor.update(descriptor)
        self.save_descriptor(self._descriptor)

        return self._descriptor

    def setup_inputs(self):
        """
        Set up the input layer for this component.
        """

        def _build_input(_input_descriptor: InputDescriptor) -> nodes.InputNode:
            """
            Internal function that creates an input node instance from given input descriptor data.

            :param InputDescriptor _input_descriptor: input descriptor instance.
            :return: input node created from input descriptor.
            :rtype: nodes.InputNode
            """

            parent = root_transform if _input_descriptor.parent is None else input_layer.input_node(
                _input_descriptor.parent)
            try:
                input_node = input_layer.input_node(_input_descriptor.id)
            except errors.NoddleInvalidInputNodeMetaData:
                input_node = None
            if input_node is None:
                _input_descriptor.name = name_manager.resolve(
                    'inputName', {'componentName': name, 'side': side, 'type': 'input', 'id': _input_descriptor.id})
                input_node = input_layer.create_input(**_input_descriptor)

            input_node.setParent(parent, maintain_offset=True)

            return input_node

        name, side = self.name(), self.side()
        name_manager = self.naming_manager()
        hierarchy_name, meta_name = naming.compose_names_for_layer(
                self.naming_manager(), self.name(), self.side(), 'inputs')
        input_layer = self._meta.create_layer(
            consts.INPUT_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        root_transform = input_layer.root_transform()
        if root_transform is None:
            root_transform = input_layer.create_transform(name=hierarchy_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.NoddleInputLayer.ID] = input_layer

        descriptor = self.descriptor
        input_layer_descriptor = descriptor.input_layer
        current_inputs = {input_node.id(): input_node for input_node in input_layer.iterate_inputs()}
        new_inputs: dict[str, nodes.InputNode] = {}
        for input_descriptor in input_layer_descriptor.iterate_inputs():
            input_node = _build_input(input_descriptor)
            new_inputs[input_descriptor.id] = input_node

        # remove any input node that does not exist anymore
        for input_id, input_node in current_inputs.items():
            if input_id in new_inputs:
                continue
            parent_node = input_node.parent()
            for child in input_node.children((api.kTransform,)):
                child.setParent(parent_node)
            input_layer.delete_input(input_id)

        input_settings = input_layer_descriptor.settings
        for setting in iter(input_settings):
            input_layer.addAttribute(**setting)

    def setup_outputs(self, parent_node: nodes.Joint | api.DagNode):
        """
        Set up the output layer for this component.

        :param api.DagNode parent_node: parent node.
        """

        def _build_output(_output_descriptor: OutputDescriptor) -> nodes.OutputNode:
            """
            Internal function that creates an output node instance from given output descriptor data.

            :param OutputDescriptor _output_descriptor: output descriptor instance.
            :return: output node created from output descriptor.
            :rtype: nodes.OutputNode
            """

            parent = root_transform if _output_descriptor.parent is None else output_layer.output_node(
                _output_descriptor.parent)
            try:
                output_node = output_layer.output_node(_output_descriptor.id)
            except errors.NoddleInvalidOutputNodeMetaData:
                output_node = None
            if output_node is None:
                _output_descriptor.name = name_manager.resolve(
                    'outputName', {'componentName': name, 'side': side, 'type': 'output', 'id': _output_descriptor.id})
                output_node = output_layer.create_output(**_output_descriptor)

            output_node.setParent(parent, maintain_offset=True)

            return output_node

        name, side = self.name(), self.side()
        name_manager = self.naming_manager()
        hierarchy_name, meta_name = naming.compose_names_for_layer(
            self.naming_manager(), self.name(), self.side(), 'outputs')
        output_layer = self._meta.create_layer(
            consts.OUTPUT_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        root_transform = output_layer.root_transform()
        if root_transform is None:
            root_transform = output_layer.create_transform(name=hierarchy_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.NoddleOutputLayer.ID] = output_layer

        descriptor = self.descriptor
        output_layer_descriptor = descriptor.output_layer
        current_outputs = {output_node.id(): output_node for output_node in output_layer.iterate_outputs()}
        new_outputs = {}
        for output_descriptor in output_layer_descriptor.iterate_outputs():
            output_node = _build_output(output_descriptor)
            new_outputs[output_node.id] = output_node

        # remove any output node that does not exist anymore
        for output_id, output_node in current_outputs.items():
            if output_id in new_outputs:
                continue
            parent_node = output_node.parent()
            for child in output_node.children((api.kTransform,)):
                child.setParent(parent_node)
            output_layer.delete_output(output_id)

        output_settings = output_layer_descriptor.settings
        for setting in iter(output_settings):
            output_layer.addAttribute(**setting)

    def component_parent_joint(self, parent_node: api.DagNode) -> nodes.Joint | api.DagNode:
        """
        Returns the parent component connected joint.

        :param api.DagNode parent_node: parent node.
        :return: component parent joint.
        :rtype: nodes.Joint or api.DagNode
        """

        parent_node = parent_node or self.skeleton_layer().root_transform()
        child_input_layer = self.input_layer()
        if not child_input_layer:
            return parent_node
        parent_component = self.parent()
        if not parent_component:
            return parent_node
        parent_skeleton_layer = parent_component.skeleton_layer()
        if not parent_skeleton_layer:
            return parent_node

        input_element = child_input_layer.root_input_plug()
        for source_input in input_element.child(3):
            output_node_plug = source_input.child(0).source()
            if output_node_plug is None:
                continue
            parent_output_layer = layers.NoddleOutputLayer(output_node_plug.node().object())
            parent_output_root_transform = parent_output_layer.root_transform()
            output_id = output_node_plug.parent().child(1).value()
            parent_joint = parent_skeleton_layer.joint(output_id)
            if not parent_joint:
                parent_joints = {i.id(): i for i in parent_skeleton_layer.iterate_joints()}
                total_joints = len(list(parent_joints.keys()))
                if total_joints == 0:
                    return parent_node
                if total_joints == 1:
                    return list(parent_joints.values())[0]
                parent_output_node = output_node_plug.sourceNode()
                while parent_joint is None:
                    parent_output_node = parent_output_node.parent()
                    if parent_output_node == parent_output_root_transform:
                        break
                    output_id = parent_output_node.attribute(consts.NODDLE_ID_ATTR).value()
                    parent_joint = parent_joints.get(output_id)
            return parent_joint or parent_node

        return parent_node

    @profiler.fn_timer
    def build_skeleton(self, parent_node: api.DagNode | None = None) -> bool:
        """
        Builds the skeleton system for this component.

        :param api.DagNode or None parent_node: optional parent node component skeleton root joint will be parented
            under.
        :return: True if build guide operation was successful; False otherwise.
        :rtype: bool
        :raises errors.CritComponentDoesNotExistError: if the component does not exist.
        :raises errors.CritBuildComponentGuideUnknownError: if an unknown error occurs while building the guide system.
        """

        if not self.exists():
            raise errors.NoddleComponentDoesNotExistError(self.descriptor.name)

        self._generate_objects_cache()

        if self.has_polished():
            self._set_has_polished(False)

        self._is_building_skeleton = True

        container = self.container()
        if container is None:
            container = self.create_container()
            self._build_objects_cache['container'] = container
        if container is not None:
            container.makeCurrent(True)
            container.lock(False)

        self.logger.info('Starting skeleton building with namespace: {}'.format(self.namespace()))
        try:
            self.setup_inputs()
            hierarchy_name, meta_name = naming.compose_names_for_layer(
                self.naming_manager(), self.name(), self.side(), 'skeleton')
            skeleton_layer = self._meta.create_layer(
                consts.SKELETON_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
            skeleton_layer.update_metadata(self.descriptor.skeleton_layer.get(consts.METADATA_DESCRIPTOR_KEY, []))
            self._build_objects_cache[layers.NoddleSkeletonLayer.ID] = skeleton_layer
            if container:
                container.addNode(skeleton_layer)
            parent_joint = self.component_parent_joint(parent_node)
            self.pre_setup_skeleton_layer()
            self.setup_skeleton_layer(parent_joint)
            self.setup_outputs(parent_joint)
            self.blackbox = False
            self.save_descriptor(self._descriptor)
            self._set_has_skeleton(True)
        except Exception as exc:
            self.logger.error('Failed to setup skeleton: {}'.format(exc), exc_info=True)
            self._set_has_skeleton(False)
            raise errors.NoddleBuildComponentSkeletonUnknownError(
                'Failed {}'.format('_'.join([self.name(), self.side()])))
        finally:
            if container is not None:
                container.makeCurrent(False)
            self._is_building_skeleton = False
            self._build_objects_cache.clear()

        return True

    def pre_setup_skeleton_layer(self):
        """
        Pre setup skeleton layer based on the descriptor.

        Tries to find the joint chain used by this component within descriptor. If it is not defined, we try to find
        that data based on the startJoint and endJoint skeleton layer descriptor setting values. If the start and end
        joints are defined we try to find those joints data within based on current scene joints.
        """

        descriptor = self.descriptor
        skeleton_layer_descriptor = descriptor.skeleton_layer
        naming_manager = self.naming_manager()

        joint_descriptors = {joint.id: joint for joint in skeleton_layer_descriptor.iterate_joints()}
        if not joint_descriptors:
            start_joint = skeleton_layer_descriptor.setting('startJoint').value
            end_joint = skeleton_layer_descriptor.setting('endJoint').value or start_joint
            joint_chain = joints.joint_chain(api.node_by_name(start_joint), api.node_by_name(end_joint))
            joints.validate_rotations(joint_chain)
            for joint in joint_chain:
                data = joint.serializeFromScene()
                joint_id = data['name'].split('|')[-1]
                parent_id = data['parent'].split('|')[-1]
                joint_name = naming_manager.resolve(
                    'skinJointName',
                    {'componentName': self.name(), 'side': self.side(), 'id': joint_id, 'type': 'joint'})
                parent_descriptor = skeleton_layer_descriptor.joint(parent_id)
                skeleton_layer_descriptor.add_joint(descriptor_nodes.JointDescriptor(
                    name=joint_name, id=joint_id, type=data['type'], translate=data['translate'],
                    rotate=data['rotate'], scale=data['scale'], rotateOrder=data['rotateOrder'],
                    parent=parent_descriptor.id if parent_descriptor else None))

    def setup_selection_set_joints(
            self, skeleton_layer: layers.NoddleSkeletonLayer,
            deform_joints: dict[str, nodes.Joint]) -> list[nodes.Joint]:
        """
        Function that handles the addition of joints into the skeleton layer deform joints selection set.

        :param layers.NoddleSkeletonLayer skeleton_layer: skeleton layer instance.
        :param dict[str, nodes.Joint] deform_joints: list of default skeleton layer bind joints.
        :return: list of bind joints to add.
        :rtype: list[nodes.Joint]
        """

        if deform_joints:
            return list(deform_joints.values())

        return []

    def setup_skeleton_layer(self, parent_joint: nodes.Joint):
        """
        Setup skeleton layer for this component.

        :param meta_nodes.Joint or api.DagNode parent_joint: parent joint or node which the joints will be parented
            under.
        """

        skeleton_layer = self.skeleton_layer()
        descriptor = self.descriptor
        skeleton_layer_descriptor = descriptor.skeleton_layer
        naming_manager = self.naming_manager()

        existing_joints = {joint.id(): joint for joint in skeleton_layer.iterate_joints()}
        new_joint_ids: dict[str, nodes.Joint] = {}
        primary_root_joint = parent_joint or skeleton_layer.root_transform()

        for joint_descriptor in skeleton_layer_descriptor.iterate_joints():
            existing_joint = existing_joints.get(joint_descriptor.id)
            joint_descriptor_parent = joint_descriptor.get('parent')
            if joint_descriptor_parent is None:
                joint_parent = primary_root_joint
            else:
                joint_parent = existing_joints[joint_descriptor_parent]
            joint_name = naming_manager.resolve(
                'skinJointName',
                {'componentName': self.name(), 'side': self.side(), 'id': joint_descriptor.id, 'type': 'joint'})

            # When we have an existing joint we need to update its transforms.
            if existing_joint:
                new_joint_ids[joint_descriptor.id] = existing_joint
                existing_joint.rotateOrder.set(joint_descriptor.rotateOrder)
                existing_joint.segmentScaleCompensate.set(0)
                existing_joint.setParent(joint_parent)
                existing_joint.rename(joint_name)
                continue

            new_joint = skeleton_layer.create_joint(
                name=joint_name,
                id=joint_descriptor.id,
                rotateOrder=joint_descriptor.rotateOrder,
                translate=joint_descriptor.translate,
                rotate=joint_descriptor.rotate,
                parent=joint_parent
            )
            new_joint.segmentScaleCompensate.set(False)
            existing_joints[joint_descriptor.id] = new_joint
            new_joint_ids[joint_descriptor.id] = new_joint

        # purge any joints which were removed from the descriptor. this can happen in dynamically generated components.
        for joint_id, existing_joint in existing_joints.items():
            if joint_id in new_joint_ids:
                continue
            parent_node = existing_joint.parent()
            for child in existing_joint.children((api.kTransform, api.kJoint)):
                child.setParent(parent_node)
            print('deleting ....')
            skeleton_layer.delete_joint(joint_id)

        # Binding components deform joints to the selection set. removing anything we don't need any more
        selection_set = skeleton_layer.selection_set()
        if selection_set is None:
            name = naming_manager.resolve(
                'selectionSet', {
                    'componentName': self.name(), 'side': self.side(), 'selectionSet': "componentDeform",
                    'type': 'objectSet'})
            selection_set = skeleton_layer.create_selection_set(name, parent=self.rig.meta.selection_sets()['skeleton'])

        bind_joints = self.setup_selection_set_joints(skeleton_layer, new_joint_ids)
        current_selection_set_members = selection_set.members(True)
        to_remove = [i for i in current_selection_set_members if i not in bind_joints]
        if to_remove:
            selection_set.removeMembers(to_remove)
        if bind_joints:
            selection_set.addMembers(bind_joints)
        # skeleton_layer.set_live_link(
        # 	self.input_layer().setting_node(consts.NODDLE_INPUT_OFFSET_ATTR_NAME_ATTR),
        # 	id_mapping=self.id_mapping()[consts.SKELETON_LAYER_TYPE], state=True)

    @profiler.fn_timer
    def build_rig(self, parent_node: api.DagNode | None = None) -> bool:
        """
        Builds the rig for this component.

        :param api.DagNode or None parent_node: parent node for the rig to be parented to. If None, the rig will not be
            parented to anything.
        :return: True if the component rig was built successfully; False otherwise.
        :raises errors.NoddleComponentDoesNotExistError: if the current component does not exist.
        :raises errors.NoddleBuildComponentRigUnknownError: if the component build rig process fails.
        """

        if not self.exists():
            raise errors.NoddleComponentDoesNotExistError(self.descriptor.name)
        elif self.has_rig():
            self.logger.info(f'Component "{self.name()}" already have a rig, skipping the build!')
            return True

        if not self.skeleton_layer():
            self.build_skeleton()

        self._generate_objects_cache()
        if self.has_polished():
            self._set_has_polished(False)

        self.serialize_from_scene()

        self._is_building_rig = True
        container = self.container()
        try:
            if container is None and self.configuration.use_containers:
                container = self.create_container()
                self._build_objects_cache['container'] = container
            if container is not None:
                container.makeCurrent(True)
                container.lock(False)
            parent_joint = self.component_parent_joint(parent_node)
            self.pre_setup_rig(parent_joint)
            self.setup_rig(parent_joint)
            self.post_setup_rig(parent_joint)
            self._set_has_rig(True)
            self.blackbox = self.configuration.blackbox
            self.save_descriptor(self._descriptor)
        except Exception:
            msg = f'Failed to build rig for component {"_".join([self.name(), self.side()])}'
            self.logger.error(msg, exc_info=True)
            raise errors.NoddleBuildComponentRigUnknownError(msg)
        finally:
            self._is_building_rig = False
            if container is not None:
                container.makeCurrent(False)
                self._build_objects_cache.clear()

        # return True

    def pre_setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        """
        Pre setup rig function that is run before setup_rig function is called.

        :param  nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        component_name, component_side = self.name(), self.side()
        hierarchy_name, meta_name = naming.compose_names_for_layer(
            self.naming_manager(), component_name, component_side, 'rig')
        rig_layer = self._meta.create_layer(
            consts.RIG_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.NoddleRigLayer.ID] = rig_layer
        name = self.naming_manager().resolve(
            'settingsName', {
                'componentName': component_name, 'side': component_side, 'section': consts.RIG_LAYER_TYPE,
                'type': 'settings'})
        rig_layer.create_settings_node(name, attr_name=consts.CONTROL_PANEL_TYPE)
        self._setup_rig_settings()

    @decorators.abstractmethod
    def setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        """
        Main rig setup function. Can be overriden to customize the way rig are created in custom components.

        :param  nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        raise NotImplementedError

    def post_setup_rig(self, parent_node: nodes.Joint | api.DagNode | None = None):
        """
        Post setup rig function that is run after setup_rig function is called.

        :param  nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        descriptor = self.descriptor
        control_panel = self.control_panel()
        rig_layer = self.rig_layer()

        parent_component = self.parent()
        if parent_component is not None and descriptor.hook:
            parent_output_hook = parent_component.output_layer().find_output_nodes(descriptor.hook)[0]
            if parent_output_hook:
                parent_input = self.input_layer().find_inputs('parent')[0]
                _, parent_constraint_nodes = api.build_constraint(
                    parent_input,
                    drivers={
                        'targets': (
                            (parent_output_hook.fullPathName(partial_name=True, include_namespace=False),
                             parent_output_hook),)},
                    constraint_type='parent', maintainOffset=True
                )
                rig_layer.add_extra_nodes(parent_constraint_nodes)
            else:
                self.logger.warning(
                    f'Was not possible to attach {self} to component {parent_component} because no output hook with '
                    f'ID {descriptor.hook} found')

        controller_tag_plug = control_panel.addAttribute(
            **dict(
                name=consts.NODDLE_CONTROL_NODE_ATTR, type=api.kMFnkEnumAttribute, keyable=False, channelBox=True,
                enums=['Not Overridden', 'Inherit Parent Controller', 'Show on Mouse Proximity']
            )
        )
        controls = list(rig_layer.iterate_controls())
        selection_set = rig_layer.selection_set()
        if selection_set is None:
            selection_set_name = self.naming_manager().resolve(
                'selectionSet',
                {'componentName': self.name(), 'side': self.side(), 'selectionSet': 'componentCtrls',
                 'type': 'objectSet'})
            selection_set = rig_layer.create_selection_set(
                selection_set_name, parent=self.rig.meta.selection_sets()['ctrls'])
        controller_tags = list(self._create_rig_controller_tags(controls, controller_tag_plug))
        selection_set.addMembers(controls + [control_panel])
        rig_layer.add_extra_nodes(controller_tags)

        container = self._merge_component_into_container()

        if container is not None:
            container.publishNodes(list(rig_layer.iterate_controls()) + controller_tags)
            container.publishAttributes(
                [i for i in control_panel.iterateExtraAttributes() if i.partialName(
                    include_node_name=False) not in consts.ATTRIBUTES_TO_SKIP_PUBLISH])

        for rig_joint in rig_layer.iterate_joints():
            rig_joint.hide()

        # layout_id = self.descriptor.get(consts.RIG_MARKING_MENU_DESCRIPTOR_KYE) or consts.DEFAULT_RIG_MARKING_MENU
        # components.create_triggers(rig_layer, layout_id)

    def setup_space_switches(self):
        """
        Function that handles the creation of space switches based on component descriptor data.
        This method is called after the rig is built.
        """

        rig = self.rig
        rig_layer = self.rig_layer()

    def _descriptor_from_scene(self) -> descriptor_component.ComponentDescriptor | None:
        """
        Internal function that tries to retrieve the descriptor from this component meta node instance.

        :return: component descriptor.
        :rtype: descriptor_component.ComponentDescriptor or None
        """

        if not self._meta or not self._meta.exists():
            return None

        data = self._meta.raw_descriptor_data()
        translated_data = descriptor_component.parse_raw_descriptor(data)
        return descriptor_component.load_descriptor(translated_data, self._original_descriptor)

    def _generate_objects_cache(self):
        """
        Internal function that initializes internal build objects cache.
        """

        self._build_objects_cache = self._meta.layer_id_mapping()
        self._build_objects_cache['container'] = self.container()
        self._build_objects_cache['parent'] = self.parent()
        self._build_objects_cache['naming'] = self.naming_manager()

    def _set_meta_parent(self, parent_component: Component) -> bool:
        """
        Internal function that sets the internal meta parent.

        :param Component parent_component: parent component.
        :return: True if meta parent was set successfully; False otherwise.
        :rtype: bool
        """

        if self._meta is None:
            self.logger.warning(f'Component "{self}" has no meta node specified!')
            return False

        parents = list(self._meta.iterate_meta_parents())
        if parent_component.meta in parents:
            return True

        self.remove_all_parents()
        for parent in parents:
            if parent.attribute(base.MCLASS_ATTR_NAME).asString() == consts.COMPONENTS_LAYER_TYPE:
                self._meta.remove_meta_parent(parent)
                break

        self._meta.add_meta_parent(parent_component.meta)

        return True

    def _set_has_skeleton(self, flag: bool):
        """
        Internal function that updates the has skeleton attribute of the meta node instance.

        :param bool flag: True if component has skeleton; False otherwise.
        """

        self.logger.debug('Setting hasSkeleton to: {}'.format(flag))
        has_skeleton_attr = self._meta.attribute(consts.NODDLE_HAS_SKELETON_ATTR)
        has_skeleton_attr.isLocked = False
        has_skeleton_attr.setBool(flag)

    def _set_has_rig(self, flag: bool):
        """
        Internal function that updates the has rig attribute of the meta node instance.

        :param bool flag: True if component has a rig; False otherwise.
        """

        self.logger.debug('Setting hasRig to: {}'.format(flag))
        has_rig_attr = self._meta.attribute(consts.NODDLE_HAS_RIG_ATTR)
        has_rig_attr.isLocked = False
        has_rig_attr.setBool(flag)

    def _set_has_polished(self, flag: bool):
        """
        Internal function that updates the has hasPolished attribute of the meta node instance.

        :param bool flag: True if component has been polished; False otherwise.
        """

        self.logger.debug('Setting hasPolished to: {}'.format(flag))
        has_rig_attr = self._meta.attribute(consts.NODDLE_HAS_POLISHED_ATTR)
        has_rig_attr.isLocked = False
        has_rig_attr.setBool(flag)

    def _setup_rig_settings(self):
        """
        Internal function that setup rig settings.
        """

        rig_layer = self.rig_layer()
        settings = self.descriptor.rig_layer.get('settings', {})
        # space_switching = self.descriptor.space_switching
        control_panel_descriptor = settings.get('controlPanel', [])
        # spaceswitch.merge_attributes_with_space_switches(control_panel_descriptor, space_switching, exclude_active=True)
        if control_panel_descriptor:
            settings['controlPanel'] = control_panel_descriptor
        naming_manager = self.naming_manager()
        component_name, component_side = self.name(), self.side()
        for name, attr_data in iter(settings.items()):
            node = rig_layer.setting_node(name)
            if node is None:
                attr_name = name
                name = naming_manager.resolve(
                    'settingsName', {
                        'componentName': component_name, 'side': component_side, 'section': name, 'type': 'settings'})
                node = rig_layer.create_settings_node(name, attr_name=attr_name)
            for i in iter(attr_data):
                node.addAttribute(**i)

    def _create_rig_controller_tags(self, controls: list[nodes.ControlNode], visibility_plug: api.Plug):
        """
        Creates rig controller tags for given controls.

        :param list[nodes.ControlNode] controls: control nodes instance we want to create tags of.
        :param api.Plug visibility_plug: plug that will connect controller tag to.
        """

        parent = None
        for control in controls:
            yield control.add_controller_tag(
                name='_'.join([control.name(), 'tag']), parent=parent, visibility_plug=visibility_plug)
            parent = control

    @profiler.fn_timer
    def _merge_component_into_container(self) -> api.ContainerAsset | None:
        """
        Internal function that takes all connected nodes recursively and add them to the container. A new container
        will be created if it does not exist.

        :return: component asset container.
        :rtype: api.ContainerAsset or None
        """

        container = self.container()
        if container is None and self.configuration.use_containers:
            container = self.create_container()
        if container is None:
            return None

        self.logger.debug('Merging nodes which are missing from container')
        meta = self._meta
        root_transform = meta.root_transform()
        nodes_to_add = [root_transform, meta]

        for found_layer in meta.layers_by_id((
                consts.INPUT_LAYER_TYPE, consts.OUTPUT_LAYER_TYPE, consts.SKELETON_LAYER_TYPE,
                consts.RIG_LAYER_TYPE, consts.XGROUP_LAYER_TYPE)).values():
            if not found_layer:
                continue
            objects = [found_layer, found_layer.root_transform()] + list(found_layer.iterate_settings_nodes())
            objects.extend(list(found_layer.iterate_extra_nodes()))
            nodes_to_add.extend(object for obj in objects if obj not in nodes_to_add)

        if nodes_to_add:
            container.addNodes(nodes_to_add)

        return container
