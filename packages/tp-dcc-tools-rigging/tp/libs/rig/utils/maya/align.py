from __future__ import annotations

import math
from typing import List, Iterator

from tp.maya import api
from tp.maya.om import mathlib


def construct_plane_from_positions(
		position_vectors: List[api.OpenMaya.MVector, api.OpenMaya.MVector, api.OpenMaya.MVector],
		nodes: List[api.DagNode, ...], rotate_axis: api.OpenMaya.MVector = mathlib.Z_AXIS_VECTOR) -> api.OpenMaya.MPlane:
	"""
	Constructs a plane instance based on the averaged normal of the given node rotations.

	:param  List[api.OpenMaya.MVector, api.OpenMaya.MVector, api.OpenMaya.MVector] position_vectors: list with two or
		three vectors or more defining normals.
	:param List[api.DagNode, ...] nodes: list of nodes which will have their rotations taken into account when creating
		the plane to get the best normal direction.
	:param api.OpenMaya.MVector rotate_axis: rotation axis to use.
	:return: newly created plane.
	:rtype: api.OpenMaya.MPlane
	"""

	plane_a = api.OpenMaya.MPlane()
	normal = api.OpenMaya.MVector(api.OpenMaya.MVector.kXaxisVector)
	if len(position_vectors) == 3:
		normal = mathlib.three_point_normal(*position_vectors)
	elif len(position_vectors) > 3:
		average_position = api.average_position(nodes)
		normal = mathlib.three_point_normal(
			nodes[0].translation(space=api.kWorldSpace), average_position, nodes[-1].translation(space=api.kWorldSpace))
	else:
		for i in range(len(position_vectors)):
			current = api.Vector(position_vectors[i][0], position_vectors[i][1], position_vectors[i][2])
			prev = api.Vector(position_vectors[i - 1][0], position_vectors[i - 1][1], position_vectors[i - 1][2])
			normal += api.Vector(
				(prev.z + current.z) * (prev.y - current.y),
				(prev.x + current.x) * (prev.z - current.z),
				(prev.y + current.y) * (prev.x - current.x),
			)
		normal.normalize()

	average_normal = api.average_normal_vector(nodes, rotate_axis)
	if normal * average_normal < 0:
		normal *= -1

	plane_a.setPlane(normal, -normal * position_vectors[0])

	return plane_a


def align_nodes_iterator(
		nodes: List[api.DagNode], plane: api.OpenMaya.MPlane,
		skip_end: bool = True) -> Iterator[api.DagNode, api.DagNode]:
	"""
	Generator function that iterates over each node, protect its position in the world and returns eac node, and it's
	target.

	This function will handle setting translations while compensating for hierarchy state.

	:param List[api.DagNode] nodes: list of nodes to align.
	:param api.OpenMaya.MPlane plane: plane wher each node will be protected on.
	:param bool skip_end: whether to skip end node.
	:return: iterated nodes as a tuple with the node to set aligment as first element and the target node as the second
		element.
	:rtype: Iterator[api.DagNode, api.DagNode]
	"""

	node_array = nodes[:-1] if skip_end else nodes
	child_map = {}
	change_map = []
	last_index = len(node_array) - 1

	# un-parent all children so we can change the positions and orientations
	for current_node in reversed(node_array):
		children = current_node.children((api.kNodeTypes.kTransform, api.kNodeTypes.kJoint))
		child_map[current_node] = children
		for child in children:
			child.setParent(None)

	# update all positions and orientations
	for i, current_node in enumerate(node_array):
		translation = current_node.translation(space=api.kWorldSpace)
		if i == last_index:
			target_node = nodes[i + 1] if skip_end else None
			new_translation = translation if skip_end else mathlib.closest_point_on_plane(translation, plane)
		else:
			target_node = nodes[i + 1]
			new_translation = mathlib.closest_point_on_plane(translation, plane)
		current_node.setTranslation(new_translation, space=api.kWorldSpace)
		change_map.append((current_node, target_node, new_translation))

	# now yield, so client can run any code before re-parenting the nodes
	for current_node, target_node, new_translation in change_map:
		yield current_node, target_node
		for child in child_map[current_node]:
			child.setParent(current_node)


def orient_nodes_iterator(nodes: list[api.DagNode]) -> Iterator[tuple[api.DagNode, api.DagNode]]:
	"""
	Generator function that yields tuples with each node and its target.

	:param list[api.DagNode] nodes: list of nodes to orient.
	:return: iterated nodes.
	:rtype: Iterator[tuple[api.DagNode, api.DagNode]]
	"""

	child_map: dict[api.DagNode, list[api.DagNode]] = {}
	change_map: list[tuple[api.DagNode, api.DagNode]] = []

	# First we un-parent all children, so we can change the positions and orientations.
	for i, current_node in enumerate(reversed(nodes)):
		children = current_node.children((api.kNodeTypes.kTransform, api.kNodeTypes.kJoint))
		child_map[current_node] = children
		for child in children:
			child.setParent(None)

	# Retrieve the target node for each of the nodes.
	last_index = len(nodes) - 1
	for i, current_node in enumerate(nodes):
		if not child_map[current_node] or i == last_index:
			target_node = None
		else:
			target_node = nodes[i + 1]
		change_map.append((current_node, target_node))

	for current_node, target_node in change_map:

		# Yield, so we can update positions and orientations.
		yield current_node, target_node

		# After transforming the nodes, we re-parent back together.
		for child in child_map[current_node]:
			child.setParent(current_node)


def orient_nodes(
		nodes: list[api.DagNode], primary_axis: api.Vector, secondary_axis: api.Vector,
		world_up_axis: api.Vector, skip_end: bool = True):

	joints: list[api.DagNode] = []

	# Iterator automatically handles the un-parenting and re-parenting of the joints.
	for current_node, target_node in orient_nodes_iterator(nodes):

		if skip_end and target_node is None:
			continue

		# When orienting joints whe need to make sure to reset joint orient to zero.
		if current_node.hasFn(api.kNodeTypes.kJoint):
			current_node.setRotation(api.EulerRotation(), api.kTransformSpace)
			current_node.attribute('jointOrient').set(api.Vector())
			current_node.attribute('rotateAxis').set(api.Vector())
			current_node.setScale(api.Vector(1.0, 1.0, 1.0))

		if target_node is None:
			current_node.resetTransform(translate=False, rotate=True, scale=False)
			continue

		rotation = mathlib.look_at(
			current_node.translation(space=api.kWorldSpace),
			target_node.translation(space=api.kWorldSpace),
			aim_vector=primary_axis, up_vector=secondary_axis, world_up_vector=world_up_axis)

		if current_node.hasFn(api.kNodeTypes.kJoint):
			current_node.setRotation(rotation, space=api.kWorldSpace)
			joints.append(current_node)
		else:
			current_node.setRotation(rotation, space=api.kWorldSpace)


def world_axis_to_rotation(
		axis: int, invert: bool = False, rotation_order: int = api.consts.kRotateOrder_XYZ) -> api.EulerRotation:
	"""
	From given world axis, returns the world rotation to align to that axis.

	:param int axis: axis index to align to.
	:param bool invert: whether to invert the rotation.
	:param int rotation_order: rotation order to use.
	:return: world rotation to align to the axis.
	:rtype: api.EulerRotation
	"""

	normal_direction = api.Vector()
	degree_90 = math.pi * 0.5
	if axis == mathlib.X_AXIS_INDEX:
		normal_direction[2] = -degree_90 if not invert else degree_90
	elif axis == mathlib.Y_AXIS_INDEX and invert:
		normal_direction[0] = math.pi
	elif axis == mathlib.Z_AXIS_INDEX:
		normal_direction[0] = degree_90 if not invert else -degree_90

	return api.EulerRotation(normal_direction, rotation_order)
