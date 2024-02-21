from tp.core import dcc

from tp.common.nodegraph.api import (
    dt, DataType, DATA_TYPES_REGISTER, function_from_signature, NodeGraph, InputSocket, OutputSocket, NoddleNode
)

if dcc.is_maya():
    from tp.tools.rig.noddle.builder.controllers.maya.nodes.node_component import ComponentNode, AnimComponentNode
