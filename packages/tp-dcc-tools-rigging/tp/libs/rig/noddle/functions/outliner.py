from __future__ import annotations

from typing import Iterable

from tp.maya import api
from tp.libs.rig.noddle import consts


def set_color(node: api.DGNode, color: int | str | Iterable[float, float, float]):
    """
    Sets the color of the given node within outliner panel.

    :param api.DGNode node: node to set outliner color of.
    :param int or str | Iterable[float, float, float] color: color to set.
    """

    if isinstance(color, int):
        color = consts.ColorIndex.index_to_rgb(color)
    elif isinstance(color, str):
        color = consts.ColorIndex.index_to_rgb(consts.ColorIndex[color].value)

    node.useOutlinerColor.set(True)
    node.outlinerColor.set(color)
