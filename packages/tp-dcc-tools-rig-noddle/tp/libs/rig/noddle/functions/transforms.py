from __future__ import annotations

from tp.maya import api


def get_vector(
        source: api.DagNode, destination: api.DagNode,
        parent_space: api.OpenMaya.MSpace = api.kWorldSpace) -> api.Vector:
    """
    Returns the vector between the two given nodes.

    :param api.DagNode source:
    :param api.DagNode destination:
    :param api.OpenMaya.MSpace parent_space: space used to retrieve nodes translation.
    :return: vector between given nodes.
    :rtype: api.Vector
    """

    return destination.translation(parent_space) - source.translation(parent_space)
