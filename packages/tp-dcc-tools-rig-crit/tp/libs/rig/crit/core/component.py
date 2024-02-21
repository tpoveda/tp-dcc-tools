from __future__ import annotations

import copy
import json
import typing
import contextlib
from typing import Iterator, Iterable

from tp.bootstrap import log
from tp.common.python import profiler, decorators
from tp.maya import api
from tp.maya.cmds import helpers
from tp.maya.meta import base

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import errors, naming
from tp.libs.rig.crit.descriptors import component, spaceswitch
from tp.libs.rig.crit.functions import components
from tp.libs.rig.crit.meta import layers, nodes as meta_nodes, component as meta_component

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.meta.rig import CritRig
    from tp.libs.rig.crit.core.namingpresets import Preset
    from tp.libs.rig.crit.core.config import Configuration
    from tp.libs.rig.crit.descriptors.layers import GuideLayerDescriptor
    from tp.libs.rig.crit.descriptors.nodes import GuideDescriptor, InputDescriptor, OutputDescriptor

logger = log.tpLogger


def construct_component_order(components: list[Component]) -> dict[Component, Component]:
    """
    Handles the component order based on DG order. Parent components will be built before child components.

    :param list[Component] components: list of components to build.
    :return: list of components ordered by build order.
    :rtype: dict[Component, Component]
    """

    unsorted = {}
    for found_component in components:
        parent = found_component.parent()
        unsorted[found_component] = parent

    ordered = {}
    while unsorted:
        for child, parent in list(unsorted.items()):
            if parent in unsorted:
                continue
            else:
                del(unsorted[child])
                ordered[child] = parent

    return ordered


def reset_joint_transforms(
        skeleton_layer: layers.CritSkeletonLayer, guide_layer_descriptor: GuideLayerDescriptor, id_mapping: dict):
    """
    Resets all joints on the given skeleton layer to match the guide descriptor.

    :param layers.CritSkeletonLayer skeleton_layer: component skeleton layer instance.
    :param GuideLayerDescriptor guide_layer_descriptor: component guide layer
        descriptor instance.
    :param dict id_mapping:
    """

    descriptor_id_map = id_mapping[consts.SKELETON_LAYER_TYPE]
    joint_mapping = {v: k for k, v in descriptor_id_map.items()}
    guide_descriptors = {
        i.id: i for i in guide_layer_descriptor.find_guides(*descriptor_id_map.keys()) if i is not None}
    for joint in skeleton_layer.iterate_joints():
        guide_id = joint_mapping.get(joint.id())
        if not guide_id:
            continue
        guide_descriptor: GuideDescriptor = guide_descriptors.get(guide_id)
        world_matrix = guide_descriptor.transformation_matrix(scale=False)
        world_matrix.setScale((1, 1, 1), api.kWorldSpace)
        joint.resetTransform()
        joint.setWorldMatrix(world_matrix.asMatrix())


@contextlib.contextmanager
def disconnect_components_context(components: list[Component]):
    """
    Context manager which disconnects the list of given components temporally. Yields once all
    components are disconnected.

    :param list[Component] components: list of components to temporally disconnect.
    """

    visited = set()
    for _component in components:
        if _component not in visited:
            _component.pin()
            visited.add(_component)
        for child in _component.iterate_children(depth_limit=1):
            if child in visited:
                continue
            visited.add(child)
            child.pin()
    yield
    for i in visited:
        i.unpin()


def generate_connection_binding_guide(component: Component) -> tuple[dict, layers.CritGuideLayer]:
    """
    Generates the connection binding data for the given component.

    :param Component component: component we want to generate connection binding guide data for.
    :return: component binding guide data.
    :rtype: tuple[dict, CritGuideLayer]
    """

    binding = {}
    name, side = component.name(), component.side()
    child_layer = component.guide_layer()
    binding[':'.join([name, side, 'root'])] = child_layer.guide('root')

    current_parent = component.parent()
    if current_parent:
        name, side = current_parent.name(), current_parent.side()
        layer = current_parent.guide_layer()
        for found_guide in layer.iterate_guides():
            binding[':'.join([name, side, found_guide.id()])] = found_guide

    return binding, child_layer


class Component:
    """
    Component class that encapsulates a single rigging component.
    """

    ID = ''
    ICON = 'tpdcc'
    DOCUMENTATION = ''
    REQUIRED_PLUGINS = list()
    BETA_VERSION = False

    def __init__(
            self, rig: Rig, descriptor: component.ComponentDescriptor | None = None,
            meta: meta_component.CritComponent | None = None):
        super().__init__()

        self._meta = meta
        self._rig = rig
        self._descriptor = None
        self._original_descriptor: component.ComponentDescriptor | None = None
        self._container = None
        self._configuration = rig.configuration
        self._is_building_guide = False
        self._is_building_skeleton = False
        self._is_building_rig = False
        self._build_objects_cache = dict()

        if descriptor is None and meta is not None:
            no_component_type = False
            component_type = meta.attribute(consts.CRIT_COMPONENT_TYPE_ATTR).asString()
            if not component_type:
                no_component_type = True
                component_type = self.ID
            component_descriptor = self.configuration.initialize_component_descriptor(component_type)
            if no_component_type:
                meta.attribute(consts.CRIT_COMPONENT_TYPE_ATTR).set(component_type)
            self._original_descriptor = self.configuration.components_manager().load_component_descriptor(
                component_type)
            scene_state = self._descriptor_from_scene()
            if scene_state:
                scene_data = component.migrate_to_latest_version(scene_state, original_descriptor=component_descriptor)
                component_descriptor.update(scene_data)
            self._descriptor = component_descriptor
        elif descriptor and meta:
            self._original_descriptor = copy.deepcopy(descriptor)
            self._descriptor = self._descriptor_from_scene()
        else:
            self._original_descriptor = descriptor
            self._descriptor = copy.deepcopy(descriptor)

        self.logger = log.get_logger('.'.join([__name__, '_'.join([self.name(), self.side()])]))

    def __hash__(self):
        return hash(self._meta) if self._meta is not None else hash(id(self))

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>-{self.name()}:{self.side()}'

    def __bool__(self) -> bool:
        return self.exists()

    def __eq__(self, other: Component) -> bool:
        return other is not None and isinstance(other, Component) and self._meta == other.meta

    def __ne__(self, other: Component) -> bool:
        return other is not None and isinstance(other, Component) and self._meta != other.meta

    @classmethod
    def load_required_plugins(cls):
        """
        Loads all required plugins for this component to work as expected.

        :raises Exception: if something went wrong while loading plugins.
        """

        for plugin_name in cls.REQUIRED_PLUGINS:
            if not helpers.is_plugin_loaded(plugin_name):
                try:
                    logger.info(f'Loading plugin {plugin_name} required by {cls}')
                    helpers.load_plugin(plugin_name, quiet=True)
                except Exception:
                    logger.exception(f'Failed to load plugin {plugin_name} required by {cls}')
                    raise

    @property
    def meta(self) -> meta_component.CritComponent:
        """
        Returns component meta node instance.

        :return: meta node instance.
        :rtype: meta_component.CritComponent
        """

        return self._meta

    @meta.setter
    def meta(self, value: meta_component.CritComponent):
        """
        Sets component meta node instance.

        :param meta_component.CritComponent value: meta node instance to set.
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
            consts.CRIT_COMPONENT_TYPE_ATTR).asString()

    @property
    def rig(self) -> Rig:
        """
        Returns the current rig instance this component belongs to.

        :return: rig instance.
        :rtype: Rig
        """

        return self._rig

    @property
    def descriptor(self) -> component.ComponentDescriptor:
        """
        Returns the component descriptor instance.

        :return: component descriptor instance.
        :rtype: component.ComponentDescriptor
        """

        return self._descriptor

    @descriptor.setter
    def descriptor(self, value: component.ComponentDescriptor):
        """
        Sets the component descriptor.

        :param component.ComponentDescriptor value: component descriptor to set.
        """

        if type(value) == dict:
            value = component.load_descriptor(value, self._original_descriptor)

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
    def create(
            self, parent: CritRig | None = None) -> meta_component.CritComponent:
        """
        Creates the component within current scene.

        :param CritRig or None parent: optional rig parent layer which component will connect to via its meta node
            instance.
        :return: newly created component meta node instance.
        :rtype: meta_component.CritComponent
        """

        if not parent or not isinstance(parent, layers.CritComponentsLayer):
            parent = None

        self.load_required_plugins()

        self.logger.debug('Creating component stub in current scene...')
        descriptor = self.descriptor
        naming_manager = self.naming_manager()
        component_name, side = self.name(), self.side()
        hierarchy_name, meta_name = naming.compose_component_root_names(naming_manager, component_name, side)
        self.logger.debug('Creating Component meta node instance...')
        meta_node = meta_component.CritComponent(name=meta_name, parent=parent)
        meta_node.attribute(consts.CRIT_NAME_ATTR).set(component_name)
        meta_node.attribute(consts.CRIT_SIDE_ATTR).set(side)
        meta_node.attribute(consts.CRIT_ID_ATTR).set(component_name)
        meta_node.attribute(consts.CRIT_VERSION_ATTR).set(str(descriptor.get('version', '')))
        meta_node.attribute(consts.CRIT_COMPONENT_TYPE_ATTR).set(descriptor.get('type', ''))
        notes = meta_node.attribute('notes')
        if notes is None:
            meta_node.addAttribute('notes', type=api.kMFnDataString, value=self.DOCUMENTATION)
        else:
            notes.set(self.DOCUMENTATION)
        parent_transform = parent.root_transform() if parent else None
        meta_node.create_transform(hierarchy_name, parent=parent_transform)
        self._meta = meta_node

        return meta_node

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

    def is_hidden(self) -> bool:
        """
        Returns whether component is hidden in the scene.

        :return: True if component is hidden; False otherwise.
        :rtype: bool
        """

        return self.exists() and self._meta.root_transform().isHidden()

    def is_enabled(self) -> bool:
        """
        Returns whether component is enabled.

        :return: True if component is enabled; False otherwise.
        :rtype: bool
        """

        if self.exists():
            enabled = self._meta.attribute(consts.CRIT_IS_ENABLED_ATTR).asBool()
            if enabled:
                parent = self.parent()
                while parent:
                    _enabled = parent.is_enabled()
                    if not _enabled:
                        return False
                    parent = parent.parent()

        return self.descriptor.get(consts.ENABLED_DESCRIPTOR_KEY, True)

    def name(self) -> str:
        """
        Returns the name of the component from its descriptor.

        :return: component name.
        :rtype: str
        """

        return self.descriptor.name

    def rename(self, name: str):
        """
        Renames the component by setting the meta and descriptor name attribute and its namespace.

        :param str name: new component name.
        """

        old_name, side = self.name(), self.side()
        self.descriptor.name = name
        if self._meta is None:
            return

        naming_manager = self.naming_manager()
        old_name = naming_manager.resolve('componentName', {'componentName': old_name, 'side': side})
        new_name = naming_manager.resolve('componentName', {'componentName': name, 'side': side})

        for component_node in self.iterate_nodes():
            component_node.rename(component_node.name().replace(old_name, new_name))

        self._meta.attribute(consts.CRIT_NAME_ATTR).set(name)
        self._meta.attribute(consts.CRIT_ID_ATTR).set(name)
        self.save_descriptor(self.descriptor)
        self._update_space_switch_component_dependencies(name, side)

    def side(self) -> str:
        """
        Returns the side of the component from its descriptor.

        :return: component side.
        :rtype: str
        """

        return self.descriptor.side

    def set_side(self, side: str):
        """
        Sets the components side.

        :param str side: new component side.
        """

        name, old_side = self.name(), self.side()
        self.descriptor.side = side
        if self._meta is None:
            return

        naming_manager = self.naming_manager()
        old_name = naming_manager.resolve('componentName', {'componentName': name, 'side': old_side})
        new_name = naming_manager.resolve('componentName', {'componentName': name, 'side': side})

        for component_node in self.iterate_nodes():
            component_node.rename(component_node.name().replace(old_name, new_name))

        self._meta.attribute(consts.CRIT_SIDE_ATTR).set(side)
        self.save_descriptor(self.descriptor)
        self._update_space_switch_component_dependencies(self.name(), side)

    def serialized_token_key(self) -> str:
        """
        Returns the serialized data key for this component, which results in the joined name, side with ':' as
        separator.

        :return: joined name.
        :rtype: str
        """

        return ':'.join((self.name(), self.side())) if self.exists() else ''

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
            if parent_meta.hasAttribute(consts.CRIT_IS_COMPONENT_ATTR):
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

        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get('parent')

        found_parent = None
        for parent_meta in self._meta.iterate_meta_parents(recursive=False):
            if parent_meta.hasAttribute(consts.CRIT_IS_COMPONENT_ATTR):
                found_parent = self._rig.component(
                    parent_meta.attribute(consts.CRIT_NAME_ATTR).value(),
                    parent_meta.attribute(consts.CRIT_SIDE_ATTR).value()
                )
                break

        return found_parent

    def set_parent(self, parent_component: Component | None, driver_guide: meta_nodes.Guide | None = None) -> bool:
        """
        Connects this component to the parent component through the given driver guide.

        :param Component parent_component: parent component instancen.
        :param meta_nodes.Guide driver_guide: driver guide.
        :return: True if set parent component operation was successful; False otherwise.
        :rtype: bool
        """

        if parent_component == self:
            return False

        if driver_guide:
            if not parent_component.id_mapping()[consts.SKELETON_LAYER_TYPE].get(driver_guide.id()):
                self.logger.warning('Setting parent to a guide which does not belong to a joint is not allowed')
                return False

        if parent_component is None:
            self.remove_all_parents()
            self._meta.add_meta_parent(self.rig.components_layer())
            return True

        did_set_parent = self._set_meta_parent(parent_component)
        if not did_set_parent:
            return False

        self.descriptor.parent = ':'.join([parent_component.name(), parent_component.side()])

        if not driver_guide:
            return False
        elif not self.has_guide() and not self._is_building_guide:
            self.logger.warning('Guide system has not been built yet!')
            return False

        guide_layer = self.guide_layer()
        root_guide = guide_layer.guide('root')
        if not root_guide:
            self.logger.error('No root guide on this componente, unable to set parent!')
            return False

        root_srt = root_guide.srt(0)
        world_matrix = root_guide.worldMatrix()

        # pre-calculate local matrix for the guide from drive rto avoid double transforms
        local_matrix_offset = world_matrix * driver_guide.worldMatrix().inverse()
        root_srt.setWorldMatrix(driver_guide.worldMatrix())

        driver_guide_layer = parent_component.guide_layer()

        _, parent_constraint_extras = api.build_constraint(
            root_srt,
            {'targets': ((driver_guide.fullPathName(partial_name=True, include_namespace=False), driver_guide),)},
            constraint_type='parent', maintainOffset=True)
        _, scale_constraint_extras = api.build_constraint(
            root_srt,
            {'targets': ((driver_guide.fullPathName(partial_name=True, include_namespace=False), driver_guide),)},
            constraint_type='scale', maintainOffset=True)
        root_guide.setMatrix(local_matrix_offset)

        connector_name = self.naming_manager().resolve(
            'object',
            {'componentName': self.name(), 'side': self.side(), 'section': driver_guide.id(), 'type': 'connector'})
        guide_layer.create_connector(
            connector_name, root_guide, driver_guide, size=0.5, color=(1, 1, 0), parent=guide_layer.root_transform())

        driver_guide_plug = driver_guide_layer.guide_plug_by_id(driver_guide.id()).child(0)
        driven_guide_plug = guide_layer.guide_plug_by_id('root').child(4).nextAvailableDestElementPlug()
        dest_guide_plug = driven_guide_plug.child(0)
        dest_constraint_array = driven_guide_plug.child(1)
        driver_guide_plug.connect(dest_guide_plug)
        for n in parent_constraint_extras + scale_constraint_extras:
            n.message.connect(dest_constraint_array.nextAvailableDestElementPlug())

    def remove_upstream_connectors(self, parent_component: Component | None = None):
        """
        Removes upstream connectors from this component guide layer.

        :param Component or None parent_component: optional parent component to remove connectos from. If None, all
            connectors will be removed.
        """

        if not self.has_guide():
            self.logger.info(f'Component "{self}" has no guides')
            return

        guide_layer = self.guide_layer()
        if not guide_layer:
            self.logger.info(f'Component "{self}" has no guide layer')
            return

        for connector in guide_layer.iterate_connectors():
            end_guide = connector.end_guide()
            # TODO: this isn't required or we should just get upstream metaNode to speed things up
            connector_guide_parent = self.rig.component_from_node(end_guide)
            if parent_component is None:
                connector.delete()
            elif connector_guide_parent == parent_component:
                connector.delete()

    def remove_parent(self, parent_component: Component | None):
        """
        Removes parent relationship between this component and the parent component.

        :param Component or None parent_component: parent component to remove. If None, all parents will be removed.
        """

        if not self.exists():
            return

        parent = parent_component.meta if parent_component else None
        self.remove_upstream_connectors(parent_component=parent_component)
        self._meta.remove_meta_parent(parent)
        self._meta.add_meta_parent(self._rig.components_layer())
        self.descriptor.parent = None
        self.descriptor.connections = {}
        self.save_descriptor(self.descriptor)

    def remove_all_parents(self):
        """
        Removes all parent components from the current component
        """

        if not self.exists():
            return
        self.disconnect_all()
        parent_component = self.parent()
        if parent_component:
            self.remove_parent(parent_component)

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
        Renames the namespace which ascts as the component name.

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

    def current_naming_preset(self) -> Preset:
        """
        Returns the current naming convention preset instance for this component.

        :return: naming convention preset.
        :rtype: Preset
        """

        local_override = self.descriptor.get(consts.NAMING_PRESET_DESCRIPTOR_KEY)
        local_preset = self.configuration.name_presets_manager().find_preset(local_override) if local_override else None

        return local_preset if local_preset is not None else self.configuration.current_naming_preset

    def update_naming(self, layer_types: tuple | None = None, mod: api.DGModifier | None = None, apply: bool = True):
        """
        Updates any nodes names on the component from the current naming manager instance.

        :param tuple[str] layer_types: a tuple of layer types whose nodes we want to rename.
        :param api.DGModifier or None mod: modifier to use when renaming a node.
        :param bool apply: whether to run the modifier immediately.
        :return: modifier instance used, or the created one if None is given.
        :rtype: api.DGModifier
        """

        layer_types = layer_types or (consts.GUIDE_LAYER_TYPE, consts.SKELETON_LAYER_TYPE)

        self._generate_objects_cache()
        mod = mod or api.DGModifier()
        name_manager = self.naming_manager()
        meta = self._meta
        root_transform = self.root_transform()
        container = self.container()
        component_name, component_side = self.name(), self.side()

        nodes_to_lock = [meta, root_transform]
        if container is not None:
            nodes_to_lock.append(container)
        for node_to_lock in nodes_to_lock:
            node_to_lock.lock(False, mod=mod, apply=False)

        try:
            hierarchy_name, meta_name = naming.compose_component_root_names(name_manager, component_name, component_side)
            meta.rename(meta_name, mod=mod, apply=False)
            root_transform.rename(hierarchy_name, mod=mod, apply=False)
            if container is not None:
                container_name = naming.compose_container_name(name_manager, component_name, component_side)
                container.rename(container_name, mod=mod, apply=False)
            if consts.GUIDE_LAYER_TYPE in layer_types and self.has_guide():
                self._set_guide_naming(name_manager, mod)
            if consts.SKELETON_LAYER_TYPE in layer_types and self.has_skeleton():
                self._set_skeleton_naming(name_manager, mod)
            for node_to_lock in nodes_to_lock:
                node_to_lock.lock(True, mod=mod, apply=False)
            if apply:
                mod.doIt()
        finally:
            self._build_objects_cache.clear()

        return mod

    def set_guide_naming(self, naming_manager: NameManager, mod: api.DGModifier):
        """
        Function that can be overridden in subclasses to update the naming convention for the guides.

        :param NameManager naming_manager: name manager instance for this component.
        :param api.DGModifier mod: modifier instance to use when renaming nodes.
        """

        pass

    def set_skeleton_naming(self, naming_manager: NameManager, mod: api.DGModifier):
        """
        Function that can be overridden in subclasses to update the naming convention for skeleton layer, input layer
        and output layer.

        :param NameManager naming_manager: name manager instance for this component.
        :param api.DGModifier mod: modifier instance to use when renaming nodes.
        """

        pass

    def has_guide(self) -> bool:
        """
        Returns whether the guides for this component are already been built.

        :return: True if guides are already built; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.CRIT_HAS_GUIDE_ATTR).value()

    def has_skeleton(self) -> bool:
        """
        Returns whether the skeleton for this component is already been built.

        :return: True if skeleton is already built; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.CRIT_HAS_SKELETON_ATTR).value()

    def has_rig(self) -> bool:
        """
        Returns whether the rig for this component is already been built.

        :return: True if rig is already built; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.CRIT_HAS_RIG_ATTR).value()

    def has_polished(self) -> bool:
        """
        Returns whether this component is already polished.

        :return: True if rig is already polished; False otherwise.
        :rtype: bool
        """

        return self.exists() and self.meta.attribute(consts.CRIT_HAS_POLISHED_ATTR).value()

    def save_descriptor(self, descriptor_to_save: component.ComponentDescriptor | None = None):
        """
        Saves the given descriptor as the descriptor cache and bakes the descriptor into the component meta node
        instance.

        :param dict or tp.rigtoolkit.crit.lib.maya.core.descriptor.component.ComponentDescriptor descriptor_to_save: descriptor
            data to save.
        """

        descriptor_to_save = descriptor_to_save or self._descriptor

        if type(descriptor_to_save) == dict:
            descriptor_to_save = component.load_descriptor(descriptor_to_save, self._original_descriptor)

        self._descriptor = descriptor_to_save
        self._meta.save_descriptor_data(descriptor_to_save.to_scene_data())

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
            if child_meta.hasAttribute(consts.CRIT_IS_COMPONENT_ATTR):
                child_component = self._rig.component(
                    child_meta.attribute(consts.CRIT_NAME_ATTR).value(),
                    child_meta.attribute(consts.CRIT_SIDE_ATTR).value())
                if child_component:
                    yield child_component

    def find_layer(self, layer_type: str) -> layers.CritLayer | None:
        """
        Finds and returns the layer instance of given type for this component.

        :param str layer_type: layer type to get.
        :return: found layer meta node instance.
        :rtype: layers.CritLayer or None
        :raises ValueError: if given layer type is not supported.
        """

        if layer_type not in consts.LAYER_TYPES:
            raise ValueError('Unsupported layer type: {}, supported types: {}'.format(layer_type, consts.LAYER_TYPES))
        if not self.exists():
            return None

        return self._meta.layer(layer_type)

    def input_layer(self) -> layers.CritInputLayer | None:
        """
        Returns the input layer meta node instance for this component.

        :return: input layer meta node instance.
        :rtype: layers.CritInputLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritInputLayer.ID)

        return root.layer(consts.INPUT_LAYER_TYPE)

    def output_layer(self) -> layers.CritOutputLayer | None:
        """
        Returns the output layer meta node instance for this component.

        :return: output layer meta node instance.
        :rtype: layers.CritOutputLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritOutputLayer.ID)

        return root.layer(consts.OUTPUT_LAYER_TYPE)

    def guide_layer(self) -> layers.CritGuideLayer | None:
        """
        Returns the guide layer meta node instance for this component.

        :return: guide's layer meta node instance.
        :rtype: layers.CritGuideLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritGuideLayer.ID)

        return root.layer(consts.GUIDE_LAYER_TYPE)

    def skeleton_layer(self) -> layers.CritSkeletonLayer | None:
        """
        Returns skeleton layer meta node instance for this component.

        :return: skeleton layer meta node instance.
        :rtype: layers.CritSkeletonLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritSkeletonLayer.ID)

        return root.layer(consts.SKELETON_LAYER_TYPE)

    def rig_layer(self) -> layers.CritRigLayer | None:
        """
        Returns rig layer meta node instance for this component.

        :return: deform layer meta node instance.
        :rtype: layers.CritRigLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritRigLayer.ID)

        return root.layer(consts.RIG_LAYER_TYPE)

    def geometry_layer(self) -> layers.CritGeometryLayer | None:
        """
        Returns geometry layer meta node instance for this component.

        :return: geometry layer meta node instance.
        :rtype: layers.CritGeometryLayer or None
        """

        root = self._meta
        if not root:
            return
        if self._is_building_guide or self._is_building_skeleton or self._is_building_rig:
            return self._build_objects_cache.get(layers.CritGeometryLayer.ID)

        return root.layer(consts.GEOMETRY_LAYER_TYPE)

    def iterate_nodes(self) -> Iterator[api.DGNode | api.DagNode]:
        """
        Generator function that iterates over all node linked to this component.

        :return: iterated linked component nodes.
        :rtype: Iterator[api.DGNode | api.DagNode]
        """

        container = self.container()
        if container is not None:
            yield container

        meta = self.meta
        if meta is not None:
            yield meta

        transform = self.root_transform()
        if transform is not None:
            yield transform

        for i in self._meta.layers_by_id((
                consts.GUIDE_LAYER_TYPE, consts.RIG_LAYER_TYPE, consts.INPUT_LAYER_TYPE, consts.OUTPUT_LAYER_TYPE,
                consts.SKELETON_LAYER_TYPE, consts.XGROUP_LAYER_TYPE)).values():
            if not i:
                continue
            yield i
            for child in i.iterate_children():
                yield child

    def control_panel(self) -> meta_nodes.SettingsNode | None:
        """
        Returns control panel instance for this rig layer instance.

        :return: control panel node from the scene.
        :rtype: meta_nodes.SettingNode or None
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

        ids = {k.id: k.id for k in self.descriptor.guide_layer.iterate_guides(include_root=False)}
        return {
            consts.SKELETON_LAYER_TYPE: ids,
            consts.INPUT_LAYER_TYPE: ids,
            consts.OUTPUT_LAYER_TYPE: ids,
            consts.RIG_LAYER_TYPE: ids
        }

    @profiler.fn_timer
    def align_guides(self) -> bool:
        """
        Automatically handles guide alignment for this component based on the 3 CRIT guide properties:
            1. autoAlign: defines whether guide requires auto-alignment.
            2. autoAlignAimVector: defines the primary axis which to align on.
            3. autoAlignUpVector: defines the local up vector for the guide.

        :return: True if auto align operation was successful; False otherwise.
        :rtype: bool
        """

        if not self.has_guide():
            return False

        guide_layer = self.guide_layer()
        guide_layer.align_guides()

        return True

    def disconnect(self, component_to_disconnect: Component):
        """
        Disconnects this component guides from the given component guides one.

        :param Component component_to_disconnect: component we want to disconnect from.
        """

        if not self.has_guide():
            return

        guide_layer = self.guide_layer()
        for guide in guide_layer.iterate_guides():
            parent_srt = guide.srt()
            if not parent_srt:
                continue
            for constraint in api.iterate_constraints(parent_srt):
                for _, driver in constraint.iterate_drivers():
                    if driver is None:
                        continue
                    try:
                        driver_component = self.rig.component_from_node(driver)
                        if driver_component != component_to_disconnect:
                            continue
                    except errors.CritMissingMetaNode:
                        continue
                    constraint.delete()

    def disconnect_all(self):
        """
        Disconnects all guides by deleting incoming constraints on all guides and disconnects the metadata.
        """

        if not self.has_guide():
            return

        guide_layer = self.guide_layer()
        for guide_compound_plug in guide_layer.iterate_guides_compound_attribute():
            source_node = guide_compound_plug.child(0).sourceNode()
            if source_node is None:
                continue
            guide = meta_nodes.Guide(source_node.object())
            parent_srt = guide.srt()
            if not parent_srt:
                continue
            for constraint in api.iterate_constraints(parent_srt):
                constraint.delete()

            # remove metadata connections
            for source_guide_element in guide_compound_plug.child(4):
                source_guide_element.child(0).disconnectAll()

    @contextlib.contextmanager
    def disconnect_component_context(self):
        """
        Context manager to pin and upnin this component and all its children.
        """

        try:
            self.pin()
            for child in self.iterate_children(depth_limit=1):
                child.pin()
            yield
        finally:
            self.unpin()
            for child in self.iterate_children(depth_limit=1):
                child.unpin()

    def pin(self) -> dict:
        """
        Pins the current component guides in place.

        :return: serialized pin connections data.
        :rtype: dict
        ..info:: this work by serializing all upstream connections on the guide layer meta node instance, then we
            disconnect while maintaining parenting (metadata).
        """

        if not self.has_guide():
            return {}
        guide_layer = self.guide_layer()
        if not guide_layer or guide_layer.is_pinned():
            return {}

        self.logger.debug('Activating pin.')
        connection = self.serialize_component_guide_connections()
        guide_layer.attribute(consts.CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR).set(json.dumps(connection))
        guide_layer.attribute(consts.CRIT_GUIDE_PIN_PINNED_ATTR).set(True)
        self.disconnect_all()

        return connection

    def unpin(self) -> bool:
        """
        Unpins the current component guides.

        :return: True if the unpin operation was successful; False otherwise.
        :rtype: bool
        """

        if not self.has_guide():
            return False
        guide_layer = self.guide_layer()
        if not guide_layer or not guide_layer.is_pinned():
            return False

        self.logger.debug('Activating unpin.')
        connection = json.loads(guide_layer.attribute(consts.CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR).value())
        self._descriptor[consts.CONNECTIONS_DESCRIPTOR_KEY] = connection
        self.save_descriptor(self._descriptor)
        guide_layer.attribute(consts.CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR).set('')
        guide_layer.attribute(consts.CRIT_GUIDE_PIN_PINNED_ATTR).set(False)
        self.deserialize_component_connections(layer_type=consts.GUIDE_LAYER_TYPE)

        return True

    def serialize_component_guide_connections(self) -> dict:
        """
        Serializes the connection for this component to the parent.
        """

        existing_connection_descriptor = self._descriptor.get('connections', {})
        if not self.has_guide():
            return existing_connection_descriptor

        guide_layer = self.guide_layer()
        root_guide = guide_layer.guide('root')
        if not root_guide:
            return existing_connection_descriptor

        root_srt = root_guide.srt(0)
        if not root_srt:
            return existing_connection_descriptor

        guide_constraints = []
        for constraint in api.iterate_constraints(root_srt):
            content = constraint.serialize()
            controller, controller_attr = content.get('controller', (None, None))
            if controller:
                content['controller'] = (controller[0].fullPathName(), controller[1])
            targets = []
            for target_label, target in content.get('targets', []):
                if not meta_nodes.Guide.is_guide(target):
                    continue
                target_component = self._rig.component_from_node(target)
                full_name = ':'.join([target_component.name(), target_component.side(), meta_nodes.Guide(target.object()).id()])
                targets.append((target_label, full_name))
            content['targets'] = targets
            guide_constraints.append(content)
        if not guide_constraints:
            return existing_connection_descriptor

        return {'id': 'root', 'constraints': guide_constraints}

    def deserialize_component_connections(self, layer_type: str = consts.GUIDE_LAYER_TYPE) -> tuple[list, dict]:
        """
        Deserializes the component connections for given layer type.

        :param str layer_type: layer type to deserialize connections of.
        :return: deserialized layer connections
        :rtype: tuple[list, dict]
        """

        return self._remap_connections(layer_type)

    def space_switch_ui_data(self) -> dict:
        """
        Returns the available space switch driven and driver settings for this component instance
        :return: dictionary containing the information about what space switch controls are available for either being
        driven or being drivers of space switches.
        :rtype: dict
        ..note:: drivers marked as internal will force a non-editable driver state within UI driver column and only
            displayed in the "driver component" column.
        .. code-block:: pytho

            def spaceSwitchUiData(self):
                driven = [crit.SpaceSwitchUIDriven(id_="myControlId", label="User DisplayLabel")]
                drivers = [crit.SpaceSwitchUIDriver(id_="myControlId", label="User DisplayLabel", internal=True)]
                return {"driven": driven, "drivers": drivers}
        """

        return {
            'driven': [],
            'drivers': []
        }

    def subsystems(self) -> dict:
        """
        Returns the subsystems for this component instance.

        :return: dictionary with keys of the subsystems and values of the corresponding subsystem instances. e.g:
            {
                'twists': :class:`tp.libs.rig.crit.subsystems.twist.TwistSubSystem`,
                'bendy': :class:`tp.libs.rig.crit.subsystems.bendy.BendySubSystem`
            }
        :rtype: dict
        ..note:: if the subsystems have already been created, the cached version is returned.
        """

        cached = self._build_objects_cache.get('subsystems', None)
        return cached if cached is not None else self.create_subsystems()

    def create_subsystems(self) -> dict:
        """
        Function that creates the subsystems for the current component instance.

        :return: dictionary with keys of the subsystems and values of the corresponding subsystem instances. e.g:
            {
                'twists': :class:`tp.libs.rig.crit.subsystems.twist.TwistSubSystem`,
                'bendy': :class:`tp.libs.rig.crit.subsystems.bendy.BendySubSystem`
            }
        :rtype: dict
        """

        return {}

    @profiler.fn_timer
    def serialize_from_scene(self, layer_ids: Iterable[str] | None = None) -> component.ComponentDescriptor:
        """
        Serializes the component from the root transform down using the individual layers.

        :param Iterable[str] layer_ids: optional iterable of CRIT layer IDs that should be serialized.
        :return: component descriptor.
        :rtype: component.ComponentDescriptor
        """

        if not self.has_guide() and not self.has_skeleton() and not self.has_rig():
            try:
                self._descriptor.update(component.parse_raw_descriptor(self._meta.raw_descriptor_data()))
            except ValueError:
                self.logger.warning('Descriptor in scene is not valid, skipping descriptor update!')
            return self._descriptor

        descriptor = self._meta.serializeFromScene(layer_ids)
        data = self.serialize_component_guide_connections()
        descriptor['connections'] = data
        parent_component = self.parent()
        descriptor['parent'] = ':'.join([parent_component.name(), parent_component.side()]) if parent_component else ''
        self._descriptor.update(descriptor)
        self.save_descriptor(self._descriptor)

        return self._descriptor

    def _remap_connections(self, layer_type: str = consts.GUIDE_LAYER_TYPE) -> tuple[list, dict]:
        """
        Internal function that handles the connection remapping.

        :param str layer_type: layer type to deserialize connections of.
        :return: remapped connections.
        :rtype: tuple[list, dict]
        :raises ValueError: if the layer we want to serialize is not built yet.
        :raises ValueError: if the binding connection support for given layer type is not supported.
        """

        if not self.descriptor.connections:
            return list(), dict()

        # now build the IO mapping before transfer this basically takes the inputs/guides and output/guides nodes
        # from the targetComponent and the parent components and creates a binding, so we can inject into the connection
        # graph

        if layer_type == consts.GUIDE_LAYER_TYPE:
            guide_layer = self.guide_layer()
            if guide_layer is None:
                raise ValueError('Target Component: {} does not have the guide layer built!'.format(self.name()))
            binding, child_layer = generate_connection_binding_guide(self)
            constraints = self._create_guide_constraints_from_data(self.descriptor.connections, binding)
        else:
            raise ValueError('Binding connection for layer of type: {} is not supported!'.format(layer_type))

        return constraints

    def component_parent_guide(self) -> tuple[Component | None, meta_nodes.Guide | None]:
        """
        Returns the connected parent component guide node.

        :return: tuple for the parent component and the connected parent guide node.
        :rtype: tuple[Component or None, meta_nodes.Guide or None]
        """

        if not self.has_guide():
            return None, None

        guide_layer = self.guide_layer()
        root_guide = guide_layer.guide('root')
        if not root_guide:
            return None, None

        root_srt = root_guide.srt(0)
        if not root_srt:
            return None, None

        for constraint in api.iterate_constraints(root_srt):
            for _, target in constraint.drivers():
                if target and meta_nodes.Guide.is_guide(target):
                    parent_component = self._rig.component_from_node(target)
                    return parent_component, meta_nodes.Guide(target.object())

        return None, None

    @profiler.fn_timer
    def build_guide(self) -> bool:
        """
        Builds the guide system for this component. This method handles:
            - Creation of the guide system.
            - Setting up guide layer metadata.

        :return: True if build guide operation was successful; False otherwise.
        :rtype: bool
        :raises errors.CritComponentDoesNotExistError: if the component does not exist.
        :raises errors.CritBuildComponentGuideUnknownError: if an unknown error occurs while building the guide system.
        """

        if not self.exists():
            raise errors.CritComponentDoesNotExistError(self.descriptor.name)

        self._generate_objects_cache()

        if self.has_guide():
            self.guide_layer().root_transform().show()
        if self.has_polished():
            self._set_has_polished(False)
        has_skeleton = self.has_skeleton()
        if has_skeleton:
            self._set_has_skeleton(False)

        self.logger.info('Building guide: {}'.format(self.name()))
        self._is_building_guide = True

        container = self.container()
        if container is None:
            container = self.create_container()
            self._build_objects_cache['container'] = container
        if container is not None:
            container.makeCurrent(True)
            container.lock(False)

        self.logger.info('Starting guide building with namespace: {}'.format(self.namespace()))
        try:
            hierarchy_name, meta_name = naming.compose_names_for_layer(
                self.naming_manager(), self.name(), self.side(), consts.GUIDE_LAYER_TYPE)
            guide_layer = self._meta.create_layer(
                consts.GUIDE_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
            guide_layer.update_metadata(self.descriptor.guide_layer.get(consts.METADATA_DESCRIPTOR_KEY, []))
            self._build_objects_cache[layers.CritGuideLayer.ID] = guide_layer
            self.pre_setup_guide()
            self.setup_guide()
            self.post_setup_guide()
            self.save_descriptor(self._descriptor)
            self._set_has_guide(True)
            if has_skeleton:
                reset_joint_transforms(self.skeleton_layer(), self.descriptor.guide_layer, self.id_mapping())
        except Exception as exc:
            self.logger.error('Failed to setup guides: {}'.format(exc), exc_info=True)
            self._set_has_guide(False)
            raise errors.CritBuildComponentGuideUnknownError('Failed {}'.format('_'.join([self.name(), self.side()])))
        finally:
            if container is not None:
                container.makeCurrent(False)
            self._is_building_guide = False
            self._build_objects_cache.clear()

        return True

    def pre_setup_guide(self):
        """
        Pre setup guide function that is run before build_guide function is called. This function handles:
            - The creation of the guides structure using the component descriptor data.
        """

        self._setup_guide_settings()

        self.logger.debug('Generating guides from descriptor...')
        guide_layer = self.guide_layer()
        current_guides = {guide_node.id(): guide_node for guide_node in guide_layer.iterate_guides()}
        component_name, component_side = self.name(), self.side()
        name_manager = self.naming_manager()

        # re-parent existing guides if required
        post_parenting = list()
        for guide_descriptor in self.descriptor.guide_layer.iterate_guides():
            guide_id = guide_descriptor['id']
            current_scene_guide = current_guides.get(guide_id)
            guide_name = name_manager.resolve(
                'guideName', {'componentName': component_name, 'side': component_side, 'id': guide_id, 'type': 'guide'})
            if current_scene_guide is not None:
                current_scene_guide.createAttributesFromDict({v['name']: v for v in guide_descriptor.get('attributes', list())})
                current_scene_guide.rename(guide_name)
                _, parent_id = current_scene_guide.guide_parent()
                if parent_id != guide_descriptor['parent']:
                    post_parenting.append((current_scene_guide, guide_descriptor['parent']))
                continue

            # create new guide if it does not exist
            shape_transform = guide_descriptor.get('shapeTransform', dict())
            new_guide = guide_layer.create_guide(
                id=guide_descriptor['id'],
                name=guide_name,
                translate=guide_descriptor.get('translate', (0.0, 0.0, 0.0)),
                rotate=guide_descriptor.get('rotate', (0.0, 0.0, 0.0, 1.0)),
                scale=guide_descriptor.get('scale', (1.0, 1.0, 1.0)),
                rotateOrder=guide_descriptor.get('rotateOrder', 0),
                shape=guide_descriptor.get('shape'),
                locShape=guide_descriptor.get('locShape'),
                color=guide_descriptor.get('color'),
                shapeTransform={
                    'translate': shape_transform.get('translate', (0.0, 0.0, 0.0)),
                    'rotate': shape_transform.get('rotate', (0.0, 0.0, 0.0, 1.0)),
                    'scale': shape_transform.get('scale', (1.0, 1.0, 1.0)),
                    'rotateOrder': shape_transform.get('rotateOrder', 0),
                    'worldMatrix': shape_transform.get('worldMatrix'),
                    'matrix': shape_transform.get('matrix')
                },
                parent=guide_descriptor.get('parent', 'root'),
                root=guide_descriptor.get('root', False),
                worldMatrix=guide_descriptor.get('worldMatrix'),
                matrix=guide_descriptor.get('matrix'),
                srts=guide_descriptor.get('srts', list()),
                selectionChildHighlighting=self.configuration.selection_child_highlighting,
                pivotShape=guide_descriptor.get('pivotShape', 0),
                pivotColor=guide_descriptor.get('pivotColor', consts.DEFAULT_GUIDE_PIVOT_COLOR),
                attributes=guide_descriptor.get('attributes', list())
            )
            current_guides[guide_id] = new_guide

            shape_node = new_guide.shape_node()
            if shape_node:
                [guide_layer.add_extra_nodes(cns.utility_nodes() for cns in api.iterate_constraints(shape_node))]

        for child_guide, parent_id in post_parenting:
            child_guide.setParent(current_guides[parent_id])

        self.logger.info('Completed pre-setup guide successfully!')

    def setup_guide(self):
        """
        Main guide setup function. Can be overriden to customize the way guides are created in custom components.
        """

        pass

    def post_setup_guide(self):
        """
        Post setup guide function that is run after setup_guide function is called.
        """

        guide_layer = self.guide_layer()
        guide_layer_transform = guide_layer.root_transform()

        # delete guides in the scene that does not need to exist
        scene_guides = {found_guide.id() for found_guide in guide_layer.iterate_guides()}
        default_guides = {guide_descriptor['id'] for guide_descriptor in self.descriptor.guide_layer.iterate_guides()}
        to_delete = [guide_id for guide_id in scene_guides if guide_id not in default_guides]
        if to_delete:
            guide_layer.delete_guides(*to_delete)

        container = self._merge_component_into_container()
        if container is not None:
            self.logger.info('Publishing guide settings to container')
            container.lock(False)
            settings = guide_layer.setting_node(consts.GUIDE_LAYER_TYPE)
            if settings is not None:
                container.unPublishAttributes()
                container.removeUnboundAttributes()
                container.publishAttributes(
                    [i for i in settings.iterateExtraAttributes() if i.partialName(
                        include_node_name=False) not in consts.ATTRIBUTES_TO_SKIP_PUBLISH and not i.isChild and not i.isElement])
            container.blackBox = self.configuration.blackbox

        connectors_group = guide_layer.sourceNodeByName(consts.CRIT_GUIDE_CONNECTORS_GROUP_ATTR)
        name_manager = self.naming_manager()
        component_name, component_side = self.name(), self.side()
        if connectors_group is None:
            name = naming.compose_connectors_group_name(name_manager, component_name, component_side)
            connectors_group = api.factory.create_dag_node(name, 'transform')
            connectors_group.setParent(guide_layer_transform)
            guide_layer.connect_to(consts.CRIT_GUIDE_CONNECTORS_GROUP_ATTR, connectors_group)

        self.logger.debug('Tagging and annotating guide structure')
        guides = list(guide_layer.iterate_guides())
        nodes_to_publish = list()
        for guide in guides:
            parent_guide, id_plug = guide.guide_parent()
            if parent_guide is not None:
                connector_name = name_manager.resolve(
                    'object', {'componentName': component_name, 'side': component_side, 'section': guide.id(), 'type': 'connector'})
                guide_layer.create_connector(
                    connector_name, start_guide=guide, end_guide=parent_guide, parent=connectors_group)
            guide.lock(True)
            nodes_to_publish.append(guide)
            shape_node = guide.shape_node()
            if shape_node:
                nodes_to_publish.append(shape_node)
        if nodes_to_publish and container is not None:
            container.publishNodes(nodes_to_publish)

        # TODO: Bring back controller tags once Autodesk fixes them
        # tags = list(self.create_guide_controller_tags(guides, None))
        # guide_layer.add_extra_nodes(tags)
        # if container is not None:
        # 	container.addNodes(tags)

        layout_id = self.descriptor.get(consts.GUIDE_MARKING_MENU_DESCRIPTOR_KEY) or consts.DEFAULT_GUIDE_MARKING_MENU
        components.create_triggers(guide_layer, layout_id)

        self.deserialize_component_connections(layer_type=consts.GUIDE_LAYER_TYPE)

    def setup_inputs(self):
        """
        Set up the input layer for this component.
        """

        def _build_input(_input_descriptor: InputDescriptor) -> meta_nodes.InputNode:
            """
            Internal function that creates an input node instance from given input descriptor data.

            :param InputDescriptor _input_descriptor: input descriptor instance.
            :return: input node created from input descriptor.
            :rtype: meta_nodes.InputNode
            """

            parent = root_transform if _input_descriptor.parent is None else input_layer.input_node(_input_descriptor.parent)
            try:
                input_node = input_layer.input_node(_input_descriptor.id)
            except errors.CritInvalidInputNodeMetaData:
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
                self.naming_manager(), self.name(), self.side(), consts.INPUT_LAYER_TYPE)
        input_layer = self._meta.create_layer(consts.INPUT_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        root_transform = input_layer.root_transform()
        if root_transform is None:
            root_transform = input_layer.create_transform(name=hierarchy_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.CritInputLayer.ID] = input_layer

        descriptor = self.descriptor
        input_layer_descriptor = descriptor.input_layer
        current_inputs = {input_node.id(): input_node for input_node in input_layer.iterate_inputs()}
        new_inputs = {}
        for input_descriptor in input_layer_descriptor.iterate_inputs():
            input_node = _build_input(input_descriptor)
            new_inputs[input_node.id] = input_node

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

    def setup_outputs(self, parent_node: meta_nodes.Joint | api.DagNode):
        """
        Set up the output layer for this component.

        :param api.DagNode parent_node: parent node.
        """

        def _build_output(_output_descriptor: OutputDescriptor) -> meta_nodes.OutputNode:
            """
            Internal function that creates an output node instance from given output descriptor data.

            :param OutputDescriptor _output_descriptor: output descriptor instance.
            :return: output node created from output descriptor.
            :rtype: meta_nodes.OutputNode
            """

            parent = root_transform if _output_descriptor.parent is None else output_layer.output_node(_output_descriptor.parent)
            try:
                output_node = output_layer.output_node(_output_descriptor.id)
            except errors.CritInvalidOutputNodeMetaData:
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
                self.naming_manager(), self.name(), self.side(), consts.OUTPUT_LAYER_TYPE)
        output_layer = self._meta.create_layer(
            consts.OUTPUT_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        root_transform = output_layer.root_transform()
        if root_transform is None:
            root_transform = output_layer.create_transform(name=hierarchy_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.CritOutputLayer.ID] = output_layer

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

    def component_parent_joint(self, parent_node: api.DagNode) -> meta_nodes.Joint | api.DagNode:
        """
        Returns the parent component connected joint.

        :param api.DagNode parent_node: parent node.
        :return: component parent joint.
        :rtype: meta_nodes.Joint or api.DagNode
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
            parent_output_layer = layers.CritOutputLayer(output_node_plug.node().object())
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
                    output_id = parent_output_node.attribute(consts.CRIT_ID_ATTR).value()
                    parent_joint = parent_joints.get(output_id)
            return parent_joint or parent_node

        return parent_node

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
            raise errors.CritComponentDoesNotExistError(self.descriptor.name)

        self._generate_objects_cache()

        if self.has_polished():
            self._set_has_polished(False)

        self.serialize_from_scene(layer_ids=(consts.GUIDE_LAYER_TYPE,))

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
            self.deserialize_component_connections(layer_type=consts.INPUT_LAYER_TYPE)
            hierarchy_name, meta_name = naming.compose_names_for_layer(
                self.naming_manager(), self.name(), self.side(), consts.SKELETON_LAYER_TYPE)
            skeleton_layer = self._meta.create_layer(
                consts.SKELETON_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
            skeleton_layer.update_metadata(self.descriptor.skeleton_layer.get(consts.METADATA_DESCRIPTOR_KEY, []))
            self._build_objects_cache[layers.CritSkeletonLayer.ID] = skeleton_layer
            if container:
                container.addNode(skeleton_layer)
            parent_joint = self.component_parent_joint(parent_node)
            self._setup_guide_offsets()
            self.pre_setup_skeleton_layer()
            self.setup_skeleton_layer(parent_joint)
            self.setup_outputs(parent_joint)
            self.post_setup_skeleton_layer(parent_joint)
            self.blackbox = False
            self.save_descriptor(self._descriptor)
            self._set_has_skeleton(True)
        except Exception as exc:
            self.logger.error('Failed to setup skeleton: {}'.format(exc), exc_info=True)
            self._set_has_skeleton(False)
            raise errors.CritBuildComponentSkeletonUnknownError('Failed {}'.format('_'.join([self.name(), self.side()])))
        finally:
            if container is not None:
                container.makeCurrent(False)
            self._is_building_skeleton = False
            self._build_objects_cache.clear()

        return True

    def pre_setup_skeleton_layer(self):
        """
        Pre setup skeleton layer based on the descriptor.

        For each guide in the guide layer descriptor, it checks if a matching skeleton joint exists in the skeleton
        layer descriptor. If it does, it sets the translation, rotation and rotation order of the skeleton joint to the
        values of the corresponding guide.
        """

        descriptor = self.descriptor
        guide_layer_descriptor = descriptor.guide_layer
        skeleton_layer_descriptor = descriptor.skeleton_layer

        guide_descriptors = {k.id: k for k in guide_layer_descriptor.iterate_guides()}
        joint_descriptors = {k.id: k for k in skeleton_layer_descriptor.iterate_deform_joints()}
        for guide_id, guide_descriptor in guide_descriptors.items():
            joint_descriptor = joint_descriptors.get(guide_id)
            if joint_descriptor is None:
                continue
            joint_descriptor.translate = guide_descriptor.get('translate', (0.0, 0.0, 0.0))
            joint_descriptor.rotate = guide_descriptor.get('rotate', (0.0, 0.0, 0.0, 1.0))
            joint_descriptor.rotateOrder = guide_descriptor.get('rotateOrder', 0)

    def setup_selection_set_joints(
            self, skeleton_layer: layers.CritSkeletonLayer,
            deform_joints: dict[str, meta_nodes.Joint]) -> list[meta_nodes.Joint]:
        """
        Function that handles the addition of joints into the skeleton layer deform joints selection set.

        :param layers.CritSkeletonLayer skeleton_layer: skeleton layer instance.
        :param dict[str, meta_nodes.Joint] deform_joints: list of default skeleton layer bind joints.
        :return: list of bind joints to add.
        :rtype: list[meta_nodes.Joint]
        """

        if deform_joints:
            return list(deform_joints.values())

        return []

    def setup_skeleton_layer(self, parent_joint: meta_nodes.Joint):
        """
        Setup skeleton layer for this component.

        :param meta_nodes.Joint or api.DagNode parent_joint: parent joint or node which the joints will be parented
            under.
        """

        skeleton_layer = self.skeleton_layer()
        descriptor = self.descriptor
        guide_layer_descriptor = descriptor.guide_layer
        skeleton_layer_descriptor = descriptor.skeleton_layer
        naming_manager = self.naming_manager()
        guide_descriptors = {k.id: k for k in guide_layer_descriptor.iterate_guides()}
        existing_joints = {k.id(): k for k in skeleton_layer.iterate_joints()}
        skeleton_layer_transform = skeleton_layer.root_transform()
        new_joint_ids = {}
        primary_root_joint = parent_joint or skeleton_layer_transform
        id_mapping = {v: k for k, v in self.id_mapping()[consts.SKELETON_LAYER_TYPE].items()}

        # find joints that do not exist anymore
        for jnt in skeleton_layer_descriptor.iterate_deform_joints():
            existing_joint = existing_joints.get(jnt.id)
            guide = guide_descriptors.get(id_mapping.get(jnt.id, ''))
            descriptor_parent = jnt.get('parent')
            joint_parent = primary_root_joint if descriptor_parent is None else existing_joints[descriptor_parent]
            joint_name = naming_manager.resolve(
                'skinJointName',
                {'componentName': self.name(), 'side': self.side(), 'id': jnt.id, 'type': 'joint'})
            if existing_joint:
                if not guide:
                    continue
                new_joint_ids[jnt.id] = existing_joint
                existing_joint.rotateOrder.set(jnt.rotateOrder)
                existing_joint.segmentScaleCompensate.set(False)
                existing_joint.setParent(joint_parent)
                existing_joint.rename(joint_name)
                continue

            new_node = skeleton_layer.create_joint(
                name=joint_name, id=jnt.id, rotateOrder=jnt.rotateOrder, translate=jnt.translate, rotate=jnt.rotate,
                parent=joint_parent)
            new_node.segmentScaleCompensate.set(False)
            existing_joints[jnt.id] = new_node
            new_joint_ids[jnt.id] = new_node

        # purge any joints that where removed from the descriptor
        for jnt_id, existing_joint in existing_joints.items():
            if jnt_id in new_joint_ids:
                continue
            parent_joint = existing_joint.parent()
            for child in existing_joint.children((api.kTransform, api.kJoint)):
                child.setParent(parent_joint)
            skeleton_layer.delete_joint(jnt_id)

        # binding components skeleton joints to the selection set
        selection_set = skeleton_layer.selection_set()
        if selection_set is None:
            selection_set_name = naming_manager.resolve(
                'selectionSet', {'componentName': self.name(), 'side': self.side(), 'selectionSet': 'componentSkeleton', 'type': 'objectSet'})
            selection_set = skeleton_layer.create_selection_set(
                selection_set_name, parent=self.rig.meta.selection_sets()['skeleton'])

        bind_joints = self.setup_selection_set_joints(skeleton_layer, new_joint_ids)
        current_selection_set_members = selection_set.members(True)
        to_remove = [i for i in current_selection_set_members if i not in bind_joints]
        if to_remove:
            selection_set.removeMembers(to_remove)
        if bind_joints:
            selection_set.addMembers(bind_joints)
        # skeleton_layer.set_live_link(
        # 	self.input_layer().setting_node(consts.CRIT_INPUT_OFFSET_ATTR_NAME_ATTR),
        # 	id_mapping=self.id_mapping()[consts.SKELETON_LAYER_TYPE], state=True)

    def post_setup_skeleton_layer(self, parent_joint: meta_nodes.Joint):
        """
        Post setup skeleton layer for this component.

        :param meta_nodes.Joint parent_joint: parent joint.
        """

        skeleton_layer = self.skeleton_layer()
        guide_offset = self.input_layer().setting_node(consts.CRIT_INPUT_OFFSET_ATTR_NAME_ATTR)
        # skeleton_layer.set_live_link(guide_offset, state=False)

        guide_layer = self.guide_layer()
        if guide_layer is not None:
            guide_layer.set_live_link(guide_offset, state=False)

        if self.configuration.build_skeleton_marking_menu:
            layout_id = self.descriptor.get(
                consts.SKELETON_MARKING_MENU_DESCRIPTOR_KEY) or consts.DEFAULT_SKELETON_MARKING_MENU
            components.create_triggers(skeleton_layer, layout_id)

        container = self.container()
        if container is not None:
            container.publishNodes(skeleton_layer.joints())

        skeleton_layer.root_transform().hide()

    @profiler.fn_timer
    def build_rig(self, parent_node: api.DagNode | None = None) -> bool:
        """
        Builds the rig for this component.

        :param api.DagNode or None parent_node: parent node for the rig to be parented to. If None, the rig will not be
            parented to anything.
        :return: True if the component rig was built successfully; False otherwise.
        :raises errors.CritComponentDoesNotExistError: if the current component does not exist.
        :raises errors.CritBuildComponentRigUnknownError: if the component build rig process fails.
        """

        if not self.exists():
            raise errors.CritComponentDoesNotExistError(self.descriptor.name)
        elif self.has_rig():
            self.logger.info(f'Component "{self.name()}" already have a rig, skipping the build!')
            return True

        self._generate_objects_cache()
        if self.has_polished():
            self._set_has_polished(False)

        self.serialize_from_scene()

        # reset_joint_transforms(self.skeleton_layer(), self.descriptor.guide_layer, self.id_mapping())

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
        #     self.post_setup_rig(parent_joint)
        #     self._set_has_rig(True)
        #     self.blackbox = self.configuration.blackbox
        #     self.save_descriptor(self._descriptor)
        except Exception:
            msg = f'Failed to build rig for component {"_".join([self.name(), self.side()])}'
            self.logger.error(msg, exc_info=True)
            raise errors.CritBuildComponentRigUnknownError(msg)
        finally:
            self._is_building_rig = False
            if container is not None:
                container.makeCurrent(False)
                self._build_objects_cache.clear()

        return True

    def pre_setup_rig(self, parent_node: meta_nodes.Joint | api.DagNode | None = None):
        """
        Pre setup rig function that is run before setup_rig function is called.

        :param  meta_nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        component_name, component_side = self.name(), self.side()
        hierarchy_name, meta_name = naming.compose_names_for_layer(
            self.naming_manager(), component_name, component_side, consts.RIG_LAYER_TYPE)
        rig_layer = self._meta.create_layer(
            consts.RIG_LAYER_TYPE, hierarchy_name, meta_name, parent=self._meta.root_transform())
        self._build_objects_cache[layers.CritRigLayer.ID] = rig_layer
        name = self.naming_manager().resolve(
            'settingsName', {
                'componentName': component_name, 'side': component_side, 'section': consts.RIG_LAYER_TYPE,
                'type': 'settings'})
        rig_layer.create_settings_node(name, attr_name=consts.CONTROL_PANEL_TYPE)
        self._setup_rig_settings()

    @decorators.abstractmethod
    def setup_rig(self, parent_node: meta_nodes.Joint | api.DagNode | None = None):
        """
        Main rig setup function. Can be overriden to customize the way rig are created in custom components.

        :param  meta_nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        raise NotImplementedError

    def post_setup_rig(self, parent_node: meta_nodes.Joint | api.DagNode | None = None):
        """
        Post setup rig function that is run after setup_rig function is called.

        :param  meta_nodes.Joint or api.DagNode or None parent_node: parent node for the rig to be parented to. If
            None, the rig will not be parented to anything.
        """

        control_panel = self.control_panel()
        rig_layer = self.rig_layer()

        controller_tag_plug = control_panel.addAttribute(
            **dict(
                name=consts.CRIT_CONTROL_NODE_ATTR, type=api.kMFnkEnumAttribute, keyable=False, channelBox=True,
                enums=['Not Overridden', 'Inherit Parent Controller', 'Show on Mouse Proximity']
            )
        )
        controls = list(rig_layer.iterate_controls())
        selection_set = rig_layer.selection_set()
        if selection_set is None:
            selection_set_name = self.naming_manager().resolve(
                'selectionSet',
                {'componentName': self.name(), 'side': self.side(), 'selectionSet': 'componentCtrls', 'type': 'objectSet'})
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

        layout_id = self.descriptor.get(consts.RIG_MARKING_MENU_DESCRIPTOR_KYE) or consts.DEFAULT_RIG_MARKING_MENU
        components.create_triggers(rig_layer, layout_id)

    def setup_space_switches(self):
        """
        Setup space switches from the descriptor data.
        """

        # rig = self.rig
        # rig_layer = self.rig_layer()
        # existing_space_constraints = {i.controller_attribute_name(): i for i in rig_layer.space_switches()}

    @profiler.fn_timer
    def delete(self) -> bool:
        """
        Deletes the entire component from current scene.
        If this component has children, those children meta nodes will be re-parented to the rig components layer.

        :return: True if component deletion operation was successful; False otherwise.
        :rtype: bool
        """

        container = self.container()
        current_children = list(self.iterate_children())
        for child in current_children:
            child.meta.add_meta_parent(self.rig.components_layer())
        self.logger.debug('Starting component deletion operation')
        self.delete_rig()
        self.delete_skeleton()
        self.delete_guide()
        if self._meta.exists():
            self._meta.delete()
        if container is not None:
            self.logger.debug('Deleting container')
            container.delete()
        self._meta = None

        return True

    @profiler.fn_timer
    def delete_guide(self):
        """
        Deletes component guides.
        """

        self.logger.debug(f'Deleting component guides: "{self}"')
        container = self.container()
        guides_layer = self.guide_layer()
        if not guides_layer:
            self._set_has_guide(False)
            return True

        to_delete = []
        self.logger.debug('Start guides layer deletion process...')
        child_components = list(self.iterate_children())
        if child_components:
            self.logger.debug('Child component exists, removing guide connections...')
            guides = guides_layer.iterate_guides()
            for child in child_components:
                child_guide_layer = child.guide_layer()
                if child_guide_layer is None:
                    continue
                to_delete.extend([connector for connector in child.guide_layer().iterate_connectors() if connector.end_node() in guides])

        if container is not None:
            container.lock(False)
            guide_settings = guides_layer.setting_node(consts.GUIDE_LAYER_TYPE)
            if guide_settings:
                self.logger.debug('Purging published guide container settings')
                for i in container.publishedAttributes():
                    try:
                        plug_name = i.partialName(include_node_name=False)
                    except RuntimeError:
                        self.logger.warning(f'Object does not exist: {i}')
                        continue
                    if guide_settings.hasAttribute(plug_name):
                        container.unPublishAttribute(plug_name)

        modifier = api.DagModifier()
        [i.delete(mod=modifier, apply=False) for i in to_delete if i.exists()]
        guides_layer.delete(mod=modifier, apply=True)
        self._set_has_guide(False)

        return True

    @profiler.fn_timer
    def delete_skeleton(self):
        """
        Deletes component skeleton.
        """

        pass

    @profiler.fn_timer
    def delete_rig(self):
        """
        Deletes component rig.
        """

        pass

    def _descriptor_from_scene(self) -> component.ComponentDescriptor | None:
        """
        Internal function that tries to retrieve the descriptor from this component meta node instance.

        :return: component descriptor.
        :rtype: component.ComponentDescriptor or None
        """

        if not self._meta or not self._meta.exists():
            return None

        data = self._meta.raw_descriptor_data()
        translated_data = component.parse_raw_descriptor(data)
        return component.load_descriptor(translated_data, self._original_descriptor)

    def _generate_objects_cache(self):
        """
        Internal function that initializes internal build objects cache.
        """

        self._build_objects_cache = self._meta.layer_id_mapping()
        self._build_objects_cache['container'] = self.container()
        self._build_objects_cache['parent'] = self.parent()
        self._build_objects_cache['naming'] = self.naming_manager()
        self._build_objects_cache['subsystems'] = self.subsystems()

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

    def _set_has_guide(self, flag: bool):
        """
        Internal function that updates the has guide attribute of the meta node instance.

        :param bool flag: True if component has guides; False otherwise.
        """

        self.logger.debug('Setting hasGuide to: {}'.format(flag))
        has_guide_attr = self._meta.attribute(consts.CRIT_HAS_GUIDE_ATTR)
        has_guide_attr.isLocked = False
        has_guide_attr.setBool(flag)

    def _set_has_skeleton(self, flag: bool):
        """
        Internal function that updates the has skeleton attribute of the meta node instance.

        :param bool flag: True if component has skeleton; False otherwise.
        """

        self.logger.debug('Setting hasSkeleton to: {}'.format(flag))
        has_skeleton_attr = self._meta.attribute(consts.CRIT_HAS_SKELETON_ATTR)
        has_skeleton_attr.isLocked = False
        has_skeleton_attr.setBool(flag)

    def _set_has_rig(self, flag: bool):
        """
        Internal function that updates the has rig attribute of the meta node instance.

        :param bool flag: True if component has a rig; False otherwise.
        """

        self.logger.debug('Setting hasRig to: {}'.format(flag))
        has_rig_attr = self._meta.attribute(consts.CRIT_HAS_RIG_ATTR)
        has_rig_attr.isLocked = False
        has_rig_attr.setBool(flag)

    def _set_has_polished(self, flag: bool):
        """
        Internal function that updates the has hasPolished attribute of the meta node instance.

        :param bool flag: True if component has been polished; False otherwise.
        """

        self.logger.debug('Setting hasPolished to: {}'.format(flag))
        has_rig_attr = self._meta.attribute(consts.CRIT_HAS_POLISHED_ATTR)
        has_rig_attr.isLocked = False
        has_rig_attr.setBool(flag)

    def _setup_guide_offsets(self):
        """
        Internal function that set up live link nodes for guides.
        """

        pass

    def _setup_guide_settings(self):
        """
        Internal function that setup guide settings.
        """

        guide_layer = self.guide_layer()
        component_settings = self.descriptor.guide_layer.settings
        if not component_settings:
            return
        existing_settings = guide_layer.guide_settings()
        outgoing_connections = dict()
        if existing_settings is not None:
            existing_settings.attribute('message').disconnectAll()
            for attr in existing_settings.iterateExtraAttributes():
                if attr.isSource:
                    outgoing_connections[attr.partialName()] = list(attr.destinations())
            existing_settings.delete()

        name = self.naming_manager().resolve(
            'settingsName', {
                'componentName': self.name(), 'side': self.side(), 'section': consts.GUIDE_LAYER_TYPE,
                'type': 'settings'})
        settings_node = guide_layer.create_settings_node(name, attr_name=consts.GUIDE_LAYER_TYPE)
        modifier = api.DGModifier()
        for setting_descriptor in iter(component_settings):
            if not settings_node.hasAttribute(setting_descriptor.name):
                attr = settings_node.addAttribute(**setting_descriptor)
            else:
                attr = settings_node.attribute(setting_descriptor.name)
                attr.setFromDict(setting_descriptor)
            conns = outgoing_connections.get(setting_descriptor.name, list())
            for dest in conns:
                if not dest.exists():
                    continue
                attr.connect(dest, mod=modifier, apply=False)
        modifier.doIt()

    def _setup_rig_settings(self):
        """
        Internal function that setup rig settings.
        """

        rig_layer = self.rig_layer()
        settings = self.descriptor.rig_layer.get('settings', {})
        space_switching = self.descriptor.space_switching
        control_panel_descriptor = settings.get('controlPanel', [])
        spaceswitch.merge_attributes_with_space_switches(control_panel_descriptor, space_switching, exclude_active=True)
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

    def _create_rig_controller_tags(self, controls: list[meta_nodes.ControlNode], visibility_plug: api.Plug):
        """
        Creates rig controller tags for given controls.

        :param list[meta_nodes.ControlNode] controls: control nodes instance we want to create tags of.
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
                consts.INPUT_LAYER_TYPE, consts.OUTPUT_LAYER_TYPE, consts.GUIDE_LAYER_TYPE,
                consts.SKELETON_LAYER_TYPE, consts.RIG_LAYER_TYPE, consts.XGROUP_LAYER_TYPE)).values():
            if not found_layer:
                continue
            objects = [found_layer, found_layer.root_transform()] + list(found_layer.iterate_settings_nodes())
            objects.extend(list(found_layer.iterate_extra_nodes()))
            nodes_to_add.extend(object for obj in objects if obj not in nodes_to_add)

        if nodes_to_add:
            container.addNodes(nodes_to_add)

        return container

    def _set_guide_naming(self, naming_manager: NameManager, mod: api.OpenMaya.MDGModifier):
        """
        Internal function that updates the node names of the guide layer nodes.

        :param NameManager naming_manager: naming manager instance to use.
        :param api.MDGModifier mod: optional modifier to use to rename the nodes.
        """

        def _change_lock_guide_layer(state, apply=True):
            """
            Internal function that sets the lock state of the guide layer nodes.

            :param bool state: True to lock the guide; False otherwise.
            :param bool apply: whether to apply lock guide change status.
            """

            guide_layer.lock(state, mod=mod, apply=False)
            transform.lock(state, mod=mod, apply=False)
            for found_guide in guides:
                found_guide.lock(state, mod=mod, apply=False)
            guide_settings.lock(state, mod=mod, apply=apply)

        component_name, component_side = self.name(), self.side()
        hierarchy_name, meta_name = naming.compose_names_for_layer(
            naming_manager, component_name, component_side, consts.GUIDE_LAYER_TYPE)
        guide_layer = self.guide_layer()
        transform = guide_layer.root_transform()
        guides = list(guide_layer.iterate_guides(include_root=True))
        guide_settings = guide_layer.setting_node(consts.GUIDE_LAYER_TYPE)

        _change_lock_guide_layer(False, apply=True)

        try:
            name = naming_manager.resolve(
                'settingsName', {
                    'componentName': component_name, 'side': component_side,
                    'section': consts.GUIDE_LAYER_TYPE, 'type': 'settings'})
            guide_settings.rename(name, mod=mod, apply=False)
            for found_guide in guides:
                tag = found_guide.controller_tag()
                if tag is None:
                    continue
                tag.rename('_'.join([found_guide.name(), 'tag']), mod=mod, apply=False)

            connectors_group = guide_layer.attribute(consts.CRIT_GUIDE_CONNECTORS_GROUP_ATTR).sourceNode()
            connectors_group.rename(naming.compose_connectors_group_name(naming_manager, component_name, component_side))
            guide_layer.rename(meta_name, mod=mod, apply=False)
            transform.rename(hierarchy_name, mod=mod, apply=False)
            self.set_guide_naming(naming_manager, mod)
        finally:
            _change_lock_guide_layer(True)

    def _create_guide_constraints_from_data(self, constraint_data: dict, node_binding: dict) -> list[dict]:
        """
        Internal function that creates the "constraints" for the given layer.

        :param dict constraint_data: deserialized constraint data.
        :param dict node_binding: layer node binding data.
        :return: list of created constraints.
        :rtype: list[dict]
        """

        constraints = list()
        parent_component = self.parent()

        for constraint in constraint_data['constraints']:
            for _, target_id in constraint['targets']:
                parent_target = node_binding.get(target_id)
                if not parent_target:
                    continue
                self.set_parent(parent_component, parent_target)
                break
            break

        return constraints

    def _set_skeleton_naming(self, naming_manager: NameManager, mod: api.OpenMaya.MDGModifier):
        """
        Internal function that updates the node names of the skeleton layer nodes.

        :param NameManager naming_manager: naming manager instance to use.
        :param api.MDGModifier mod: optional modifier to use to rename the nodes.
        """

        def _change_lock_skeleton_layer(state):
            """
            Internal function that sets the lock state of the skeleton layer nodes.

            :param bool state: True to lock the nodes; False otherwise.
            """

            for _layer_node in layer_mapping.values():
                try:
                    transform = _layer_node.root_transform()
                    _layer_node.lock(state, mod=mod, apply=False)
                    transform.lock(state, mod=mod, apply=False)
                except AttributeError:
                    continue
            for setting_attr in settings:
                setting_attr.lock(state, mod=mod, apply=False)

        component_name, component_side = self.name(), self.side()
        layer_mapping = self._meta.layers_by_id((consts.INPUT_LAYER_TYPE, consts.OUTPUT_LAYER_TYPE, consts.SKELETON_LAYER_TYPE))
        settings = []
        for layer_node in layer_mapping.values():
            settings.extend(list(layer_node.iterate_settings_nodes()))

        try:
            _change_lock_skeleton_layer(False)
            for layer_id, layer_node in layer_mapping.items():
                hierarchy_name, meta_name = naming.compose_names_for_layer(
                    naming_manager, component_name, component_side, layer_id)
                try:
                    transform = layer_node.root_transform()
                    layer_node.rename(meta_name, mod=mod, apply=False)
                    transform.rename(hierarchy_name, mod=mod, apply=False)
                except AttributeError:
                    continue
                for setting in settings:
                    name = naming_manager.resolve(
                        'settingsName', {
                            'componentName': component_name, 'side': component_side,
                            'section': setting.id(), 'type': 'settings'})
                    setting.rename(name, mod=mod, apply=False)
        finally:
            _change_lock_skeleton_layer(True)

        self.set_skeleton_naming(naming_manager, mod)

    def _update_space_switch_component_dependencies(self, new_name: str, new_side: str):
        """
        Internal function that updates any component space switches which contains this component current name as a
        driver and updates it to the new name.

        :param str new_name: new name for this component which all component space switches will be updated with.
        :param str new_side: new side for this component which all component space switches will be updated with.
        """

        pass


class SpaceSwitchUIDriver:
    """
    Space Switch UI driver Control Data class
    """

    def __init__(self, id: str, label: str, internal: bool = False):
        self._id = id
        self._label = label
        self._internal = internal

    @property
    def id(self) -> str:
        return self._id

    @property
    def label(self) -> str:
        return self._label

    @property
    def internal(self) -> bool:
        return self._internal

    def serialize(self) -> dict:
        """
        Serializes the object attributes into a dictionary.

        :return: serialized object.
        :rtype: dict
        """

        return {
            'id': self._id,
            'label': self._label,
            'internal': self._internal
        }


class SpaceSwitchUIDriven:
    """
    Space Switch UI driven Control Data class
    """

    def __init__(self, id: str, label: str):
        self._id = id
        self._label = label

    @property
    def id(self) -> str:
        return self._id

    @property
    def label(self) -> str:
        return self._label

    def serialize(self) -> dict:
        """
        Serializes the object attributes into a dictionary.

        :return: serialized object.
        :rtype: dict
        """

        return {
            'id': self._id,
            'label': self._label
        }
