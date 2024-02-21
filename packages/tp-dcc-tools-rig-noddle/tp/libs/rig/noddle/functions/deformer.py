from __future__ import annotations

from tp.maya import api
from tp.maya.om import dagpath


def list_deformer_paths(deformer_type: int, under_group: api.DagNode | None = None) -> list[str]:
    """
    List all deformer full paths of given type.

    :param int deformer_type: type of the deformer to retrieve.
    :param api.DagNode or None under_group: optional group to find deformers under. If not given, all deformers within
        scene will be checked.
    :return: list of deformer node full paths.
    :rtype: list[str]
    """

    found_deformers: list[str] = []
    if under_group:
        for child_node in under_group.children():
            for deformer_node in dagpath.iterate_associated_deformers(child_node.object(), api_type=deformer_type):
                deformer_node_path = dagpath.dag_path(deformer_node).fullPathName()
                if deformer_node_path not in found_deformers:
                    found_deformers.append(deformer_node_path)

    return found_deformers
