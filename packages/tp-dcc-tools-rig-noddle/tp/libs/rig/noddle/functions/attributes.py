from __future__ import annotations

from typing import List, Iterable

from tp.maya import api
from tp.maya.meta import base


def lock(
        node: api.DagNode, attribute_names: Iterable[str, ...], channel_box: bool = False,
        key: bool = False) -> List[str]:
    """
    Lock attributes of given node.

    :param api.DagNode node: node whose attributes we watn to lock.
    :param Iterable[str, ...] attribute_names: attribute names to lock.
    :param bool channel_box: whether to remove attributes from channel box.
    :param bool key: whether to set attributes as keyable.
    :return: list of locked attribute names.
    :rtype: List[str]
    """

    locked_attributes = []
    for attr_name in attribute_names:
        attr = node.attribute(attr_name)
        attr.lock(True)
        attr.show() if channel_box else attr.hide()
        attr.setKeyable(key)
        locked_attributes.append(f'.{attr_name}')

    return locked_attributes


def add_divider(node: api.DGNode, attr_name: str = 'divider'):
    """
    Adds a divider attribute into the given node.

    :param api.DGNode node: node to add divider into.
    :param str attr_name: divider attribute name.
    """

    node.addAttribute(
        attr_name, type=api.kMFnkEnumAttribute, enums=['--------------'], channelBox=True, lock=True)


def add_meta_parent_attribute(nodes: List[api.DGNode]):
    """
    Adds meta parent attribute to all given nodes.

    :param List[api.DGNode] nodes: list of nodes to add meta parent attribute to.
    """

    for node in nodes:
        if not node.hasAttribute(base.MPARENT_ATTR_NAME):
            node.addAttribute(base.MPARENT_ATTR_NAME, type=api.kMFnMessageAttribute)
