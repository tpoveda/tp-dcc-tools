from __future__ import annotations

import abc
import dataclasses
from collections.abc import Mapping
from typing import Iterator, Generator, Any

from tp.common.python import decorators


@dataclasses.dataclass
class ADataClass(Mapping, metaclass=abc.ABCMeta):
    """
    Overload of 'Mapping' used to outline abstract data class behaviour.
    """

    def __getstate__(self) -> dict:
        """
        Overrides internal function that returns a pickled object from this collection.

        :return: pickled object.
        :rtype: dict
        """

        state = {'__name__': self.class_name, '__module__': self.module_name}
        for key, value in self.items():
            if hasattr(value, '__getstate__'):
                state[key] = value.__getstate__() if hasattr(value, '__getstate__') else value

        return state

    def __setstate__(self, state: dict):
        """
        Overrides internal function that inherits the contents of the pickled object.

        :param dict state: pickled object.
        """

        self.update(state)

    def __getitem__(self, key: str | int) -> Any:
        """
        Overrides internal function that returns the indexed item.

        :param str or int key: item key.
        :return: indexed item.
        :rtype: Any
        """

        if isinstance(key, str):
            return getattr(self, key)
        elif isinstance(key, int):
            data_fields = dataclasses.fields(self.__class__)
            num_data_fields = len(data_fields)
            if 0 <= key < num_data_fields:
                return getattr(self, data_fields[key].name)
            else:
                raise IndexError('__getitem__() index is out of range!')
        else:
            raise TypeError(f'__getitem__() expects either a str or int ({type(key).__name__} given)!')

    def __setitem__(self, key: str | int, value: Any):
        """
        Internal function that updates an indexed item.

        :param str or int key: index of the item to update.
        :param Any value: new item value.
        """

        if isinstance(key, str):
            return setattr(self, key, value)
        elif isinstance(key, int):
            data_fields = dataclasses.fields(self.__class__)
            num_data_fields = len(data_fields)
            if 0 <= key < num_data_fields:
                return setattr(self, data_fields[key].name, value)
            else:
                raise IndexError('__setitem__() index is out of range!')
        else:
            raise TypeError(f'__setitem__() expects either a str or int ({type(key).__name__} given)!')

    def __contains__(self, item: Any) -> bool:
        """
        Internal function that evaluation whether this instance contains the given item.

        :param Any item: item to check existence of.
        :return: True if item exists within this collection; False otherwise.
        :rtype: bool
        """

        return item in self.keys()

    def __eq__(self, other: Any) -> bool:
        """
        Internal function that implements equal operator.

        :param Any other: item to check against.
        :return: True if given item is equal to this collection; False otherwise.
        :rtype: bool
        """

        return self is other

    def __ne__(self, other: Any) -> bool:
        """
        Internal function that implements not equal operator.

        :param Any other: item to check against.
        :return: True if given item is not equal to this collection; False otherwise.
        :rtype: bool
        """

        return self is not other

    def __len__(self) -> int:
        """
        Internal function that returns the size of this collection instance.

        :return: collection size.
        :rtype: int
        """

        return len(list(self.fields()))

    def __iter__(self) -> Iterator[str]:
        """
        Internal function that returns a generator that yields keys from this collection instance.

        :return: iterated keys.
        :rtype: Iterator[str]
        """

        return self.keys()

    @decorators.classproperty
    def class_name(cls) -> str:
        """
        Returns class name.

        :return: class name.
        :rtype: str
        """

        return cls.__name__

    @decorators.classproperty
    def module_name(cls) -> str:
        """
        Returns module name.

        :return: module name.
        :rtype: str
        """

        return cls.__module__

    @classmethod
    def fields(cls) -> Iterator[dataclasses.Field]:
        """
        Returns an iterator that yields fields from this instance.

        :return: iterated fields.
        :rtype: Iterator[dataclasses.Field]
        """

        return iter(dataclasses.fields(cls))

    def keys(self) -> Generator[str]:
        """
        Returns a generator that yields keys from this instance.

        :return: iterated keys.
        :rtype: Generator[str]
        """

        for field in self.fields():
            yield field.name

    def values(self) -> Generator[Any]:
        """
        Returns a generator that yields values from this instance.

        :return: iterated values.
        :rtype: Generator[Any]
        """

        for key in self.keys():
            yield getattr(self, key)

    def items(self) -> Generator[tuple[str, Any]]:
        """
        Returns a generator that yields values from this instance.

        :return: iterated values.
        :rtype: Generator[tuple[str, Any]]
        """

        for key in self.keys():
            yield key, getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Returns indexed item.
        If no item exists, then the default value is returned instead.

        :param int or str key: key to get vaue of.
        :param Any default: default value to return if no item found.
        :return: item value.
        :rtype: Any
        """

        return getattr(self, key, default)

    def update(self, obj: dict):
        """
        Copies the values from the given object to this instance.

        :param dict obj: dictionary to copy values from.
        """

        for key, value in obj.items():
            setattr(self, key, value)

    def copy(self, **kwargs) -> ADataClass:
        """
        Returns a copy of this instance.
        Any keyword arguments supplied will be passed to the update method.

        :param dict kwargs: keyword arguments to copy.
        :return: copied instance.
        :rtype: AbstractDataClass
        """

        copy = dataclasses.replace(self)
        copy.update(kwargs)

        return copy
