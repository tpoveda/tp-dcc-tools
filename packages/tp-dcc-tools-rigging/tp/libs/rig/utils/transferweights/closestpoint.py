from __future__ import annotations

import typing
from itertools import chain

from overrides import override
from scipy.spatial import cKDTree

from tp.core import log
from tp.dcc.dataclasses import vector
from tp.libs.rig.utils.transferweights import abstracttransfer

if typing.TYPE_CHECKING:
    from tp.dcc.skin import Skin

logger = log.rigLogger


class ClosestPoint(abstracttransfer.AbstractTransfer):
    """
    Overload of AbstractTransfer that transfer weights by closes point.
    """

    __slots__ = ('_vertex_points', '_point_tree')
    __title__ = 'Closest Point'

    def __init__(self, *args):
        super().__init__(*args)

        self._vertex_points = self._skin.control_points(*self._vertex_indices)
        self._point_tree = cKDTree(self._vertex_points)

    @property
    def vertex_points(self) -> list[vector.Vector]:
        """
        Getter method that returns the vertex points.

        :return: list of vertex points.
        :rtype: list[vector.Vector]
        """

        return self._vertex_points

    @property
    def point_tree(self) -> cKDTree:
        """
        Getter method that returns the point tree.

        :return: point tree.
        :rtype: cKDTree
        """

        return self._point_tree

    @override
    def transfer(self, other_skin: Skin, vertex_indices: list[int]):
        """
        Transfers the weights from this skin to the given one.

        :param  Skin other_skin: skin to transfer weights to.
        :param list[int] vertex_indices: vertex indices to transfer skin weights for.
        """

        # Get the closest points from the point tree.
        vertex_points = other_skin.control_points(*vertex_indices)
        distances, closest_indices = self._point_tree.query(vertex_points)

        # Get associated vertex weights.
        # Remember we have to convert our local indices back to global!
        closest_vertex_indices = [self.vertex_map[x] for x in closest_indices]
        closest_vertices = self.skin.vertex_weights(*closest_vertex_indices)

        updates = {
            vertex_index: closest_vertices[closestVertexIndex] for (vertex_index, closestVertexIndex) in zip(
                vertex_indices, closest_vertex_indices)}

        # Remap source weights to target.
        influence_ids = set(chain(*[list(x.keys()) for x in updates.values()]))
        influence_map = self.skin.create_influence_map(other_skin, influence_ids=influence_ids)

        updates = self.skin.remap_vertex_weights(updates, influence_map)
        other_skin.apply_vertex_weights(updates)

        logger.info('Finished transferring weights via closest point!')
