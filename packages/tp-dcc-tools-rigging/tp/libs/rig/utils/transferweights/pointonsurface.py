from __future__ import annotations

import typing
from itertools import chain

from overrides import override

from tp.core import log
from tp.libs.rig.utils.transferweights import abstracttransfer

if typing.TYPE_CHECKING:
    from tp.dcc.skin import Skin


logger = log.rigLogger


class PointOnSurface(abstracttransfer.AbstractTransfer):
    """
    Overload of AbstractTransfer that transfer weights by closest point on surface.
    """

    __slots__ = ('_face_indices',)
    __title__ = 'Point on Surface'

    def __init__(self, *args):
        super().__init__(*args)

        self._face_indices = set(self.mesh.iterate_connected_faces(
            *self.vertex_indices, component_type=self.mesh.ComponentType.Vertex))

    @property
    def face_indices(self) -> set[int]:
        """
        Getter method that returns the cached face indices.

        :return: list of face indices.
        :rtype: set[int]
        """

        return self._face_indices

    @override
    def transfer(self, other_skin: Skin, vertex_indices: list[int]):
        """
        Transfers the weights from this skin to the given one.

        :param  Skin other_skin: skin to transfer weights to.
        :param list[int] vertex_indices: vertex indices to transfer skin weights for.
        :raises TypeError: if not expected number of vertices found for a face.
        """

        vertex_points = other_skin.controlPoints(*vertex_indices)
        hits = self.mesh.closest_point_on_surface(*vertex_points, dataset=self.face_indices)

        updates = {}
        for vertexIndex, hit in zip(vertex_indices, hits):
            # Evaluate which operation to perform
            num_face_vertices = len(self.mesh.face_vertex_indices(hit.face_index)[0])
            if num_face_vertices == 3:
                updates[vertexIndex] = self.skin.barycentric_weights(hit.triangle_vertex_indices, hit.bary_coords)
            elif num_face_vertices == 4:
                updates[vertexIndex] = self.skin.bilinear_weights(hit.face_vertex_indices, hit.bi_coords)
            else:
                raise TypeError(f'transfer() expects 3-4 vertices per face ({num_face_vertices} found)!')

        # Remap source weights to target
        influence_ids = set(chain(*[list(x.keys()) for x in updates.values()]))
        influence_map = self.skin.create_influence_map(other_skin, influence_ids=influence_ids)
        updates = self.skin.remap_vertex_weights(updates, influence_map)
        other_skin.apply_vertex_weights(updates)

        logger.info('Finished transferring weights via point on surface!')
