from __future__ import annotations

from typing import Callable

from tp.tools.rig.noddle.builder import api

from tp.common.nodegraph.nodes import node_for_each


class ForEachComponent(node_for_each.ForEachNode):
    ID = 105
    DEFAULT_TITLE = "For Each Component"
    COLLECTION_DATA_TYPE = api.DataType.COMPONENT


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
    register_node(ForEachComponent.ID, ForEachComponent)
