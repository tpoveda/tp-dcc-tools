from __future__ import annotations

import math
from typing import Iterator

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaAnim as OpenMayaAnim

from tp.core import log
from tp.common.python import helpers
from tp.maya.om import utils, mathlib, plugs, animation, scene, factory
from tp.maya.api import exceptions, attributetypes, curves

MIRROR_BEHAVIOUR = 0
MIRROR_ORIENTATION = 1

logger = log.tpLogger


def check_node(node: str | OpenMaya.MObject) -> bool:
	"""
	Checks if a node is a valid node and raise and exception if the node is not valid.

	:param str or OpenMaya.MObject node: name of the node to be checked or MObject to be checked
	:return: True if the given node is valid.
	:rtype: bool
	"""

	if helpers.is_string(node):
		if not cmds.objExists(node):
			return False
	elif isinstance(node, OpenMaya.MObject):
		return not node.isNull()

	return True


def is_dag_node(mobj: OpenMaya.MObject) -> bool:
	"""
	Checks if an MObject is a DAG node.

	:param OpenMaya.MObject mobj: Maya object to check.
	:return: True if the MObject is a DAG node or False otherwise.
	:rtype: bool
	"""

	return mobj.hasFn(OpenMaya.MFn.kDagNode)


def is_shape(mobj: OpenMaya.MObject) -> bool:
	"""
	Returns whether the given node is a valid shape node.

	:param OpenMaya.MObject mobj: object to check as a shape node.
	:return: True if the given node is a valid shape node; False otherwise.
	:rtype: bool
	"""

	if not mobj.hasFn(OpenMaya.MFn.kShape):
		return False

	return True


def is_valid_mobject(node: OpenMaya.MObject) -> bool:
	"""
	Returns whether given node is a valid MObject.

	:param OpenMaya.MObject node: Maya object to check.
	:return: True if given Maya object is valid; False otherwise.
	:rtype: bool
	"""

	handle = OpenMaya.MObjectHandle(node)

	return handle.isValid() and handle.isAlive()


def mobject_by_name(node_name: str) -> OpenMaya.MObject | None:
	"""
	Returns an MObject from the given node name.

	:param str node_name: name of the node to get.
	:return: Maya object instance from give name.
	:rtype: OpenMaya.MObject or None
	"""

	selection_list = OpenMaya.MSelectionList()
	try:
		selection_list.add(node_name)
	except RuntimeError:
		logger.warning(f'Node "{node_name}" does not exist or multiple nodes with same name within scene')
		return None
	try:
		return selection_list.getDagPath(0).node()
	except TypeError:
		return selection_list.getDependNode(0)
	except Exception as exc:
		logger.warning(f'Impossible to get MObject from name {node_name} : {exc}')
		return None


def mobject_by_uuid(uuid: OpenMaya.MUuid) -> OpenMaya.MObject | list[OpenMaya.MObject] | None:
	"""
	Returns an MObject from the given UUID.
	If multiples nodes are found with the same UUID, a list will be returned.

	:param OpenMaya.MUuid uuid: UUID to get object for.
	:return: Maya object instance from given uuid.
	:rtype: OpenMaya.MObject or list[OpenMaya.MObject] or None
	"""

	nodes = list(iterate_nodes_by_uuid(uuid))
	if not nodes:
		return None

	if len(nodes) == 1:
		return nodes[0]

	return nodes


def mobject_by_handle(handle: OpenMaya.MObjectHandle) -> OpenMaya.MObject:
	"""
	Returns an MObject from given MObjectHandle.

	:param OpenMaya.MObjectHandle handle: Maya object handle.
	:return: Maya object instance from given handle.
	:rtype: OpenMaya.MObject
	"""

	return handle.object()


def mobject_by_dag_path(dag_path: OpenMaya.MDagPath) -> OpenMaya.MObject:
	"""
	Returns an MObject from given MDagPath.

	:param OpenMaya.MDagPath dag_path: DAG path instance.
	:return: Maya object instance from given dag path.
	:rtype: OpenMaya.MObject
	"""

	return dag_path.node()


__get_mobject__ = {
	'str': mobject_by_name,
	'MUuid': mobject_by_uuid,
	'MObjectHandle': mobject_by_handle,
	'MDagPath': mobject_by_dag_path
}


def mobject(
		value: str | OpenMaya.MObject | OpenMaya.MObjectHandle | OpenMaya.MDagPath,
		validate_node: bool = False) -> OpenMaya.MObject | None:
	"""
	Returns an MObject for the input scene object.

	:param str or OpenMaya.MObject or OpenMaya.MObjectHandle or OpenMaya.MDagPath value: Maya node to get MObject for.
	:param bool validate_node: whether validate node.
	:return: Maya object instance from given name.
	:rtype: OpenMaya.MObject or None
	:raises exceptions.MissingObjectByNameError: if no node with given name exists.
	:raises TypeError: if given node is not a valid Maya node.
	"""

	if validate_node:
		check_node(value)

	if isinstance(value, OpenMaya.MObject):
		return value

	type_name = type(value).__name__
	func = __get_mobject__.get(type_name, None)
	if func is not None:
		return func(value)
	# else:
	# 	# TODO: PyMEL returns OpenMaya1 MObject, we need to convert them into OpenMaya 2.0 objects
	# 	try:
	# 		if value.__module__.startswith('pymel'):
	# 			return value.__apimfn__().object()
	# 	except AttributeError:
	# 		if value.__class__.__module__.startswith('pymel'):
	# 			return value.__apimfn__().object()

	raise TypeError(f'mobject() expects {tuple(__get_mobject__.keys())} ({type(value).__name__} given)')


def name(mobj: OpenMaya.MObject, partial_name: bool = False, include_namespace: bool = True) -> str:
	"""
	Returns full or partial name for a given MObject (which must be valid).

	:param OpenMaya.MObject mobj: Maya object we want to retrieve name of
	:param bool partial_name: whether to return full path or partial name of the Maya object
	:param bool include_namespace: whether object namespace should be included in the path or stripped
	:return: name of the Maya object.
	:rtype: str
	"""

	if mobj.hasFn(OpenMaya.MFn.kDagNode):
		dag_node = OpenMaya.MFnDagNode(mobj)
		node_name = dag_node.partialPathName() if partial_name else dag_node.fullPathName()
	else:
		node_name = OpenMaya.MFnDependencyNode(mobj).name()

	if not include_namespace:
		node_name = OpenMaya.MNamespace.stripNamespaceFromName(node_name)

	return node_name


def names_from_mobjs(mobjs: list[OpenMaya.MObject]) -> list[str]:
	"""
	Returns names of the given list of Maya object handles.

	:param list[OpenMaya.MObject] mobjs: list of Maya objects to retrieve names of.
	:return: list of names.
	:rtype: list[str]
	"""

	names_list: list[str] = []
	for mobj in mobjs:
		object_handle = OpenMaya.MObjectHandle(mobj)
		if not object_handle.isValid() or not object_handle.isAlive():
			continue
		names_list.append(name(object_handle.object()))

	return names_list


def set_names(nodes, names):
	"""
	Renames given list of nodes with the given list of names
	:param nodes: list(MObject)
	:param names: list(str)
	"""

	nodes = helpers.force_list(nodes)
	names = helpers.force_list(names)

	# TODO: Check why after calling this function, the undo does not allow to undo the renaming operation
	for node, node_name in zip(nodes, names):
		OpenMaya.MFnDagNode(node).setName(node_name)


def rename(
		mobj: OpenMaya.MObject, new_name: str, mod: OpenMaya.MDagModifier | None = None,
		apply: bool = True) -> OpenMaya.MObject:
	"""
	Renames given MObject dependency node with the new given name.

	:param OpenMaya.MObject mobj: Maya object to rename.
	:param str new_name: new Maya object name.
	:param OpenMaya.MDagModifier or None mod: optional Maya modifier to rename Maya object with.
	:param bool apply: whether to apply changes instantly.
	:return: renamed Maya object.
	:rtype: OpenMaya.MObject
	"""

	dag_mod = mod or OpenMaya.MDagModifier()
	dag_mod.renameNode(mobj, new_name)
	if mod is None and apply:
		dag_mod.doIt()

	return mobj


def mdag_path(mobj):
	"""
	Takes an object name as a string and returns its MDAGPath.

	:param OpenMaya.MObject mobj: Maya object instance to get DAG path of.
	:return: DAG Path.
	:rtype: str
	"""

	# sel = OpenMaya.MSelectionList()
	# sel.add(objName)
	# return sel.getDagPath(0)

	check_node(mobj)

	selection_list = OpenMaya.MGlobal.getSelectionListByName(mobj)
	dag_path = selection_list.getDagPath(0)

	return dag_path


def root(mobj):
	"""
	Traverses the given Maya object parents until the root node is found and returns that MObject.

	:param OpenMaya.MObject mobj: Maya object to get root of.
	:return: root Maya object.
	:rtype: OpenMaya.MObject
	"""

	current = mobj
	for node in iterate_parents(mobj):
		if node is None:
			return current
		current = node

	return current


def roots(mobj):
	"""
	Returns all root nodes of the given ones

	:param list(OpenMaya.MObject) mobj: nodes to get roots from.
	:return: list of root Maya objects.
	:rtype: list(OpenMaya.MObject)
	"""

	found_roots = set()
	for mobj in mobj:
		found_root = root(mobj)
		if found_root:
			found_roots.add(root)

	return list(found_roots)


def root_node(mobj, node_type):
	"""
	Recursively traverses up the hierarchy until finding the first object that does not have a parent.

	:param OpenMaya.MObject mobj: Maya object to get root of.
	:param OpenMaya.MFn.kType node_type: node type for the root node.
	:return: found root node.
	:rtype: OpenMaya.MObject
	"""

	parent_mobj = parent(mobj)
	if not parent_mobj:
		return mobj
	if parent_mobj.apiType() != node_type:
		return mobj

	return root_node(parent_mobj, node_type) if parent_mobj else mobj


def depend_node(mobj):
	"""
	Returns the dependency node instance of the given node.

	:param Maya object instance to get depend node instance of.
	:return: Depend node instance.
	:rtype: OpenMaya.MFnDependencyNode
	"""

	check_node(mobj)

	return OpenMaya.MFnDependencyNode(mobj)


def plug(mobj, plug_name):
	"""
	Get the plug of given Maya object.

	:param OpenMaya.MObject mobj: Maya object to get plug of.
	:param str plug_name: name of the plug to get.
	:rtype: OpenMaya.MPlug
	"""

	check_node(mobj)

	dep_node = depend_node(mobj)
	attr = dep_node.attribute(plug_name)
	plug = OpenMaya.MPlug(mobj, attr)

	return plug


def shape(node, intermediate=False):
	"""
	Returns the shape node of given node.

	:param OpenMaya.MObject node: Maya object to get shape of.
	:param bool intermediate: whether to get intermediate shapes.
	:return: list of node shapes.
	:rtype: list(str)
	"""

	if type(node) in [list, tuple]:
		node = node[0]

	check_node(node)

	if not node.apiType() == OpenMaya.MFn.kTransform:
		return node

	path = OpenMaya.MDagPath.getAPathTo(node)
	num_shapes = path.numberOfShapesDirectlyBelow()
	if num_shapes:
		path.extendToShape(0)
		return path.node()

	return node


def iterate_selected_nodes(filter_to_apply: tuple[int] | None = None) -> Iterator[OpenMaya.MObject]:
	"""
	Generator function that iterates over selected nodes.

	:param tuple[int] or None filter_to_apply: list of node types to filter by.
	:return: iterated selected nodes.
	:rtype: Iterator[OpenMaya.MObject]
	"""

	def _type_conditional(_filters: tuple[int] | None, _node_type: int):
		try:
			iter(_filters)
			return _node_type in _filters or not _filters
		except TypeError:
			return _node_type == _filters or not _filters

	selection = OpenMaya.MGlobal.getActiveSelectionList()
	for i in range(selection.length()):
		node = selection.getDependNode(i)
		if _type_conditional(filter_to_apply, node.apiType()):
			yield node


def selected_nodes(filter_to_apply: tuple[int] | None = None) -> list[OpenMaya.MObject]:
	"""
	Returns current selected nodes.

	:param tuple[int] or None filter_to_apply: list of node types to filter by.
	:return: list of selected nodes.
	:rtype: list[OpenMaya.MObject]
	"""

	return list(iterate_selected_nodes(filter_to_apply))


def iterate_nodes_by_uuid(*uuids: str | OpenMaya.MUuid | tuple[str | OpenMaya.MUuid]) -> Iterator[OpenMaya.MObject]:
	"""
	Generator function that yields dependency nodes with the given UUID.

	:param tuple[str or OpenMaya.MUuid] uuids: uuids.
	:return: list of nodes.
	:rtype: list[OpenMaya.MObject]
	"""

	for uuid in uuids:
		uuid = OpenMaya.MUuid(uuid) if isinstance(uuid, str) else uuid
		selection = OpenMaya.MSelectionList()
		selection.add(uuid)
		for i in range(selection.length()):
			yield selection.getDependNode(i)


def iterate_parents(node):
	"""
	Generator function that iterate over all given Maya object parents.

	:param OpenMaya.MObject node: Maya object whose parents we want to iterate over.
	:return: generator of iterated parents.
	:rtype: generator(OpenMaya.MObject)
	"""

	parent_mobj = parent(node)
	while parent_mobj is not None:
		yield parent_mobj
		parent_mobj = parent(parent_mobj)


def has_parent(node):
	"""
	Returns whether given Maya object is parented.

	:param OpenMaya.MObject node: Maya object.
	:return: True if the Maya object is parented under other Maya object; False otherwise.
	:rtype: bool
	"""

	parent_mobj = parent(node)
	if parent_mobj is None or parent_mobj.isNull():
		return False

	return True


def parent(mobj):
	"""
	Returns the parent MObject of the given Maya object.

	:param OpenMaya.MObject mobj: Maya object we want to retrieve parent of.
	:return: parent Maya object.
	:rtype: OpenMaya.MObject or None
	"""

	if not mobj.hasFn(OpenMaya.MFn.kDagNode):
		return None

	dag_path = OpenMaya.MDagPath.getAPathTo(mobj)
	if dag_path.node().apiType() == OpenMaya.MFn.kWorld:
		return None

	dag_node = OpenMaya.MFnDagNode(dag_path).parent(0)
	if dag_node.apiType() == OpenMaya.MFn.kWorld:
		return None

	return dag_node


def children(node, recursive=False, filter_types=None):
	"""
	 Function that returns all children of the give Maya object.

	:param OpenMaya.MObject node: Maya object whose children we want to retrieve.
	:param bol recursive: True to recursively find children; False otherwise.
	:param tuple(OpenMaya.MFn.kType) filter_types: filter children types. If not given all type will be returned.
	:return: tuple of found children.
	:rtype: tuple(OpenMaya.MObject)
	"""

	filter_types = filter_types or (OpenMaya.MFn.kTransform,)
	return tuple(iterate_children(node, recursive=recursive, filter_types=filter_types))


def iterate_children(node, recursive=False, filter_types=None):
	"""
	Generator function that iterates over all children of the give Maya object.

	:param OpenMaya.MObject node: Maya object whose children we want to retrieve.
	:param bol recursive: True to recursively find children; False otherwise.
	:param tuple(OpenMaya.MFn.kType) filter_types: filter children types. If not given all type will be returned.
	:return: generator of iterated children.
	:rtype: generator(OpenMaya.MObject)
	"""

	dag_node = OpenMaya.MDagPath.getAPathTo(node)
	child_count = dag_node.childCount()
	if not child_count:
		return
	filter_types = filter_types or ()
	for i in range(child_count):
		child_obj = dag_node.child(i)
		if not filter_types or child_obj.apiType() in filter_types:
			yield child_obj
			if recursive:
				for child in iterate_children(child_obj, recursive=recursive, filter_types=filter_types):
					yield child


def attribute_check(mobj, attribute):
	"""
	Check an object for a given attribute.

	:param OpenMaya.MObject mobj: Maya object instance.
	:param str attribute: name of an attribute.
	:return: True if the attribute exists; False otherwise.
	:rtype: bool
	"""

	check_node(mobj)

	dep_node = depend_node(mobj)
	dep_fn = OpenMaya.MFnDependencyNode()
	dep_fn.setObject(dep_node)
	return dep_fn.hasAttribute(attribute)


def connect_nodes(parent_mobj, parent_plug, child_mobj, child_plug):
	"""
	Connects two nodes using Maya API.

	:param OpenMaya.MObject parent_obj: Maya object to connect.
	:param str parent_plug: name of plug on parent node.
	:param OpenMaya.MObject child_mobj: Maya object of the child node.
	:param str child_plug: name of plug on child node.
	"""

	parent_plug = plug(parent_mobj, parent_plug)
	child_plug = plug(child_mobj, child_plug)
	mdg_mod = OpenMaya.MDGModifier()
	mdg_mod.connect(parent_plug, child_plug)
	mdg_mod.doIt()


def disconnect_nodes(parent_mobj, parent_plug, child_mobj, child_plug):
	"""
	Disconnects two nodes using Maya API.

	:param OpenMaya.MObject parent_mobj: Maya object to disconnect.
	:param str parent_plug: name of plug on parent node.
	:param OpenMaya.MObject child_mobj: Maya object of the child node.
	:param str child_plug: name of plug on child node.
	"""

	parent_plug = plug(parent_mobj, parent_plug)
	child_plug = plug(child_mobj, child_plug)
	mdg_mod = OpenMaya.MDGModifier()
	mdg_mod.disconnect(parent_plug, child_plug)
	mdg_mod.doIt()


def plug_value(plug):
	"""
	:param OpenMaya.MPlug plug: plug instance.
	:return: value of the passed in node plug.
	:rtype: any
	"""

	plug_attr = plug.attribute()
	api_type = plug_attr.apiType()

	# Float Groups - rotate, translate, scale; Compounds
	if api_type in [OpenMaya.MFn.kAttribute3Double, OpenMaya.MFn.kAttribute3Float, OpenMaya.MFn.kCompoundAttribute]:
		result = list()
		if plug.isCompound:
			for c in range(plug.numChildren()):
				result.append(plug_value(plug.child(c)))
			return result

	# Distance
	elif api_type in [OpenMaya.MFn.kDoubleLinearAttribute, OpenMaya.MFn.kFloatLinearAttribute]:
		return plug.asMDistance().asCentimeters()

	# Angle
	elif api_type in [OpenMaya.MFn.kDoubleAngleAttribute, OpenMaya.MFn.kFloatAngleAttribute]:
		return plug.asMAngle().asDegrees()

	# TYPED
	elif api_type == OpenMaya.MFn.kTypedAttribute:
		plug_type = OpenMaya.MFnTypedAttribute(plug_attr).attrType()

		# Matrix
		if plug_type == OpenMaya.MFnData.kMatrix:
			return OpenMaya.MFnMatrixData(plug.asMObject()).matrix()

		# String
		elif plug_type == OpenMaya.MFnData.kString:
			return plug.asString()

	# Matrix
	elif api_type == OpenMaya.MFn.kMatrixAttribute:
		return OpenMaya.MFnMatrixData(plug.asMObject()).matrix()

	# NUMBERS
	elif api_type == OpenMaya.MFn.kNumericAttribute:

		plug_type = OpenMaya.MFnNumericAttribute(plug_attr).numericType()

		# Boolean
		if plug_type == OpenMaya.MFnNumericData.kBoolean:
			return plug.asBool()

		# Integer - Short, Int, Long, Byte
		elif plug_type in [
			OpenMaya.MFnNumericData.kShort, OpenMaya.MFnNumericData.kInt,  OpenMaya.MFnNumericData.kLong,
			OpenMaya.MFnNumericData.kByte]:
			return plug.asInt()

		# Float - Float, Double, Address
		elif plug_type in [
			OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble, OpenMaya.MFnNumericData.kAddr]:
			return plug.asDouble()

	# Enum
	elif api_type == OpenMaya.MFn.kEnumAttribute:
		return plug.asInt()


def get_attribute_data_type(data):
	"""
	Returns the OpenMaya.MFnData id for the given object.
	If the object type could not identified the function returns OpenMaya.MFnData.kInvalid
	:param data: object to get the data type of
	:return: int, value for the data type
	"""

	data_type = OpenMaya.MFnData.kInvalid
	if isinstance(data, str):
		data_type = OpenMaya.MFnData.kString
	if isinstance(data, float):
		data_type = OpenMaya.MFnData.kFloatArray
	if isinstance(data, int):
		data_type = OpenMaya.MFnData.kIntArray

	# TODO: Add support for other types

	return data_type


def translation(mobj, space=None, scene_units=False):
	"""
	Returns the translation for the given Maya object.

	:param OpenMaya.MObject mobj: Maya object to get translation of.
	:param OpenMaya.MFn.type space: coordinate system to use.
	:param bool scene_units: whether the translation vector needs to be converted to scene units.
	:return: object translation.
	:rtype: OpenMaya.MVector
	"""

	space = space or OpenMaya.MSpace.kTransform
	transform = OpenMaya.MFnTransform(OpenMaya.MFnDagNode(mobj).getPath())
	translation = transform.translation(space)

	return mathlib.convert_to_scene_units(translation) if scene_units else translation


def set_translation(mobj, position, space=None, scene_units=False):
	"""
	Sets the translation for the given Maya object.

	:param OpenMaya.MObject mobj: Maya object to set translation of.
	:param OpenMaya.MVector position: translation to set.
	:param OpenMaya.MFn.type space: coordinate system to use.
	:param bool scene_units: whether the translation vector needs to be converted to scene units.
	"""

	space = space or OpenMaya.MSpace.kTransform
	transform = OpenMaya.MFnTransform(OpenMaya.MFnDagNode(mobj).getPath())
	position = mathlib.convert_from_scene_units(position) if scene_units else position
	transform.setTranslation(position, space)


def rotation(mobj, space=None, as_quaternion=False):
	"""
	Returns the rotation for the given Maya object.

	:param OpenMaya.MObject or OpenMaya.MDagPath mobj: Maya object to get rotation of.
	:param OpenMaya.MFn.type space: coordinate system to use.
	:param bool as_quaternion: whether to return rotation as a quaternion.
	:return: Maya object rotation.
	:rtype: OpenMaya.MEulerRotation or OpenMaya.MQuaternion
	"""

	space = space or OpenMaya.MSpace.kTransform
	transform = OpenMaya.MFnTransform(mobj)

	return transform.rotation(space=space, asQuaternion=as_quaternion)


def set_rotation(mobj, rotation, space=None):
	"""
	Sets the rotation for the given Maya object.

	:param OpenMaya.MObject mobj: Maya object to set rotation of.
	:param OpenMaya.MEulerRotation or OpenMaya.MQuaternion rotation: rotation to set.
	:param OpenMaya.MFn.type space: coordinate system to use.
	"""

	transform = OpenMaya.MFnTransform(OpenMaya.MFnDagNode(mobj).getPath())
	if isinstance(rotation, (list, tuple)):
		rotation = OpenMaya.MEulerRotation([OpenMaya.MAngle(i, OpenMaya.MAngle.kDegrees).asRadians() for i in rotation])
	transform.setRotation(rotation, space)


def set_matrix(mobj: OpenMaya.MObject, matrix: OpenMaya.MMatrix, space: OpenMaya.MSpace = OpenMaya.MSpace.kTransform):
	"""
	Sets the object matrix using MTransform.

	:param OpenMaya.MObject mobj: Maya object to modify.
	:param OpenMaya.MMatrix matrix: Matrix to set.
	:param OpenMaya.MSpace space: coordinate space to set the matrix by.
	"""

	dag = OpenMaya.MFnDagNode(mobj)
	transform = OpenMaya.MFnTransform(dag.getPath())
	transform_matrix = OpenMaya.MTransformationMatrix(matrix)
	transform.setTranslation(transform_matrix.translation(space), space)
	transform.setRotation(transform_matrix.rotation(asQuaternion=True), space)
	transform.setScale(transform_matrix.scale(space))


def matrix(mobj, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns local matrix of the given MObject pointing to DAG node.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve world matrix of.
	:param OpenMaya.MDGContext ctx: MDGContext to use.
	:return: local matrix.
	:rtype: OpenMaya.MMatrix
	"""

	return OpenMaya.MFnMatrixData(OpenMaya.MFnDependencyNode(mobj).findPlug('matrix', False).asMObject(ctx)).matrix()


def world_matrix_plug(mobj):
	"""
	Returns the MPlug pointing worldMatrix of the given MObject pointing a DAG node.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve world matrix plug of.
	:return: world matrix plug instance.
	:rtype: OpenMaya.MPlug
	"""

	world_matrix = OpenMaya.MFnDependencyNode(mobj).findPlug('worldMatrix', False)
	return world_matrix.elementByLogicalIndex(0)


def world_matrix(mobj, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns world matrix of the given MObject pointing to DAG node.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve world matrix of.
	:param OpenMaya.MDGContext ctx: MDGContext to use.
	:return: world matrix.
	:rtype: OpenMaya.MMatrix
	"""

	return OpenMaya.MFnMatrixData(world_matrix_plug(mobj).asMObject(ctx)).matrix()


def world_inverse_matrix(mobj, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns world inverse matrix of the given Maya object.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve world inverse matrix of.
	:param OpenMaya.MDGContext ctx: MDGContext to use.
	:return: world inverse matrix.
	:rtype: OpenMaya.MMatrix
	"""

	inverse_matrix_plug = OpenMaya.MFnDependencyNode(mobj).findPlug('worldInverseMatrix', False)
	matrix_plug = inverse_matrix_plug.elementByLogicalIndex(0)

	return OpenMaya.MFnMatrixData(matrix_plug.asMObject(ctx)).matrix()


def parent_matrix(mobj, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns the parent matrix of the given Maya object.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve parent matrix of.
	:param OpenMaya.MDGContext ctx: MDGContext to use.
	:return: parent matrix.
	:rtype: OpenMaya.MMatrix
	"""

	parent_matrix_plug = OpenMaya.MFnDependencyNode(mobj).findPlug('parentMatrix', False)
	matrix_plug = parent_matrix_plug.elementByLogicalIndex(0)

	return OpenMaya.MFnMatrixData(matrix_plug.asMObject(ctx)).matrix()


def parent_inverse_matrix_plug(mobj):
	"""
	Returns parent inverse matrix MPlug of the given Maya object.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve parent inverse matrix plug of.
	:return: parent inverse matrix plug instance.
	:rtype: OpenMaya.MPlug
	"""

	parent_inverse_matrix_plug = OpenMaya.MFnDependencyNode(mobj).findPlug('parentInverseMatrix', False)
	return parent_inverse_matrix_plug.elementByLogicalIndex(0)


def parent_inverse_matrix(mobj, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns the parent inverse matrix of the given Maya object.

	:param OpenMaya.MObject mobj: Maya object of the DAG node we want to retrieve parent inverse matrix of.
	:param OpenMaya.MDGContext ctx: MDGContext to use.
	:return: parent inverse matrix.
	:rtype: OpenMaya.MMatrix
	"""

	return OpenMaya.MFnMatrixData(parent_inverse_matrix_plug(mobj).asMObject(ctx)).matrix()


def offset_matrix(start_mobj, end_mobj, space=None, ctx=OpenMaya.MDGContext.kNormal):
	"""
	Returns the offset matrix between the given two objects.

	:param OpenMaya.MObject start_mobj: start transform Maya object.
	:param OpenMaya.MObject end_mobj: end transform Maya object.
	:param OpenMaya.MSpace or None space: coordinate space to use.
	:param OpenMaya.MDGContext ctx: context to use.
	:return: resulting offset matrix.
	:rtype: OpenMaya.MMatrix
	"""

	space = space or OpenMaya.MSpace.kWorld
	if space == OpenMaya.MSpace.kWorld:
		start = world_matrix(start_mobj, ctx=ctx)
		end = world_matrix(end_mobj, ctx=ctx)
	else:
		start = matrix(start_mobj, ctx=ctx)
		end = matrix(end_mobj, ctx=ctx)

	if int(OpenMaya.MGlobal.mayaVersion()) < 2020:
		output_matrix = end * start.inverse()
	else:
		output_matrix = end * start.inverse() * plugs.plug_value(
			OpenMaya.MFnDependencyNode(start_mobj).findPlug('offsetParentMatrix', False), ctx).inverse()

	return output_matrix


def set_parent(child, new_parent=None, maintain_offset=False, mod=None, apply=True):
	"""
	Sets the parent of the given child.

	:param OpenMaya.MObject child: child node which will have its parent changed
	:param OpenMaya.MObject new_parent: new parent for the child.
	:param bool maintain_offset: bool, whether current transformation is maintained relative to the new parent
	:param OpenMaya.MDagModifier or None mod: modifier to add to; if None, a new will be created.
	:param bool apply: whether to apply modifier immediately
	:return: modifier used to set the parent.
	:rtype: OpenMaya.MDagModifier
	"""

	new_parent = new_parent or OpenMaya.MObject.kNullObj
	if child == new_parent:
		return False

	mod = mod or OpenMaya.MDagModifier()
	if maintain_offset:
		if new_parent == OpenMaya.MObject.kNullObj:
			offset = world_matrix(child)
		else:
			start = world_matrix(new_parent)
			end = world_matrix(child)
			offset = end * start.inverse()
	mod.reparentNode(child, new_parent)
	if apply:
		mod.doIt()
	if maintain_offset:
		if int(OpenMaya.MGlobal.mayaVersion()) < 2020:
			set_matrix(child, offset)
		else:
			value = plugs.plug_value(OpenMaya.MFnDependencyNode(child).findPlug('offsetParentMatrix', False))
			set_matrix(child, offset * value.inverse())

	return mod


def decompose_transform_matrix(matrix, rotation_order, space=None):
	"""
	Returns decomposed translation, rotation and scale of the given Maya matrix.

	:param OpenMaya.MMatrix matrix: maya transform matrix to decompose.
	:param rotation_order: rotation order getting transform matrix of.
	:param OpenMaya.MSpace space: coordinate space to decompose matrix of.
	:return: decompose matrix in translation, rotation and scale.
	:rtype: tuple(OpenMaya.MVector, OpenMaya.MVector, OpenMaya.MVector)
	"""

	space = space or OpenMaya.MSpace.kWorld

	transform_matrix = OpenMaya.MTransformationMatrix(matrix)
	transform_matrix.reorderRotation(rotation_order)
	rotation = transform_matrix.rotation(asQuaternion=space == OpenMaya.MSpace.kWorld)

	return transform_matrix.translation(space), rotation, transform_matrix.scale(space)


def node_color_data(mobj):
	"""
	Returns the color data in the given Maya node.

	:param OpenMaya.MObject mobj: Maya object to get color data of.
	:return: dictionary containing node color data.
	:rtype: dict
	"""

	depend_node = OpenMaya.MFnDagNode(OpenMaya.MFnDagNode(mobj).getPath())
	plug = depend_node.findPlug('overrideColorRGB', False)
	enabled_plug = depend_node.findPlug('overrideEnabled', False)
	override_rgb_colors = depend_node.findPlug('overrideRGBColors', False)
	use_outliner = depend_node.findPlug('useOutlinerColor', False)

	return {
		'overrideEnabled': plugs.plug_value(enabled_plug),
		'overrideColorRGB': plugs.plug_value(plug),
		'overrideRGBColors': plugs.plug_value(override_rgb_colors),
		'useOutlinerColor': plugs.plug_value(use_outliner),
		'outlinerColor': plugs.plug_value(depend_node.findPlug('outlinerColor', False))
	}


def set_node_color(mobj, color, outliner_color=None, use_outliner_color=False, mod=None):
	"""
	Sets the given Maya object its override color. MObject can represent an object or a shape.

	:param OpenMaya.MObject mobj: Maya object we want to change color of.
	:param OpenMaya.MColor or tuple(float, float, float), color: RGB color to set.
	:param OpenMaya.MColor or tuple(float, float, float) or None outliner_color: RGB color to set to outliner item.
	:param bool use_outliner_color: bool, whether to apply outliner color.
	:param OpenMaya.MDGModifier mod: bool, optional Maya context to use.
	"""

	color = helpers.force_list(color)
	if color and len(color) > 3:
		color = color[:-1]

	modifier = mod or OpenMaya.MDGModifier()
	depend_node = OpenMaya.MFnDagNode(OpenMaya.MFnDagNode(mobj).getPath())
	plug = depend_node.findPlug('overrideColorRGB', False)
	enabled_plug = depend_node.findPlug('overrideEnabled', False)
	override_rgb_colors = depend_node.findPlug('overrideRGBColors', False)
	if not enabled_plug.asBool():
		enabled_plug.setBool(True)
	if not override_rgb_colors.asBool():
		depend_node.findPlug('overrideRGBColors', False).setBool(True)

	fn_data = OpenMaya.MFnNumericData(plug.asMObject()).setData(color)
	modifier.newPlugValue(plug, fn_data.object())

	if outliner_color and use_outliner_color:
		outliner_color = helpers.force_list(outliner_color)
		if len(outliner_color) > 3:
			outliner_color = outliner_color[:-1]
		use_outliner = depend_node.findPlug('useOutlinerColor', False)
		modifier.newPlugValueBool(use_outliner, True)
		outliner_color_plug = depend_node.findPlug('outlinerColor', False)
		fn_data = OpenMaya.MFnNumericData(outliner_color_plug.asMObject()).setData(outliner_color)
		modifier.newPlugValue(outliner_color_plug, fn_data.object())

	if mod is None:
		modifier.doIt()


def iterate_shapes(mobj, filter_types=None):
	"""
	Generator function that returns all the given shape DAG paths directly below the given DAG path.

	:param OpenMaya.MObject mobj: Maya objects to search shapes of.
	:param list(str) filter_types: list of filter shapes for teh shapes to return.
	:return: list of iterate shape DAG paths.
	:rtype: generator(OpenMaya.MDagPath)
	"""

	dag_path = OpenMaya.MDagPath(mobj)
	filter_types = helpers.force_list(filter_types)
	for i in range(dag_path.numberOfShapesDirectlyBelow()):
		shape_dag_path = OpenMaya.MDagPath(dag_path)
		shape_dag_path.extendToShape(i)
		if not filter_types or shape_dag_path.apiType() in filter_types:
			yield shape_dag_path


def shapes(mobj, filter_types=None):
	"""
	Returns all the given shape DAG paths directly below the given DAG path as a list.

	:param OpenMaya.MObject mobj: Maya object to search shapes of
	:param list(str) filter_types: list of filter shapes for teh shapes to return
	:return: list of iterated shapes.
	:rtype: list(OpenMaya.MDagPath)
	"""

	return list(iterate_shapes(mobj, filter_types=filter_types))


def shape_at_index(dag_path, index):
	"""
	Finds and returns the shape Dag Path under the given path for the given index.

	:param OpenMaya.MDagPath dag_path: dag path to get shape index of.
	:param int index: shape index.
	:return: found shape DAG path.
	:rtype: OpenMaya.MDagPath or None
	"""

	if index in range(dag_path.numberOfShapesDirectlyBelow()):
		return OpenMaya.MDagPath(dag_path).extendToShape(index)

	return None


def get_child_path_at_index(path, index):
	"""
	Returns MDagPath of the child node at given index from given MDagPath.

	:param OpenMaya.MDagPath path: path of the node we want to get child DAG path of.
	:param int index: child index to get DAG path of.
	:return: child path at given index.
	:rtype: OpenMaya.MDagPath
	"""

	existing_child_count = path.childCount()
	if existing_child_count < 1:
		return None
	index = index if index >= 0 else path.childCount() - abs(index)
	copy_path = OpenMaya.MDagPath(path)
	copy_path.push(path.child(index))

	return copy_path


def get_child_paths(path):
	"""
	Returns all MDagPaths that are child of the given MDagPath.

	:param OpenMaya.MDagPath path: path of the node we want to retrieve child paths of.
	:return: list of child DAG paths.
	:rtype: list(OpenMaya.MDagPath)
	"""

	out_paths = [get_child_path_at_index(path, i) for i in range(path.childCount())]

	return out_paths


def get_child_paths_by_fn(path, fn):
	"""
	Returns all children paths of the given MDagPath that supports given MFn type.

	:param OpenMaya.MDagPath path: DAG path of the node we want to get child paths of.
	:param OpenMaya.MFn fn: Maya function we want to retrieve children of.
	:return: list of child DAG paths.
	:rtype list(OpenMaya.MDagPath)
	"""

	return [child_path for child_path in get_child_paths(path) if child_path.hasFn(fn)]


def get_child_transforms(path):
	"""
	Returns all the child transforms of the given MDagPath
	:param path: MDagPath
	:return: list(MDagPath), list of all transforms below given path
	"""

	return get_child_paths_by_fn(path, OpenMaya.MFn.kTransform)


def lock_node(mobj, state=True, modifier=True):
	"""
	Sets the lock state of the given node.

	:param OpenMaya.MObject mobj: the node mobject to set the lock state of
	:param bool state: lock state for the node
	:param OpenMaya.MDGModifier modifier: Maya modifier to apply.
	:return: OpenMaya.MDGModifier or None
	"""

	if OpenMaya.MFnDependencyNode(mobj).isLocked != state:
		mod = modifier or OpenMaya.MDGModifier()
		mod.setNodeLockState(mobj, state)
		if modifier is not None:
			modifier.doIt()
		return modifier


def unlock_connected_attributes(mobj):
	"""
	Unlocks all connected attributes to the given Maya object.

	:param OpenMaya.MObject mobj: Maya object representing a DAG node.
	"""

	for source, target in iterate_connections(mobj, source=True, destination=True):
		if source.isLocked:
			source.isLocked = False


def unlock_and_disconnect_connected_attributes(mobj):
	"""
	Unlocks and disconnects all attributes to the given Maya object.

	:param OpenMaya.MObject mobj: Maya object representing a DAG node.
	"""

	for source, target in iterate_connections(mobj, source=False, destination=True):
		plugs.disconnect_plug(source)


def iterate_connections(node, source=True, destination=True):
	"""
	Returns a generator function containing a tuple of Maya plugs.

	:param OpenMaya.MObject node: Maya node to search.
	:param bool source: if True, all upstream connections are returned.
	:param bool destination: if True, all downstream connections are returned.
	:return: tuple of MPlug instances, the first element is the connected MPlug of the given node and the other one is
		the connected MPlug from the other node.
	:rtype: generator(tuple(OpenMaya.MPlug, OpenMaya.Mplug)),
	"""

	dep = OpenMaya.MFnDependencyNode(node)
	for plug in iter(dep.getConnections()):
		if source and plug.isSource:
			for i in iter(plug.destinations()):
				yield plug, i
		if destination and plug.isDestination:
			yield plug, plug.source()


def delete(node):
	"""
	Deletes given node.

	:param OpenMaya.MObject node: Maya object to delete.
	"""

	if not is_valid_mobject(node):
		return

	lock_node(node, False)
	unlock_and_disconnect_connected_attributes(node)

	dag_modifier = OpenMaya.MDagModifier()
	dag_modifier.deleteNode(node)
	dag_modifier.doIt()


def has_attribute(mobj, name):
	"""
	Returns whether given Maya object has given attribute added to it.

	:param OpenMaya.MObject mobj: Maya object to check search attribute in.
	:param str name: name of the attribute to check.
	:return: True if the Maya object has given attribute; False otherwise.
	:rtype: bool
	"""

	return OpenMaya.MFnDependencyNode(mobj).hasAttribute(name)


def add_attribute(
		mobj, long_name, short_name, type=attributetypes.kMFnNumericDouble, isArray=False,
		apply=True, mod=None, **kwargs):
	"""
	Adds a new attribute to the given Maya object.

	:param OpenMaya.MObject mobj: node to add attribute to.
	:param str long_name: attribute long name.
	:param str short_name: attribute short name.
	:param int type: Maya attribute type.
	:param bool apply: whether to apply changes instantly.
	:param OpenMaya.MDGModifier mod: Maya modifier to add attribute with.
	:param dict kwargs: keyword arguments.
	:return: Maya object linked to the attribute.
	:rtype: OpenMaya.MFnAttribute
	:raises ValueError: if the attribute already exists.
	:raises TypeError: if the attribute type is not supported.

	.. code-block:: python

		# message attribute
		attr_mobj = addAttribute(myNode, "testMsg", "testMsg", attrType=attributetypes.kMFnMessageAttribute,
								 isArray=False, apply=True)
		# double angle
		attr_mobj = addAttribute(myNode, "myAngle", "myAngle", attrType=attributetypes.kMFnUnitAttributeAngle,
								 keyable=True, channelBox=False)
		# enum
		attr_mobj = addAttribute(myNode, "myEnum", "myEnum", attrType=attributetypes.kMFnkEnumAttribute,
								 keyable=True, channelBox=True, enums=["one", "two", "three"])
	"""

	if has_attribute(mobj, long_name):
		raise exceptions.AttributeAlreadyExistsError('Node "{}" already has attribute "{}"'.format(name(mobj), long_name))

	default = kwargs.get('default')
	channel_box = kwargs.get('channelBox')
	keyable = kwargs.get('keyable')
	numeric_class, data_constant = attributetypes.numeric_type_to_maya_fn_type(type)

	if numeric_class is not None:
		attr = numeric_class()
		if type == attributetypes.kMFnNumericAddr:
			aobj = attr.createAddr(long_name, short_name)
		elif type == attributetypes.kMFnNumeric3Float:
			aobj = attr.createPoint(long_name, short_name)
		else:
			aobj = attr.create(long_name, short_name, data_constant)
	elif type == attributetypes.kMFnkEnumAttribute:
		attr = OpenMaya.MFnEnumAttribute()
		aobj = attr.create(long_name, short_name)
		fields = kwargs.get('enums', list())
		# maya creates an invalid enumAttribute if when creating we don't create any fields
		# so this just safeguards to a single value
		if not fields:
			fields = ['None']
		for index in range(len(fields)):
			attr.addField(fields[index], index)
	elif type == attributetypes.kMFnCompoundAttribute:
		attr = OpenMaya.MFnCompoundAttribute()
		aobj = attr.create(long_name, short_name)
	elif type == attributetypes.kMFnMessageAttribute:
		attr = OpenMaya.MFnMessageAttribute()
		aobj = attr.create(long_name, short_name)
	elif type == attributetypes.kMFnDataString:
		attr = OpenMaya.MFnTypedAttribute()
		string_data = OpenMaya.MFnStringData().create('')
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kString, string_data)
	elif type == attributetypes.kMFnUnitAttributeDistance:
		attr = OpenMaya.MFnUnitAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MDistance())
	elif type == attributetypes.kMFnUnitAttributeAngle:
		attr = OpenMaya.MFnUnitAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MAngle())
	elif type == attributetypes.kMFnUnitAttributeTime:
		attr = OpenMaya.MFnUnitAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MTime())
	elif type == attributetypes.kMFnDataMatrix:
		attr = OpenMaya.MFnMatrixAttribute()
		aobj = attr.create(long_name, short_name)
	# elif type == attributetypes.kMFnDataFloatArray:
	#     attr = OpenMaya.MFnFloatArray()
	#     aobj = attr.create(long_name, short_name)
	elif type == attributetypes.kMFnDataDoubleArray:
		data = OpenMaya.MFnDoubleArrayData().create(OpenMaya.MDoubleArray())
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kDoubleArray, data)
	elif type == attributetypes.kMFnDataIntArray:
		data = OpenMaya.MFnIntArrayData().create(OpenMaya.MIntArray())
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kIntArray, data)
	elif type == attributetypes.kMFnDataPointArray:
		data = OpenMaya.MFnPointArrayData().create(OpenMaya.MPointArray())
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kPointArray, data)
	elif type == attributetypes.kMFnDataVectorArray:
		data = OpenMaya.MFnVectorArrayData().create(OpenMaya.MVectorArray())
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kVectorArray, data)
	elif type == attributetypes.kMFnDataStringArray:
		data = OpenMaya.MFnStringArrayData().create()
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kStringArray, data)
	elif type == attributetypes.kMFnDataMatrixArray:
		data = OpenMaya.MFnMatrixArrayData().create(OpenMaya.MMatrixArray())
		attr = OpenMaya.MFnTypedAttribute()
		aobj = attr.create(long_name, short_name, OpenMaya.MFnData.kMatrixArray, data)
	else:
		raise TypeError('Unsupported Attribute Type: {}, name: {}'.format(type, long_name))

	attr.array = isArray
	storable = kwargs.get('storable', True)
	writable = kwargs.get('writable', True)
	connectable = kwargs.get('connectable', True)
	min_value = kwargs.get('min')
	max_value = kwargs.get('max')
	soft_min = kwargs.get('softMin')
	soft_max = kwargs.get('softMax')
	value = kwargs.get('value')
	locked = kwargs.get('locked', False)
	nice_name = kwargs.get('niceName', None)

	attr.storable = storable
	attr.writable = writable
	attr.connectable = connectable
	if nice_name:
		attr.setNiceNameOverride(nice_name)

	if channel_box is not None:
		attr.channelBox = channel_box
	if keyable is not None:
		attr.keyable = keyable
	if default is not None:
		if type == attributetypes.kMFnDataString:
			default = OpenMaya.MFnStringData().create(default)
		elif type == attributetypes.kMFnDataMatrix:
			default = OpenMaya.MMatrix(default)
		elif type == attributetypes.kMFnUnitAttributeAngle:
			default = OpenMaya.MAngle(default, OpenMaya.MAngle.kRadians)
		elif type == attributetypes.kMFnUnitAttributeDistance:
			default = OpenMaya.MDistance(default)
		elif type == attributetypes.kMFnUnitAttributeTime:
			default = OpenMaya.MTime(default)
		plugs.set_attribute_fn_default(aobj, default)
	if min_value is not None:
		plugs.set_attr_min(aobj, min_value)
	if max_value is not None:
		plugs.set_attr_max(aobj, max_value)
	if soft_min is not None:
		plugs.set_attr_soft_min(aobj, soft_min)
	if soft_max is not None:
		plugs.set_attr_soft_max(aobj, soft_max)
	if aobj is not None and apply:
		modifier = mod or OpenMaya.MDGModifier()
		modifier.addAttribute(mobj, aobj)
		modifier.doIt()
		plug = OpenMaya.MPlug(mobj, aobj)
		kwargs['type'] = type
		if value is not None:
			plugs.set_plug_value(plug, value)
		plug.isLocked = locked

	return attr


def add_compound_attribute(mobj, long_name, short_name, attr_map, isArray=False, apply=True, mod=None, **kwargs):
	"""
	Adds a new compound attribute to the given Maya object.

	:param OpenMaya.MObject mobj: node to add compound attribute to.
	:param str long_name: compound attribute long name.
	:param str short_name: compound attribute short name.
	:param list(dict) attr_map: list of child attributes to add.
		e.g. [{"name":str, "type": attributetypes.kType, "isArray": bool}]
		:param bool isArray: whether the compound attribute is an array.
	:param bool apply: whether to apply changes instantly.
	:param OpenMaya.MDGModifier mod: Maya modifier to add attribute with.
	:param dict kwargs: keyword arguments.
	:return: MObject linked to the compound attribute.
	:rtype: OpenMaya.MFnAttribute
	"""

	exists = False
	modifier = mod or OpenMaya.MDGModifier()
	compound_mobj = OpenMaya.MObject.kNullObj

	if has_attribute(mobj, long_name):
		exists = True
		compound_attribute = OpenMaya.MFnCompoundAttribute(plugs.as_mplug('.'.join([name(mobj), long_name])).attribute())
	else:
		compound_attribute = OpenMaya.MFnCompoundAttribute()
		compound_mobj = compound_attribute.create(long_name, short_name)
		compound_attribute.array = isArray

	for attr_data in attr_map:
		if not attr_data:
			continue
		if not exists and attr_data['type'] == attributetypes.kMFnCompoundAttribute:
			# when create child compounds maya only wants the root attribute to be created. All children will be
			# created because we execute the addChild()
			child = add_compound_attribute(
				mobj, attr_data['name'], attr_data['name'],  attr_data.get('children', []),
				apply=False, mod=modifier, **attr_data)
		else:
			try:
				child = add_attribute(
					mobj, short_name=attr_data['name'], long_name=attr_data['name'], mod=modifier, apply=exists,
					**attr_data)
			except exceptions.AttributeAlreadyExistsError:
				continue
		if child is not None:
			attr_obj = child.object()
			compound_attribute.addChild(attr_obj)

	if apply and not exists:
		modifier.addAttribute(mobj, compound_mobj)
		modifier.doIt()
		kwargs['children'] = attr_map
		plugs.set_plug_info_from_dict(OpenMaya.MPlug(mobj, compound_mobj), **kwargs)

	return compound_attribute


def add_proxy_attribute(mobj, source_plug, **kwargs):
	"""
	Adds a new proxy attribute into the given node.

	:param OpenMaya.MObject mobj: Maya object to add proxy attribute into.
	:param OpenMaya.MPlug source_plug: source proxy plug.
	:param dict kwargs: extra keyword arguments.
	:return: created proxy attribute.
	:rtype: OpenMaya.MFnAttribute
	"""

	# numeric compound attributes e.g: double3 isn't supported via addCompound as it's an
	# actual maya type mfn.kAttributeDouble3 which means we don't create it via MFnCompoundAttribute.
	# therefore we manage that for via the kwargs dict.
	if kwargs['type'] == attributetypes.kMFnCompoundAttribute:
		attr1 = add_compound_attribute(mobj, attrMap=kwargs['children'], **kwargs)
		attr1.isProxyAttribute = True
		attr_plug = OpenMaya.MPlug(mobj, attr1.object())
		plugs.set_compound_as_proxy(attr_plug, source_plug)
	else:
		attr1 = add_attribute(mobj, **kwargs)
		attr1.isProxyAttribute = True
		proxy_plug = OpenMaya.MPlug(mobj, attr1.object())
		# is it's an attribute we're adding which is a special type like double3
		# then ignore connecting the compound as maya proxy attributes require the children
		# not the parent to be connected.
		if proxy_plug.isCompound:
			attr1.isProxyAttribute = True
			plugs.set_compound_as_proxy(proxy_plug, source_plug)
		else:
			attr1.isProxyAttribute = True
			plugs.connect_plugs(source_plug, proxy_plug)

	return attr1


def iterate_attributes(mobj, skip=None, include_attributes=None):
	"""
	Generator function to iterate over all plugs of a given Maya object.

	:param OpenMaya.MObject mobj: Maya object to iterate.
	:param list(str) skip: list of attributes to skip.
	:param list(str) include_attributes: list of attributes to force iteration over.
	:return: generator of iterated attributes.
	:rtype: iterator(OpenMaya.MPlug)
	"""

	skip = skip or ()
	dep = OpenMaya.MFnDependencyNode(mobj)
	for idx in range(dep.attributeCount()):
		attr = dep.attribute(idx)
		attr_plug = OpenMaya.MPlug(mobj, attr)
		name = attr_plug.partialName()

		if any(i in name for i in skip):
			continue
		elif include_attributes and not any(i in name for i in include_attributes):
			continue
		elif attr_plug.isElement or attr_plug.isChild:
			continue
		yield attr_plug
		for child in plugs.iterate_children(attr_plug):
			yield child


def iterate_extra_attributes(mobj, skip=None, filtered_types=None, include_attributes=None):
	"""
	Generator function to iterate over all extra plugs of a given Maya object.

	:param OpenMaya.MObject mobj: Maya object to iterate.
	:param list(str) skip: list of attributes to skip.
	:param list(str) filtered_types: optional list of types we want to filter.
	:param list(str) include_attributes: list of attributes to force iteration over.
	:return: generator of iterated extra attributes.
	:rtype: iterator(OpenMaya.MPlug)
	"""

	skip = skip or ()
	filtered_types = filtered_types or ()
	include_attributes = include_attributes or ()
	dep = OpenMaya.MFnDependencyNode(mobj)
	for i in range(dep.attributeCount()):
		try:
			attr = dep.attribute(i)
		except RuntimeError:
			logger.error(f'Was not possible to retrieve attribute with index {i} from attribute {dep}')
			continue
		plug_found = OpenMaya.MPlug(mobj, attr)
		if not plug_found.isDynamic:
			continue
		plug_name = plug_found.partialName()

		if skip and any(i in plug_name for i in skip):
			continue
		elif include_attributes and not any(i in plug_name for i in include_attributes):
			continue
		elif not filtered_types or plugs.plug_type(plug_found) in filtered_types:
			yield plug_found


def set_lock_state_on_attributes(mobj, attributes, state=True):
	"""
	Locks and unlocks the given attributes.

	:param OpenMaya.MObject mobj: node whose attributes we want to lock/unlock.
	:param list(str) attributes: list of attributes names to lock/unlock.
	:param bool state: whether to lock or unlock the attributes.
	:return: True if the attributes lock/unlock operation was successful; False otherwise.
	:rtype: bool
	"""

	attributes = helpers.force_list(attributes)
	dep = OpenMaya.MFnDependencyNode(mobj)
	for attr in attributes:
		try:
			found_plug = dep.findPlug(attr, False)
		except RuntimeError:        # missing plug
			continue
		if found_plug.isLocked != state:
			found_plug.isLocked = state

	return True


def show_hide_attributes(mobj, attributes, state=False):
	"""
	Shows or hides given attributes in the channel box.

	:param OpenMaya.MObject mobj: node whose attributes we want to show/hide.
	:param list(str) attributes: list of attributes names to lock/unlock
	:param bool state: whether to hide or show the attributes.
	:return: True if the attributes show/hide operation was successful; False otherwise.
	:rtype: bool
	"""

	attributes = helpers.force_list(attributes)
	dep = OpenMaya.MFnDependencyNode(mobj)
	for attr in attributes:
		found_plug = dep.findPlug(attr, False)
		if found_plug.isChannelBox != state:
			found_plug.isChannelBox = state

	return True


def serialize_node(node, skip_attributes=None, include_connections=True, include_attributes=None,
				   extra_attributes_only=False, use_short_names=False, include_namespace=True):
	"""
	Function that converts given OpenMaya.MObject into a serialized dictionary. This function iterates through all
	attributes, serializing any extra attribute found and any default value that has not changed (defaultValue) and not
	connected or is an array attribute will be skipped.

	Output example:
	{
		'name': '|root|auto|node',
		'parent': '|root|auto',
		'type': 'transform'
		'attributes':
		[
			{
				'type': 0,
				'channelBox': false,
				'default': false,
				'isArray': false,
				'isDynamic': true,
				'keyable': true,
				'locked': false,
				'max': null,
				'min': null,
				'name': 'test',
				'softMax': null,
				'softMin': null,
				'value': false
			},
		],
		'connections':
		[
			{
			  'destination': '|root|auto|config',
			  'destinationPlug': 'run',
			  'source': '|control1|control2',
			  'sourcePlug': 'translateX'
			},
		]
	}

	:param OpenMaya.MObject node: node to serialize.
	:param list(str) skip_attributes: list of attributes names to skip serialization of.
	:param bool include_connections: whether to find and serialize all connections where the destination is this
		node.
	:param list(str) include_attributes: list of attributes to serialize
	:param bool extra_attributes_only: whether to serialize only the extra attributes of this node.
	:param bool use_short_names: whether to use short names to serialize node data.
	:param bool include_namespace: whether to include the namespace as part of node.
	:return: dictionary containing node data.
	:rtype: dict
	"""

	data = dict()

	if node.hasFn(OpenMaya.MFn.kDagNode):
		dep = OpenMaya.MFnDagNode(node)
		name = dep.fullPathName().split('|')[-1] if use_short_names else dep.fullPathName()
		parent_dep = OpenMaya.MFnDagNode(dep.parent(0))
		parent_dep_name = parent_dep.fullPathName().split('|')[-1] if use_short_names else parent_dep.fullPathName()
		if not include_namespace:
			name = name.split('|')[-1].split(':')[-1]
			if parent_dep_name:
				parent_dep_name = parent_dep_name.split('|')[-1].split(':')[-1]
		else:
			name = name.replace(OpenMaya.MNamespace.getNamespaceFromName(name).split('|')[-1] + ':', '')
			if parent_dep_name:
				parent_dep_name = parent_dep_name.replace(
					OpenMaya.MNamespace.getNamespaceFromName(parent_dep_name).split('|')[-1] + ':', '')
		data['parent'] = parent_dep_name
	else:
		dep = OpenMaya.MFnDependencyNode(node)
		name = dep.name()
		if not include_namespace:
			name = name.split('|')[-1].split(':')[-1]
		else:
			name = name.replace(OpenMaya.MNamespace.getNamespaceFromName(name).split('|')[-1] + ':', '')

	data['name'] = name
	data['type'] = dep.typeName

	req = dep.pluginName
	if req:
		data['requirements'] = req
	attributes = list()
	visited = list()

	if node.hasFn(OpenMaya.MFn.kAnimCurve):
		data.update(animation.serialize_curve(node))
	else:
		if extra_attributes_only:
			iterator = list(iterate_extra_attributes(node, skip=skip_attributes, include_attributes=include_attributes))
		else:
			iterator = list(iterate_attributes(node, skip=skip_attributes, include_attributes=include_attributes))
		for plug_found in iterator:
			if not plug_found:
				continue
			if (plug_found.isDefaultValue() and not plug_found.isDynamic) or plug_found.isChild:
				continue
			attr_data = plugs.serialize_plug(plug_found)
			if attr_data:
				attributes.append(attr_data)
			visited.append(plug_found)
		if attributes:
			data['attributes'] = attributes

	if include_connections:
		connections = list()
		for destination, source in iterate_connections(node, source=False, destination=True):
			connections.append(plugs.serialize_connection(destination))
		if connections:
			data['connections'] = connections

	return data


def serialize_nodes(nodes, skip_attributes=None, include_connections=True):
	"""
	Serializes given Maya objects.

	:param list(OpenMaya.MObject) nodes: Maya objects to serialize.
	:param list(str) skip_attributes: list of attributes names to skip serialization of.
	:param bool include_connections: whether to find and serialize all connections where the destination is this
		node.
	:return: generator with the serialized nodes and the serialized data
	:rtype: generator(tuple(OpenMaya.MObject, dict))
	"""

	for node in nodes:
		node_data = serialize_node(node, skip_attributes=skip_attributes, include_connections=include_connections)
		if node.hasFn(OpenMaya.MFn.kNurbsCurve):
			curve_data = curves.serialize_transform_curve(node)
			if curve_data:
				node_data['shape'] = curve_data
		yield node, node_data


def serialize_selected_nodes(skip_attributes=None, include_connections=None):
	"""
	Serializes selected Maya objects.

	:param list(str) skip_attributes: list of attributes names to skip serialization of.
	:param bool include_connections: whether to find and serialize all connections where the destination is this
		node.
	:return: generator with the serialized nodes and the serialized data
	:rtype: generator(tuple(OpenMaya.MObject, dict))
	"""

	nodes = selected_nodes()
	if not nodes:
		return

	yield serialize_nodes(nodes, skip_attributes=skip_attributes, include_connections=include_connections)


def deserialize_node(data, parent=None, include_attributes=True):
	"""
	Deserializes given data and creates a new node based on that data.

	:param dict data: node data (returned by serialize_node function).
	:param OpenMaya.MObject parent: the parent of the newly created node.
	:param bool include_attributes: whether to deserialize node attributes.
	:return: tuple with the newly created Maya object and a list of created plugs.
	:rtype: tuple(OpenMaya.MObject, list(OpenMaya.MPlug))

	Input example:
	{
		'name': '|root|auto|node',
		'parent': '|root|auto',
		'type': 'transform'
		'attributes':
		[
			{
				'type': 0,
				'channelBox': false,
				'default': false,
				'isArray': false,
				'isDynamic': true,
				'keyable': true,
				'locked': false,
				'max': null,
				'min': null,
				'name': 'test',
				'softMax': null,
				'softMin': null,
				'value': false
			},
		],
		'connections':
		[
			{
			  'destination': '|root|auto|config',
			  'destinationPlug': 'run',
			  'source': '|control1|control2',
			  'sourcePlug': 'translateX'
			},
		]
	}
	"""

	node_name = data['name'].split('|')[-1]
	node_type = data.get('type')
	if node_type is None:
		return None, list()

	requirements = data.get('requirements', '')
	if requirements and not cmds.pluginInfo(requirements, loaded=True, query=True):
		try:
			cmds.loadPlugin(requirements)
		except RuntimeError:
			logger.error('Could not load plugin: {}'.format(requirements), exc_info=True)
			return None, list()

	if 'parent' in data:
		parent = parent or data['parent']
		new_node = factory.create_dag_node(node_name, node_type, parent)
		mfn = OpenMaya.MFnDagNode(new_node)
		node_name = mfn.fullPathName()
	else:
		new_node = factory.create_dg_node(node_name, node_type)
		if new_node.hasFn(OpenMaya.MFn.kAnimCurve):
			mfn = OpenMayaAnim.MFnAnimCurve(new_node)
			mfn.setPreInfinityType(data['preInfinity'])
			mfn.setPostInfinityType(data['postInfinity'])
			mfn.setIsWeighted(data['weightTangents'])
			mfn.addKeysWithTangents(
				data['frames'],
				data['values'],
				mfn.kTangentGlobal,
				mfn.kTangentGlobal,
				data['inTangents'],
				data['outTangents'],
			)
			for i in range(len(data['frames'])):
				mfn.setAngle(i, OpenMaya.MAngle(data['inTangentAngles'][i]), True)
				mfn.setAngle(i, OpenMaya.MAngle(data['outTangentAngles'][i]), False)
				mfn.setWeight(i, data['inTangentWeights'][i], True)
				mfn.setWeight(i, data['outTangentWeights'][i], False)
				mfn.setInTangentType(i, data['inTangents'][i])
				mfn.setOutTangentType(i, data['outTangents'][i])
		else:
			mfn = OpenMaya.MFnDependencyNode(new_node)

		node_name = mfn.name()

	created_attributes = list()
	if not include_attributes:
		return new_node, created_attributes

	for attr_data in data.get('attributes', tuple()):
		name = attr_data['name']
		try:
			found_plug = mfn.findPlug(name, False)
			found = True
		except RuntimeError:
			found_plug = None
			found = False
		if found:
			try:
				if found_plug.isLocked:
					continue
				plugs.set_plug_info_from_dict(found_plug, **attr_data)
			except RuntimeError:
				full_name = ".".join([node_name, name])
				logger.error('Failed to set plug data: {}'.format(full_name), exc_info=True)
		else:
			if attr_data.get('isChild', False):
				continue
			short_name = name.split('.')[-1]
			children = attr_data.get('children')
			try:
				if children:
					attr = add_compound_attribute(new_node, short_name, short_name, attr_map=children, **attr_data)
				elif attr_data.get('isElement', False):
					continue
				else:
					attr = add_attribute(new_node, short_name, short_name, **attr_data)
			except exceptions.AttributeAlreadyExistsError:
				continue
			created_attributes.append(OpenMaya.MPlug(new_node, attr.object()))

	return new_node, created_attributes


def deserialize_nodes(nodes_data):
	"""
	Deserializes given nodes based on given data

	:param list(dict) nodes_data: list of serialized node data.
	:return: newly created nodes.
	:rtype: list(OpenMaya.MObject)
	"""

	created_nodes = list()
	for node_data in nodes_data:
		created_node = deserialize_node(node_data)
		if created_node:
			created_nodes.append(created_node)

	return created_nodes


def aim_to_node(source, target, aim_vector=None, up_vector=None, world_up_vector=None):
	"""
	Aim source node to target node using quaternions.

	:param OpenMaya.MObject source: node to aim towards the target node.
	:param OpenMaya.MObject target: node source node will point to.
	:param OpenMaya.MVector or list(float, float, float) or None aim_vector: vector for the aim axis.
	:param OpenMaya.MVector or list(float, float, float) or None up_vector: up vector for the aim.
	:param OpenMaya.MVector or list(float, float, float) or None world_up_vector: would up vector for the aim.
	"""

	if aim_vector is not None and isinstance(aim_vector, (list, tuple)):
		aim_vector = OpenMaya.MVector(*aim_vector)
	if up_vector is not None and isinstance(up_vector, (list, tuple)):
		up_vector = OpenMaya.MVector(*up_vector)
	if world_up_vector is not None and isinstance(world_up_vector, (list, tuple)):
		world_up_vector = OpenMaya.MVector(*world_up_vector)

	eye_aim = aim_vector or mathlib.X_AXIS_VECTOR
	eye_up = up_vector or mathlib.Y_AXIS_VECTOR
	world_up = world_up_vector or OpenMaya.MGlobal.upAxis()
	eye_dag = OpenMaya.MDagPath.getAPathTo(source)
	target_dag = OpenMaya.MDagPath.getAPathTo(target)
	transform_fn = OpenMaya.MFnTransform(eye_dag)
	eye_pivot_pos = transform_fn.rotatePivot(OpenMaya.MSpace.kWorld)
	transform_fn = OpenMaya.MFnTransform(target_dag)
	target_pivot_pos = transform_fn.rotatePivot(OpenMaya.MSpace.kWorld)

	aim_vector = target_pivot_pos - eye_pivot_pos
	eye_u = aim_vector.normal()
	eye_w = (eye_u ^ OpenMaya.MVector(world_up.x, world_up.y, world_up.z)).normal()
	eye_v = eye_w ^ eye_u
	quat_u = OpenMaya.MQuaternion(eye_aim, eye_u)
	up_rotated = eye_up.rotateBy(quat_u)
	try:
		angle = math.acos(up_rotated * eye_v)
	except (ZeroDivisionError, ValueError):
		# if it is already aligned we just return
		return

	# align to aim
	quat_v = OpenMaya.MQuaternion(angle, eye_u)
	if not eye_v.isEquivalent(up_rotated.rotateBy(quat_v), 1.0e-5):
		angle = (2 * math.pi) - angle
		quat_v = OpenMaya.MQuaternion(angle, eye_u)
	quat_u *= quat_v
	transform_fn.setObject(eye_dag)
	transform_fn.setRotation(quat_u, OpenMaya.MSpace.kWorld)


def aim_nodes(
		target_node: OpenMaya.MObject, driven: List[OpenMaya.MObject],
		aim_vector: OpenMaya.MVector | List[float, float, float] | None = None,
		up_vector: OpenMaya.MVector | List[float, float, float] | None = None,
		world_up_vector: OpenMaya.MVector | List[float, float, float] | None = None):
	"""
	Aim target node to the iven driven joints using strictly math (no aim constraint).

	:param OpenMaya.MObject target_node: node we want to aim to.
	:param List[penMaya.MObject] driven: list of nodes we want to aim to target one.
	:param OpenMaya.MVector or List[float, float, float] or None aim_vector: optional vector used to aim target node to
		driven ones.
	:param OpenMaya.MVector or List[float, float, float] or None up_vector: optional vector used to define the up
		vector when aiming target node to driven ones.
	:param OpenMaya.MVector or List[float, float, float] or None world_up_vector: optional vector used to define the
		world up vector when aiming target node to driven ones.
	"""

	for driven_node in iter(driven):
		found_children = []
		for child in list(iterate_children(
				driven_node, recursive=False, filter_types=(OpenMaya.MFn.kTransform, OpenMaya.MFn.kJoint))):
			set_parent(child, None, maintain_offset=True)
			found_children.append(child)
		aim_to_node(
			driven_node, target_node, aim_vector=aim_vector, up_vector=up_vector, world_up_vector=world_up_vector)
		for child in iter(found_children):
			set_parent(child, driven_node, maintain_offset=True)


def aim_selected(aim_vector=None, up_vector=None, world_up_vector=None):
	"""
	Aim the current selected nodes to the last selected one.

	:param OpenMaya.MVector or list(float, float, float) or None aim_vector: vector for the aim axis.
	:param OpenMaya.MVector or list(float, float, float) or None up_vector: up vector for the aim.
	:param OpenMaya.MVector or list(float, float, float) or None world_up_vector: would up vector for the aim.
	:raises ValueError: if less than 2 nodes are selected.
	"""

	selected = scene.selected_nodes()
	if len(selected < 2):
		raise ValueError('Please select more than 2 nodes!')
	target = selected[-1]
	to_aim = selected[:-1]
	aim_nodes(target, to_aim, aim_vector=aim_vector, up_vector=up_vector, world_up_vector=world_up_vector)


def mirror_transform(node, parent, translate, rotate, mirror_function=MIRROR_BEHAVIOUR):
	"""
	Mirrors the translation and rotation of a transform node relative to another node (or the world).

	:param OpenMaya.MObject node: Maya object transform node we want to mirror.
	:param OpenMaya.MObject or OpenMaya.MObject.kNullObj or None parent: parent transform to mirror relative to.
	:param tuple(str) translate: axis to mirror (can be one or more).
	:param str rotate: rotate plane ('xy', 'yz' or 'xz')
	:param int mirror_function: mirror type.
	:return: mirrored translation vector and the mirrored rotation matrix.
	:rtype: tuple(OpenMaya.MVector, OpenMaya.MMatrix)
	"""

	current_matrix = world_matrix(node)
	transform_matrix = OpenMaya.MTransformationMatrix(current_matrix)
	translation = transform_matrix.translation(OpenMaya.MSpace.kWorld)
	if len(translate) == 3:
		translation *= -1
	else:
		for i in translate:
			translation[mathlib.AXIS[i]] *= -1
	transform_matrix.setTranslation(translation, OpenMaya.MSpace.kWorld)

	# mirror the rotation on a specific plane
	quat = transform_matrix.rotation(asQuaternion=True)
	if mirror_function == MIRROR_BEHAVIOUR:
		if rotate == 'xy':
			quat = OpenMaya.MQuaternion(quat.y * -1, quat.x, quat.w, quat.z * -1)
		elif rotate == 'yz':
			quat = OpenMaya.MQuaternion(quat.w * -1, quat.z, quat.y * -1, quat.x)
		else:
			quat = OpenMaya.MQuaternion(quat.z, quat.w, quat.x * -1, quat.y * -1)
	else:
		if rotate == 'xy':
			quat.z *= -1
			quat.w *= -1
		elif rotate == 'yz':
			quat.x *= -1
			quat.w *= -1
		else:
			quat.y *= -1
			quat.w *= -1
	transform_matrix.setRotation(quat)
	rot = transform_matrix.asRotateMatrix()

	# put mirror rotation matrix in the space of the parent
	if parent != OpenMaya.MObject.kNullObj:
		inverse_matrix = parent_inverse_matrix(parent)
		rot *= inverse_matrix

	return translation, OpenMaya.MTransformationMatrix(rot).rotation(asQuaternion=True)


def mirror_joint(node, parent, translate, rotate, mirror_function=MIRROR_BEHAVIOUR):
	"""
	Mirrors the translation and rotation of a joint node relative to another node (or the world).

	:param OpenMaya.MObject node: Maya object joint node we want to mirror.
	:param OpenMaya.MObject or OpenMaya.MObject.kNullObj or None parent: parent transform to mirror relative to.
	:param tuple(str) translate: axis to mirror (can be one or more).
	:param str rotate: rotate plane ('xy', 'yz' or 'xz')
	:param int mirror_function: mirror type.
	:return: mirrored translation vector and the mirrored rotation matrix.
	:rtype: tuple(OpenMaya.MVector, OpenMaya.MMatrix)
	"""

	dep_node = OpenMaya.MFnDependencyNode(node)
	rotate_order = dep_node.findPlug('rotateOrder', False).asInt()
	transform_matrix_rotate_order = utils.int_to_mtransform_rotation_order(rotate_order)
	translation, rotation_matrix = mirror_transform(
		node, parent, translate=translate, rotate=rotate, mirror_function=mirror_function)
	joint_order = OpenMaya.MEulerRotation(plugs.plug_value(dep_node.findPlug('jointOrient', False)))
	joint_orient = OpenMaya.MTransformationMatrix().setRotation(joint_order).asMatrixInverse()
