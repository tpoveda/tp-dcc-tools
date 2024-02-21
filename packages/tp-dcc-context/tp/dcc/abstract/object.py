from __future__ import annotations

import abc
import typing
from typing import Any, Generator
from collections import deque

from tp.dcc.abstract import base
from tp.common.python import decorators

if typing.TYPE_CHECKING:
    from tp.dcc.abstract.node import AbstractNode


class AFnObject(base.AFnBase):
    """
    Custom context class that outlines parent/child interfaces.
    """

    __slots__ = ()
    __sep_char__ = '/'
    __alt_sep_char__ = '\\'

    @decorators.classproperty
    def sep_char(cls) -> str:
        """
        Returns path separator for the associated DCC.

        :return: path separator.
        :rtype: str
        """

        return cls.__sep_char__

    @decorators.classproperty
    def alt_sep_char(cls) -> str:
        """
        Returns alternative path separator for the associated DCC.

        :return: alternative path separator.
        :rtype: str
        """

        return cls.__alt_sep_char__

    @abc.abstractmethod
    def name(self) -> str:
        """
        Returns the name of this object.

        :return: object name.
        :rtype: str
        """

    @abc.abstractmethod
    def set_name(self, name: str):
        """
        Updates the name of this object.

        :param str name: object name.
        """

        pass

    @abc.abstractmethod
    def namespace(self) -> str:
        """
        Returns the namespace for this object.

        :return: object namespace.
        :rtype: str
        """

        pass

    @abc.abstractmethod
    def set_namespace(self, new_namespace: str):
        """
        Updates the namespace for this object.

        :param str new_namespace: object namespace.
        """

        pass

    def absolute_name(self) -> str:
        """
        Returns the absolute name of this object.

        :return: object absolute name.
        :rtype: str
        """

        namespace = self.namespace()
        name = self.name()
        if namespace:
            return f'{namespace}:{name}'

        return name

    def path(self) -> str:
        """
        Returns path to this object.

        :return: object path.
        :rtype: str
        """

        return self.sep_char.join([self.__class__(x).absolute_name() for x in self.trace()])

    def find_common_path(self, *objects: AbstractNode | list[AbstractNode]) -> str:
        """
        Returns the common path from the given objects.

        :param AbstractNode or list[AbstractNode] objects: object/s to find common path from.
        :return: common path.
        :rtype: str
        """

        paths = [obj.path() for obj in objects]
        sub_strings = [path.split(self.sep_char) for path in paths]
        depths = [len(sub_string) for sub_string in sub_strings]
        min_depth = min(depths)

        common_path: list[str] = []
        for i in range(min_depth):
            identical = len(set([sub_string[1] for sub_string in sub_strings])) == 1
            if identical:
                common_path.append(sub_strings[0][i])
            else:
                break

        return self.sep_char.join(common_path)

    @abc.abstractmethod
    def parent(self) -> Any | None:
        """
        Returnsr parent of this object.

        :return: parent object.
        :rtype: Any or None
        """

        pass

    @abc.abstractmethod
    def set_parent(self, parent: Any | None):
        """
        Updates the parent of this object.

        :param Any or None parent: new object parent.
        """

        pass

    def has_parent(self) -> bool:
        """
        Returns whether this object has a parent.

        :return: True if object has a parent; False otherwise.
        :rtype: bool
        """

        return self.parent() is not None

    def iterate_parents(self) -> Generator[Any]:
        """
        Iterator function that returns a generator that yields all the parents of this object.

        :return: iterated parents.
        :rtype: Generator[Any]
        """

        fn_obj = self.__class__()
        fn_obj.set_object(self.object())
        parent = fn_obj.parent()

        while parent is not None:
            yield parent
            fn_obj.set_object(parent)
            parent = fn_obj.parent()

    def parents(self) -> list[Any]:
        """
        Returns list of al the parents of this object.

        :return: object parents.
        :rtype: list[Any]
        """

        return list(self.iterate_parents())

    def top_level_parent(self) -> Any | None:
        """
        Returns the top level parent of this object.

        :return: top level parent.
        :rtype: Any or None
        """

        parents = self.parents()
        return parents[-1] if parents else None

    def trace(self) -> Generator[Any]:
        """
        Returns a generator that yields all the objects from the top-level parent to this object.

        :return: iterated objects from the top-level parent to this object.
        :rtype: Generator[Any]
        """

        for parent in reversed(self.parents()):
            yield parent

        yield self.object()

    @abc.abstractmethod
    def iterate_children(self) -> Generator[Any]:
        """
        Returns a generator that yields all the children from this object.

        :return: iterated children from this object.
        :rtype: Generator[Any]
        """

        pass

    def children(self) -> list[Any]:
        """
        Returns a list of children from this object.

        :return: children from this object.
        :rtype: list[Any]
        """

        return list(self.iterate_children())

    def iterate_descendants(self) -> Generator[Any]:
        """
        Returns a generator that yields all the descendants from this object.

        :return: iterated descendants from this object.
        :rtype: Generator[Any]
        """

        queue = deque(self.children())
        fn_node = self.__class__()
        while len(queue) > 0:
            node = queue.popleft()
            yield node
            fn_node.set_object(node)
            queue.extend(fn_node.children())

    def descendants(self) -> list[Any]:
        """
        Returns a list of all the descendants from this object.

        :return: list of descendants.
        :rtype: list[Any]
        """

        return list(self.iterate_descendants())
