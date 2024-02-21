from __future__ import annotations

import inspect
import weakref
from collections import abc
from weakref import ReferenceType
from typing import Iterator, Sequence, Any


class WeakRefList(abc.MutableSequence):
    """
    Overloads of MutableSequence used to store weak references to objects.
    """

    __slots__ = ('__weakrefs__',)

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.__weakrefs__: list[ReferenceType[Any]] = []

        num_args = len(args)
        if num_args == 1:
            self.extend(args[0])

    def __getitem__(self, index: int) -> ReferenceType[Any]:
        """
        Internal function that returns an indexed item.

        :param int index: index to get item from.
        :return: indexed item.
        :rtype: ReferenceType
        """

        return self.__weakrefs__[index]()

    def __setitem__(self, index: int, value: Any):
        """
        Internal function that updates an indexed item.

        :param int index: index of the item to update.
        :param Any value: new item to store weak reference of.
        """

        self.__weakrefs__[index] = self.ref(value)

    def __delitem__(self, index: int):
        """
        Internal function that removes an indexed item.

        :param int index: index of the item to delete.
        """

        del self.__weakrefs__[index]

    def __iter__(self) -> Iterator[Any]:
        """
        Internal function that returns a generator for this sequence.

        :return: iterated items.
        :rtype: Iterator[Any]
        """

        for ref in self.__weakrefs__:
            yield ref()

    def __len__(self) -> int:
        """
        Internal function that returns the length of this sequence.

        :return: sequence length.
        :rtype: int
        """

        return len(self.__weakrefs__)

    def __contains__(self, item: Any) -> bool:
        """
        Internal function that evaluates whether given item exists witin this sequence.

        :param Any item: item to check existence of.
        :return: True if item exists within sequence; False otherwise.
        :rtype: bool
        """

        return item in self.__weakrefs__

    def append(self, value: Any):
        """
        Appends a value to the end of the list.

        :param Any value: item to add into the list.
        """

        self.__weakrefs__.append(self.ref(value))

    def insert(self, index: int, value: Any):
        """
        Inserts new item in the given index.

        :param int index: index to insert item into.
        :param Any value: item to insert into the list.
        """

        self.__weakrefs__.insert(index, self.ref(value))

    def extend(self, values: Sequence[Any]):
        """
        Appends a sequence of values to the end of this list.

        :param Sequence[Any] values: items to append into this list.
        """

        self.__weakrefs__.extend([self.ref(value) for value in values])

    def index(self, value: Any) -> int:
        """
        Returns the index the given value is located at.

        :param Any value: value to check index of.
        :return: item index.
        :rtype: int
        """

        if not isinstance(value, weakref.ref):
            value = weakref.ref(value)

        return self.__weakrefs__.index(value)

    def remove(self, value: Any):
        """
        Removes a value from this list.

        :param Any value: item to remove.
        """

        self.__weakrefs__.remove(value)

    def ref(self, value: Any) -> ReferenceType[Any]:
        """
        Returns a reference to the given value.

        :param Any value: value to get reference of.
        :return: reference from value.
        :rtype: ReferenceType[Any]
        """

        if inspect.ismethod(value):
            return weakref.WeakMethod(value, self.remove)
        else:
            return weakref.ref(value, self.remove)
