from __future__ import annotations

import typing
from itertools import chain

from overrides import override

from tp.core import log
from tp.dcc.dataclasses import vector
from tp.libs.rig.utils.transferweights import abstracttransfer

if typing.TYPE_CHECKING:
    from tp.dcc.skin import Skin


logger = log.rigLogger


class InverseDistance(abstracttransfer.AbstractTransfer):
    """
    Overload of AbstractTransfer that transfer weights via inverse distance.
    """

    __slots__ = ('_vertex_points', '_power')
    __title__ = 'Inverse Distance'

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self._vertex_points = self._skin.control_points(*self._vertex_indices)
        self._power = kwargs.get('power', 2.0)

    @property
    def vertex_points(self) -> list[vector.Vector]:
        """
        Getter method that returns the vertex points.

        :return: list of vertex points.
        :rtype: list[vector.Vector]
        """

        return self._vertex_points

    @property
    def power(self) -> float:
        """
        Getter method that returns the distance power.

        :return: distance power.
        :rtype: float
        """

        return self._power

    @override
    def transfer(self, other_skin: Skin, vertex_indices: list[int]):
        """
        Transfers the weights from this skin to the given one.

        :param  Skin other_skin: skin to transfer weights to.
        :param list[int] vertex_indices: vertex indices to transfer skin weights for.
        """

        vertex_points = other_skin.controlPoints(*vertex_indices)
        vertex_weights = self.skin.vertex_weights(*self.vertex_indices)

        updates = {}
        for vertex_index, vertex_point in zip(vertex_indices, vertex_points):
            distances = [vertex_point.distanceBetween(otherPoint) for otherPoint in self.vertex_points]
            updates[vertex_index] = self.skin.inverse_distance_weights(vertex_weights, distances, power=self.power)

        # Remap source weights to target
        influence_ids = set(chain(*[list(x.keys()) for x in updates.values()]))
        influence_map = self.skin.createInfluenceMap(other_skin, influenceIds=influence_ids)

        updates = self.skin.remapVertexWeights(updates, influence_map)
        other_skin.applyVertexWeights(updates)

        logger.info('Finished transferring weights via inverse distance!')
