from __future__ import annotations

import abc
import enum
import dataclasses
from typing import Iterator

from tp.dcc.abstract import base
from tp.dcc.dataclasses import vector


class ComponentType(enum.IntEnum):
    """
    Enumerator that holds all available mesh components.
    """

    Vertex = 0
    Edge = 1
    Face = 2


@dataclasses.dataclass
class Hit:
    """
    Data class to store hit related data
    """

    point: vector.Vector = dataclasses.field(default_factory=lambda: vector.Vector())
    face_index: int = 0
    face_vertex_indices: list[int] = dataclasses.field(default_factory=lambda: [])
    bi_coords: tuple[float, float] = dataclasses.field(default_factory=lambda: (0.0, 0.0))
    triangle_index: int = 0
    triangle_vertex_indices: list[int] = dataclasses.field(default_factory=lambda: [])
    bary_coords: tuple[float, float, float] = dataclasses.field(default_factory=lambda: (0.0, 0.0, 0.0))


class AbstractMesh(base.AFnBase):
    """
    Overloads of base.AbstractBase that outlines DCC context behaviour for meshes.
    """

    __slots__ = ()
    __face_triangles__ = {}     # Lookup optimization

    ComponentType = ComponentType
    Hit = Hit

    def range(self, *args) -> Iterator:
        """
        Returns a generator that yields a range of mesh elements.

        :return: iterated mesh elements.
        :rtype: Iterator
        :raises TypeError: if an invalid number of arguments are given.
        ..note:: helps support programs that don't utilize zero-based arrays.
        """

        num_args = len(args)
        start, stop, step = self.array_index_type, self.array_index_type, 1
        if num_args == 1:
            stop = args[0] + self.arrayIndexType
        elif num_args == 2:
            start = args[0]
            stop = args[1] + self.arrayIndexType
        elif num_args == 3:
            start = args[0]
            stop = args[1] + self.arrayIndexType
            step = args[2]
        else:
            raise TypeError(f'range() expects at least 1 argument ({num_args} given)!')

        return range(start, stop, step)

    def enumerate(self, elements: list[int]) -> Iterator:
        """
        Returns a generator that yields local indices for global mesh elements.

        :param elements:
        :return: iterated local indices for global mesh elements.
        :rtype: Iterator
        ..note:: helps support programs that don't utilize zero-based arrays.
        """

        return enumerate(elements, start=self.array_index_type)

    @abc.abstractmethod
    def num_vertices(self) -> int:
        """
        Returns the number of vertices in this mesh.

        :return: number of vertices.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def num_edges(self) -> int:
        """
        Returns the number of edges in this mesh.

        :return: number of edges.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def num_faces(self) -> int:
        """
        Returns the number of faces in this mesh.

        :return: number of faces.
        :rtype: int
        """

        pass

    def num_face_vertex_indices(self, *indices: int | list[int]) -> int:
        """
        Returns the number of face-vertex indices.

        :param int or list[int] indices: indices to loop.
        :return: umber of face-vertex indices.
        :rtype: int
        """

        return sum([len(face_vertex_indices) for face_vertex_indices in self.iterate_face_vertex_indices(*indices)])

    def num_triangles(self) -> int:
        """
        Returns the number of triangles in this mesh.

        :return: number of triangles.
        :rtype: int
        """

        return sum(len(x) * 3 for x in self.iterate_face_triangle_indices())

    @abc.abstractmethod
    def selected_vertices(self) -> list[int]:
        """
        Returns list of selected vertex indices.

        :return: selected vertex indices.
        :rtype: list[int]
        """

        pass

    @abc.abstractmethod
    def selected_edges(self) -> list[int]:
        """
        Returns list of selected edge indices.

        :return: selected edge indices.
        :rtype: list[int]
        """

        pass

    @abc.abstractmethod
    def selected_faces(self) -> list[int]:
        """
        Returns list of selected face indices.

        :return: selected face indices.
        :rtype: list[int]
        """

        pass

    @abc.abstractmethod
    def iterate_vertices(
            self, *indices: int | list[int], cls: type = vector.Vector,
            world_space: bool = False) -> Iterator[vector.Vector]:
        """
        Returns a generator that yields vertex points.

        :param int | list[int] indices: optional indices to iterate. If not given, all vertex points will be yielded.
        :param type cls: vector class to use to yield result with.
        :param bool world_space: whether to return vertices position in object or world space.
        :return: iterated vertex points.
        :rtype: Iterator[vector.Vector]
        """

        pass

    def vertices(
            self, *indices: int | list[int], cls: type = vector.Vector,
            world_space: bool = False) -> list[vector.Vector]:
        """
        Returns a list of vertex points.

        :param int | list[int] indices: optional indices to iterate.
        :param type cls: vector class to use to yield result with.
        :param bool world_space: whether to return vertices position in object or world space.
        :return: vertex points.
        :rtype: Iterator[vector.Vector]
        """

        return list(self.iterate_vertices(*indices, cls=cls, world_space=world_space))

    @abc.abstractmethod
    def iterate_vertex_normals(self, *indices: int | list[int], cls: type = vector.Vector) -> Iterator[vector.Vector]:
        """
        Returns a generator that yields vertex normals.

        :param int | list[int] indices: optional indices to iterate. If not given, all vertex normals will be yielded.
        :param type cls: vector class to use to yield result with.
        :return: iterated vertex normals.
        :rtype: Iterator[vector.Vector]
        """

        pass

    def vertex_normals(self, *indices: int | list[int], cls: type = vector.Vector) -> list[vector.Vector]:
        """
        Returns a list vertex normals.

        :param int | list[int] indices: optional indices to iterate.
        :param type cls: vector class to use to yield result with.
        :return: vertex normals.
        :rtype: list[vector.Vector]
        """

        return list(self.iterate_vertex_normals(*indices, cls=cls))

    @abc.abstractmethod
    def has_edge_smoothings(self) -> bool:
        """
        Returns whether this mesh uses edge smooth.

        :return: True if mesh uses edge smooth; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def iterate_edge_smoothings(self, *indices: int | list[int]) -> Iterator[bool]:
        """
        Returns a generator that yields edge smoothings for the given indices.

        :param int | list[int] indices: optional indices to iterate. If not given, all edge smoothings will be yielded.
        :return: iterated edge smoothings.
        :rtype: Iterator[bool]
        """

        pass

    def edge_smoothings(self, *indices: int | list[int]) -> list[bool]:
        """
        Returns a list of edge smoothings for the given indices.

        :param int | list[int] indices: optional indices to iterate. If not given, all edge smoothings will be yielded.
        :return: edge smoothings.
        :rtype: list[bool]
        """

        return list(self.iterate_edge_smoothings(*indices))

    @abc.abstractmethod
    def has_smoothing_groups(self) -> bool:
        """
        Returns whether this mesh uses smoothing groups.

        :return: True if mesh uses smoothing groups; False otherwise.
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def num_smoothing_groups(self) -> int:
        """
        Returns the number of smoothing groups currently in use by this mesh.

        :return: number of smoothing groups currently in use by this mesh.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def iterate_smoothing_groups(self, *indices: int | list[int]) -> Iterator[int]:
        """
        Returns a generator that yields face smoothing groups for the given indices.

        :param int | list[int] indices: optional indices to iterate. If not given, all faces will be yielded.
        :return: iterated smoothing groups.
        :rtype: Iterator[int]
        """

        pass

    def smoothing_groups(self, *indices: int | list[int]) -> list[int]:
        """
        Returns a list of face smoothing groups for the given indices.

        :param int | list[int] indices: optional indices to iterate.
        :return: face smoothing groups.
        :rtype: list[int]
        """

        return list(self.iterate_smoothing_groups(*indices))
