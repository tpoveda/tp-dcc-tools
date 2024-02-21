from __future__ import annotations

import maya.cmds as cmds

MAYA_TRANSLATE_ATTRS = ['translateX', 'translateY', 'translateZ']
MAYA_ROTATE_ATTRS = ['rotateX', 'rotateY', 'rotateZ']
MAYA_SCALE_ATTRS = ['scaleX', 'scaleY', 'scaleZ']
MAYA_TRANSFORM_ATTRS = MAYA_TRANSLATE_ATTRS + MAYA_ROTATE_ATTRS + MAYA_SCALE_ATTRS


def reset_transform_attributes(
		node_name: str, translate: bool = True, rotate: bool = True, scale: bool = True, visibility: bool = False):
	"""
	Resets teh transforms of the given node name.

	:param str node_name: name of the node whose transform attributes we want to reset.
	:param bool translate: whether to reset translate transform attributes.
	:param bool rotate: whether to reset rotate transform attributes.
	:param bool scale: whether to reset scale transform attributes.
	:param bool visibility: whether to reset visibility attribute.
	"""

	if translate:
		cmds.setAttr(f'{node_name}.translate', 0.0, 0.0, 0.0)
	if rotate:
		cmds.setAttr(f'{node_name}.rotate', 0.0, 0.0, 0.0)
	if scale:
		cmds.setAttr(f'{node_name}.scale', 1.0, 1.0, 1.0)
	if visibility:
		cmds.setAttr(f'{node_name}.visibility', 1.0)


def transform_is_zeroed(node_name: str) -> bool:
	"""
	Returns whether the `translate` and `rotate` attributes are zeroed out and `scale` values are set to 1.0.

	:param str node_name: Maya transform name to check.
	:return: True if `translate` and `rotate` attributes are zeroed out and `scale` values are set to 1.0.
	:rtype: bool
	"""

	zeroed = True
	if cmds.getAttr(f'{node_name}.translate')[0] != (0.0, 0.0, 0.0):
		zeroed = False
	if cmds.getAttr(f'{node_name}.rotate')[0] != (0.0, 0.0, 0.0):
		zeroed = False
	if cmds.getAttr(f'{node_name}.scale')[0] != (1.0, 1.0, 1.0):
		zeroed = False

	return zeroed


def locked_connected_attributes(
		node: str, attributes: list[str] | None = None, keyframes: bool = False,
		constraints: bool = False) -> list[str]:
	"""
	Retrieves all locked or connected attributes from the given list of nodes.

	:param str node: Maya node full path names.
	:param list[str] or None attributes: list of attributes to check. If not given, all keyable attributes will be
		checked.
	:param bool keyframes: whether to check for keyframes.
	:param bool constraints: whether to check for constraints.
	:return: list with all the attributes locked or connected.
	:rtype: list[str]
	"""

	locked_connected_attrs: list[str] = []

	attributes = attributes or cmds.listAttr(node, keyable=True)
	for attr in attributes:
		node_attr = '.'.join((node, attr))
		if not cmds.getAttr(node_attr, settable=True):
			locked_connected_attrs.append(node_attr)
		if keyframes and cmds.keyframe(node, attribute=attr, selected=False, query=True):
			locked_connected_attrs.append(node_attr)

	if constraints:
		for attr in attributes:
			node_attr = '.'.join((node, attr))
			if cmds.listConnections(node_attr, type='constraint'):
				locked_connected_attrs.append(node_attr)

	return locked_connected_attrs


def locked_connected_attributes_for_nodes(
		nodes: list[str], attributes: list[str] | None = None, keyframes: bool = False, constraints: bool = False):
	"""
	Retrieves all locked or connected attributes from the given list of nodes.

	:param list[str] nodes: list of Maya node full path names.
	:param list[str] or None attributes: list of attributes to check. If not given, all keyable attributes will be
		checked.
	:param bool keyframes: whether to check for keyframes.
	:param bool constraints: whether to check for constraints.
	:return: a tuple containing the list of nodes with locked or connected attributes and also all the attributes locked
		or connected.
	"""

	locked_nodes: list[str] = []
	locked_attributes: list[str] = []

	for node in nodes:
		locked_connected_attrs = locked_connected_attributes(
			node, attributes=attributes, keyframes=keyframes, constraints=constraints)
		if locked_connected_attrs:
			locked_nodes.append(node)
			locked_attributes.extend(locked_connected_attrs)

	return locked_nodes, locked_attributes


def disconnect_attribute(node_name: str, attribute_name: str) -> bool:
	"""
	Disconnects attribute that belongs to given node.

	:param str node_name: Maya node name.
	:param str attribute_name: attribute name to disconnect.
	:return: True if attribute was disconnected successfully; False otherwise.
	:rtype: bool
	"""

	node_attribute = f'{node_name}.{attribute_name}'
	connected_attributes = cmds.listConnections(node_attribute, plugs=True)
	if not connected_attributes:
		return False

	try:
		cmds.disconnectAttr(connected_attributes[0], node_attribute)
		return True
	except RuntimeError:
		pass

	return False


def unlock_disconnect_attributes(node_name: str, attribute_names: list[str]):
	"""
	Unlocks/Delete keys/Disconnects all given attributes from given node.

	:param str node_name: Maya node name.
	:param list[str] attribute_names: attribute names to disconnect.
	"""

	for attribute_name in attribute_names:
		cmds.setAttr(f'{node_name}.{attribute_name}', lock=False)
		remove_attribute_keys(node_name, attribute_name)
		disconnect_attribute(node_name, attribute_name)


def unlock_disconnect_transform(node_name: str):
	"""
	Unlocks/Deletes keys/Disconnects `translate`, `rotate` and `scale` attributes.

	:param str node_name: Maya node name to unlock and disconnect attributes of.
	"""

	unlock_disconnect_attributes(node_name, MAYA_TRANSFORM_ATTRS)


def remove_attribute_keys(node_name: str, attribute_name: str, time_range: tuple[int, int] = (-10000, 10000)):
	"""
	Deletes all the keys on an attribute within the range.

	:param str node_name: Maya node name.
	:param str attribute_name: Maya attribute name.
	:param tuple[int, int] time_range: time range.
	"""

	if cmds.keyframe(node_name, attribute=attribute_name, selected=False, query=True):
		cmds.cutKey(node_name, time=time_range, attribute=attribute_name)
