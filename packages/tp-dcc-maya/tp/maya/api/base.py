from __future__ import annotations

import contextlib
from functools import wraps
from typing import Iterator, Iterable, Any

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaAnim as OpenMayaAnim

from overrides import override

from tp.core import log
from tp.common.python import helpers
from tp.maya.api import exceptions, consts, types, attributetypes
from tp.maya.om import nodes, plugs, utils, factory, mathlib

LOCAL_TRANSLATE_ATTRS = ['translateX', 'translateY', 'translateZ']
LOCAL_ROTATE_ATTRS = ['rotateX', 'rotateY', 'rotateZ']
LOCAL_SCALE_ATTRS = ['scaleX', 'scaleY', 'scaleZ']
LOCAL_TRANSFORM_ATTRS = LOCAL_TRANSLATE_ATTRS + LOCAL_ROTATE_ATTRS + LOCAL_SCALE_ATTRS

logger = log.tpLogger


def lock_node_context(fn: callable):
    """
    Decorator function to lock and unlock the node.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def locker(*args, **kwargs):
        node = args[0]
        set_locked = False
        if node.isLocked and not node.isReferenced():
            node.lock(False)
            set_locked = True
        try:
            return fn(*args, **kwargs)
        finally:
            if set_locked and node.exists():
                node.lock(True)

    return locker


def lock_node_plug_context(fn: callable):
    """
    Decorator function to lock and unlock a node plug.

    :param callable fn: decorated function.
    """

    @wraps(fn)
    def locker(*args, **kwargs):
        plug = args[0]
        node = plug.node()
        set_locked = False
        set_plug_locked = False
        if node.isLocked and node.isReferenced():
            node.lock(False)
            set_locked = True
        if plug.isLocked:
            plug.lock(False)
            set_plug_locked = True
        try:
            return fn(*args, **kwargs)
        finally:
            if node.exists():
                if set_plug_locked and plug.exists():
                    plug.lock(True)
                if set_locked:
                    node.lock(True)

    return locker


@contextlib.contextmanager
def lock_state_attr_context(node: DGNode, attr_names: list[str], state: bool):
    """
    Context manager which handles the lock state for a list of attribute on the given node.

    :param DGNode node: node to lock/unlock attributes of.
    :param list[str] attr_names: list of attribute names.
    :param bool state: lock state to set while executing the context scope.
    """

    attributes = []
    try:
        for attr_name in attr_names:
            attr = node.attribute(attr_name)
            if attr is None:
                continue
            if attr.isLocked != state:
                attributes.append(attr)
                attr.lock(state)
        yield
    finally:
        for attr in attributes:
            if not attr:
                continue
            attr.lock(not state)


def node_by_object(
        mobj: OpenMaya.MObject) -> DGNode | DagNode | NurbsCurve | Mesh | Camera | IkHandle | Joint | ContainerAsset \
                                    | AnimCurve | SkinCluster | AnimLayer | ObjectSet | BlendShape | DisplayLayer:
    """
    Returns the correct API node for the given MObject by wrapping the MObject within an API node instance.

    :param OpenMaya.MObject mobj: Maya object.
    :return: API node instance.
    :rtype: DGNode
    """

    if mobj.hasFn(OpenMaya.MFn.kDagNode):
        dag_path = OpenMaya.MDagPath.getAPathTo(mobj)
        if mobj.hasFn(OpenMaya.MFn.kNurbsCurve):
            sup = NurbsCurve
        elif mobj.hasFn(OpenMaya.MFn.kMesh):
            sup = Mesh
        elif mobj.hasFn(OpenMaya.MFn.kCamera):
            sup = Camera
        elif mobj.hasFn(OpenMaya.MFn.kIkHandle):
            sup = IkHandle
        elif mobj.hasFn(OpenMaya.MFn.kJoint):
            sup = Joint
        else:
            sup = DagNode
        object_to_set = dag_path
    else:
        if mobj.hasFn(OpenMaya.MFn.kContainer):
            sup = ContainerAsset
        elif mobj.hasFn(OpenMaya.MFn.kAnimCurve):
            sup = AnimCurve
        elif mobj.hasFn(OpenMaya.MFn.kSkinClusterFilter):
            sup = SkinCluster
        elif mobj.hasFn(OpenMaya.MFn.kControllerTag):
            sup = DGNode
        elif mobj.hasFn(OpenMaya.MFn.kSet):
            sup = ObjectSet
        elif mobj.hasFn(OpenMaya.MFn.kBlendShape):
            sup = BlendShape
        elif mobj.hasFn(OpenMaya.MFn.kDisplayLayer):
            sup = DisplayLayer
        else:
            sup = DGNode
        object_to_set = mobj

    return sup(object_to_set)


def node_by_name(
        node_name: str | OpenMaya.MObject) -> DGNode | DagNode | NurbsCurve | Mesh | Camera | IkHandle | Joint | \
                                              ContainerAsset | AnimCurve | SkinCluster | AnimLayer | ObjectSet | \
                                              BlendShape | DisplayLayer | None:
    """
    Returns a DAG node instance based on the given node name (expecting a full path).

    :param str or OpenMaya.Mobject node_name: Maya node name or object instance.
    :return: API node instance.
    :rtype: DGNode or DagNode
    """

    mobj = nodes.mobject(node_name)
    if mobj is None:
        return None
    if mobj.hasFn(OpenMaya.MFn.kDagNode):
        dag_path = OpenMaya.MDagPath.getAPathTo(mobj)
        if mobj.hasFn(OpenMaya.MFn.kNurbsCurve):
            sup = NurbsCurve
        elif mobj.hasFn(OpenMaya.MFn.kMesh):
            sup = Mesh
        elif mobj.hasFn(OpenMaya.MFn.kCamera):
            sup = Camera
        elif mobj.hasFn(OpenMaya.MFn.kIkHandle):
            sup = IkHandle
        elif mobj.hasFn(OpenMaya.MFn.kJoint):
            sup = Joint
        else:
            sup = DagNode
        object_to_set = dag_path
    else:
        if mobj.hasFn(OpenMaya.MFn.kContainer):
            sup = ContainerAsset

        elif mobj.hasFn(OpenMaya.MFn.kAnimCurve):
            sup = AnimCurve
        elif mobj.hasFn(OpenMaya.MFn.kSkinClusterFilter):
            sup = SkinCluster
        elif mobj.hasFn(OpenMaya.MFn.kControllerTag):
            sup = DGNode
        elif mobj.hasFn(OpenMaya.MFn.kAnimLayer):
            sup = AnimLayer
        elif mobj.hasFn(OpenMaya.MFn.kSet):
            sup = ObjectSet
        elif mobj.hasFn(OpenMaya.MFn.kBlendShape):
            sup = BlendShape
        elif mobj.hasFn(OpenMaya.MFn.kDisplayLayer):
            sup = DisplayLayer
        else:
            sup = DGNode
        object_to_set = mobj

    return sup(object_to_set)


def nodes_by_names(node_names):
    """
    Returns DAG node instances based on the given node names (expecting a full path).

    :param list(str) node_names: Maya node name.
    :return: API node instances.
    :rtype: list(DGNode) or list(DagNode)
    """

    for node_name in node_names:
        yield node_by_name(node_name)


def nodes_by_type_names(node_type_names):
    """
    Returns node instances based on the given node type name.

    :param str or list(str) node_type_names: node types to retrieve.
    :return: list of node instances.
    :rtype: list(DGNode) or list(DagNode)
    """

    found_node_names = cmds.ls(type=node_type_names, long=True)
    for found_node_name in found_node_names:
        yield node_by_name(found_node_name)


def plug_by_name(plug_path):
    """
    Returns the Plug instance for the given plug path.

    :param str plug_path: full path to the plug.
    :return: plug instance matching the given plug path.
    :rtype: Plug
    :raises exceptions.InvalidPlugPathError: if given plug path is not valid.
    """

    if '.' not in plug_path:
        raise exceptions.InvalidPlugPathError(plug_path)

    plug = plugs.as_mplug(plug_path)
    return Plug(node_by_object(plug.node()), plug)


def iterate_selected(filter_types: tuple[int] = ()) -> Iterator[DGNode]:
    """
    Generator function that yields all DAG node instances from selected objects in Maya.

    :param tuple(OpenMaya.MFn.kType) filter_types: optional tuple of types to filter selected nodes by.
    :return: iterated selected DAG nodes.
    :rtype: Iterator[DGNode]
    """

    return map(node_by_object, nodes.iterate_selected_nodes(filter_to_apply=filter_types))


def selected(filter_types: tuple[int] = ()) -> list[DGNode]:
    """
    Returns DAG node instances from selected objects in Maya.

    :param tuple(int) filter_types: optional tuple of types to filter selected nodes by.
    :return: list of selected DAG nodes.
    :rtype: list[DGNode]
    """

    return list(iterate_selected(filter_types=filter_types))


def select(objects: list[DGNode], mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> OpenMaya.MDGModifier:
    """
    Selects all given nodes in current scene.

    :param list(DGNode) objects: list of nodes to select.
    :param OpenMaya.MDGModifier mod: optional modifier to run command in.
    :param bool apply: whether to apply the modifier immediately.
    :return: modifier used to run the select operation.
    :rtype: OpenMaya.MDGModifier
    """

    mod = mod or OpenMaya.MDGModifier()
    mod.pythonCommandToExecute(f'from maya import cmds;cmds.select({[i.fullPathName() for i in objects]})')
    if apply:
        mod.doIt()

    return mod


def clear_selection(mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> OpenMaya.MDGModifier:
    """
    Clears current selection.

    :param OpenMaya.MDGModifier mod: optional modifier to run command in.
    :param bool apply: whether to apply the modifier immediately.
    :return: modifier used to clear current selection operation.
    :rtype: OpenMaya.MDGModifier
    """

    mod = mod or OpenMaya.MDGModifier()
    mod.pythonCommandToExecute('from maya import cmds;cmds.select(clear=True)')
    if apply:
        mod.doIt()

    return mod


class DGNode:
    """
    Wrapper class for Maya Dependency Graph nodes.
    """

    MFN_TYPE = OpenMaya.MFnDependencyNode

    def __init__(self, node: OpenMaya.MObject | None = None):
        self._handle = None  # type: OpenMaya.MObjectHandle or None
        self._mfn = None  # type: OpenMaya.MFn or None
        if node is not None:
            self.setObject(node)

    def __hash__(self):
        """
        Overrides __hash__ function to return the linked node hash code.

        :return: node hash code.
        :rtype: str
        """

        return self._handle.hashCode() if self._handle is not None else super(DGNode, self).__hash__()

    def __repr__(self):
        """
        Overrides __repr__ function to return the display string for this instance.

        :return: display string.
        :rtype: str
        """

        return self.fullPathName()

        # return '<{}> {}'.format(self.__class__.__name__, self.fullPathName())

    def __str__(self):
        """
        Overrides __str__ function to return the full path name for this instance.

        :return: full path name.
        :rtype: str
        """

        return self.fullPathName()

    def __bool__(self):
        """
         Overrides __bool__ function to return the False if the object does not exists.
         """

        return self.exists()

    def __getitem__(self, item):
        """
        Overrides __getitem__ function to attempt to retrieve the MPlug for this node.

        :param str item: attribute name.
        :return: Plug
        """

        fn = self.MFN_TYPE
        try:
            return Plug(self, fn.findPlug(item, False))
        except RuntimeError:
            raise KeyError('{} has no attribute by the name {}'.format(self.name(), item))

    def __setitem__(self, key, value):
        """
        Overrides __setitem__ function to attempt to set node attribute.

        :param str key: attribute name.
        :param any value: attribute value.
        """

        if key.startswith('_'):
            setattr(self, key, value)
            return
        if self.hasAttribute(key) is not None:
            if isinstance(value, Plug):
                self.connect(key, value)
                return
            self.setAttribute(key, value)
            return
        else:
            raise RuntimeError('Node {} has no attribute called: {}'.format(self.name(), key))

    def __getattr__(self, name):
        """
        Overrides __getattr__ function to try to access node attribute.

        :param str name: name of the attribute to access.
        :return: attribute value.
        :rtype: any
        """

        attr = self.attribute(name)
        if attr is not None:
            return attr

        return super(DGNode, self).__getattribute__(name)

    def __setattr__(self, key, value):
        """
        Overrides __setattr__ function to try to call node before calling the function.

        :param str key: name of the attribute to set.
        :param any value: value of the attribute.
        """

        if key.startswith('_'):
            super(DGNode, self).__setattr__(key, value)
            return
        if self.hasAttribute(key) is not None:
            if isinstance(value, Plug):
                self.connect(key, value)
                return
            self.setAttribute(key, value)
            return

        super(DGNode, self).__setattr__(key, value)

    def __eq__(self, other):
        """
        Overrides __eq__ function to check whether other object is equal to this one.

        :param DGNode other: object instance to check.
        :return: True if given object and current rule are equal; False otherwise.
        :rtype: bool
        """

        if not isinstance(other, DGNode) or (isinstance(other, DGNode) and other.handle() is None):
            return False

        return self._handle == other.handle()

    def __ne__(self, other):
        """
        Overrides __ne__ function to check whether other object is not equal to this one.

        :param DGNode other: object instance to check.
        :return: True if given object and current rule are not equal; False otherwise.
        :rtype: bool
        """

        if not isinstance(other, DGNode):
            return True

        return self._handle != other.handle()

    def __contains__(self, key):
        """
        Overrides __contains__ function to check whether an attribute with given name exists in current DG node.

        :param str key: attribute name.
        :return: True if attribute with given name exists; False otherwise.
        :rtype: bool
        """

        return self.hasAttribute(key)

    def __delitem__(self, key):
        """
        Overrides __delitem__ to delete attribute with given name from node.

        :param str key: name of the attribute to delete.
        """

        self.deleteAttribute(key)

    @staticmethod
    def sourceNode(plug):
        """
        Helper function that returns the source node of the given plug.

        :param Plug plug: plug to return source node of.
        :return: either the source node or None if the plug is not connected to any node.
        :rtype: DGNode or None
        """

        source = plug.source()
        return source.node() if source is not None else None

    @property
    def typeName(self):
        """
        Returns Maya API type name.

        :return: API type name.
        :rtype: str
        """

        return self._mfn.typeName

    @property
    def isLocked(self):
        """
        Returns whether the node is locked.

        :return: True if node is locked; False otherwise.
        :rtype: bool
        """

        return self.mfn().isLocked

    def create(
            self, name: str, node_type: str, namespace: str | None = None,
            mod: OpenMaya.MDGModifier | None = None) -> DGNode:
        """
        Function that builds the node within the Maya scene.

        :param str name: name of the new node.
        :param str node_type: Maya node type to create.
        :param str or None namespace: optional node namespace.
        :param DGModifier mod: optional Maya modifier to add to.
        :return: newly created meta node instance.
        :rtype: DGNode
        """

        if namespace:
            name = namespace + name.split(':')[-1]
        self.setObject(factory.create_dg_node(name, node_type=node_type, mod=mod))
        return self

    def serializeFromScene(
            self, skip_attributes=None, include_connections=True, extra_attributes_only=False, use_short_names=False,
            include_namespace=True):
        """
        Serializes current node into a dictionary compatible with JSON.

        :param iterable or None skip_attributes: list of attributes names to serialize.
        :param bool include_connections: whether to find and serialize all connections where the destination is this
            node.
        :param bool extra_attributes_only: whether to serialize only the extra attributes of this node.
        :param bool use_short_names: whether to use short names to serialize node data.
        :param bool include_namespace: whether to include the namespace as part of node.
        :return: JSON compatible dictionary.
        :rtype: dict
        """

        try:
            return nodes.serialize_node(
                self.object(), skip_attributes=skip_attributes, include_connections=include_connections,
                extra_attributes_only=extra_attributes_only, use_short_names=use_short_names,
                include_attributes=include_connections)
        except RuntimeError:
            return dict()

    def exists(self):
        """
        Returns whether the node is currently valid within the Maya scene.

        :return: True if the node is valid; False otherwise.
        :rtype: bool
        """

        node = self._handle
        return False if node is None else node.isValid() and node.isAlive()

    def handle(self):
        """
        Returns the OpenMaya.MObjectHandle instance attached to this instance.

        :return: Maya Object handle.
        :rtype: OpenMaya.MObjectHandle or None
        ..warning:: Client of this function is responsible for dealing with object existence.
        """

        return self._handle

    def mfn(self):
        """
        Returns the function set for this node.

        :return: DAG node or Dependency Node depending on the node type.
        :rtype: OpenMaya.MDagNode or OpenMaya.MDependencyNode
        """

        if self._mfn is None and self._handle is not None:
            self._mfn = self.MFN_TYPE(self.object())

        return self._mfn

    def typeId(self):
        """
        Returns the Maya typeId from the function set.

        :return: type ID or -1 if the node is not valid.
        :rtype: int
        """

        return self._mfn.typeId if self.exists() else -1

    def hasFn(self, fn_type):
        """
        Returns whether the underlying MObject has the given OpenMaya.MFn.kConstant type.

        :param int fn_type: type id.
        :return: True if the MObject has the given MFn type; False otherwise.
        :rtype: bool
        """

        return self.object().hasFn(fn_type)

    def apiType(self):
        """
        Returns the Maya API type integer

        :return: Maya API type.
        :rtype: int
        """

        return self._handle.object().apiType()

    def object(self):
        """
        Returns the object of the node.

        :return: Maya object linked to this node.
        :rtype: OpenMaya.MObject
        """

        return self._handle.object() if self.exists() else None

    def setObject(self, mobj):
        """
        Sets the MObject for this instance.

        :param OpenMaya.MObject or OpenMaya.MDagPath mobj: Maya Object representing an OpenMaya.MFnDependencyNode or
            an OpenMaya.MDagPath
        """

        object_path = mobj
        if isinstance(mobj, OpenMaya.MDagPath):
            mobj = mobj.node()
        if not mobj.hasFn(OpenMaya.MFn.kDependencyNode):
            raise ValueError('Invalid MObject type {}'.format(mobj.apiTypeStr))
        self._handle = OpenMaya.MObjectHandle(mobj)
        self._mfn = self.MFN_TYPE(object_path)

    def name(self, include_namespace=True):
        """
        Returns the name for the node.

        :param bool include_namespace: whether to include the namespace.
        :return: node name.
        :rtype: str
        """

        if not self.exists():
            return ''

        node_name = self.mfn().name()
        return node_name if include_namespace else OpenMaya.MNamespace.stripNamespaceFromName(node_name)

    def fullPathName(self, partial_name=False, include_namespace=True):
        """
        Returns the node scene name, this result is dependent on the arguments.

        :param bool partial_name: whether to return the partial name of the node.
        :param bool include_namespace: whether to include the namespace.
        :return: node full path name.
        :rtype: str
        :raises RuntimeError: if the node wrapped within this instance does not exist.
        """

        if not self.exists():
            raise RuntimeError('Current node does not exists!')

        return nodes.name(self.object(), partial_name, include_namespace)

    @lock_node_context
    def rename(self, new_name, maintain_namespace=False, mod=None, apply=True):
        """
        Renames this node.

        :param str new_name: new node name.
        :param bool maintain_namespace: whether to maintain current namespace.
        :param OpenMaya.MDGModifier mod: modifier to add rename operation to.
        :param bool apply: whether to rename node immediately using the modifier.
        :return: True if the rename operation was successful; False otherwise.
        :rtype: bool
        """

        if maintain_namespace:
            current_namespace = self.namespace()
            name = ':'.join([current_namespace, new_name])
        try:
            nodes.rename(self.object(), new_name, mod=mod, apply=apply)
        except RuntimeError:
            logger.error('Failed to rename node: {}-{}'.format(self.name(), new_name), exc_info=True)
            return False

        return True

    def namespace(self):
        """
        Returns the current namespace for the node.

        :return: node namespace.
        :rtype: str
        """

        name = OpenMaya.MNamespace.getNamespaceFromName(self.fullPathName()).split('|')[-1]
        root = OpenMaya.MNamespace.rootNamespace()
        if not name.startswith(root):
            name = root + name

        return name

    def parentNamespace(self):
        """
        Returns the parent namespace from the node.

        :return: parent namespace.
        :rtype: str
        """

        namespace = self.namespace()
        if namespace == ':':
            return namespace

        OpenMaya.MNamespace.setCurrentNamespace(namespace)
        parent = OpenMaya.MNamespace.parentNamespace()
        OpenMaya.MNamespace.setCurrentNamespace(namespace)

        return parent

    def renameNamespace(self, namespace: str):
        """
        Renames the current namespace with the given one.

        :param str namespace: new namespace.
        """

        current_namespace = self.namespace()
        if not current_namespace:
            return

        if current_namespace == namespace:
            return

        parent_namespace = self.parentNamespace()
        if current_namespace == ':':
            OpenMaya.MNamespace.addNamespace(namespace)
            self.rename(':'.join([namespace, self.name()]))
            return

        OpenMaya.MNamespace.setCurrentNamespace(parent_namespace)
        OpenMaya.MNamespace.renameNamespace(current_namespace, namespace)
        OpenMaya.MNamespace.setCurrentNamespace(namespace)

    def removeNamespace(self, mod=None, apply=True):
        """
        Deletes the namespace from this node.

        :param DGModifier mod: optional Maya modifier to apply; if None, one will be created.
        :param bool apply: whether to apply modifier immediately.
        :return: True if the remove namespace operation was successful; False otherwise.
        :rtype: bool
        """

        namespace = self.namespace()
        if namespace:
            return self.rename(self.name(include_namespace=False), maintain_namespace=False, mod=mod, apply=apply)

        return False

    def lock(self, state: bool, mod: OpenMaya.MDGModifier | None = None, apply: bool = True):
        """
        Sets the lock state for this node.

        :param bool state: lock state to change to.
        :param OpenMaya.MDGModifier mod: optional Maya modifier to apply; if None, one will be created.
        :param bool apply: whether to apply modifier immediately.
        :return: created Maya modifier.
        :rtype: DGModifier
        """

        if self.isLocked != state:
            modifier = mod or OpenMaya.MDGModifier()
            modifier.setNodeLockState(self.object(), state)
            if apply:
                modifier.doIt()

        return mod

    def isReferenced(self):
        """
        Returns whether the node is referenced.

        :return: True if node is referenced; False otherwise.
        :rtype: bool
        """

        return self.mfn().isFromReferencedFile

    def isDefaultNode(self):
        """
        Returns whether this node is a default Maya node.

        :return: True if this node is a default Maya node; False otherwise.
        :rtype: bool
        """

        return self.mfn().isDefaultNode

    def delete(self, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
        """
        Deletes the node from the scene.

        :param OpenMaya.MDGModifier mod: modifier to add the delete operation into.
        :param bool apply: whether to apply the modifier immediately.
        :return: True if the node deletion was successful; False otherwise.
        :raises RuntimeError: if deletion operation fails.
        :rtype: bool
        """

        if self.exists():
            if self.isLocked:
                self.lock(False)
            try:
                if mod:
                    mod.commandToExecute('delete {}'.format(self.fullPathName()))
                    if apply:
                        mod.doIt()
                else:
                    cmds.delete(self.fullPathName())
                self._mfn = None
                return True
            except RuntimeError:
                logger.error('Failed node deletion, {}'.format(self.mfn().name()), exc_info=True)
                raise

        return False

    def hasAttribute(self, attribute_name):
        """
        Returns whether the attribute given name exist on this node.

        :param str attribute_name: name of the attribute to check.
        :return: True if the given attribute exists on the node; False otherwise.
        :rtype: bool
        """

        # arrays don't get picked up by hasAttribute unfortunately
        if '[' in attribute_name:
            sel = OpenMaya.MSelectionList()
            try:
                sel.add(attribute_name)
                return True
            except RuntimeError:
                return False
        return self.mfn().hasAttribute(attribute_name)

    def attribute(self, name: str) -> Plug | None:
        """
        Returns the attribute with the given name this node.

        :param str name: name of the attribute to find.
        :return: found plug instance or None.
        :rtype: Plug or None
        """

        fn = self._mfn
        if any(i in name for i in ('[', '.')):
            sel = OpenMaya.MSelectionList()
            try:
                sel.add('.'.join((self.fullPathName(), name)))
                mplug = sel.getPlug(0)
            except RuntimeError:
                # raised when the plug does not exist.
                return None
            return Plug(self, mplug)
        elif fn.hasAttribute(name):
            return Plug(self, fn.findPlug(name, False))

    def setAttribute(self, name, value, mod=None, apply=True):
        """
        Sets the value of the attribute if it exists.

        :param str name: name of the attribute to set value of.
        :param any value: value of the attribute to set.
        :param OpenMay.MDGModifier mod: modifier to add set attribute value operation into.
        :param bool apply: whether to apply the modifier immediately.
        :return: True if the attribute set value operation was successful; False otherwise.
        :rtype: bool
        """

        attr = self.attribute(name)
        if attr is not None:
            attr.set(value, mod=mod, apply=apply)
            return True

        return False

    @lock_node_context
    def addAttribute(self, name, type=attributetypes.kMFnNumericDouble, mod=None, **kwargs):
        """
        Adds an attribute into this node.

        :param str name: name of the attribute to add.
        :param int or None type: type of the attribute to add.
        :param OpenMaya.MDGModifier mod: optional modifier to add.
        :return: newly created plug.
        :rtype: Plug
        """

        if self.hasAttribute(name):
            return self.attribute(name)

        children = kwargs.get('children')
        if children:
            plug = self.addCompoundAttribute(name, attr_map=children, mod=mod, **kwargs)
        else:
            mobj = self.object()
            attr = nodes.add_attribute(mobj, name, name, type=type, mod=mod, **kwargs)
            plug = Plug(self, OpenMaya.MPlug(mobj, attr.object()))

        return plug

    @lock_node_context
    def addCompoundAttribute(self, name, attr_map, isArray=False, mod=None, **kwargs):
        """
        Creates a compound attribute with the given children attributes.

        :param str name: name of the compound attribute to add.
        :param list(dict()) attr_map: [{"name":str, "type": attributetypes.kType, "isArray": bool}]
        :param bool isArray: whether to add the compound attribute as an array.
        :param OpenMaya.MDGModifer mod: modifier to add.
        :param dict wargs: extra keyword arguments.
        :return: newly created compound plug.
        :rtype: Plug
        """

        mobj = self.object()
        compound = nodes.add_compound_attribute(mobj, name, name, attr_map, isArray=isArray, mod=mod, **kwargs)
        return Plug(self, OpenMaya.MPlug(mobj, compound.object()))

    @lock_node_context
    def addProxyAttribute(self, source_plug, name):
        """
        Creates a proxy attribute where the created plug on this node will be connected to the source plug while still
        being modifiable.

        :param Plug source_plug: plug to copy to the current node which whill become the primary attribute.
        :param str name: name for the proxy attribute, if the attribute already exists then no proxy will happen.
        :return: proxy plug instance.
        :rtype: Plug or None
        """

        if self.hasAttribute(name):
            return None

        plug_data = plugs.serialize_plug(source_plug.plug())
        plug_data['long_name'] = name
        plug_data['short_name'] = name
        plug_data['type'] = plug_data['type']
        current_obj = self.object()
        return Plug(self, OpenMaya.MPlug(
            current_obj, nodes.add_proxy_attribute(current_obj, source_plug.plug(), **plug_data).object()))

    @lock_node_context
    def createAttributesFromDict(self, data: dict, mod: OpenMaya.MDGModifier | None = None) -> list[Plug]:
        """
        Creates an attribute on the node based on the attribute data in the following form:
        {
            "channelBox": true,
            "default": 3,
            "isDynamic": true,
            "keyable": false,
            "locked": false,
            "max": 9999,
            "min": 1,
            "name": "jointCount",
            "softMax": null,
            "softMin": null,
            "type": 2,
            "value": 3
        }

        :param dict data: serialized attribute data.
        :param OpenMaya.MDGModifier or None mod: optional modifier to add.
        :return: list of created plugs.
        :rtype: list[Plug].
        """

        created_plugs = []
        mfn = self.mfn()
        mobj = self.object()
        for name, attr_data in iter(data.items()):
            children = attr_data.get('children')
            if children:
                compound = nodes.add_compound_attribute(mobj, name, name, children, mod=mod, **attr_data)
                created_plugs.append(Plug(self, OpenMaya.MPlug(mobj, compound.object())))
            else:
                if self.hasAttribute(name):
                    created_plugs.append(Plug(self, mfn.findPlug(name, False)))
                    continue
                attr = nodes.add_attribute(mobj, name, name, attr_data.pop('type', None), mod=mod, **attr_data)
                created_plugs.append(Plug(self, OpenMaya.MPlug(mobj, attr.object())))

        return created_plugs

    def renameAttribute(self, name, new_name):
        """
        Renames an attribute on the current node.

        :param str name: name of the attribute to rename.
        :param str new_name: new attribute name.
        :return: True if the rename attribute operation was successful; False otherwise.
        :rtype: bool
        :raises AttributeError: if the attribute to rename does not exist.
        """

        try:
            plug = self.attribute(name)
        except RuntimeError:
            raise AttributeError('No attribute named: {}'.format(name))

        return plug.rename(new_name)

    def deleteAttribute(self, attribute_name, mod=None):
        """
        Removes the attribute with given name from this node.

        :param str attribute_name: attribute name to delete.
        :param DagModifier mod: optional Maya modifier to add to.
        :return: True if the attribute was deleted successfully; False otherwise.
        :rtype: bool
        """

        attr = self.attribute(attribute_name)
        if attr is not None:
            attr.delete(mod=mod)
            return True

        return False

    def connect(self, attribute_name, destination_plug, mod=None, apply=True):
        """
        Connects the attribute on this node with given name as the source to the destination plug.

        :param str attribute_name: name of the attribute that will be used as the source.
        :param Plug destination_plug: destination plug.
        :param OpenMaya.MDagModifier mod: optional modifier to add.
        :param bool apply: whether to apply the operation immediately.
        :return: True if the connect operation was successful; False otherwise.
        :rtype: bool
        """

        source = self.attribute(attribute_name)
        if source is not None:
            return source.connect(destination_plug, mod=mod, apply=apply)

        return False

    def iterateConnections(self, source: bool = True, destination: bool = True) -> Iterator[tuple[Plug, Plug], ...]:
        """
        Generator function that iterates over node connections.

        :param bool source: whether to iterate source connections.
        :param bool destination: whether to iterate destination connections.
        :return: generator with the first element is the plug instance and the second the connected plug.
        :rtype: Iterator[tuple[Plug, Plug], ...]
        """

        for source_plug, destination_plug in nodes.iterate_connections(self.object(), source, destination):
            yield Plug(self, source_plug), Plug(node_by_object(destination_plug.node()), destination_plug)

    def sources(self) -> Iterator[tuple[Plug, Plug], ...]:
        """
        Generator function that iterates over source plugs.

        :return: generator with the first element is the plug instance and the second the connected plug.
        :rtype: Iterator[tuple[Plug, Plug], ...]
        """

        for source, destination in nodes.iterate_connections(self.object(), source=True, destination=False):
            yield Plug(self, source), Plug(self, destination)

    def destinations(self) -> Iterator[tuple[Plug, Plug], ...]:
        """
        Generator function that iterates over destination plugs.

        :return: generator with the first element is the plug instance and the second the connected plug.
        :rtype: Iterator[tuple[Plug, Plug], ...]
        """

        for source, destination in nodes.iterate_connections(self.object(), source=False, destination=True):
            yield Plug(self, source), Plug(self, destination)

    def setLockStateOnAttributes(self, attributes, state=True):
        """
        Locks/unlocks the given attributes.

        :param list(str) attributes: list of attributes to lock/unlock.
        :param bool state: whether to lock or unlock the attributes.
        :return: True if the lock/unlock operation was successful; False otherwise.
        :rtype: bool
        """

        return nodes.set_lock_state_on_attributes(self.object(), attributes, state=state)

    def showHideAttributes(self, attributes, state=False):
        """
        Shows or hides given attributes in the channel box.

        :param list(str) attributes: list of attributes names to lock/unlock
        :param bool state: whether to hide or show the attributes.
        :return: True if the attributes show/hide operation was successful; False otherwise.
        :rtype: bool
        """

        fn = self._mfn
        for attr in attributes:
            plug = fn.findPlug(attr, False)
            plug.isChannelBox = state
            plug.isKeyable = state

        return True

    def findAttributes(self, *names):
        """
        Searches the node for each attribute name given and returns the plug instance.

        :param iterable(str) names: list of attribute names.
        :return: each element matching plug or None if not found.
        :rtype: list(Plug or None)
        """

        results = [None] * len(names)
        for attr in nodes.iterate_attributes(self.object()):
            plug_found = Plug(self, attr)
            short_name = plug_found.name().partition('.')[-1]
            try:
                results[names.index(short_name)] = plug_found
            except ValueError:
                continue

        return results

    def iterateAttributes(self):
        """
        Generator function that iterates over all the attributes on this node.

        :return: generator of iterated attributes.
        :rtype: generator(Plug)
        """

        for attr in nodes.iterate_attributes(self.object()):
            yield Plug(self, attr)

    def iterateExtraAttributes(
            self, skip: list[str] | None = None, filtered_types: list[str] | None = None,
            include_attributes: list[str] | None = None) -> Iterator[Plug]:
        """
        Generator function that iterates over all the extra attributes on this node.

        :param list[str] or None skip: list of attributes to skip.
        :param list[str] or None filtered_types: optional list of types we want to filter.
        :param list[str] or None include_attributes: list of attributes to force iteration over.
        :return: generator of iterated extra attributes.
        :rtype: Iterator[Plug]
        """

        for attr in nodes.iterate_extra_attributes(
                self.object(), skip=skip, filtered_types=filtered_types, include_attributes=include_attributes):
            yield Plug(self, attr)

    def sourceNodeByName(
            self, plug_name: str) -> DGNode | DagNode | NurbsCurve | Mesh | Camera | IkHandle | Joint | ContainerAsset \
                                    | AnimCurve | SkinCluster | AnimLayer | ObjectSet | BlendShape | DisplayLayer | None:
        """
        Returns the source node connected to the given plug of this node instance.

        :param str plug_name: name of the plug to return source node of.
        :return: source node connected to the plug.
        :rtype: DGNode or DagNode or None
        """

        plug = self.attribute(plug_name)
        return self.sourceNode(plug) if plug is not None else None

    def serializeFromScene(
            self, skip_attributes=(), include_connections=True, include_attributes=(), extra_attributes_only=False,
            use_short_names=False, include_namespace=True):
        """
        Serializes current node instance and returns a JSON compatible dictionary with the node data.

        :param set(str) or None skip_attributes: list of attribute names to skip serialization of.
        :param bool include_connections: whether to find and serialize all connections where the destination is this
            node instance.
        :param set(str) or None include_attributes: list of attribute names to serialize.
        :param bool extra_attributes_only: whether only extra attributes will be serialized.
        :param bool use_short_names: whether to use short name of nodes.
        :param bool include_namespace: whether to include namespace as part of the node name.
        :return: serialized node data.
        :rtype: dict
        """

        try:
            return nodes.serialize_node(
                self.object(), skip_attributes=skip_attributes, include_connections=include_connections,
                include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
                use_short_names=use_short_names, include_namespace=include_namespace)
        except RuntimeError:
            return dict()


class DagNode(DGNode):
    """
    Wrapper class for OpenMaya.MDagNode that exposes functions for parenting, iterating the DAG, etc.
    """

    MFN_TYPE = OpenMaya.MFnDagNode

    def create(
            self, name: str, node_type: str, parent: OpenMaya.MObject | None = None,
            mod: OpenMaya.MDGModifier | None = None) -> DagNode:
        """
        Function that builds the node within the Maya scene.

        :param str name: name of the new node.
        :param str node_type: Maya node type to create.
        :param OpenMaya.MObject parent: optional parent object.
        :param DGModifier mod: optional Maya modifier to add to.
        :return: newly created meta node instance.
        :rtype: DGNode
        """

        # import here to avoid cyclic imports
        from tp.maya.api import factory

        if isinstance(parent, DagNode):
            parent = parent.object()
        new_node = factory.create_dag_node(name, node_type=node_type, parent=parent, mod=mod)
        self.setObject(new_node)

        return self

    def serializeFromScene(
            self, skip_attributes=(), include_connections=True, include_attributes=(), extra_attributes_only=False,
            use_short_names=False, include_namespace=True):
        """
        Serializes current node instance and returns a JSON compatible dictionary with the node data.

        :param set(str) or None skip_attributes: list of attribute names to skip serialization of.
        :param bool include_connections: whether to find and serialize all connections where the destination is this
            node instance.
        :param set(str) or None include_attributes: list of attribute names to serialize.
        :param bool extra_attributes_only: whether only extra attributes will be serialized.
        :param bool use_short_names: whether to use short name of nodes.
        :param bool include_namespace: whether to include namespace as part of the node name.
        :return: serialized node data.
        :rtype: dict
        """

        rotation_order = self.rotationOrder()
        world_matrix = self.worldMatrix()
        translation, rotation, scale = nodes.decompose_transform_matrix(
            world_matrix, utils.int_to_mtransform_rotation_order(rotation_order))

        try:
            data = nodes.serialize_node(
                self.object(), skip_attributes=skip_attributes, include_connections=include_connections,
                include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
                use_short_names=use_short_names, include_namespace=include_namespace)
            data.update({
                'translate': tuple(translation), 'rotate': tuple(rotation), 'scale': tuple(scale),
                'rotateOrder': rotation_order, 'matrix': list(self.matrix()), 'worldMatrix': list(world_matrix)
            })
            return data
        except RuntimeError:
            return dict()

    def dagPath(self):
        """
        Returns the MDagPath of this node.

        :return: DAG path for this node.
        :rtype: OpenMaya.MDagPath
        """

        return self.mfn().getPath()

    def depth(self):
        """
        Returns the depth level this node sits within the hierarchy.

        :return: hierarchy depth level.
        :rtype: int
        """

        return self.fullPathName().count('|') - 1

    def root(self):
        """
        Returns the root dag node parent from this node instance.

        :return: root node.
        :rtype: DagNode
        """

        return node_by_object(nodes.root(self.object()))

    def boundingBox(self):
        """
        Returns the bounding box information for this node.

        :return: bounding box information.
        :rtype: OpenMaya.MBoundingBox
        """

        return self._mfn.boundingBox

    def iterateShapes(self) -> Iterator[DagNode]:
        """
        Generator function that iterates over all shape nodes under this dag node instance.

        :return: iterated shape nodes.
        :rtype: Iterator[DagNode]
        """

        path = self.dagPath()
        for i in range(path.numberOfShapesDirectlyBelow()):
            dag_path = OpenMaya.MDagPath(path)
            dag_path.extendToShape(i)
            yield node_by_object(dag_path.node())

    def shapes(self) -> list[DagNode]:
        """
        Returns a list of all shape nodes under this dag node instance.

        :return: list of shape nodes.
        :rtype: list[DagNode]
        """

        return list(self.iterateShapes())

    def setShapeColor(self, color, shape_index=None):
        """
        Sets the color of this node transform or the node shape.

        :param tuple(float) color: RGB color to set.
        :param int or None shape_index: shape index to set. If None, then the transform color will be set. -1 will
            set the color of all shapes.
        """

        if shape_index is not None:
            if shape_index == -1:
                for shape in iter(nodes.shapes(self.dagPath())):
                    nodes.set_node_color(shape.node(), color)
            else:
                shape = nodes.shape_at_index(self.dagPath(), shape_index)
                nodes.set_node_color(shape.node(), color)
            return

        if len(color) == 3:
            nodes.set_node_color(self.object(), color)

    def deleteShapeNodes(self):
        """
        Deletes all shape nodes on this node.
        """

        for shape in self.shapes():
            shape.delete()

    def parent(self):
        """
        Returns the parent node as an MObject

        :return: parent Maya object.
        :rtype: DagNode or None
        """

        mobj = self.object()
        if mobj is None:
            return None
        parent = nodes.parent(mobj)
        if parent:
            return node_by_object(parent)

        return parent

    @lock_node_context
    def setParent(
            self, parent: DagNode | None, maintain_offset: bool = True, mod: OpenMaya.MDagModifier | None = None,
            apply: bool = True) -> OpenMaya.MDagModifier:
        """
        Sets the parent of this node.

        :param DagNode or None parent: new parent node.
        :param bool maintain_offset: whether to maintain it is current position in world space.
        :param OpenMaya.MDagModifier mod: optional modifier to add.
        :param bool apply: whether to apply the modifier immediately.
        :return: Maya modifier used to set parent.
        :rtype: OpenMaya.MDagModifier
        """

        parent_lock = False
        set_locked = False
        new_parent = None
        if parent is not None:
            new_parent = parent.object()
            parent_lock = parent.isLocked
            if parent_lock:
                set_locked = True
                parent.lock(False)
        try:
            result = nodes.set_parent(self.object(), new_parent, maintain_offset=maintain_offset, mod=mod, apply=apply)
        finally:
            if set_locked:
                parent.lock(parent_lock)

        return result

    def child(self, index, node_types=()):
        """
        Returns the immediate child object based on given index.

        :param int index: index of the child to find.
        :param tuple(OpenMaya.MFn.kType) node_types: node types to get child of.
        :return: found child.
        :rtype: DagNode
        """

        path = self.dagPath()
        current_index = 0
        for i in range(path.childCount()):
            child = path.child(i)
            if (not node_types or child.apiType() in node_types) and current_index == index:
                return node_by_object(child)
            current_index += 1

    def addChild(self, node):
        """
        Re-parent given node to this node.

        :param DagNode node: child node to re-parent to this node.
        """

        node.setParent(self)

    def iterateParents(self):
        """
        Ggenerator function that iterates over each parent until root has been reached.

        :return: iteated parent nodes.
        :rtype: generator(DagNode)
        """

        for parent in nodes.iterate_parents(self.object()):
            yield node_by_object(parent)

    def iterateChildren(self, recursive=True, node_types=()):
        """
        Generator function that iterates over each child of this node.

        :param bool recursive: whether to recursively loop all children of children.
        :param tuple(OpenMaya.MFn.KType) node_types: list of node types.
        :return: generator(DagNode)
        """

        path = OpenMaya.MDagPath.getAPathTo(self.object()).getPath()
        for i in range(path.childCount()):
            child = path.child(i)
            if not node_types or child.apiType() in node_types:
                yield node_by_object(child)
            if recursive:
                for child in node_by_object(child).iterateChildren(recursive, node_types):
                    yield child

    def children(self, node_types: tuple[Any, ...] = ()) -> list[DagNode]:
        """
        Returns all immediate children objects.

        :param tuple[Any] node_types: node types to get children of.
        :return: found children.
        :rtype: list[DagNode]
        """

        path = self.dagPath()
        children = list()
        for i in range(path.childCount()):
            child = path.child(i)
            if not node_types or child.apiType() in node_types:
                children.append(node_by_object(child))

        return children

    def iterateSiblings(self, node_types: tuple[OpenMaya.MFn] = (types.kTransform,)) -> Iterator[DagNode]:
        """
        Generator function that iterates over all sibling nodes of this node.

        :param tuple[OpenMaya.MFn] node_types: list of node types to filter.
        :return: iterated sibling nodes.
        :rtype: Iterator[DagNode]
        """

        parent = self.parent()
        if parent is None:
            return
        for child in parent.iterateChildren(recursive=False, node_types=node_types):
            if child != self:
                yield child

    def translation(self, space=None, scene_units=False):
        """
        Returns the translation for this node.

        :param OpenMaya.MFn.type space: coordinate system to use.
        :param bool scene_units: whether the translation vector needs to be converted to scene units.
        :return: object translation.
        :rtype: OpenMaya.MVector
        """

        space = space or types.kWorldSpace
        return nodes.translation(self.object(), space, scene_units=scene_units)

    def setTranslation(self, translation, space=None, scene_units=False):
        """
        Sets the translation component of this node.

        :param OpenMaya.MVector or tuple(float) translation: vector that represents a position in space.
        :param int space: space to work.
        :param bool scene_units: whether the translation vector needs to be converted to scene units.
        """

        space = space or types.kTransformSpace
        nodes.set_translation(self.object(), OpenMaya.MVector(translation), space=space, scene_units=scene_units)

    def rotation(self, space=None, as_quaternion=True):
        """
        Returns the rotation for this node.

        :param OpenMaya.MFn.type space: coordinate system to use.
        :param bool as_quaternion: whether to return rotation as a quaternion.
        :return: Maya object rotation.
        :rtype: OpenMaya.MEulerRotation or OpenMaya.MQuaternion
        """

        return nodes.rotation(self.dagPath(), space or types.kTransformSpace, as_quaternion=as_quaternion)

    def setRotation(self, rotation, space=None):
        """
        Sets the translation component of this node.

        :param tuple or list or OpenMaya.MEulerAngle or OpenMaya.MQuaternion rotation: rotation to set.
        :param int space: space to work.
        """

        space = space or types.kWorldSpace
        transform = OpenMaya.MFnTransform(self._mfn.getPath())
        if isinstance(rotation, types.Quaternion):
            transform.setRotation(rotation, space)
            return
        elif isinstance(rotation, (tuple, list)):
            if space == types.kWorldSpace and len(rotation) > 3:
                rotation = OpenMaya.MQuaternion(rotation)
            else:
                rotation = OpenMaya.MEulerRotation(
                    [OpenMaya.MAngle(i, OpenMaya.MAngle.kDegrees).asRadians() for i in rotation])
        if space != types.kTransformSpace and isinstance(rotation, types.EulerRotation):
            space = types.kTransformSpace

        transform.setRotation(rotation, space)

    def scale(self, space=None):
        """
        Returns the scale for this node.

        :param OpenMaya.MFn.type space: coordinate system to use.
        :return: object scale.
        :rtype: OpenMaya.MVector
        """

        space = space or types.kTransformSpace
        transform = self.transformationMatrix(space)
        return types.Vector(transform.scale(space))

    def setScale(self, scale):
        """
        Sets the scale for this node.

        :param list or tuple or OpenMaya.MVector scale: scale to set.
        """

        transform = OpenMaya.MFnTransform(self._mfn.getPath())
        transform.setScale(scale)

    def rotationOrder(self):
        """
        Returns the rotation order for this node.

        :return: rotation order index.
        :rtype: int
        """

        return self.rotateOrder.value()

    def setRotationOrder(self, rotate_order=consts.kRotateOrder_XYZ, preserve=True):
        """
        Sets rotation order for this node.

        :param int rotate_order: rotate order index (defaults to XYZ).
        :param bool preserve: If True, X, Y, Z rotations will be modified so that the resulting rotation under the new
            order is the same as it was under the old. If False, then X, Y, Z rotations are unchanged.
        """

        rotate_order = utils.int_to_mtransform_rotation_order(rotate_order)
        transform = OpenMaya.MFnTransform(self._mfn.getPath())
        transform.setRotationOrder(rotate_order, preserve)

    def worldMatrix(self, context: OpenMaya.MDGContext = types.DGContext.kNormal) -> OpenMaya.MMatrix:
        """
        Returns the world matrix of this node.

        :param OpenMaya.MDGContext context: optional context to use.
        :return: world matrix.
        :rtype: OpenMaya.MMatrix
        """

        world_matrix = self._mfn.findPlug('worldMatrix', False).elementByLogicalIndex(0)
        return OpenMaya.MFnMatrixData(world_matrix.asMObject(context)).matrix()

    def setWorldMatrix(self, matrix: OpenMaya.MMatrix):
        """
        Sets the world matrix of this node.

        :param OpenMaya.MMatrix matrix: world matrix to set.
        """

        nodes.set_matrix(self.object(), matrix, space=OpenMaya.MSpace.kWorld)

    def matrix(self, context=types.DGContext.kNormal):
        """
        Returns the local marix of this node.

        :param OpenMaya.MDGContext context: optional context to use.
        :return: local matrix.
        :rtype: OpenMaya.MMatrix
        """

        local_matrix = self._mfn.findPlug('matrix', False)
        return OpenMaya.MFnMatrixData(local_matrix.asMObject(context)).matrix()

    def setMatrix(self, matrix):
        """
        Sets the local matrix of this node.

        :param OpenMaya.MMatrix matrix: local matrix to set.
        """

        nodes.set_matrix(self.object(), matrix, space=OpenMaya.MSpace.kTransform)

    def transformationMatrix(
            self, rotate_order: int | None = None, space:
            OpenMaya.MSpace | None = types.kWorldSpace) -> types.TransformationMatrix:
        """
        Returns the current node matrix in the form of MTransformationMatrix.

        :param int rotate_order: rotation order to use.
        :param OpenMaya.MSpace space: coordinate space to use.
        :return: Maya transformation matrix instance.
        :rtype: types.TransformationMatrix
        """

        transform = types.TransformationMatrix(self.worldMatrix() if space == types.kWorldSpace else self.matrix())
        rotate_order = self.rotationOrder() if rotate_order is None else rotate_order
        rotate_order = utils.int_to_mtransform_rotation_order(rotate_order)
        transform.reorderRotation(rotate_order)

        return transform

    def parentInverseMatrix(self, ctx=OpenMaya.MDGContext.kNormal):
        """
        Returns the current node parent inverse matrix.

        :param OpenMaya.MDGContext ctx: context to use.
        :return: parent inverse matrix.
        :rtype: OpenMaya.MMatrix
        """

        return nodes.parent_inverse_matrix(self.object(), ctx=ctx)

    def offsetMatrix(self, target_node, space=types.kWorldSpace, ctx=OpenMaya.MDGContext.kNormal):
        """
        Returns the offset matrix between this ndoe and the given target node.

        :param DagNode target_node: target transform node.
        :param OpenMaya.MSpace space: coordinate space.
        :param OpenMaya.MDGContext ctx: context to use.
        :return: parent inverse matrix.
        :rtype: OpenMaya.MMatrix
        """

        return nodes.offset_matrix(self.object(), target_node.object(), space=space, ctx=ctx)

    def decompose(self, ctx=OpenMaya.MDGContext.kNormal):
        """
        Returns the world matrix decomposed for this node.

        :param OpenMaya.MDGContext ctx: context to use.
        :return: tuple with the world translation, rotation and scale of this node.
        :rtype: tuple(OpenMaya.MVector, OpenMaya.MVector, OpenMaya.MVector)
        """

        return nodes.decompose_transform_matrix(
            self.worldMatrix(ctx), utils.int_to_mtransform_rotation_order(self.rotationOrder()),
            space=OpenMaya.MSpace.kWorld)

    def resetTransform(self, translate=True, rotate=True, scale=True):
        """
        Resets the local translate, rotate and scale attributes to 0.0.

        :param bool translate: whether to reset translate attributes.
        :param bool rotate: whether to reset rotate attributes.
        :param bool scale: whether to reset scale attributes.
        """

        translate_attr = self.attribute('translate')
        rotate_attr = self.attribute('rotate')
        scale_attr = self.attribute('scale')
        if translate and not translate_attr.isDestination and translate_attr.numConnectedChildren() == 0:
            self.setTranslation((0.0, 0.0, 0.0))
        if rotate and not rotate_attr.isDestination and rotate_attr.numConnectedChildren() == 0:
            self.setRotation(types.Quaternion(), space=types.kTransformSpace)
        if scale and not scale_attr.isDestination and scale_attr.numConnectedChildren() == 0:
            self.setScale((1.0, 1.0, 1.0))

    def isHidden(self):
        """
        Returns whether this node is visible.

        :return: True if this node is visible; False otherwise.
        :rtype: bool
        """

        return self._mfn.findPlug('visibility', False).asFloat() < 1.0

    def setVisible(
            self, flag: bool, mod: OpenMaya.MDGModifier | OpenMaya.MDagModifier | None = None,
            apply: bool = True) -> bool:
        """
        Sets whether this node is visible.

        :param bool flag: True to make this node visible; False to hide it.
        :param OpenMaya.MDGModifier or OpenMaya.MDagModifier or None mod: optional modifier to use to set the
            visibility this node.
        :param bool apply: whether to apply the operation immediately.
        :return: True if node was showed successfully; False otherwise.
        :return: True if the set visibility operation was successful; False otherwise.
        :rtype: bool
        """

        visibility_pulg = self.attribute('visibility')
        if visibility_pulg.isLocked or visibility_pulg.isConnected and not visibility_pulg.isProxy():
            return False

        visibility_value = 1 if flag else 0
        visibility_pulg.set(visibility_value, mod, apply=apply)

        return True

    def show(self, mod=None, apply=True):
        """
        Sets the visibility for this node to 1.0.

        :param OpenMaya.MDagModifier or None mod: optional modifier to use to show this node.
        :param bool apply: whether to apply the operation immediately.
        :return: True if node was showed successfully; False otherwise.
        :rtype: bool
        """

        return self.setVisible(True, mod=mod, apply=apply)

    def hide(self, mod=None, apply=True):
        """
        Sets the visibility for this node to 0.0.

        :param OpenMaya.MDagModifier or None mod: optional modifier to use to hide this node.
        :param bool apply: whether to apply the operation immediately.
        :return: True if node was hidden successfully; False otherwise.
        :rtype: bool
        """

        return self.setVisible(False, mod=mod, apply=apply)


class Plug:
    """
    Wrapper class for OpenMaya.MPlug that provides an easier solution to access connections and values.
    """

    def __init__(self, node, mplug):
        """
        Plug constructor.

        :param DGNode or DagNode node: node instance for this plug.
        :param OpenMaya.MPlug mplug: Maya plug instance.
        """

        self._node = node  # type: DGNode or DagNode
        self._mplug = mplug  # type: OpenMaya.MPlug

    def __repr__(self):
        """
        Overrides __repr__ function to return the display string for this plug instance.

        :return: display string.
        :rtype: str
        """

        return '<{}> {}'.format(self.__class__.__name__, self._mplug.name()) if self.exists() else ''

    def __str__(self):
        """
        Overrides __str__ function to return the full path name for this instance.

        :return: full path name.
        :rtype: str
        """

        return '' if not self.exists() else self._mplug.name()

    def __eq__(self, other):
        """
        Overrides __eq__ function to compare the internal plug with the given one.

        :param Plug other: plug instance.
        :return: True if both plugs are the same; False otherwise.
        :rtype: bool
        """

        return self._mplug == other.plug()

    def __ne__(self, other):
        """
        Overrides __ne__ function to compare the internal plug with the given one.

        :param Plug other: plug instance.
        :return: True if plugs are different; False otherwise.
        :rtype: bool
        """

        return self._mplug != other.plug()

    def __abs__(self):
        """
        Overrides __abs__ function to return the absolute value of a plug.

        :return: absolute value of the plug.
        :rtype: any
        """

        return abs(self.value())

    def __int__(self):
        """
        Overrides __int__ function to return the value of the plug as an integer.

        :return: plug value as an integer.
        :rtype: int
        """

        return self._mplug.asInt()

    def __float__(self):
        """
        Overrides __float__ function to return the value of the plug as a float.

        :return: plug value as a float.
        :rtype: float
        """

        return self._mplug.asFloat()

    def __neg__(self):
        """
        Overrides __neg__ function to return the negative value of the plug.

        :return: plug negative value.
        :rtype: any
        """

        return -self.value()

    def __bool__(self):
        """
        Overrides __bool__ function to return True if the plug exists.

        :return: True if the plug exists; False otherwise.
        :rtype: bool
        """

        return self.exists()

    def __getitem__(self, item):
        """
        Overrides __getitem__ function to return the child attribute if this plug is a compound one. Index starts from 0.

        :param int item: element or child index to get.
        :return: child plug found.
        :rtype: Plug or None
        :raises TypeError: if attribute does not support indexing.
        """

        if self._mplug.isArray:
            return self.element(item)
        if self._mplug.isCompound:
            return self.child(item)

        raise TypeError('{} does not support indexing'.format(self._mplug.name()))

    def __getattr__(self, item):
        """
        Overrides __getattr__ function to try to access OpenMaya.MPlug attribute before accessing this instance
        attribute.

        :param str item: name of the attribute to access.
        :return: attribute value.
        :rtype: any
        """

        if hasattr(self._mplug, item):
            return getattr(self._mplug, item)

        return super(Plug, self).__getattribute__(item)

    def __setattr__(self, key, value):
        """
        Overrides __setattr__ function to try to call OpenMaya.MPlug function before calling the function.
        If a Plug instance is passed, given plug will be connected into this plug instance.

        :param str key: name of the attribute to set.
        :param any value: value of the attribute.
        """

        if key.startswith('_'):
            super(Plug, self).__setattr__(key, value)
            return
        elif hasattr(self._mplug, key):
            return setattr(self._mplug, key, value)
        elif isinstance(value, Plug):
            value.connect(self)

        super(Plug, self).__setattr__(key, value)

    def __iter__(self):
        """
        Overrides __iter__ function that allow the iteration of all the compound plugs.

        :return: generator of iterated compound plugs.
        :rtype: collections.Iterator[:class:`Plug`]
        """

        mplug = self._mplug
        if mplug.isArray:
            indices = mplug.getExistingArrayAttributeIndices()
            # case in maya 2023 where num of indices is zero but 2022 is [0]
            # for consistency and because 0 is usually a valid logical index to bind to(connection,setattr)
            for index in indices or [0]:
                yield Plug(self._node, mplug.elementByLogicalIndex(index))
        elif mplug.isCompound:
            for index in range(mplug.numChildren()):
                yield Plug(self._node, mplug.child(index))

    def __len__(self):
        """
        Overrides __len__ function to return the total number of attributes in compound or array attributes or 0
        if the attribute is not iterable.

        :return: total number of array or compound attributes.
        :rtype: int
        """

        mplug = self._mplug
        if mplug.isArray:
            return self._mplug.evaluateNumElements()
        elif self._mplug.isCompound:
            return self._mplug.numChildren()

        return 0

    def __rshift__(self, other):
        """
        Overrides __rshift__ function to allow to connect this plug instance into a downstream plug.

        :param Plug other: downstream plug to connect.
        """

        self.connect(other)

    def __lshift__(self, other):
        """
        Overrides __lshift__ function to connect this plug instance into an upstream plug.

        :param Plug other: upstream plug to connect.
        """

        other.connect(self)

    def __floordiv__(self, other):
        """
        Overrides __floordiv__ function to allow to disconnect this plug from the given one.

        :param Plug other: plug to disconnect from.
        """

        self.disconnect(other)

    @staticmethod
    def _convert_value_type(value):
        """
        Internal static method that converts given value to a valid value type.

        :param any value: value to convert.
        :return: converted value.
        :rtype: any
        """

        is_mobj = type(value) == OpenMaya.MObject
        is_valid_mobj = False if not is_mobj else nodes.is_valid_mobject(value)
        if is_mobj and is_valid_mobj:
            return node_by_object(value)
        elif is_mobj and not is_valid_mobj:
            return None
        elif isinstance(value, (list, tuple)):
            value = [Plug._convert_value_type(val) for val in value]

        return value

    def apiType(self):
        """
        Returns the Maya API type integer

        :return: Maya API type.
        :rtype: int
        """

        return plugs.plug_type(self._mplug)

    def mfn(self):
        """
        Returns the Maya function set for this plug.

        :return: Maya function set.
        :rtype: OpenMaya.MFnBase
        """

        attr = self._mplug.attribute()
        return plugs.plug_fn(attr)(attr)

    def mfnType(self):
        """
        Returns the Maya function set attribute type.

        :return: attribute type index.
        :rtype: int
        """

        return plugs.plug_fn(self._mplug.attribute())

    def exists(self):
        """
        Returns whether this plug is valid.

        :return: True if plag is valid; False otherwise.
        :rtype: bool
        """

        return self._mplug and not self._mplug.isNull

    def partialName(
            self, include_node_name=False, include_non_mandatory_indices=True, include_instanced_indices=True,
            use_alias=False, use_full_attribute_path=True, use_long_names=True):
        """
        Returns the partial name for the plug.

        :param bool include_node_name:
        :param bool include_non_mandatory_indices:
        :param bool include_instanced_indices:
        :param bool use_alias:
        :param bool use_full_attribute_path:
        :param bool use_long_names:
        :return: plug partial name.
        :rtype: str
        """

        return self._mplug.partialName(
            include_node_name, include_non_mandatory_indices, include_instanced_indices, use_alias,
            use_full_attribute_path, use_long_names)

    def plug(self):
        """
        Returns the Maya MPlug object.

        :return: Maya MPlug object.
        :rtype: OpenMaya.MPlug
        """

        return self._mplug

    def node(self):
        """
        Returns the attached node API instance for this plug.

        :return: DGNode or DagNode for this plug.
        :rtype: DGNode or DagNode
        """

        return self._node

    def default(self):
        """
        Returns the default value of this plug instance.

        :return: default plug value.
        :rtype: str or int or float.
        """

        if not self.exists():
            return

        return plugs.plug_default(self._mplug)

    def setDefault(self, value):
        """
        Sets the default for this plug default instance.

        :param str or int or float value: default value to set.
        :return: True if set default operation was successful; False otherwise.
        :rtype: bool
        """

        return plugs.set_plug_default(self._mplug, value) if self.exists() else False

    def isProxy(self):
        """
        Returns whether this plug is a proxy one.

        :return: True if plug is a proxy one; False otherwise.
        :rtype: bool
        """

        return OpenMaya.MFnAttribute(self._mplug.attribute()).isProxyAttribute

    def setAsProxy(self, source_plug):
        """
        Sets the current attribute as a proxy attribute and connects to the given source plug.

        :param Plug source_plug: source plug to connect this plug.
        """

        if self._mplug.isCompound:
            plugs.set_compound_as_proxy(self.plug(), source_plug.plug())
            return

        OpenMaya.MFnAttribute(self._mplug.attribute()).isProxyAttribute = True
        source_plug.connect(self)

    def isAnimated(self):
        """
        Returns whether current plug is animated.

        :return: True if current plug is animated; False otherwise.
        :rtype: bool
        :raises exception
        """

        if not self.exists():
            raise exceptions.ObjectDoesNotExistError('Current Plug does not exist')

        return OpenMayaAnim.MAnimUtil.isAnimated(self._mplug)

    def findAnimation(self):
        """
        Returns the anim curve/s that are animating this plug instance.

        :return: list of animation curves.
        :rtype:
        """

        if not self.exists():
            raise exceptions.ObjectDoesNotExistError('Current Plug does not exist')

        return [node_by_object(i) for i in OpenMayaAnim.MAnimUtil.findAnimation(self._mplug)]

    def array(self):
        """
        Returns the plug array for this array element.

        :return: plug array.
        :rtype: Plug
        """

        assert self._mplug.isElement, 'Plug: {} is not an array element'.format(self.name())
        return Plug(self._node, self._mplug.array())

    def parent(self):
        """
        Returns the parent plug if this plug is a compound.

        :return: parent plug.
        :rtype: Plug
        """

        assert self._mplug.isChild, 'Plug {} is not a child attribute'.format(self.name())
        return Plug(self._node, self._mplug.parent())

    def children(self):
        """
        Returns all the child plugs of this compound plug.

        :return: children plugs.
        :rtype: list(Plug)
        """

        return [Plug(self._node, self._mplug.child(i)) for i in range(self._mplug.numChildren())]

    @lock_node_plug_context
    def rename(self, name, mod=None):
        """
        Renames the current plug.

        :param str name: new plug name.
        :param DGModifier or None mod: optional modifier to add to.
        :return: True if the rename operation was valid; False otherwise.
        :rtype: bool
        """

        with plugs.set_locked_context(self._mplug):
            mod = mod or OpenMaya.MDGModifier()
            mod.renameAttribute(self.node().object(), self.attribute(), name, name)
            mod.doIt()

        return True

    def show(self):
        """
        Shows the attribute in the channel box and makes the attribute keyable.
        """

        self._mplug.isChannelBox = True

    def hide(self):
        """
        Hides the attribute from the channel box and makes the attribute non-keyable.
        """

        self._mplug.isChannelBox = False

    def lock(self, flag):
        """
        Sets the current plug lock state.

        :param bool flag: True to lock current plug; False to unlock it.
        """

        self._mplug.isLocked = flag

    def lockAndHide(self):
        """
        Locks and hides the attribute.
        """

        self._mplug.isLocked = True
        self._mplug.isChannelBox = False
        self._mplug.isKeyable = False

    def setKeyable(self, flag):
        """
        Sets the keyable state of the attribute.

        :param bool flag: True to make the attribute keyable; False otherwise.
        """

        self._mplug.isKeyable = flag

    def child(self, index) -> Plug:
        """
        Returns the child plug by index.

        :param int index: child index.
        :return: child plug at given index.
        :rtype: Plug
        """

        assert self._mplug.isCompound, 'Plug: {} is not a compound'.format(self._mplug.name())
        if index < 0:
            new_index = max(0, len(self) + index)
            return Plug(self._node, self._mplug.child(new_index))

        return Plug(self._node, self._mplug.child(index))

    def element(self, index: int) -> Plug:
        """
        Returns the logical element plug if this plug is an array.

        :param int index: element index.
        :return: element plug.
        :rtype: Plug
        """

        assert self._mplug.isArray, 'Plug: {} is not an array'.format(self._mplug.name())
        if index < 0:
            new_index = max(0, len(self) + index)
            return Plug(self._node, self._mplug.elementByLogicalIndex(new_index))

        return Plug(self._node, self._mplug.elementByLogicalIndex(index))

    def elementByPhysicalIndex(self, index):
        """
        Returns the element plug by the physical index if this plug is an array.

        :param int index: physical index.
        :return: element plug.
        :rtype: Plug
        """

        assert self._mplug.isArray, 'Plug {} is not an array'.format(self.name())
        return Plug(self._node, self._mplug.elementByPhysicalIndex(index))

    def nextAvailableElementPlug(self):
        """
        Returns the next available output plug for this array.

        :return:  next available output plug.
        :rtype: Plug
        ..info: availability is based on connections of elements plug and their children.
        """

        assert self._mplug.isArray, 'Plug {} is not an array'.format(self.name())
        return Plug(self._node, plugs.next_available_element_plug(self._mplug))

    def nextAvailableDestElementPlug(self):
        """
        Returns the next available input plug for this array.

        :return:  next available input plug.
        :rtype: Plug
        ..info: availability is based on connections of elements plug and their children.
        """

        assert self._mplug.isArray, 'Plug {} is not an array'.format(self.name())
        return Plug(self._node, plugs.next_available_dest_element_plug(self._mplug))

    def value(self, ctx=types.DGContext.kNormal):
        """
        Returns the value of the plug.

        :param DGContext ctx: context to use.
        :return: plug value.
        :rtype: any
        """

        value = plugs.plug_value(self._mplug, ctx=ctx)
        value = Plug._convert_value_type(value)

        return value

    @lock_node_plug_context
    def set(self, value, mod=None, apply=True):
        """
        Sets the value of this plug instance.

        :param any value: OpenMaya value type.
        :param DGModifier mod: optional Maya modifier to add to.
        :param bool apply: whether to apply modifier immediately.
        :return: created Maya modifier.
        :rtype: DGModifier
        :raises exceptions.ReferenceObjectError: if the node is locked or is a reference.
        """

        if self.node().isReferenced() and self.isLocked:
            raise exceptions.ReferenceObjectError('Plug {} is a reference or is locked'.format(self.name()))

        return plugs.set_plug_value(self._mplug, value, mod=mod, apply=apply)

    @lock_node_plug_context
    def setFromDict(self, **data: dict):
        """
        Set plug data from given dictionary.

        :param dict data: serialized plug data.
        """

        plugs.set_plug_info_from_dict(self._mplug, **data)

    @lock_node_plug_context
    def connect(self, plug, children=None, force=True, mod=None, apply=True):
        """
        Connects given plug to this plug instance.

        :param Plug or OpenMaya.MPlug plug: plug to connect into this plug.
        :param children:
        :param bool force: whether to force the connection.
        :param DGModifier mod: optional Maya modifier to add to.
        :param bool apply: whether to apply modifier immediately.
        :return: created Maya modifier.
        :rtype: DGModifier
        """

        if self.isCompound and children:
            children = children or list()
            self_len = len(self)
            child_len = len(children)
            if children == 0:
                plugs.connect_plugs(self._mplug, plug.plug(), force=force, mod=mod)
            if child_len > self_len:
                children = children[:self_len]
            elif children < self_len:
                children += [False] * (self_len - child_len)
            return plugs.connect_vector_plugs(self._mplug, plug.plug(), children, force=force, mod=mod, apply=apply)

        return plugs.connect_plugs(self._mplug, plug.plug(), mod=mod, force=force, apply=apply)

    @lock_node_plug_context
    def disconnect(self, plug, mod=None, apply=True):
        """
        Disconnects given destination plug.

        :param Plug or OpenMaya.MPlug plug: destination plug.
        :param DGModifier or None mod: optional Maya modifier to add to.
        :param bool apply: whether to apply modifier immediately.
        :return: created Maya modifier.
        :rtype: DGModifier
        """

        modifier = mod or OpenMaya.MDGModifier()
        modifier.disconnect(self._mplug, plug.plug())
        if mod is None and apply:
            modifier.doIt()

        return modifier

    @lock_node_plug_context
    def disconnectAll(self, source=True, destination=True, mod=None):
        """
        Disconnects all plugs from the current plug.

        :param bool source: whether to disconnect source connections.
        :param bool destination: whether to disconnect destination connections.
        :param DGModifier or None mod: optional Maya modifier to add to.
        :return: tuple with the result and modifier used to apply the operation.
        """

        return plugs.disconnect_plug(self._mplug, source=source, destination=destination, modifier=mod)

    def source(self):
        """
        Returns the source plug from this plug or None if it is not connected to any node.

        :return: connected source node plug.
        :rtype: Plug or None
        """

        source = self._mplug.source()
        return Plug(node_by_object(source.node()), source) if not source.isNull else None

    def sourceNode(self) -> DGNode | DagNode | None:
        """
        Returns the source node from this plug or None if it is not connected to any node.

        :return: source node.
        :rtype: DGNode or None
        """

        source = self.source()
        return source.node() if source is not None else None

    def destinations(self) -> Iterator[Plug]:
        """
        Generator function that iterates over all destination plugs connected to this plug instance.

        :return: iterated destination plugs.
        :rtype: Iterator[Plug]
        """

        for destination_plug in self._mplug.destinations():
            yield Plug(node_by_object(destination_plug.node()), destination_plug)

    def destinationNodes(self) -> Iterator[DGNode]:
        """
        Generator function that iterates over all destination nodes.

        :return: iterated destination nodes.
        :rtype: Iterator[DGNode]
        """

        for destination_plug in self.destinations():
            yield destination_plug.node()

    def serializeFromScene(self) -> dict:
        """
        Serializes current plug instance as a dictionary.

        :return: serialized plug data.
        :rtype: dict
        """

        return plugs.serialize_plug(self._mplug) if self.exists() else {}

    @lock_node_plug_context
    def delete(self, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> OpenMaya.MDGModifier:
        """
        Deletes the plug from the attached node. If batching is needed then use the modifier parameter to pass a
        DGModifier, once all operations are done, call modifier.doIt() function.

        :param OpenMaya.DGModifier mod: modifier to dad to. If None, one will be created.
        :param bool apply: if True, then plugs value will be set immediately with the modifier, if False, then is
            user is responsible to call modifier.doIt() function.
        :return: Maya DGModifier used for the operation.
        :rtype: OpenMaya.MDGModifier
        :raises exceptions.ReferenceObjectError: in the case where the plug is not dynamic and is referenced.
        """

        if not self.isDynamic and self.node().isReferenced():
            raise exceptions.ReferenceObjectError('Plug {} is reference and locked'.format(self.name()))

        # if self.isLocked:
        #     self.lock(False)

        modifier = mod or OpenMaya.MDGModifier()

        if self._mplug.isElement:
            logical_index = self._mplug.logicalIndex()
            modifier = plugs.remove_element_plug(self._mplug.array(), logical_index, mod=modifier, apply=apply)
        else:
            modifier.removeAttribute(self.node().object(), self.attribute())

        if mod is None or apply:
            modifier.doIt()

        return modifier

    @lock_node_plug_context
    def deleteElements(self, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> OpenMaya.MDGModifier:
        """
        Deletes all array elements from this plug.

        :param OpenMaya.DGModifier mod: modifier to dad to. If None, one will be created.
        :param bool apply: if True, then plugs value will be set immediately with the modifier, if False, then is
            user is responsible to call modifier.doIt() function.
        :return: Maya DGModifier used for the operation.
        :rtype: OpenMaya.MDGModifier
        :raises exceptions.ReferenceObjectError: in the case where the plug is not dynamic and is referenced.
        :raises TypeError: if plug is not an array.
        """

        if not self.isDynamic and self.node().isReferenced():
            raise exceptions.ReferenceObjectError('Plug {} is reference and locked'.format(self.name()))
        if not self._mplug.isArray:
            raise TypeError('Invalid plug type to delete, must be of type Array')

        modifier = mod or OpenMaya.MDGModifier()
        for element in self:
            logical_index = element.logicalIndex()
            modifier = plugs.remove_element_plug(self._mplug, logical_index, mod=modifier, apply=apply)

        if mod is None or apply:
            modifier.doIt()

        return modifier


class NurbsCurve(DagNode):
    """
    Wrapper class for MFnNurbsCurve function providing a set of common methods.
    """

    MFN_TYPE = OpenMaya.MFnNurbsCurve


class Mesh(DagNode):
    pass


class Camera(DagNode):
    pass


class IkHandle(DagNode):
    SCENE_UP = 0
    OBJECT_UP = 1
    OBJECT_UP_START_END = 2
    OBJECT_ROTATION_UP = 3
    OBJECT_ROTATION_UP_START_END = 4
    VECTOR = 5
    VECTOR_START_END = 6
    RELATIVE = 7

    FORWARD_POSITIVE_X = 0
    FORWARD_POSITIVE_Y = 1
    FORWARD_POSITIVE_Z = 2
    FORWARD_NEGATIVE_X = 3
    FORWARD_NEGATIVE_Y = 4
    FORWARD_NEGATIVE_Z = 5

    UP_POSITIVE_Y = 0
    UP_NEGATIVE_Y = 1
    UP_CLOSET_Y = 2
    UP_POSITIVE_Z = 3
    UP_NEGATIVE_Z = 4
    UP_CLOSET_Z = 5
    UP_POSITIVE_X = 6
    UP_NEGATIVE_X = 7
    UP_CLOSET_X = 8

    def vector_to_forward_axis_enum(self, vec: Iterable[float, float, float]) -> int:
        """
        Returns forward axis index from given vector.
        The forward axis direction is determined by finding the axis with the largets magnitude in the vector.

        If the sum of the values in the vector is negative, the method will return the corresponding negative up axis
        value.Available up axis enum values are:
            - IkHandle.FORWARD_NEGATIVE_X: The negative X axis
            - IkHandle.FORWARD_NEGATIVE_Y: The negative Y axis
            - IkHandle.FORWARD_NEGATIVE_Z: The negative Z axis

        If the sum of the values in the vector is not negative, the method will return the axis index corresponding to
        the forward axis direction.

        The possible axis indexes are:
            - XAXIS: The X axis
            - YAXIS: The Y axis
            - ZAXIS: The Z axis

        :param Iterable[float, float, float] vec: vector.
        :return: forward axis index.
        :rtype: int
        """

        axis_index = mathlib.X_AXIS_INDEX
        is_negative = sum(vec) < 0.0

        for axis_index, value in enumerate(vec):
            if int(value) != 0:
                break

        if is_negative:
            return {
                mathlib.X_AXIS_INDEX: IkHandle.FORWARD_NEGATIVE_X,
                mathlib.Y_AXIS_INDEX: IkHandle.FORWARD_NEGATIVE_Y,
                mathlib.Z_AXIS_INDEX: IkHandle.FORWARD_NEGATIVE_Z,
            }[axis_index]

        return axis_index

    def vector_to_up_axis_enum(self, vec: Iterable[float, float, float]) -> int:
        """
        Returns up axis index from given vector.
        The up axis direction is determined by finding the axis with the largest magnitude in the vector.

        If the sum of the values in the vector is negative, the method will return the corresponding negative up axis
        value.Available up axis enum values are:
            - IkHandle.UP_NEGATIVE_X: The negative X axis
            - IkHandle.UP_POSITIVE_Y: The negative Y axis
            - IkHandle.UP_NEGATIVE_Z: The negative Z axis

        If the sum of the values in the vector is not negative, the method will return the axis index corresponding to
        the up axis direction.

        The possible axis indexes are:
            - XAXIS: The X axis
            - YAXIS: The Y axis
            - ZAXIS: The Z axis

        :param Iterable[float, float, float] vec: vector.
        :return: up axis index.
        :rtype: int
        """

        axis_index = mathlib.X_AXIS_INDEX
        is_negative = sum(vec) < 0.0

        for axis_index, value in enumerate(vec):
            if int(value) != 0:
                break

        axis_mapping = {
            mathlib.X_AXIS_INDEX: IkHandle.UP_POSITIVE_X,
            mathlib.Y_AXIS_INDEX: IkHandle.UP_POSITIVE_Y,
            mathlib.Z_AXIS_INDEX: IkHandle.UP_POSITIVE_Z,
        }
        if is_negative:
            axis_mapping = {
                mathlib.X_AXIS_INDEX: IkHandle.UP_NEGATIVE_X,
                mathlib.Y_AXIS_INDEX: IkHandle.UP_NEGATIVE_Y,
                mathlib.Z_AXIS_INDEX: IkHandle.UP_NEGATIVE_Z,
            }

        return axis_mapping[axis_index]


class Joint(DagNode):

    @override(check_signature=False)
    def create(self, **kwargs: dict) -> Joint:

        name = kwargs.get('name', 'joint')
        joint = nodes.factory.create_dag_node(name, 'joint')
        self.setObject(joint)
        world_matrix = kwargs.get('worldMatrix', None)
        if world_matrix is not None:
            transform_matrix = types.TransformationMatrix(types.Matrix(world_matrix))
            transform_matrix.setScale((1, 1, 1), types.kWorldSpace)
            self.setWorldMatrix(transform_matrix.asMatrix())
        else:
            self.setTranslation(types.Vector(kwargs.get('translate', (0.0, 0.0, 0.0))), space=types.kWorldSpace)
            self.setRotation(types.Quaternion(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0))))

        self.setRotationOrder(kwargs.get('rotateOrder', consts.kRotateOrder_XYZ))
        self.setParent(kwargs.get('parent', None), maintain_offset=True)
        self.segmentScaleCompensate.set(False)

        return self

    @override(check_signature=False)
    def setParent(
            self, parent: Joint | DagNode | None, maintain_offset: bool = True,
            mod: OpenMaya.MDagModifier | None = None, apply: bool = True) -> OpenMaya.MDagModifier:

        rotation = self.rotation(space=types.kWorldSpace)
        result = super().setParent(parent, maintain_offset=True)
        if parent is None:
            return result

        parent_quat = parent.rotation(types.kWorldSpace, as_quaternion=True)
        new_rotation = rotation * parent_quat.inverse()
        self.jointOrient.set(new_rotation.asEulerRotation())
        self.setRotation((0.0, 0.0, 0.0), types.kTransformSpace)
        if parent.apiType() == types.kJoint:
            parent.attribute('scale').connect(self.inverseScale)

    def aim_to_child(
            self, aim_vector: OpenMaya.MVector | list[float, float, float],
            up_vector: OpenMaya.MVector | list[float, float, float], use_joint_orient: bool = True):
        """
        Aims this joint to point to its first child in the hierarchy. If joint has no chain, rotation will be reset.

        :param OpenMaya.MVector or list[float, float, float] aim_vector: vector to use as the aim vector.
        :param OpenMaya.MVector or list[float, float, float] up_vector: vector to use as the up vector.
        :param bool use_joint_orient: whether to move rotation values to the joint orient after aiming.
        """

        child = self.child(0)
        if child is None:
            self.setRotation(types.Quaternion())
            return

        nodes.aim_nodes(target_node=child.object(), driven=[self.object()], aim_vector=aim_vector, up_vector=up_vector)

        if use_joint_orient:
            self.jointOrient.set(self.rotation())
            self.setRotation(types.Quaternion())


class ContainerAsset(DGNode):
    """
    Wrapper class for MFnContainerNode nodes providing a set of common methods.
    """

    MFN_TYPE = OpenMaya.MFnContainerNode

    def create(self, name):
        """
        Creates the MFnSet and sets this instance MObject to the new node.

        :param str name: name for the asset container node.
        """

        # import here to avoid cyclic imports
        from tp.maya.api import factory

        container = factory.create_dg_node(name, 'container')
        self.setObject(container)

        return self

    def serializeFromScene(self):
        """
        Serializes current asset container instance and returns a JSON compatible dictionary with the container data.

        :return: serialized asset container data.
        :rtype: dict
        """

        members = self.members()
        if not members:
            return dict()

        published_attributes = self.publishedAttributes()
        published_nodes = self.publishedNodes()

        return {
            'graph': nodes.serialize_nodes(members),
            'attributes': published_attributes,
            'nodes': published_nodes
        }

    def delete(self, remove_container=True):
        """
        Deletes the node from the scene.

        :param bool remove_container: If True, then the container will be deleted, otherwise only members will be
            removed.
        """

        container_name = self.fullPathName()
        self.lock(False)
        cmds.container(container_name, edit=True, removeContainer=remove_container)

    # ==================================================================================================================
    # PROPERTIES
    # ==================================================================================================================

    @property
    def blackBox(self):
        """
        Returns the current black box attribute value.

        :return: True if the contents of the container are public; False otherwise.
        :rtype: bool
        """

        return self.attribute('blackBox').asBool()

    @blackBox.setter
    def blackBox(self, flag):
        """
        Sets current black box attribute value.

        :param bool flag: True if the contents of the container are not public; False otherwise.
        """

        mfn = self.mfn()
        if not mfn:
            return
        self.attribute('blackBox').set(flag)

    # ==================================================================================================================
    # BASE
    # ==================================================================================================================

    def isCurrent(self):
        """
        Returns whether this current container is the current active container.

        :return: True if this container is the active one; False otherwise.
        :rtype: bool
        """

        return self._mfn.isCurrent()

    def makeCurrent(self, value):
        """
        Sets this container to be the currently active.

        :param bool value: whether to make container currently active.
        """

        self._mfn.makeCurrent(value)

    def members(self):
        """
        Returns current members of this container instance.

        :return: list of member nodes.
        :rtype: list(DagNode)
        """

        return map(node_by_object, self.mfn().getMembers())

    def addNode(self, node_to_add):
        """
        Adds the given node to the container without publishing it.

        :param DGNode node: node to add into this container.
        :return: True if the add node operation was successful; False otherwise.
        :rtype: bool
        :raises RuntimeError: if something wrong happens when adding the node into the container.
        """

        mobj = node_to_add.object()
        if mobj != self._handle.object():
            try:
                cmds.container(
                    self.fullPathName(), edit=True, addNode=node_to_add.fullPathName(), includeHierarchyBelow=True)
            except RuntimeError:
                raise
            return True

        return False

    def addNodes(self, nodes_to_add):
        """
        Adds the given nodes to the container without published them.

        :param list(DGNode) nodes_to_add: nodes to add into this container.
        """

        container_path = self.fullPathName(False, True)
        for node_to_add in iter(nodes_to_add):
            if node_to_add == self:
                continue
            cmds.container(container_path, edit=True, addNode=node_to_add.fullPathName(), includeHierarchyBelow=True)

    def publishedAttributes(self) -> list[Plug]:
        """
        Returns all published attributes in this contdainer.

        :return: list of published attributes.
        :rtype: list(Plug)
        """

        results = cmds.container(self.fullPathName(), query=True, bindAttr=True)
        if not results:
            return []

        # cmds returns a flat list of attribute name, published name, so we chunk as pai
        return [plug_by_name(attr) for attr, _ in helpers.chunk(results, 2)]

    def publishAttribute(self, attribute):
        """
        Publishes the given attribute to the container.

        :param attribute: attribute to publish.
        """

        self.publishAttributes([attribute])

    def publishAttributes(self, attributes):
        """
        Publishes the given attributes to the container.

        :param list(Plug) attributes: list of attributes to publish.
        """

        container_name = self.fullPathName()
        current_publishes = self.publishedAttributes()
        for plug in attributes:
            if plug in current_publishes or plug.isChild or plug.isElement:
                continue
            name = plug.name()
            short_name = plug.partialName()
            try:
                cmds.container(str(container_name), edit=True, publishAndBind=[str(name), str(short_name)])
            except RuntimeError:
                pass

    def unPublishAttribute(self, attribute_name):
        """
        Unpublishes attribute with given name from this container.

        :param str attribute_name: name of the attribute to unpublish.
        :return: True if the attribute was unpublished successfully; False otherwise.
        :rtype: bool
        """

        container_name = self.fullPathName()
        try:
            cmds.container(container_name, edit=True, unbindAndUnpublish='.'.join([container_name, attribute_name]))
        except RuntimeError:
            return False

        return True

    def unPublishAttributes(self):
        """
        Unpublish all attributes published in this container.
        """

        for published_attribute in self.publishedAttributes():
            self.unpublish_attribute(published_attribute.partialName(use_long_names=False))

    def publishedNodes(self):
        """
        Returns list of published node in this contdainer.

        :return: list of published nodes.
        :rtype: list(DGNode)
        """

        return [node_by_object(node[1] for node in self.mfn().getPublishedNodes(
            OpenMaya.MFnContainerNode.kGeneric) if not node[0].isNull())]

    def publishNode(self, node_to_publish):
        """
        Publishes the given node to the container.

        :param DGNode node: node to publish.
        """

        self.publishNodes([node_to_publish])

    def publishNodes(self, nodes_to_publish):
        """
        Publishes the given nodes to the container.

        :param list(DGNode) nodes_to_publish: list of nodes to publish.
        """

        container_name = self.fullPathName()

        for node_to_publish in nodes_to_publish:
            node_name = node_to_publish.fullPathName()
            short_name = node_name.split('|')[-1].split(':')[-1]
            try:
                cmds.containerPublish(container_name, publishNode=[short_name, node_to_publish.mfn().typeName])
            except RuntimeError:
                pass
            try:
                cmds.containerPublish(container_name, bindNode=[short_name, node_name])
            except RuntimeError:
                pass

    def unPublishNode(self, node):
        """
        Unpublishes given node from the container.

        :param DGNode node: node to unpublish.
        """

        message_plug = node.attribute('message')
        container_name = self.fullPathName()
        for dest_plug in message_plug.destinations():
            node = dest_plug.node().object()
            if node.hasFn(OpenMaya.MFn.kContainer):
                parent_name = dest_plug.parent().partialName(use_alias=True)
                cmds.containerPublish(container_name, unbindNode=parent_name)
                cmds.containerPublish(container_name, unpublishNode=parent_name)
                break


class AnimCurve(DGNode):
    MFN_TYPE = OpenMayaAnim.MFnAnimCurve

    @property
    def numKeys(self) -> int:
        """
        Returns the total amount of keys for this animation curve.

        :return: total keys amount.
        :rtype: int
        """

        return self.mfn().numKeys

    def input(self, index: int) -> OpenMaya.MTime | float:
        """
        Returns the input (MTime for T* curves or double for U* curves) of the key at the specified index.

        :return: index to get input of.
        :rtype: OpenMaya.MTime or float
        """

        return self.mfn().input(index)


class SkinCluster(DGNode):
    MFN_TYPE = OpenMayaAnim.MFnSkinCluster


class ObjectSet(DGNode):
    """
    Wrapper class for Maya object sets
    """

    MFN_TYPE = OpenMaya.MFnSet

    @override(check_signature=False)
    def create(self, name: str, mod: OpenMaya.MDGModifier | None = None,
               members: list[DGNode] | None = None) -> ObjectSet:
        """
        Creates the MFnSet and sets this instance MObject to the new node.

        :param str name: name for the object set node.
        :param OpenMaya.MDGModifier or None mod: modifier to add to, if None it will create one.
        :param list[DGNode] or None members: list of nodes to add as members of this object set.
        :return: instance of the new object set.
        :rtype: ObjectSet
        """

        obj = factory.create_dg_node(name, 'objectSet', mod=mod)
        self.setObject(obj)
        if members is not None:
            self.addMembers(members)

        return self

    def isMember(self, node: DGNode) -> bool:
        """
        Returns whether given node is a member of this set.

        :param DGNode node: node to check for membership.
        :return: True if given node is a member of this set; False otherwise.
        :rtype: bool
        """

        return self._mfn.isMember(self.object()) if node.exists() else False

    def addMember(self, node: DGNode) -> bool:
        """
        Adds given node to the set.

        :param DGNode node: node to add as a new member to this set.
        :return: True if the node was added successfully; False otherwise.
        :rtype: bool
        """

        if not node.exists():
            return False
        elif node.hasFn(types.kDagNode):
            if self in node.instObjGroups[0].destinationNodes():
                return False
            node.instObjGroups[0].connect(self.dagSetMembers.nextAvailableDestElementPlug())
        else:
            if self in node.attribute('message').destinationNodes():
                return False
            node.message.connect(self.dnSetMembers.nextAvailableDestElementPlug())

        return True

    def addMembers(self, new_members: list[DGNode]):
        """
        Adds a list of new objects into the set.

        :param list[DGNode] new_members: list of nodes to add as new members to this set.
        """

        for member in new_members:
            self.addMember(member)

    def members(self, flatten: bool = False) -> list[DGNode]:
        """
        Returns the members of this set as a list.

        :param bool flatten: whether all sets that exist inside this set will be expanded into a list of their contents.
        :return: a list of all members in the set.
        :rtype: list[DGNode]
        """

        return list(map(node_by_name, self._mfn.getMembers(flatten).getSelectionStrings()))

    def removeMember(self, member: DGNode):
        """
        Removes given item from the set.

        :param DGNode member: item to remove.
        """

        if member.exists():
            self.removeMembers([member])

    def removeMembers(self, members: list[DGNode]):
        """
        Removes items of the list from the set.

        :param list[DGNode] members: member nodes to remove.
        """

        member_list = OpenMaya.MSelectionList()
        for member in members:
            if not member.exists():
                continue
            member_list.add(member.fullPathName())

        self._mfn.removeMembers(member_list)

    def clear(self):
        """
        Removes all members from this set.
        """

        self._mfn.clear()


class BlendShape(DGNode):
    pass


class DisplayLayer(DGNode):
    pass


class AnimLayer(DGNode):

    def iterateAnimCurves(self):
        """
        Generator function that iterates over all animation curves linked to this animation layer.

        :return: list of animation curves.
        :rtype: list(AnimCurve)
        """

        for anim_curve_name in cmds.animLayer(self.fullPathName(), query=True, animCurves=True) or []:
            anim_curve = AnimCurve(node=nodes.mobject(anim_curve_name))
            yield anim_curve

    def animCurves(self):
        """
        Returns all animation curves linked to this animation layer.

        :return: list of animation curves.
        :rtype: list(AnimCurve)
        """

        return list(self.iterateAnimCurves())
