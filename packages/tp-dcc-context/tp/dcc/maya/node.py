from __future__ import annotations

from typing import Generator, Iterator, Any

from six import integer_types
from overrides import override

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.dcc.abstract import node
from tp.dcc.maya.collections import userproperties
from tp.maya.om import dagpath, attributes, plugs, plugmutators
from tp.maya.cmds import namespace


class FnNode(node.AFnNode):
    """
    Overload of node.AbstractNode that implements context behaviour for Maya scene nodes.
    """

    __slots__ = ()
    __handles__: dict[int, OpenMaya.MObjectHandle] = {}
    __sep_char__ = '|'
    __alt_sep_char__ = '|'

    @classmethod
    @override
    def node_by_handle(cls, handle: int) -> OpenMaya.MObject | None:
        """
        Returns a node with the given handle.

        :param int handle: handle to get node for.
        :return: Maya node from given handle.
        :rtype: OpenMaya.MObject or None
        """

        handle = cls.__handles__.get(handle, OpenMaya.MObjectHandle())
        return handle.object() if handle.isAlive() else None

    @override(check_signature=False)
    def accepts_object(self, obj: Any) -> bool:
        return isinstance(obj, (str, OpenMaya.MObject, OpenMaya.MDagPath, OpenMaya.MObjectHandle))

    @override(check_signature=False)
    def object(self) -> OpenMaya.MObject | None:
        handle = super().object()
        return self.node_by_handle(handle) if isinstance(handle, integer_types) else handle

    @override(check_signature=False)
    def set_object(self, obj: str | OpenMaya.MObject | OpenMaya.MDagPath):
        depend_node = dagpath.mobject(obj)
        if not depend_node.isNull():
            handle = OpenMaya.MObjectHandle(depend_node)
            self.__handles__[handle.hashCode()] = handle
            super().set_object(handle.hashCode())
        else:
            raise TypeError(f'set_object() expects a valid object ({obj} given)!')

    @override
    def handle(self) -> int:
        return OpenMaya.MObjectHandle(self.object()).hashCode()

    @override
    def name(self) -> str:
        return namespace.strip_namespace(OpenMaya.MFnDependencyNode(self.object()).name())

    @override
    def set_name(self, name: str):
        OpenMaya.MFnDependencyNode(self.object()).setName(name)

    @override
    def namespace(self) -> str:
        return OpenMaya.MFnDependencyNode(self.object()).namespace

    @override
    def set_namespace(self, new_namespace: str):
        OpenMaya.MFnDependencyNode(self.object()).namespace = new_namespace

    @override(check_signature=False)
    def parent(self) -> OpenMaya.MObject | None:
        obj: OpenMaya.MObject | None = self.object()
        if not obj.hasFn(OpenMaya.MFn.kDagNode):
            return None

        fn_dag_node = OpenMaya.MFnDagNode(obj)
        parent = fn_dag_node.parent(0)

        return parent if not parent.hasFn(OpenMaya.MFn.kWorld) else None

    @override(check_signature=False)
    def set_parent(self, parent: OpenMaya.MObject | None):
        obj: OpenMaya.MObject | None = self.object()
        if not obj.hasFn(OpenMaya.MFn.kDagNode):
            return

        dag_modifier = OpenMaya.MDagModifier()
        dag_modifier.reparentNode(obj, parent)
        dag_modifier.doIt()

    @override(check_signature=False)
    def iterate_children(self, api_type: int = OpenMaya.MFn.kTransform) -> Generator[OpenMaya.MObject, None, None]:
        obj: OpenMaya.MObject | None = self.object()
        if not obj.hasFn(OpenMaya.MFn.kDagNode):
            return

        fn_dag_node = OpenMaya.MFnDagNode(obj)
        child_count = fn_dag_node.childCount()
        for i in range(child_count):
            child = fn_dag_node.child(i)
            if child.hasFn(api_type):
                yield fn_dag_node.child(i)
            else:
                continue

    def iterate_shapes(self) -> Generator[OpenMaya.MObject, None, None]:
        """
        Returns an iterator that yields all shapes from this node.

        :return: iterated shapes from this node.
        :rtype: Generator[OpenMaya.MObject, None, None]
        """

        fn_dag_node = OpenMaya.MFnDagNode()
        for obj in self.iterate_children(api_type=OpenMaya.MFn.kShape):
            fn_dag_node.setObject(obj)
            if fn_dag_node.isIntermediateObject:
                continue
            yield obj

    def shapes(self) -> list[OpenMaya.MObject]:
        """
        Returns list of shapes from this node.

        :return: shapes from this node.
        :rtype: list[OpenMaya.MObject]
        """

        return list(self.iterate_shapes())

    @property
    def is_intermediate_object(self) -> bool:
        """
        Returns whether this is an intermediate object.

        :return: True if this is an intermediate object.
        :rtype: bool
        """

        if not self.is_valid():
            return False

        obj: OpenMaya.MObject | None = self.object()
        if obj.hasFn(OpenMaya.MFn.kDagNode):
            return OpenMaya.MFnDagNode(obj).isIntermediateObject

        return False

    def iterate_intermediate_objects(self) -> Generator[OpenMaya.MObject, None ,None]:
        """
        Returns an iterator that yields all intermediate objects from this node.

        :return: iterated all intermediate objects from this node.
        :rtype: Generator[OpenMaya.MObject, None, None]
        """

        fn_dag_node = OpenMaya.MFnDagNode()
        for obj in self.iterate_children(api_type=OpenMaya.MFn.kShape):
            fn_dag_node.setObject(obj)
            if not fn_dag_node.isIntermediateObject:
                continue
            yield obj

    def intermediate_objects(self) -> list[OpenMaya.MObject]:
        """
        Returns list of all intermediate objects from this node.

        :return: all intermediate objects from this node.
        :rtype: list[OpenMaya.MObject]
        """

        return list(self.iterate_intermediate_objects())

    @override
    def has_attr(self, name: str) -> bool:
        return OpenMaya.MFnDependencyNode(self.object()).hasAttribute(name)

    @override
    def attr(self, name: str) -> Any:
        plug = plugs.find_plug(self.object(), name)
        return plugmutators.value(plug)

    @override
    def set_attr(self, name: str, value: Any):
        plug = plugs.find_plug(self.object(), name)
        plugmutators.set_value(plug, value)

    @override
    def iterate_attrs(self) -> Generator[str, None, None]:
        return attributes.iterate_attribute_names(self.object())

    @override
    def is_transform(self) -> bool:
        return self.object().hasFn(OpenMaya.MFn.kTransform)

    @override
    def is_joint(self) -> bool:
        return self.is_transform() and not any(
            map(self.object().hasFn, (OpenMaya.MFn.kConstraint, OpenMaya.MFn.kPluginConstraintNode)))

    @override
    def is_mesh(self) -> bool:
        return self.object().hasFn(OpenMaya.MFn.kMesh)

    @override(check_signature=False)
    def user_properties(self) -> userproperties.UserProperties:
        return userproperties.UserProperties(self.object())

    @override
    def associated_reference(self) -> Any:
        return dagpath.associated_reference_node(self.object())

    def depends_on(self, api_type: int = OpenMaya.MFn.kDependencyNode) -> list[OpenMaya.MObject]:
        """
        Returns a list of nodes that this object depends on.

        :param int api_type: dependent node types to filter by.
        :return: list of dependent nodes.
        :rtype: list[OpenMaya.MObject]
        """

        return dagpath.depends_on(self.object(), api_type=api_type)

    def dependents(self, api_type: int = OpenMaya.MFn.kDependencyNode) -> list[OpenMaya.MObject]:
        """
        Returns a list of nodes that are dependent on this object.

        :param int api_type: dependent node types to filter by.
        :return: list of dependent nodes.
        :rtype: list[OpenMaya.MObject]
        """

        return dagpath.dependents(self.object(), api_type=api_type)

    @classmethod
    @override
    def does_node_exist(cls, name: str) -> bool:
        return cmds.objExists(name)

    @classmethod
    @override(check_signature=False)
    def node_by_name(cls, name: str) -> OpenMaya.MObject | None:
        found_node = dagpath.mobject_by_name(name)
        return found_node if not found_node.isNull() else None

    @classmethod
    def node_by_handle(cls, handle: str | int) -> OpenMaya.MObject | None:
        """
        Returns a node with the given handle.
        If no node is associated with the given handle, None is returned.

        :param str or int handle: handle to get node from.
        :return: node associated with given handle.
        :rtype: OpenMaya.MObject or None
        """

        handle = cls.__handles__.get(handle, OpenMaya.MObjectHandle())
        return handle.object() if handle.isAlive() else None

    @classmethod
    @override(check_signature=False)
    def nodes_by_attribute(cls, name: str) -> list[OpenMaya.MObject]:
        try:
            selection = OpenMaya.MSelectionList()
            selection.add('*.{name}'.format(name=name))
            return [selection.getDependNode(i) for i in range(selection.length())]
        except RuntimeError:

            return []

    @classmethod
    @override(check_signature=False)
    def iterate_instances(cls, api_type: int = OpenMaya.MFn.kDependencyNode) -> Iterator[OpenMaya.MObject]:
        return dagpath.iterate_nodes(api_type=api_type)
