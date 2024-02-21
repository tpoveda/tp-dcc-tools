from __future__ import annotations

import typing

from tp.maya import api

from tp.core import command

if typing.TYPE_CHECKING:
    from tp.maya.meta.planeorient import PlaneOrientMeta


def orient_nodes(
        nodes: list[api.DagNode], primary_axis: api.OpenMaya.MVector, secondary_axis: api.OpenMaya.MVector,
        world_up_axis: api.OpenMaya.MVector, skip_end: bool = True):
    """
    Orients each one of the given nodes to the next in the list.

    :param list[api.DagNode] nodes: list of nodes from parent to child.
    :param api.OpenMaya.MVector primary_axis: primary (aim) axis for each node.
    :param api.OpenMaya.MVector secondary_axis: secondary (up) axis for each node.
    :param api.OpenMaya.MVector world_up_axis: world up axis to align all nodes.
    :param api.OpenMaya.MVector skip_end: whether the last node should be aligned.
    """

    return command.execute('tp.maya.nodes.orient', **locals())


def create_plane_orient() -> PlaneOrientMeta:
    """
    Creates a new plane orient meta node instance.

    :return: newly created plane orient meta node instance.
    :rtype: PlaneOrientMeta
    """

    return command.execute('tp.maya.planeOrient.create')


def plane_orient_align(meta_node: PlaneOrientMeta, skip_end: bool = False) -> bool:
    """
    Aligns the given plane orient meta node to the closest plane which is attached to the given meta node.

    :param PlaneOrientMeta meta_node: optional plane orient meta node instance to align.
    :param bool skip_end: whether to skip the orient of the last joint in the chain.
    :return: True if plane orient was oriented successfully; False otherwise.
    :rtype: bool
    """

    return command.execute('tp.maya.planeOrient.orient', **locals())
