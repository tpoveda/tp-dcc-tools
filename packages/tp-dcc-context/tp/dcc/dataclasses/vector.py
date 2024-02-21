from __future__ import annotations

import math
import dataclasses
from typing import Iterator

from tp.core import log
from tp.common.python import decorators
from tp.dcc.abstract import dataclass
from tp.dcc.dataclasses import transformationmatrix

logger = log.tpLogger


@dataclasses.dataclass
class Vector(dataclass.ADataClass):
    """
    Data class for 3D vectors.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):

        # Validate vector.
        if all(isinstance(x, (int, float)) for x in self):
            return

        # Check if sequence was passed to constructor.
        args = self.x
        if hasattr(args, '__getitem__') and hasattr(args, '__len__'):
            # Un-package items into vector.
            for (i, item) in enumerate(args):
                self[i] = item
        else:
            raise TypeError(f'__post_init__() expects either an int or float ({type(args).__name__} given)!')

    def __eq__(self, other: Vector) -> bool:
        return self.is_equivalent(other)

    def __ne__(self, other: Vector) -> bool:
        return not self.is_equivalent(other)

    def __lt__(self, other: Vector) -> bool:
        return self.x < other.x and self.y < other.y and self.z < other.z

    def __le__(self, other: Vector) -> bool:
        return self < other or self.is_equivalent(other)

    def __gt__(self, other: Vector) -> bool:
        return self.x > other.x and self.y > other.y and self.z > other.z

    def __ge__(self, other: Vector) -> bool:
        return self > other or self.is_equivalent(other)

    def __add__(self, other: Vector) -> Vector:
        copy = self.copy()
        copy += other

        return copy

    def __radd__(self, other: int | float) -> Vector:
        if isinstance(other, (int, float)):
            other = Vector(other, other, other)
            return other.__add__(self)

        else:
            raise NotImplemented(f'__radd__() expects either an int or float ({type(other).__name__} given)!')

    def __iadd__(self, other: int | float | Vector) -> Vector:
        if isinstance(other, Vector):
            self.x += other.x
            self.y += other.y
            self.z += other.z
        elif isinstance(other, (int, float)):
            self.x += other
            self.y += other
            self.z += other
        else:
            raise NotImplemented(f'__iadd__() expects either a float or Vector ({type(other).__name__} given)!')

        return self

    def __sub__(self, other: int | float | Vector) -> Vector:
        copy = self.copy()
        copy -= other

        return copy

    def __rsub__(self, other: int | float) -> Vector:
        if isinstance(other, (int, float)):
            other = Vector(other, other, other)
            return other.__sub__(self)
        else:
            raise NotImplemented(f'__rsub__() expects either an int or float ({type(other).__name__} given)!')

    def __isub__(self, other: int | float | Vector) -> Vector:
        if isinstance(other, Vector):
            self.x -= other.x
            self.y -= other.y
            self.z -= other.z
        elif isinstance(other, (int, float)):
            self.x -= other
            self.y -= other
            self.z -= other
        else:
            raise NotImplemented(f'__isub__() expects either a float or Vector ({type(other).__name__} given)!')

        return self

    def __mul__(self, other: int | float | Vector) -> float | Vector:
        if isinstance(other, Vector):
            return self.dot(other)
        else:
            copy = self.copy()
            copy *= other
            return copy

    def __imul__(self, other: int | float | Vector) -> Vector:
        if isinstance(other, Vector):
            self.x *= other.x
            self.y *= other.y
            self.z *= other.z
        elif isinstance(other, (int, float)):
            self.x *= other
            self.y *= other
            self.z *= other
        elif isinstance(other, transformationmatrix.TransformationMatrix):
            matrix = transformationmatrix.TransformationMatrix(row4=self)
            matrix *= other

            self.x, self.y, self.z = matrix.row4
        else:
            raise NotImplemented(f'__imul__() expects either a float or Vector ({type(other).__name__} given)!')

        return self

    def __truediv__(self, other: int | float | Vector) -> Vector:
        if isinstance(other, Vector):
            try:
                self.x /= other.x
                self.y /= other.y
                self.z /= other.z
            except ZeroDivisionError as exception:
                logger.debug(exception)
        elif isinstance(other, (float, int)):
            try:
                self.x /= other
                self.y /= other
                self.z /= other
            except ZeroDivisionError as exception:
                logger.debug(exception)
        else:
            raise NotImplemented(f'__itruediv__() expects either a float or Vector ({type(other).__name__} given)!')

        return self

    def __xor__(self, other: Vector) -> Vector:
        return self.cross(other)

    def __neg__(self) -> Vector:
        return self.inverse()

    def __iter__(self) -> Iterator[int | float]:
        return iter((self.x, self.y, self.z))

    def __len__(self) -> int:
        return 3

    @decorators.classproperty
    def x_axis(cls) -> Vector:
        """
        Returns the X-axis vector.

        :return: X-axis vector.
        :rtype: Vector
        """

        return Vector(1.0, 0.0, 0.0)

    @decorators.classproperty
    def y_axis(cls) -> Vector:
        """
        Returns the Y-axis vector.

        :return: Y-axis vector.
        :rtype: Vector
        """

        return Vector(0.0, 1.0, 0.0)

    @decorators.classproperty
    def z_axis(cls) -> Vector:
        """
        Returns the Z-axis vector.

        :return: Z-axis vector.
        :rtype: Vector
        """

        return Vector(0.0, 0.0, 1.0)

    @decorators.classproperty
    def zero(cls) -> Vector:
        """
        Returns the origin vector.

        :return: origin vector.
        :rtype: Vector
        """

        return Vector(0.0, 0.0, 0.0)

    @decorators.classproperty
    def one(cls) -> Vector:
        """
        Returns a one vector.

        :return: one vector.
        :rtype: Vector
        """

        return Vector(1.0, 1.0, 1.0)

    def is_equivalent(self, other: Vector, tolerance: float = 1e-3) -> bool:
        """
        Returns whether given vector is equivalent to this one.

        :param Vector other: vector to compare.
        :param float tolerance: comparison bias.
        :return: True if vector is equivalent; False otherwise.
        :rtype: bool
        """

        return all(math.isclose(x, y, abs_tol=tolerance) for (x, y) in zip(self, other))

    def length(self) -> float:
        """
        Returns the length of this vector.

        :return: vector lenght.
        :rtype: float
        """

        return math.sqrt(math.pow(self.x, 2.0) + math.pow(self.y, 2.0) + math.pow(self.z, 2.0))

    def dot(self, other: Vector) -> float:
        """
        Returns the dot product between this and the given vector.

        :param Vector other: vector.
        :return: dot product.
        :rtype: float
        """

        return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)

    def cross(self, other: Vector) -> Vector:
        """
        Returns the cross product between this and the given vector.

        :param Vector other: vector.
        :return: cross product.
        :rtype: Vector
        ..notes:: this solution uses the right hand rule!
        """

        x = (self.y * other.z) - (self.z * other.y)
        y = (self.z * other.x) - (self.x * other.z)
        z = (self.x * other.y) - (self.y * other.x)

        return Vector(x, y, z)

    def distance_between(self, other: Vector) -> float:
        """
        Returns the distance between this vector and the given one.

        :param Vector other: vector.
        :return: total distance between vectors.
        :rtype: float
        """

        return (other - self).length()

    def angle_between(self, other: Vector, as_degrees: bool = False) -> float:
        """
        Returns the angle (in radians), between this vector and the given one.

        :param Vector other: vector.
        :param bool as_degrees: whether to return angle in degrees or radians.
        :return: angle between vectors.
        :rtype: float
        """

        try:

            radian = math.acos(self.dot(other) / self.length() * other.length())
            if as_degrees:
                return math.degrees(radian)
            else:
                return radian
        except ZeroDivisionError:
            return 0.0

    def normal(self) -> Vector:
        """
        Returns a normalized copy of this vector.

        :return: normamlized vector.
        :rtype: Vector
        """

        try:
            return self / self.length()
        except ZeroDivisionError:
            return dataclasses.replace(self)

    def normalize(self):
        """
        Normalizes this vector.
        """

        self /= self.length()
        return self

    def inverse(self) -> Vector:
        """
        Returns an inversed copy of this vector.

        :return: inverse vector.
        :rtype: Vector
        """

        return self * -1.0

    def to_list(self) -> list[int or float]:
        """
        Converts this vector as a list.

        :return: vector as a list.
        :rtype: list[int or float]
        """

        return list(self)
