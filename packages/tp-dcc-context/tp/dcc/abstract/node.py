from __future__ import annotations

import re
import abc
import typing
from fnmatch import fnmatch
from typing import Generator, Any

from overrides import override

from tp.dcc.abstract import object
from tp.common.python import decorators

if typing.TYPE_CHECKING:
    from tp.dcc.abstract.scene import AFnScene


class AFnNode(object.AFnObject):
    """
    Overload AbstractObject that outlines scene node interfaces.
    Any overloaded function should take care of internally storing node handle for faster lookups.
    If DCC has no means of looking up nodes via handles, then the developer must use an alternative method.
    """

    __slots__ = ()
    __scene__ = None

    @decorators.classproperty
    def scene(self, cls) -> AFnScene:
        """
        Getter method that returns the scene context class.

        :return: scene node belongs to.
        :rtype: AFnScene
        """

        if cls.__scene__ is None:
            from tp.dcc import scene
            cls.__scene__ = scene.Scene()

        return cls.__scene__

    @override
    def is_valid(self) -> bool:
        return self.object() is not None

    @abc.abstractmethod
    def handle(self) -> int:
        """
        Returns the handle for this node.

        :return: node handle.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def is_transform(self) -> bool:
        """
        Returns whether this node represents a transform.

        :return: True if node represents a transform; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def is_joint(self) -> bool:
        """
        Returns whether this node represents a joint.

        :return: True if node represents a joint; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def is_mesh(self) -> bool:
        """
        Returns whether this node represents a mesh.

        :return: True if node represents a mesh; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def has_attr(self, name: str) -> bool:
        """
        Returns whether this node has the specified attribute.

        :param str name: name of the attribute to check.
        :return: True if attribute with given exists for this object; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def attr(self, name: str) -> Any:
        """
        Returns the given attribute value.

        :param str name: name of the attribute we want to get value of.
        :return: attribute value.
        :rtype: Any
        """

        pass

    @abc.abstractmethod
    def set_attr(self, name: str, value: Any):
        """
        Updates the given attribute value.

        :param str name: name of the attribute to set value of.
        :param Any value: new attribute value.
        """

        pass

    @abc.abstractmethod
    def iterate_attrs(self) -> Generator[str, None, None]:
        """
        Returns a generator that yields attribute names.

        :return: iterated attribute names.
        :rtype: Generator[str, None, None]
        """

        pass

    def list_attrs(self) -> list[str]:
        """
        Returns attribute names.

        :return: attribute names.
        :rtype: list[str]
        """

        return list(self.iterate_attrs())

    def is_selected(self) -> bool:
        """
        Returns whether this node is currently selected.

        :return: True if node is selected; False otherwise.
        :rtype: bool
        """

        return self.object() in self.scene.active_selection()

    def is_partially_selected(self) -> bool:
        """
        Returns whether this node is partially selected.

        :return: True if node is partially selected; False otherwise.
        :rtype: bool
        """

        return self.is_selected()

    def select(self, replace: bool = True):
        """
        Selects node associated with this context object.

        :param bool replace: whether to replace active selection.
        """

        self.scene.set_active_selection([self.object()], replace=replace)

    def ensure_selected(self):
        """
        Ensures this node is selected.
        """

        if not self.is_selected():
            self.select(replace=True)

    def deselect(self):
        """
        Deselects the node associated with this context object.
        """

        active_selection = self.scene.active_selection()
        obj = self.object()
        if obj not in active_selection:
            return
        active_selection.remove(obj)
        self.scene.set_active_selection(active_selection, replace=True)

    def is_isolated(self) -> bool:
        """
        Returns whether this is the only node selected.

        :return: True if this node is the only one selected; False otherwise.
        :rtype: bool
        """

        selection_count = len(self.scene.active_selection())

        return selection_count == 1 and self.is_partially_selected()

    @abc.abstractmethod
    def user_properties(self) -> dict:
        """
        Returns user properties.

        :return: user properties.
        :rtype: dict
        """

        pass

    @abc.abstractmethod
    def associated_reference(self) -> Any:
        """
        Returns the reference this node is associated with.

        :return: node reference.
        :rtype: Any
        """

        pass

    def is_referenced_node(self) -> bool:
        """
        Returns whether this node is a referenced node.

        :return: True if node is a referenced one; False otherwise.
        :rtype: bool
        """

        return self.associated_reference() is not None

    @classmethod
    @abc.abstractmethod
    def does_node_exist(cls, name: str) -> bool:
        """
        Returns whether node exists in scene with given name.

        :param str name: name of the node to check.
        :return: True if node with given name exists in scene; False otherwise.
        :rtype: bool
        """

        pass

    @classmethod
    @abc.abstractmethod
    def node_by_name(cls, name: str) -> Any:
        """
        Returns node instance with given name.

        :param str name: name of the node to get from scene.
        :return: node instance with given name.
        :rtype: Any
        """

        pass

    @classmethod
    @abc.abstractmethod
    def node_by_handle(cls, handle: int) -> Any:
        """
        Returns node instance with given handle.

        :param str handle: handle of the node to get from scene.
        :return: node instance with given handle.
        :rtype: Any
        """

        pass

    @classmethod
    @abc.abstractmethod
    def nodes_by_attribute(cls, name: str) -> list[Any]:
        """
        Returns list of nodes with the given attribute name.

        :param str name: attribute name.
        :return: nodes with given attribute.
        :rtype: list[Any]
        """

        pass

    @classmethod
    @abc.abstractmethod
    def iterate_instances(cls) -> Generator[Any, None, None]:
        """
        Returns a generator that yields instances of this node.

        :return: iterated instances.
        :rtype: Generator[Any, None, None]
        """

        pass

    @classmethod
    def instances(cls) -> list[Any]:
        """
        Returns a list of instances of this node.

        :return: list of instances.
        :rtype: list[Any]
        """

        return list(cls.iterate_instances())

    @classmethod
    def iterate_instances_by_pattern(cls, pattern: str) -> Generator[Any, None, None]:
        """
        Returns a generator that yields nodes that match the given pattern.

        :param str pattern: pattern to match.
        :return: iterated nodes that match the given pattern.
        :rtype: Generator[Any, None, None]
        """

        node = cls()
        node.set_queue(cls.iterate_instances())
        while not node.is_done():
            if fnmatch(node.name(), pattern):
                yield node.object()
            node.next()

    @classmethod
    def iterate_instances_by_regex(cls, pattern: str) -> Generator[Any, None, None]:
        """
        Returns a generator that yields nodes that match the given regex expression.

        :param str pattern: regex expression to match.
        :return: iterated nodes that match the given regex expression.
        :rtype: Generator[Any, None, None]
        """

        node = cls()
        node.set_queue(cls.iterate_instances())
        regex = re.compile(pattern)
        while not node.is_done():
            if regex.match(node.name()):
                yield node.object()
            node.next()
