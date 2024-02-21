from __future__ import annotations

import abc
from typing import Generator, Sequence, Any

from tp.dcc.abstract import object


class AFnLayer(object.AFnObject):
    """
    Overloads of AFnObject function set class to handle behaviour for DCC layers.
    """

    __slots__ = ()

    @abc.abstractmethod
    def visibility(self) -> bool:
        """
        Returns the visibility state of this layer.

        :return: True if layer is visible; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def set_visibility(self, flag: bool):
        """
        Sets visibility state of this layer.

        :param bool flag: True to make layer visible; False to hide it.
        """

        pass

    def show(self):
        """
        Sets this layer state to visible.
        """

        self.set_visibility(True)

    def hide(self):
        """
        Sets this layer state as hidden.
        """

        self.set_visibility(False)

    @abc.abstractmethod
    def iterate_nodes(self) -> Generator[Any]:
        """
        Returns a generator that yields nodes from this layer.

        :return: iterated layer nodes.
        :rtype: Generator[Any]
        """

        pass

    def nodes(self) -> list[Any]:
        """
        Returns nodes from this layer.

        :return: layer nodes.
        :rtype: list[Any]
        """

        return list(self.iterate_nodes())

    @abc.abstractmethod
    def add_nodes(self, *nodes: Sequence[Any]):
        """
        Adds the given nodes to this layer.

        :param Sequence[Any] nodes: nodes to add into this layer.
        """

        pass

    @abc.abstractmethod
    def remove_nodes(self, *nodes: Sequence[Any]):
        """
        Removes the given nodes from this layer.

        :param Sequence[Any] nodes: nodes to remove from this layer.
        """

        pass
