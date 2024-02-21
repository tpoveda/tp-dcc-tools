from __future__ import annotations

from typing import Iterator

from overrides import override

import maya.api.OpenMaya as OpenMaya

from tp.dcc import node
from tp.dcc.abstract import mesh
from tp.dcc.dataclasses import vector
from tp.maya.om import dagpath, transform


class MayaMesh(node.FnNode, mesh.AbstractMesh):
    """
    Overload of mesh.AbstractMesh used to interface with meshes in Maya.
    """

    __slots__ = ()

    @override(check_signature=False)
    def set_object(self, obj: str | OpenMaya.MObject | OpenMaya.MDagPath):
        """
        Assigns given DCC native object to this context class for manipulation.

        :param str or OpenMaya.MObject or OpenMaya.MDagPath obj: object to set.
        """

        obj = dagpath.mobject(obj)
        if obj.hasFn(OpenMaya.MFn.kTransform):
            obj = OpenMaya.MDagPath.getAPathTo(obj).extendToShape().node()

        super(mesh.AbstractMesh, self).set_object(obj)

    def object_matrix(self) -> OpenMaya.MMatrix:
        """
        Returns the object matrix for this mesh.

        :return: mesh object matrix.
        :rtype: OpenMaya.MMatrix
        """

        obj = self.object()
        if obj.hasFn(OpenMaya.MFn.kDagNode):
            return transform.world_matrix(obj)

        return OpenMaya.MMatrix()

    def component(self) -> OpenMaya.MObject:
        """
        Returns the selected component from this mesh.

        :return: selected component.
        :rtype: OpenMaya.MObject
        """

        obj = self.object()
        components = [
            component for (dagPath, component) in dagpath.iterate_active_component_selection() if dagPath.node() == obj]
        num_components = len(components)
        return components[0] if num_components else OpenMaya.MObject.kNullObj

    @override
    def num_vertices(self) -> int:
        """
        Returns the number of vertices in this mesh.

        :return: number of vertices.
        :rtype: int
        """

        return OpenMaya.MFnMesh(self.object()).numVertices

    @override
    def num_edges(self) -> int:
        """
        Returns the number of edges in this mesh.

        :return: number of edges.
        :rtype: int
        """

        return OpenMaya.MFnMesh(self.object()).numEdges

    @override
    def num_faces(self) -> int:
        """
        Returns the number of faces in this mesh.

        :return: number of faces.
        :rtype: int
        """

        return OpenMaya.MFnMesh(self.object()).numPolygons

    @override
    def selected_vertices(self) -> list[int]:
        """
        Returns list of selected vertex indices.

        :return: selected vertex indices.
        :rtype: list[int]
        """

        component = self.component()
        elements = OpenMaya.MFnSingleIndexedComponent(component).getElements()
        if component.hasFn(OpenMaya.MFn.kMeshVertComponent):
            return elements
        elif component.hasFn(OpenMaya.MFn.kMeshEdgeComponent):
            return self.connected_vertices(*elements, component_type=self.ComponentType.Edge)
        elif component.hasFn(OpenMaya.MFn.kMeshPolygonComponent):
            return self.connected_vertices(*elements, component_type=self.ComponentType.Face)

        return []

    @override
    def selected_edges(self) -> list[int]:
        """
        Returns list of selected edge indices.

        :return: selected edge indices.
        :rtype: list[int]
        """

        component = self.component()
        elements = OpenMaya.MFnSingleIndexedComponent(component).getElements()
        if component.hasFn(OpenMaya.MFn.kMeshEdgeComponent):
            return elements
        elif component.hasFn(OpenMaya.MFn.kMeshVertComponent):
            return self.connected_edges(*elements, component_type=self.ComponentType.Vertex)
        elif component.hasFn(OpenMaya.MFn.kMeshPolygonComponent):
            return self.connected_edges(*elements, component_type=self.ComponentType.Face)

        return []

    @override
    def selected_faces(self) -> list[int]:
        """
        Returns list of selected face indices.

        :return: selected face indices.
        :rtype: list[int]
        """

        component = self.component()
        elements = OpenMaya.MFnSingleIndexedComponent(component).getElements()
        if component.hasFn(OpenMaya.MFn.kMeshPolygonComponent):
            return elements
        elif component.hasFn(OpenMaya.MFn.kMeshVertComponent):
            return self.connected_faces(*elements, componentType=self.ComponentType.Vertex)
        elif component.hasFn(OpenMaya.MFn.kMeshEdgeComponent):
            return self.connected_faces(*elements, componentType=self.ComponentType.Edge)

        return []

    @override
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

        num_indices = len(indices)
        if num_indices == 0:
            indices = range(self.num_vertices())

        # Iterate through vertices.
        iter_vertices = OpenMaya.MItMeshVertex(self.object())
        object_matrix = self.object_matrix()
        for index in indices:
            iter_vertices.setIndex(index)
            point = iter_vertices.position()
            if world_space:
                point = point * object_matrix
            yield cls(point.x, point.y, point.z)

    @override
    def iterate_vertex_normals(self, *indices: int | list[int], cls: type = vector.Vector) -> Iterator[vector.Vector]:
        """
        Returns a generator that yields vertex normals.

        :param int | list[int] indices: optional indices to iterate. If not given, all vertex normals will be yielded.
        :param type cls: vector class to use to yield result with.
        :return: iterated vertex normals.
        :rtype: Iterator[vector.Vector]
        """

        num_indices = len(indices)
        if num_indices == 0:
            indices = range(self.numVertices())

        # Iterate through vertices.
        iter_vertices = OpenMaya.MItMeshVertex(self.object())
        for index in indices:
            iter_vertices.setIndex(index)
            normal = iter_vertices.getNormal()
            yield cls(normal.x, normal.y, normal.z)

    @override
    def has_edge_smoothings(self) -> bool:
        """
        Returns whether this mesh uses edge smooth.

        :return: True if mesh uses edge smooth; False otherwise.
        :rtype: bool
        """

        return True

    @override
    def iterate_edge_smoothings(self, *indices: int | list[int]) -> Iterator[bool]:
        """
        Returns a generator that yields edge smoothings for the given indices.

        :param int | list[int] indices: optional indices to iterate. If not given, all edge smoothings will be yielded.
        :return: iterated edge smoothings.
        :rtype: Iterator[bool]
        """

        num_indices = len(indices)
        if num_indices == 0:
            indices = range(self.numEdges())

        # Iterate through edges.
        iter_edges = OpenMaya.MItMeshEdge(self.object())
        for index in indices:
            iter_edges.setIndex(index)
            yield iter_edges.isSmooth

    @override
    def has_smoothing_groups(self) -> bool:
        """
        Returns whether this mesh uses smoothing groups.

        :return: True if mesh uses smoothing groups; False otherwise.
        :rtype: bool
        """

        return False

    @override
    def num_smoothing_groups(self) -> int:
        """
        Returns the number of smoothing groups currently in use by this mesh.

        :return: number of smoothing groups currently in use by this mesh.
        :rtype: int
        """

        return 0

    @override
    def iterate_smoothing_groups(self, *indices: int | list[int]) -> Iterator[int]:
        """
        Returns a generator that yields face smoothing groups for the given indices.

        :param int | list[int] indices: optional indices to iterate. If not given, all faces will be yielded.
        :return: iterated smoothing groups.
        :rtype: Iterator[int]
        """

        return iter([])
