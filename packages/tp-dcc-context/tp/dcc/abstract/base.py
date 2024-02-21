from __future__ import annotations

import abc
import inspect
import collections.abc
from collections import deque
from typing import Iterator, Any

from tp.core import log
from tp.dcc import abstract
from tp.common.python import generators, decorators

logger = log.tpLogger


class AFnBase(abc.ABC):
    """
    Abstract class for all DCC context classes.
    """

    __slots__ = ('_object', '_queue')
    __array_index_type__ = abstract.ArrayIndexType.ZeroBased

    def __init__(self, *args, **kwargs):
        super().__init__()

        # Declare class variables.
        self._object: Any = None
        self._queue = deque()

        # Check supplied arguments
        if len(args) == 1:
            arg = args[0]
            if self.accepts_queue(arg):
                self.set_queue(arg)
            else:
                self.set_object(arg)
        elif len(args) > 1:
            self.set_queue(args)

    def __call__(self, obj: Any):
        self.set_object(obj)
        return self

    def __getattribute__(self, name: str) -> Any:
        # Get class definition to check whether if this is an instance method
        cls = super().__getattribute__('__class__')
        obj = getattr(cls, name)
        if not inspect.isfunction(obj) or hasattr(AFnBase, name):
            return super().__getattribute__(name)

        # Check whether function set is valid.
        func = super().__getattribute__('is_valid')
        is_valid = func()
        if is_valid:
            return super().__getattribute__(name)
        else:
            raise TypeError(f'__getattribute__() function set object does not exist for {func.__name__}!')

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AFnBase):
            return self.object() == other.object()

        return self.object() == other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, AFnBase):
            return self.object() != other.object()

        return self.object() != other

    def __iter__(self) -> Iterator[Any]:
        while not self.is_done():
            yield self.next()

    def __len__(self) -> int:
        return len(self._queue)

    @decorators.classproperty
    def array_index_type(cls) -> int:
        """
        Getter that returns the array index for this context class.

        :return: array index type.
        :rtype: int
        """

        return cls.__array_index_type__

    def accepts_object(self, obj: Any) -> bool:
        """
        Returns whether this given DCC native node is supported by this context class.

        :param Any obj: DCC native node.
        :return: True if given object is supported by this context class; False otherwise.
        :rtype: bool
        """

        return True

    def object(self) -> Any:
        """
        Returns the DCC native node wrapped by this context class.

        :return: DCC native wrapped node.
        :rtype: Any
        """

        return self._object

    def set_object(self, obj: Any):
        """
        Assigns given DCC native object to this context class for manipulation.

        :param Any obj: DCC native object.
        :raises RuntimeError: if something went wrong while assigning DCC native node.
        :raises TypeError: if given DCC native node is not valid.
        """

        self._object = obj

    def try_set_object(self, obj: Any) -> bool:
        """
        Attempts to assign given DCC native object to this context class for manipulation.

        :param Any obj: DCC native object.
        :return: True if set object operation was successful; False otherwise.
        :rtype: bool
        """

        try:
            self.set_object(obj)
            return True
        except (RuntimeError, TypeError) as err:
            logger.debug(err)
            self.reset_object()
            return False

    def has_object(self) -> bool:
        """
        Returns whether this context class has an assigned object.

        :return: True if context clas has an assigned object; False otherwise.
        :rtype: bool
        ..warning:: this does not necessarily mean the object is valid!
        """

        return self._object is not None

    def reset_object(self):
        """
        Resets the object back to its default value.
        """

        self._object = None

    def is_valid(self) -> bool:
        """
        Returns whether wrapped DCC native node is valid.

        :return: True if DCC native node is valid; False otherwise.
        :rtype: bool
        """

        return True

    def accepts_queue(self, queue: Any) -> bool:
        """
        Returns whether the given object can be used as a queue.

        :param Any queue: object to check.
        :return: True if given object can be used as a queue; False otherwise.
        :rtype: bool
        """

        return isinstance(queue, (collections.abc.Sequence, collections.abc.Iterator)) and not isinstance(queue, str)

    def queue(self) -> deque:
        """
        Returns the object queue for this context class.

        :return: object queue.
        :rtype: deque
        """

        return self._queue

    def set_queue(self, queue: list | Iterator):
        """
        Updates the object queue for this context class.

        :param list or Iterator queue: queue to set.
        :raises TypeError: if given queue type is not a sequence.
        """

        if not self.accepts_queue(queue):
            raise TypeError(f'set_queue() expects a sequence ({type(queue).__name__} given)')

        self._queue = deque(generators.flatten(queue))
        self.next()

    def is_done(self) -> bool:
        """
        Returns whether queue is empty.

        :return: True if queue is empty; False otherwise.
        :rtype: bool
        """

        return len(self._queue) == 0 and not self.is_valid()

    def next(self) -> Any:
        """
        Attaches this context class to the next object in the queue.

        :return: next object in queue.
        :rtype: Any
        """

        if self.is_done():
            return

        if self._queue:
            obj = self._queue.popleft()
            success = self.try_set_object(obj)
            if success:
                return obj
            else:
                return self.next()
        else:
            self.reset_object()
