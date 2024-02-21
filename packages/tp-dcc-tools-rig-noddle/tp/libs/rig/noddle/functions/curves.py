from __future__ import annotations

from typing import List

import maya.cmds as cmds

from tp.maya import api


def curve_from_points(
        name: str, degree: int = 1, points: List[List[float, float, float], ...] | None = None,
        parent: api.DagNode | None = None) -> api.DagNode:
    """
    Creates a new curve from the given points in the world.

    :param str name:
    :param int degree:
    :param List[List[float, float, float], ...] or None points:
    :param api.DagNode or None parent:
    :return: newly created curve.
    :rtype: api.DagNode
    """

    points = points or []
    knot_len = len(points) + degree - 1
    knot_vecs = [v for v in range(knot_len)]
    new_curve = cmds.curve(n=name, p=points, d=1, k=knot_vecs)
    if degree != 1:
        cmds.rebuildCurve(new_curve, d=degree, ch=False)
    new_curve = api.node_by_name(new_curve)
    if parent is not None:
        new_curve.setParent(parent)

    return new_curve
