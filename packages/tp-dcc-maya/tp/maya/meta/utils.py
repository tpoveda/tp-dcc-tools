from __future__ import annotations

import maya.cmds as cmds

from tp.common.python import helpers
from tp.maya import api
from tp.maya.meta import base

AFFECTED_BY_ATTR_NAME = 'affectedBy'


def is_in_network(node: api.DGNode):
    """
    Returns whether a given object is connected to the meta node graph.

    :param base.DGNode node: node to check.
    :return: True if given node is connected to a meta node graph; False otherwise.
    :rtype: bool
    """

    return True if node.hasAttribute(AFFECTED_BY_ATTR_NAME) else False


def network_entries(node: api.DGNode | api.DagNode, in_network_type: type | None = None):
    """
    Returns all network nodes that are connected to given node.

    :param base.DGNode node: node to query.
    :param type or None in_network_type: optional filter to find the network node that connects backwards to the given
        type.
    :return: list of all meta node instances connected to given node.
    :rtype: list(MetaProperty)
    """

    entry_network_list = []
    if not is_in_network(node):
        return entry_network_list

    for network_node in cmds.listConnections('{}.message'.format(node.fullPathName()), type='network'):
        network_entry = base.create_meta_node_from_node(api.node_by_name(network_node))
        if in_network_type:
            network_entry = network_entry.downstream(in_network_type)
        if network_entry:
            entry_network_list.append(network_entry)

    return entry_network_list


def first_network_entry(node: api.DGNode | api.DagNode, in_network_type: type | None = None):
    """
    Returns the first network node connected to the given node.

    :param base.DGNode node: node to query.
    :param type or None in_network_type: optional filter to find the network node that connects backwards to the given
        type.
    :return: meta node instance connected to given node.
    :rtype: MetaProperty
    """

    return helpers.first_in_list(network_entries(node, in_network_type=in_network_type))


def network_chain(network_node: api.DGNode) -> list[api.DGNode]:
    """
    Recursive function that finds all network nodes connected upstream from the given network node.

    :param api.DGNode network_node: node to get chain from.
    :return: list of upstream network nodes.
    :rtype: list[api.DGNode]
    """

    def _network_chain(_node: api.DGNode) -> list[api.DGNode]:
        if _node.typeName == 'network':
            found_nodes.append(_node)
        for _, plug in _node.iterateConnections(source=False, destination=True):
            _network_chain(plug.node())

    found_nodes: list[api.DGNode] = []
    _network_chain(network_node)
    return found_nodes


def delete_network(network_node: api.DGNode, delete_root_node: bool = True):
    """
    Deletes all networks nodes upstream (inclusive) from the given network node.

    :param api.DGNode network_node: network node to delete from.
    :param bool delete_root_node: whether root node should be deleted.
    """

    network_nodes = network_chain(network_node)
    if not delete_root_node:
        network_nodes = network_nodes[1:]
    [n.delete() for n in network_nodes if n.exists()]
