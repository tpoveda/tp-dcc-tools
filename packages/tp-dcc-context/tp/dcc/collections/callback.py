from __future__ import annotations

from collections import abc
from typing import Iterator, Sequence, Any

from tp.dcc.collections import weakref


class CallbackList(abc.MutableSequence):
    """
    Overloads of MutableSequence used to provide callback mechanism for any list changes.
    """

    __slots__ = ('__items__', '__callbacks__')

    def __init__(self, *args, **kwargs):
        super().__init__()

        cls = kwargs.get('cls', list)
        if not callable(cls):
            raise TypeError('__init__() expects a callable class!')

        self.__items__: list = cls()
        self.__callbacks__ = {'itemAdded': weakref.WeakRefList(), 'itemRemoved': weakref.WeakRefList()}

        num_args = len(args)
        if num_args == 1:
            self.extend(args[0])

    def __getitem__(self, index: int) -> Any:
        """
        Internal function that returns an indexed item.

        :param int index: index to get item from.
        :return: indexed item.
        :rtype: ReferenceType
        """

        return self.__items__[index]

    def __setitem__(self, index: int, value: Any):
        """
        Internal function that updates an indexed item.

        :param int index: index of the item to update.
        :param Any value: new item to store.
        """

        self.__items__[index] = value
        self.itemAdded(index, value)

    def __delitem__(self, index: int):
        """
        Internal function that removes an indexed item.

        :param int index: index of the item to delete.
        """

        self.pop(index)

    def __iter__(self) -> Iterator[Any]:
        """
        Internal function that returns a generator for this sequence.

        :return: iterated items.
        :rtype: Iterator[Any]
        """

        return iter(self.__items__)

    def __len__(self) -> int:
        """
        Internal function that returns the length of this sequence.

        :return: sequence length.
        :rtype: int
        """

        return len(self.__items__)

    def __contains__(self, item: Any) -> bool:
        """
        Internal function that evaluates whether given item exists witin this sequence.

        :param Any item: item to check existence of.
        :return: True if item exists within sequence; False otherwise.
        :rtype: bool
        """

        return item in self.__items__

    def append(self, value: Any):
        """
        Appends a value to the end of the list.

        :param Any value: item to add into the list.
        """

        self.__items__.append(value)
        self.itemAdded(self.__len__() - 1, value)

    def append_if_unique(self, value: Any):
        """
        Appends an item so long it does not already exist.

        :param Any value: item to add into the list.
        """

        if value not in self:
            self.append(value)

    def insert(self, index: int, value: Any):
        """
        Inserts new item in the given index.

        :param int index: index to insert item into.
        :param Any value: item to insert into the list.
        """

        self.__items__.insert(index, value)
        self.itemAdded(index, value)

    def extend(self, values: Sequence[Any]):
        """
        Appends a sequence of values to the end of this list.

        :param Sequence[Any] values: items to append into this list.
        """

        for value in values:
            self.append(value)

    def move(self, index: int, value: Any):
        """
        Moves an index item to a different index.

        :param int index: index to move value of.
        :param Any value: value to move indexed item to the index of.
        """

        current_index = self.__items__.index(value)
        self.__items__[current_index], self.__items__[index] = self.__items__[index], self.__items__[current_index]

    def index(self, value: Any) -> int:
        """
        Returns the index the given value is located at.

        :param Any value: value to check index of.
        :return: item index.
        :rtype: int
        """

        return self.__items__.index(value)

    def remove(self, value: Any):
        """
        Removes a value from this list.

        :param Any value: item to remove.
        """

        self.pop(self.index(value))

    def pop(self, index: int) -> Any:
        """
        Removes the indexed item from this list and returns it.

        :param int index: index of the item to remove.
        :return: removed item at given index.
        :rtype: Any
        """

        if isinstance(index, int):
            item = self.__items__.pop(index)
            self.itemRemoved(item)
            return item
        elif isinstance(index, slice):
            start = 0 if index.start is None else index.start
            stop = len(self) if index.stop is None else index.stop
            step = 1 if index.step is None else index.step
            return [self.pop(i) for i in range(start, stop, step)]
        else:
            raise TypeError(f'pop() expects either an int or slice ({type(index).__name__} given)!')

    def clear(self):
        """
        Removes all items from this list.
        """

        [self.pop(0) for _ in range(len(self))]

    def callback_names(self) -> list[str]:
        """
        Returns a list of callback names that can be used.

        :return: last of available callback names.
        :rtype: list[str]
        """

        return list(self.__callbacks__.keys())

    def add_callback(self, name: str, func: callable):
        """
        Appends the given function to the given callback group.

        :param str name: name of the callback group to add callback to.
        :param callable func: callback function.
        """

        callbacks = self.__callbacks__[name]
        if func not in callbacks:
            callbacks.append(func)

    def remove_callback(self, name: str, func: callable):
        """
        Removes the given callback from given callback group.

        :param str name: name of the callback group to remove callback from.
        :param callable func: callback function.
        """

        print('revmoing callback ....', name)

        callbacks = self.__callbacks__[name]
        if func in callbacks:
            callbacks.remove(func)

    def itemAdded(self, index: int, item: Any):
        """
        Function that notifies each time an item has been added.

        :param int index: index of the added item.
        :param Any item: added item.
        """

        for func in self.__callbacks__['itemAdded']:
            func(index, item)

    def itemRemoved(self, item: Any):
        """
        Function that notifies each time an item has been removed.

        :param Any item: removed item.
        """

        for func in self.__callbacks__['itemRemoved']:
            func(item)
