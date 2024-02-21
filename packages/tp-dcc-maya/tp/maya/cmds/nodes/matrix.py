from __future__ import annotations

import maya.cmds as cmds

from tp.maya.cmds.nodes import attributes

DEFAULT_MATRIX = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def children_by_node_type(node_names: list[str], node_type: str = 'transform') -> list[str]:
    """
    Returns all nodes under the given list of node names in the hierarchy.

    :param list[str] node_names: list of Maya DAG node names to get hierarchy of.
    :param str node_type: node type to filter children by.
    :return: list of nodes including children.
    :rtype: list[str]
    """

    found_nodes: list[str] = []
    for node_name in node_names:
        found_nodes.append(node_name)
        if node_type:
            children = cmds.listRelatives(node_name, allDescendents=True, type=node_type, fullPath=True) or []
        else:
            children = cmds.listRelatives(node_name, allDescendents=True, fullPath=True) or []
        found_nodes.extend(children)

    return list(set(found_nodes))


def has_matrix_offset(transform_name: str) -> bool:
    """
    Returns whether given transform Offset Parent Matrix has been modified at all.

    :param str transform_name: Maya transform node name.
    :return: True if node has an offset; False otherwise.
    :rtype: bool
    """

    if cmds.getAttr(f'{transform_name}.offsetParentMatrix') == DEFAULT_MATRIX:
        return False

    return True


def transform_to_matrix_offset(transform_name: str, unlock_attributes: bool = True):
    """
    Sets the given transform `translate` and `rotate` attributes to be zero and the scale to be one and passes that
    information into the Offset Parent Matrix attribute.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param str transform_name: Maya transform node name.
    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    """

    # If transform is already zeroed out.
    if attributes.transform_is_zeroed(transform_name):
        return

    if unlock_attributes:
        attributes.unlock_disconnect_transform(transform_name)

    # If transform Offset Parent Matrix has been modified we move its values to transform attributes, and reset
    # transform Offset Parent Matrix.
    if has_matrix_offset(transform_name):
        matrix_transform = cmds.xform(transform_name, query=True, matrix=True, worldSpace=True)
        cmds.setAttr(f'{transform_name}.offsetParentMatrix', DEFAULT_MATRIX, type='matrix')
        cmds.xform(transform_name, matrix=matrix_transform, worldSpace=True)

    # Move transform to Offset Parent Matrix and reset transform attributes.
    matrix_transform = cmds.xform(transform_name, query=True, matrix=True, worldSpace=False)
    attributes.reset_transform_attributes(transform_name)
    cmds.setAttr(f'{transform_name}.offsetParentMatrix', matrix_transform, type='matrix')

    # In joints, we also need to zero out joint orient attribute.
    if cmds.objectType(transform_name) == 'joint':
        cmds.setAttr(f'{transform_name}.jointOrient', 0.0, 0.0, 0.0, type='float3')


def transforms_to_matrix_offset(transform_names: list[str], unlock_attributes: bool = True):
    """
    Sets the current selected transforms `translate` and `rotate` attributes to be zero and the scale to be one and
    passes that information into the Offset Parent Matrix attribute.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param list[str] transform_names: Maya DAG node names.
    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    """

    for transform_name in transform_names:
        transform_to_matrix_offset(transform_name, unlock_attributes=unlock_attributes)


def selected_transforms_to_matrix_offset(
        unlock_attributes: bool = True, children: bool = False, node_type: str = None):
    """
    Sets the current selected transforms `translate` and `rotate` attributes to be zero and the scale to be one and
    passes that information into the Offset Parent Matrix attribute.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    :param bool children: whether to reset the children of the selected transforms.
    :param str or None node_type: if given, only children of given types will be reset.
    """

    selected_transforms = cmds.ls(selection=True, type='transform')
    if not selected_transforms:
        return
    if children:
        selected_transforms = children_by_node_type(selected_transforms, node_type=node_type)

    transforms_to_matrix_offset(selected_transforms, unlock_attributes=unlock_attributes)


def reset_transform_matrix_offset(transform_name: str, unlock_attributes: bool = True):
    """
    Resets/Zeroes out the Offset Parent Matrix of the given transform nodes.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param str transform_name: Maya DAG node name.
    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    """

    if not has_matrix_offset(transform_name):
        return

    if unlock_attributes:
        attributes.unlock_disconnect_transform(transform_name)

    matrix_transform = cmds.xform(transform_name, query=True, matrix=True, worldSpace=True)
    cmds.setAttr(f'{transform_name}.offsetParentMatrix', DEFAULT_MATRIX, type='matrix')
    cmds.xform(transform_name, matrix=matrix_transform, worldSpace=True)


def reset_transforms_matrix_offset(transform_names: list[str], unlock_attributes: bool = True):
    """
    Resets/Zeroes out the Offset Parent Matrix of the given transform nodes.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param list[str] transform_names: Maya DAG node names.
    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    """

    for transform_name in transform_names:
        reset_transform_matrix_offset(transform_name)


def reset_selected_transforms_matrix_offset(
        unlock_attributes: bool = True, children: bool = False, node_type: str | None = None):
    """
    Resets/Zeroes out the Offset Parent Matrix of the selected transform nodes.
    By doing this, the position/rotation/scale of the current selected transforms are zeroed out but the transform
    will maintain its position/rotation/scale.

    :param bool unlock_attributes: whether tu unlock/delete keys/disconnect any connected transform attributes.
    :param bool children: whether to reset the children of the selected transforms.
    :param str or None node_type: if given, only children of given types will be reset.
    """

    selected_transforms = cmds.ls(selection=True, type='transform')
    if not selected_transforms:
        return
    if children:
        selected_transforms = children_by_node_type(selected_transforms, node_type=node_type)

    reset_transforms_matrix_offset(selected_transforms, unlock_attributes=unlock_attributes)
