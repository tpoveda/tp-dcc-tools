from __future__ import annotations

import os
import inspect
from typing import Iterator, Iterable, Type

from overrides import override

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.common.python import helpers, decorators, path, modules
from tp.maya.api import types, base, attributetypes


MCLASS_ATTR_NAME = 'tpMetaClass'
MVERSION_ATTR_NAME = 'tpMetaVersion'
MPARENT_ATTR_NAME = 'tpMetaParent'
MCHILDREN_ATTR_NAME = 'tpMetaChildren'
MTAG_ATTR_NAME = 'tpTag'

logger = log.tpLogger


def core_meta_node() -> Core:
    """
    Returns the initial network meta node instance. If one does not exist, it will be automatically created.

    :return: core meta node instance.
    :rtype: Core
    """

    core_nodes = find_meta_nodes_by_class_type(Core.ID)
    if not core_nodes:
        core_node = Core()
        return core_node

    return helpers.first_in_list(core_nodes)


def registry_name_for_class(class_type: Type) -> str:
    """
    Returns the metaclass name used by the register.

    :param Type class_type: metaclass type to get name of.
    :return: name of the metaclass.
    :rtype: str
    """

    return class_type.ID or class_type.__name__


def is_meta_node(node: base.DGNode) -> bool:
    """
    Returns whether given node is a meta node.

    :param base.DGNode node: node to check.
    :return: True if given node is a meta node ; False otherwise.
    :rtype: bool
    """

    if isinstance(node, MetaBase) or issubclass(type(node), MetaBase):
        return True

    if not node.hasAttribute(MCLASS_ATTR_NAME):
        return False

    if not MetaRegistry.types:
        MetaRegistry()

    return MetaRegistry.is_in_registry(node.attribute(MCLASS_ATTR_NAME).asString())


def meta_node_type_name(node: base.DGNode) -> str:
    """
    Returns the MetaClass type from the given node.

    :param base.DGNode node: node to get meta node type of.
    :return: meta node type.
    :rtype: str
    """

    if not node.hasAttribute(MCLASS_ATTR_NAME):
        return ''

    if not MetaRegistry.types:
        MetaRegistry()

    meta_class_name = node.attribute(MCLASS_ATTR_NAME).asString()
    return '' if not MetaRegistry.is_in_registry(meta_class_name) else meta_class_name


def meta_node_type(node: base.DGNode) -> Type | None:
    """
    Returns the MetaClass type from the given node.

    :param base.DGNode node: node to get meta node type of.
    :return: meta node type.
    :rtype: Type or None
    """

    if not node.hasAttribute(MCLASS_ATTR_NAME):
        return None

    if not MetaRegistry.types:
        MetaRegistry()

    meta_class_name = node.attribute(MCLASS_ATTR_NAME).asString()
    if not MetaRegistry.is_in_registry(meta_class_name):
        return None

    return MetaRegistry.get_type(meta_class_name)


def find_scene_roots() -> list[MetaBase]:
    """
    Finds all meta nodes in the scene that are root meta nodes.

    :return: list of root meta nodes within current scene.
    :rtype: list[MetaBase]
    """

    return [meta for meta in iterate_scene_meta_nodes() if not list(meta.get_meta_parents())]


def iterate_scene_meta_nodes() -> Iterator[MetaBase]:
    """
    Generator function that iterates over all meta nodes in the current Maya scene.

    :return: found meta node instances within current Maya scene.
    :rtype: Iterator[MetaBase]
    """

    it = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kAffect)
    while not it.isDone():
        mobj = it.thisNode()
        dep = OpenMaya.MFnDependencyNode(mobj)
        if dep.hasAttribute(MCLASS_ATTR_NAME):
            yield MetaBase(node=mobj)
        it.next()


def find_meta_nodes_by_class_type(class_type: Type | str) -> list[MetaBase]:
    """
    Generator function that returns all meta nodes within current scene with given meta type.

    :param Type or str class_type: metaclass type.
    :return: generator of found meta nodes with given metaclass type.
    :rtype: list[MetaBase]
    """

    class_type_name = str(class_type)
    if inspect.isclass(class_type):
        class_type_name = class_type.ID

    found_meta_nodes = []
    for meta_node in iterate_scene_meta_nodes():
        meta_class_name = meta_node.attribute(MCLASS_ATTR_NAME).value()
        if meta_class_name != class_type_name:
            continue
        found_meta_nodes.append(meta_node)

    return found_meta_nodes


def find_meta_node_from_node(
        start_node: base.DGNode, check_type: str | Type, attribute: str = 'message') -> MetaBase | None:
    """
    Searches all connections of the given attribute recursively until there are no connections to the attribute or
    the given check_type of object is found.

    :param base.DGNode start_node: node to start searching from.
    :param str or Type check_type: meta node type to search for.
    :param str attribute: name of the attribute to search on.
    :return: first meta node instance that matches given type.
    :rtype: MetaBase or None
    """

    is_type = inspect.isclass(check_type)

    if start_node.apiType() == OpenMaya.MFn.kAffect:
        if is_type:
            node_type = meta_node_type(start_node)
            if check_type in node_type.mro():
                return create_meta_node_from_node(start_node)
        else:
            node_type_name = meta_node_type(start_node)
            if check_type == node_type_name:
                return create_meta_node_from_node(start_node)

    nodes_check_list = list()

    attr_name = '.'.join([start_node.fullPathName(), attribute])
    for node_name in cmds.listConnections(attr_name) or list():
        node = base.node_by_name(node_name)
        if not node or node.apiType() != OpenMaya.MFn.kAffect:
            continue
        if is_type:
            node_type = meta_node_type(node)
            if check_type in node_type.mro():
                return create_meta_node_from_node(node)
            else:
                nodes_check_list.append(node)
        else:
            node_type_name = meta_node_type_name(node)
            if check_type == node_type_name:
                return create_meta_node_from_node(node)
            else:
                nodes_check_list.append(node)

    for node in nodes_check_list:
        next_node = find_meta_node_from_node(node, check_type=check_type, attribute=attribute)
        if next_node is None:
            continue
        else:
            return find_meta_node_from_node(node, check_type=check_type, attribute=attribute)

    return None


def create_meta_node_from_node(node: base.DGNode) -> MetaBase:
    """
    Creates a new meta node instance wrapping the given node.

    :param DGNode node: node to create meta node instance from.
    :return: newly created meta node instance.
    :rtype: MetaBase
    """

    meta_class_type = meta_node_type(node)
    return meta_class_type(node=node.object(), init_defaults=False) if meta_class_type else None


def create_meta_node_by_type(type_name: str, *args: tuple, **kwargs) -> MetaBase | None:
    """
    Creates a new meta node instance within current scene and returns the type class instance from the meta registry.

    :param str type_name: metaclass type to create.
    :param tuple args: args to pass to the class.__init__ function.
    :return: subclass instance of MetaBase for the type.
    :rtype: MetaBase or None
    """

    class_type = MetaRegistry().get_type(type_name)
    if not class_type:
        return None

    return class_type(*args, **kwargs)


def is_connected_to_meta(node: base.DGNode, type_name: str | None = None) -> bool:
    """
    Returns whether given node is directly connected to a meta node by searching upstream of the node.

    :param base.DGNode node: node to check.
    :param str or None type_name: optional meta type filter.
    :return: True if given node is connected to a meta node; False otherwise.
    :rtype: bool
    """

    for _, source in node.iterateConnections(True, False):
        if is_meta_node(source.node()):
            if type_name is not None and node.attribute(MCLASS_ATTR_NAME).asString() == type_name:
                return True

    return False


def connected_meta_nodes(node: base.DGNode | OpenMaya.MObject) -> list[MetaBase]:
    """
    Returns all the down stream connected meta nodes.

    :param DGNode or OpenMaya.MObject node: scene node to search connected nodes of.
    :return: connected down stream meta nodes.
    :rtype: list[MetaBase]
    """

    if is_meta_node(node):
        if isinstance(node, base.DGNode):
            return [MetaBase(node=node.object(), init_defaults=False)]
        return [node]

    meta_nodes = []
    for dest in node.message.destinations():
        obj = dest.node()
        if is_meta_node(obj):
            meta_nodes.append(MetaBase(node=obj.object(), init_defaults=False))

    return meta_nodes


@decorators.add_metaclass(decorators.Singleton)
class MetaRegistry(object):
    """
    Singleton class that handles global registration of the different metaclass.
    """

    meta_env = 'TPDCC_META_PATHS'
    types = dict()

    def __init__(self):
        try:
            self.reload()
        except ValueError:
            logger.error('Failed to registry environment', exc_info=True)

    @classmethod
    def is_in_registry(cls, type_name: str) -> bool:
        """
        Returns whether the given type is currently available within the registry.

        :param str type_name: name of type to check.
        :return: True if the type is already registered; False otherwise.
        :rtype: bool
        """

        return type_name in cls.types

    @classmethod
    def get_type(cls, type_name: str) -> Type:
        """
        Returns the class of the type.

        :param str type_name: class name.
        :return: class object for the given type name.
        :rtype: Type
        """

        return cls.types.get(type_name)

    @classmethod
    def register_meta_class(cls, class_obj: Type):
        """
        Registers a metaclass with the registry.
        :param Type class_obj: metaclass to register.
        """

        if issubclass(class_obj, MetaBase) or isinstance(class_obj, MetaBase):
            registry_name = registry_name_for_class(class_obj)
            if registry_name in cls.types:
                return
            logger.info(f'Registering MetaClass --> {registry_name} | {class_obj}')
            cls.types[registry_name] = class_obj

    @classmethod
    def register_meta_classes(cls, paths: list[str]):
        """
        Registers given paths within the meta registry.

        :param list[str] paths: list of module or package paths.
        """

        for _path in paths:
            if path.is_dir(_path):
                cls.register_by_package(_path)
                continue
            elif path.is_file(_path):
                imported_module = modules.import_module(modules.convert_to_dotted_path(os.path.normpath(_path)))
                if imported_module:
                    cls.register_by_module(imported_module)
                    continue

    @classmethod
    def register_by_package(cls, package_path: str):
        """
        Registers given package path into the meta registry.

        :param str package_path: package path to register (eg. tp.core)
        ..warning:: this function is expensive as it requires a recursive search by importing all sub modules.
        """

        visited_packages = set()
        for sub_module in modules.iterate_modules(package_path):
            file_name = os.path.splitext(path.basename(sub_module))[0]
            if file_name.startswith('__') or file_name in visited_packages:
                continue
            visited_packages.add(file_name)
            sub_module_obj = modules.import_module(modules.convert_to_dotted_path(os.path.normpath(sub_module)))
            for member in modules.iterate_module_members(sub_module_obj, predicate=inspect.isclass):
                cls.register_meta_class(member[1])

    @classmethod
    def register_by_module(cls, module: Type):
        """
        Registers a module by searching all class members of the module and registers any class that is an instance
        of the MetaBase class.

        :param Type module: module to register.
        """

        if inspect.ismodule(module):
            for member in modules.iterate_module_members(module, predicate=inspect.isclass):
                cls.register_meta_class(member[1])

    @classmethod
    def register_by_env(cls, env_name: str):
        """
        Registers a set of metaclass based on the given environment variable.

        :param str env_name: environment variable name.
        """

        environment_paths = os.getenv(env_name)
        if environment_paths is None:
            logger.info('No environment variable with name "{}" exists!'.format(env_name))
            return

        environment_paths = environment_paths.split(os.pathsep)

        cls.register_meta_classes(environment_paths)

    def reload(self):
        """
        Reloads meta register based on MetaRegistry environment variable.
        """

        self.register_by_env(MetaRegistry.meta_env)


class MetaFactory(type):
    """
    Metaclass for MetaBase class to create the correct MetaBase subclass based on class name if a meta node (MObject)
    exists in the given arguments.
    """

    def __call__(cls, *args, **kwargs):

        node = kwargs.get('node')
        if args:
            node = args[0]

        register = MetaRegistry

        # if the given class is not registered, we register it
        registry_name = registry_name_for_class(cls)
        if registry_name not in register.types:
            register.register_meta_class(cls)

        if not node:
            return type.__call__(cls, *args, **kwargs)

        class_type = MetaBase.get_class_name_from_plug(node)
        if class_type == registry_name:
            return type.__call__(cls, *args, **kwargs)

        registered_type = MetaRegistry().get_type(class_type)
        if registered_type is None:
            return type.__call__(cls, *args, **kwargs)

        return type.__call__(registered_type, *args, **kwargs)


@decorators.add_metaclass(MetaFactory)
class MetaBase(base.DGNode):
    """
    Base Meta Class implementation
    """

    ID = ''
    DEFAULT_NAME = ''

    def __init__(
            self, node: OpenMaya.MObject | None = None, name: str | None = None, namespace: str | None = None,
            init_defaults: bool = True, lock: bool = False, mod: OpenMaya.MDGModifier | None = None, *args, **kwargs):
        """
        Constructor.

        :param OpenMaya.MObject  or None node: node instance this meta node will be based on.
        :param str or None name: name of the meta node.
        :param bool init_defaults: whether to initialize meta defaults.
        :param bool lock: whether to lock meta node instance after building it.
        :param OpenMaya.MDGModifier or None mod: optional Maya modifier to add to.
        """

        super(MetaBase, self).__init__(node=node)

        # if not Maya node is given, a new network one will be created.
        if node is None:
            self.create(
                name or self.DEFAULT_NAME or '_'.join([registry_name_for_class(self.__class__), 'meta']),
                node_type='network', namespace=namespace, mod=mod)

        # meta attribute are only if the meta node is not a referenced
        if init_defaults and not self.isReferenced():
            if mod:
                mod.doIt()
            self._init_meta(mod=mod)

            # lock meta node only if it is not already locked
            if lock and not self.mfn().isLocked:
                self.lock(True, mod=mod)

        if node is None:
            self.setup(*args, **kwargs)

    def __repr__(self):
        return '{} ({})'.format(self.as_str(name_only=True), self.name())

    @staticmethod
    def get_class_name_from_plug(node: OpenMaya.MObject) -> str:
        """
        From the given Maya object or Meta clas instance, returns the associated class name which should exists on the
        Maya node as an attribute.

        :param OpenMaya.MObject or MetaBase node: node to find class name for.
        :return: metaclass name.
        :rtype: str
        """

        if isinstance(node, MetaBase):
            return node.attribute(MCLASS_ATTR_NAME).value()
        dep = OpenMaya.MFnDependencyNode(node)
        try:
            return dep.findPlug(MCLASS_ATTR_NAME, False).asString()
        except RuntimeError as exc:
            return str(exc)

    @classmethod
    def as_str(cls, name_only: bool = False) -> str:
        """
        Returns a string representation of this metaclass path.

        :param bool name_only: whether to only return the name of metaclass.
        :return: metaclass path representation
        :rtype: str
        """

        meta_module = cls.__module__
        meta_name = cls.__name__
        if name_only:
            return meta_name

        return '.'.join([meta_module, meta_name])

    @override
    def delete(self, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
        """
        Deletes the node from the scene.

        :param OpenMaya.MDGModifier mod: modifier to add the delete operation into.
        :param bool apply: whether to apply the modifier immediately.
        :return: True if the node deletion was successful; False otherwise.
        :raises RuntimeError: if deletion operation fails.
        :rtype: bool
        """

        child_plug = self.attribute(MCHILDREN_ATTR_NAME)
        for element in child_plug:
            element.disconnectAll(mod=mod)

        return super(MetaBase, self).delete(mod=mod, apply=apply)

    def setup(self, *args, **kwargs):
        """
        Function that is called after the create function is called.
        Can be used to customize the way a meta node is constructed.

        :param Iterable args: list of positional arguments.
        :param Dict kwargs: dictionary of keyword arguments.
        """

        pass

    def meta_attributes(self) -> list[dict]:
        """
        Returns the list of default meta attributes that should be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: List[Dict]
        """

        class_name = registry_name_for_class(self.__class__)

        return [
            {
                'name': MCLASS_ATTR_NAME,
                'value': class_name,
                'type': attributetypes.kMFnDataString,
                'locked': True,
                'storable': True,
                'writable': True,
                'connectable': False
            },
            {
                'name': MVERSION_ATTR_NAME,
                'value': '1.0.0',
                'type': attributetypes.kMFnDataString,
                'locked': True,
                'storable': True,
                'writable': True,
                'connectable': False
            },
            {
                'name': MPARENT_ATTR_NAME,
                'value': None,
                'type': attributetypes.kMFnMessageAttribute,
                'isArray': True,
                'locked': False
            },
            {
                'name': MCHILDREN_ATTR_NAME,
                'value': None,
                'type': attributetypes.kMFnMessageAttribute,
                'locked': False,
                'isArray': True
            },
            {
                'name': MTAG_ATTR_NAME,
                'value': '',
                'type': attributetypes.kMFnDataString,
                'locked': False,
                'storable': True,
                'writable': True,
                'connectable': False
            }
        ]

    def metaclass_type(self) -> str:
        """
        Returns metaclass for this meta node instance.

        :return: meta node instance type.
        :rtype: str
        """

        return self.attribute(MCLASS_ATTR_NAME).value()

    def is_root(self) -> bool:
        """
        Returns whether this meta node instance is a root one.

        :return: True if this meta node instance is connected to a meta parent node; False otherwise.
        :rtype: bool
        """

        for i in self.iterate_meta_parents():
            return True

        return False

    def tag(self) -> str:
        """
        Returns meta node tag.

        :return: meta node tag.
        :rtype: str
        """

        return self.attribute(MTAG_ATTR_NAME).value()

    def set_tag(self, tag_name: str):
        """
        Sets meta node tag attribute.

        :param str tag_name: tag value.
        """

        self.attribute(MTAG_ATTR_NAME).set(tag_name)

    def connect_to(self, attribute_name: str, node: base.DGNode):
        """
        Connects given node to the message attribute with given name.

        :param str attribute_name: name of the attribute to connect from. If the attribute does not exists, it will
            be created automatically.
        :param base.DGNode node: destination node.
        :return: destination plug.
        :rtype: OpenMaya.MPlug
        """

        node_attr_name = 'message'
        source_plug = node.attribute(node_attr_name)

        if self.hasAttribute(attribute_name):
            destination_plug = self.attribute(attribute_name)
        else:
            new_attr = self.addAttribute(attribute_name, value=None, type=attributetypes.kMFnMessageAttribute)
            if new_attr is not None:
                destination_plug = new_attr
            else:
                destination_plug = self.attribute(attribute_name)
        source_plug.connect(destination_plug)

        return destination_plug

    def connect_to_by_plug(self, destination_plug: base.Plug, node: base.DGNode) -> base.Plug:
        """
        Connects given node to the message attribute of the given plug instance.

        :param base.Plug destination_plug: target plug to connect.
        :param base.DGNode node: destination node.
        :return: destination plug.
        :rtype: base.Plug
        """

        source_plug = node.attribute('message')
        source_plug.connect(destination_plug)

        return destination_plug

    def downstream(self, check_type: str | type) -> MetaBase:
        """
        Returns the first network node by following the .message attribute connections.

        :param str or type check_type: meta node instance type to search.
        :return: first found meta node instance that matches given type.
        :rtype: MetaBase
        """

        is_type = inspect.isclass(check_type)
        if is_type:
            node_type = meta_node_type(self)
            if check_type in node_type.mro():
                return self
        else:
            node_type_name = meta_node_type(self)
            if check_type == node_type_name:
                return create_meta_node_from_node(self)

        return helpers.first_in_list(list(self.iterate_meta_parents(recursive=True, check_type=check_type)))

    def upstream(self, check_type: str | type) -> MetaBase:
        """
        Returns the first network node by following the children attribute connection.

        :param str or type check_type: meta node instance type to search.
        :return: first found meta node instance that matches given type.
        :rtype: MetaBase
        """

        is_type = inspect.isclass(check_type)

        if is_type:
            node_type = meta_node_type(self)
            if check_type in node_type.mro():
                return self
        else:
            node_type_name = meta_node_type(self)
            if check_type == node_type_name:
                return create_meta_node_from_node(self)

        return helpers.first_in_list(list(self.iterate_meta_children(check_type=check_type)))

    def meta_root(self) -> MetaBase | None:
        """
        Returns the first meta parent this meta node instance is connected to.

        :return: first meta node parent.
        :rtype: MetaBase or None
        """

        for current_parent in self.iterate_meta_parents(recursive=True):
            parents = list(current_parent.iterate_meta_parents(recursive=True))
            if not parents:
                return current_parent

        return None

    def meta_parent(self) -> MetaBase | None:
        """
        Returns direct meta parent for this meta node.

        :return: first direct meta parent.
        :rtype: MetaBase or None
        """

        meta_parents = list(self.iterate_meta_parents(recursive=False))
        return meta_parents[0] if meta_parents else None

    def iterate_meta_parents(self, recursive: bool = False, check_type: str | Type | None = None) -> Iterator[MetaBase]:
        """
        Generator function that iterates over all meta parent nodes this node is linked to.

        :param bool recursive: whether to find meta parents in a recursive manner.
        :param str or Type or None check_type: meta node type to search for.
        :return: Iterator[MetaBase]
        """

        is_type = inspect.isclass(check_type)
        parent_plug = self.attribute(MPARENT_ATTR_NAME)
        if not parent_plug:
            return
        for child_element in parent_plug:
            for dest in child_element.destinations():
                parent_meta = MetaBase(dest.node().object(), init_defaults=False)
                if not check_type:
                    yield parent_meta
                else:
                    if is_type and check_type in parent_meta.__class__.mro():
                        yield parent_meta
                    elif helpers.is_string(check_type) and check_type == parent_meta.attribute(MCLASS_ATTR_NAME).value():
                        yield parent_meta
                if recursive:
                    for i in parent_meta.iterate_meta_parents(recursive=recursive):
                        yield i

    def iterate_meta_children(self, depth_limit: int = 256, check_type: str | Type | None = None) -> Iterator[MetaBase]:
        """
        Generator function that yields all children meta node instances connected to the metaChildren plug of this meta
        node instance.

        :param int depth_limit: recursive depth limit.
        :param str or Type or None check_type: meta node type to search for.
        :return: iterated meta children.
        :rtype: Iterator[MetaBase]
        """

        is_type = inspect.isclass(check_type)
        child_plug = self.attribute(MCHILDREN_ATTR_NAME)
        for element in child_plug:
            if depth_limit < 1:
                return
            child = element.source()
            if child is None:
                continue
            child = child.node()
            if not child.hasAttribute(MCHILDREN_ATTR_NAME):
                continue
            child_meta = MetaBase(child.object(), init_defaults=False)
            if not check_type:
                yield child_meta
            else:
                if is_type and check_type in child_meta.__class__.mro():
                    yield child_meta
                elif helpers.is_string(check_type) and check_type == child_meta.attribute(MCLASS_ATTR_NAME).value():
                    yield child_meta
            for sub_child in child_meta.iterate_meta_children(depth_limit=depth_limit - 1, check_type=check_type):
                yield sub_child

    def meta_children(self, depth_limit: int = 256, check_type: str | Type | None = None) -> list[MetaBase]:
        """
        Returns all children meta node instances connected to the metaChildren plug of this meta node instance.

        :param int depth_limit: recursive depth limit.
        :param str or Type or None check_type: meta node type to search for.
        :return: meta children.
        :rtype: list[MetaBase]
        """

        return list(self.iterate_meta_children(depth_limit=depth_limit, check_type=check_type))

    def iterate_children(
            self, filter_types: set | None = None, include_meta: bool = False) -> Iterator[base.DGNode | base.DagNode]:
        """
        Generator function that iterates over all children nodes.

        :param set or None filter_types: optional lister of node filter types.
        :param bool include_meta: whether to include children meta nodes.
        :return: iterated DG/Dag nodes.
        :rtype: Iterator[base.DGNode | base.DagNode]
        """

        filter_types = filter_types or ()
        for _, destination in self.iterateConnections(False, True):
            dest_node = destination.node()
            if not filter_types or any(dest_node.hasFn(i) for i in filter_types):
                if not include_meta and is_meta_node(dest_node):
                    continue
                yield dest_node

    def find_children_by_class_type(self, class_type: str, depth_limit: int = 1) -> list[MetaBase]:
        """
        Finds all meta node children of the given type.

        :param str class_type: metaclass type name.
        :param int depth_limit: recursive depth limit.
        :return: iterable of meta node children instances found of given type.
        :rtype: list[MetaBase]
        """

        return [child for child in self.iterate_meta_children(depth_limit) if child.metaclass_type() == class_type]

    def find_children_by_class_types(self, class_types: Iterable[str], depth_limit: int = 1) -> list[MetaBase]:
        """
        Finds all meta node children of the given types.

        :param List[str] class_types: metaclass type names.
        :param int depth_limit: recursive depth limit.
        :return: iterable of meta node children instances found of given type.
        :rtype: list[MetaBase]
        """

        return [child for child in self.iterate_meta_children(depth_limit) if child.metaclass_type() in class_types]

    def add_meta_child(self, child: MetaBase, mod: OpenMaya.MDGModifier | OpenMaya.MDagModifier | None = None):
        """
        Adds a new meta child to this meta node instance.

        :param MetaBase child: meta child.
        :param OpenMaya.MDGModifier or OpenMaya.MDGModifier or None mod: optional Maya modifier to use.
        """

        child.remove_meta_parent(mod=mod)
        child.add_meta_parent(self, mod=mod)

    def add_meta_parent(self, parent: MetaBase, mod: OpenMaya.MDGModifier | OpenMaya.MDagModifier | None = None):
        """
        Sets the parent meta node for this meta node instance and removes the previous meta parent if it is already
        defined.

        :param MetaBase parent: parent meta node instance.
        :param OpenMaya.MDagModifier or OpenMaya.MDGModifier or None mod: optional Maya modifier to use.
        """

        parent_plug = self.attribute(MPARENT_ATTR_NAME)
        next_element = parent_plug.nextAvailableElementPlug()
        next_element.connect(parent.attribute(MCHILDREN_ATTR_NAME).nextAvailableDestElementPlug(), mod=mod)

    def remove_meta_parent(
            self, parent: MetaBase | None = None,
            mod: OpenMaya.MDGModifier | OpenMaya.MDagModifier | None = None) -> bool:
        """
        Removes meta parent for this meta node instance.

        :param MetaBase or None parent: optional meta parent to remove; if None, all meta parents will be removed.
        :param OpenMaya.MDagModifier or OpenMaya.MDGModifier or None mod: optional Maya modifier to use.
        :return: True if the remove meta parent operation was successful; False otherwise.
        :rtype :bool
        """

        modifier = mod or types.DGModifier()
        parent_plug = self.attribute(MPARENT_ATTR_NAME)
        for element in parent_plug:
            for dest in element.destinations():
                n = dest.node()
                if parent is None or n == parent:
                    element.disconnect(dest, mod=modifier, apply=False)
        if mod is None:
            modifier.doIt()

        return True

    def remove_all_meta_parents(self) -> bool:
        """
        Removes all meta parents for this meta node instance.
        :return: True if the remove meta parents operation was successful; False otherwise.
        :rtype :bool
        """

        parent_plug = self.attribute(MPARENT_ATTR_NAME)
        for element in parent_plug:
            for dest in element.destinations():
                element.disconnect(dest)
                element.delete()

        return True

    def _init_meta(self, mod: OpenMaya.MDGModifier | OpenMaya.MDagModifier | None = None):
        """
        Internal function that initializes standard attributes for the meta node.

        :param OpenMaya.MDagModifier or None mod: optional Maya modifier to add to.
        :return: list of created attributes.
        :rtype: list(base.Plug)
        """

        return self.createAttributesFromDict({k['name']: k for k in self.meta_attributes()}, mod=mod)


class Core(MetaBase):
    """
    Core network object, which is the starting point for any meta node graph. Must exist for other nodes to connect to.
    """

    ID = 'core'

    def __init__(
            self, node: OpenMaya.MObject | None = None, name: str | None = None, init_defaults: bool = True,
            lock: bool = False, mod: OpenMaya.MDGModifier | None = None, *args, **kwargs):
        super(Core, self).__init__(
            node=node, name=name, init_defaults=init_defaults, lock=lock, mod=mod, *args, **kwargs)


class DependentNode(MetaBase):
    """
    Base class for meta nodes that must have another meta node instance to exist. This class automatically handles
    the creation of all dependent nodes down the chain until one can connect into the existing meta node graph.
    """

    ID = 'dependentNode'
    DEPENDENT_NODE_CLASS = None

    def __init__(
            self, node: OpenMaya.MObject | None = None, name: str | None = None, parent: MetaBase | None = None,
            init_defaults: bool = True, lock: bool = False, mod: OpenMaya.MDGModifier | None = None, *args, **kwargs):
        super().__init__(node=node, name=name, init_defaults=init_defaults, lock=lock, mod=mod, *args, **kwargs)

        if node is None and self.DEPENDENT_NODE_CLASS is not None:
            parent_node = parent if parent else core_meta_node()
            dependent_node = parent_node.downstream(self.DEPENDENT_NODE_CLASS)
            if not dependent_node:
                dependent_node = self.DEPENDENT_NODE_CLASS(parent=parent_node)
            self.add_meta_parent(dependent_node)
