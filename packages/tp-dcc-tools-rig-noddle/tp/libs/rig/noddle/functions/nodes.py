from __future__ import annotations

from typing import Tuple, List, Dict

import maya.cmds as cmds

from tp.maya import api
from tp.libs.rig.noddle.functions import naming


def create(
        node_type: str, name: str | List[str], side: str, suffix: str | None = None, override_index: int | None = None,
        *args, **kwargs) -> api.DGNode | api.DagNode | api.Joint:
    """
    Creates a new node of given type.

    :param str node_type: type of the node to create.
    :param str or List[str] name: name of the node to create.
    :param str side: side of the node name to create.
    :param str suffix: optional suffix of the node name to create.
    :param int or None override_index: optional override index.
    :param Tuple args: tuple of positional arguments.
    :return: newly created node instance.
    :rtype: api.DGNode or api.DagNode or api.Joint
    """

    node = cmds.createNode(
        node_type, n=naming.generate_name(name, side, suffix, override_index=override_index), *args, **kwargs)

    return api.node_by_name(node)
