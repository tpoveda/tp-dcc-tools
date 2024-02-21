from __future__ import annotations

import dataclasses
from typing import Any
from collections import deque
from collections.abc import Sequence, Mapping

from overrides import override

from tp.dcc.abstract import dataclass


class Matrix(Sequence):
    """
    Data class for matrices.
    """

    __slots__ = ('__shape__', '__rows__', '__precision__')

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.__shape__ = Shape()
        self.__rows = deque(maxlen=0)
        self.__precision__ = kwargs.get('precision', 3)

        num_args = len(args)
        if num_args == 1:
            # Check argument type.
            arg = args[0]
            if isinstance(arg, int):
                self.reshape(Shape(arg, arg))
            elif isinstance(arg, Shape):
                self.reshape(arg)
            elif isinstance(arg, (Sequence, Mapping)):
                self.assume(arg)
            else:
                raise TypeError(f'__init__() expects either an int or Shape ({type(arg).__name__} given)!')
        elif num_args == 2:
            # Check argument types.
            rows, columns = args
            if isinstance(rows, int) and isinstance(columns, int):
                self.reshape(Shape(*args))
            else:
                raise TypeError(f'__init__() expects a pair of integers!')
        else:
            raise TypeError(f'__init__() expects either 1 or 2 arguments ({num_args} given)!')

    def __repr__(self) -> str:
        return self.to_string()

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        """
        Returns string representation of this matrix.

        :return: string representation.
        :rtype: str
        """

        return '[{rows}]'.format(
            rows=',\r'.join(str(tuple(map(lambda number: round(number, self.precision), row))) for row in iter(self)))


@dataclasses.dataclass
class Shape(dataclass.ADataClass):
    """
    Overloads of AbstractDataClass that interfaces with matrix shape data.
    """

    rows: int = 0
    columns: int = 0

    @override
    def __eq__(self, other: Shape) -> bool:
        return self.rows == other.rows and self.columns == other.columns

    @override
    def __ne__(self, other: Shape) -> bool:
        return self.rows != other.rows or self.columns != other.columns

    @classmethod
    def detect(cls, array: Any) -> Shape:
        """
        Returns the shape configuration for the given array.

        :param Any array: array.
        :return: shape instance.
        :rtype: Shape
        :raises TypeError: if non-consistent columns or items found.
        """

        is_flat = all(isinstance(item, (float, int)) for item in array)
        is_nested = all(isinstance(item, (Sequence, Mapping)) for item in array)
        if is_flat:
            return cls(1, len(array))
        elif is_nested:
            columns = len(array[0])
            is_consistent = all(len(item) == columns for item in array)
            if is_consistent:
                return cls(len(array), columns)
            else:
                raise TypeError('detect() expects consistent column sizes!')
        else:
            raise TypeError('detect() expects consistent item types!')
