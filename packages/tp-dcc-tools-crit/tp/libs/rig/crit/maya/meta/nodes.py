from __future__ import annotations

from typing import Iterator
from collections import OrderedDict

from overrides import override

import maya.cmds as cmds

from tp.core import log
from tp.common.python import helpers
from tp.maya import api
from tp.maya.api import curves
from tp.maya.om import plugs, nodes as om_nodes
from tp.maya.libs import curves as curves_library
from tp.maya.meta import base

from tp.libs.rig.crit import consts

logger = log.rigLogger


class SettingsNode(api.DGNode):
	"""
	Class that handles arbitrary settings.
	"""

	@override(check_signature=False)
	def create(self, name: str, id: str, node_type: str = 'network') -> SettingsNode:
		"""
		Creates the MFnSet and sets this instance MObject to the new node.

		:param str name: name for the asset container node.
		:param str id: name for the asset container node.
		:param str node_type: name for the asset container node.
		:return: settings node instance.
		:rtype: SettingsNode
		"""

		settings_node = api.factory.create_dg_node(name, node_type=node_type)
		self.setObject(settings_node.object())
		self.addAttribute(consts.CRIT_ID_ATTR, type=api.attributetypes.kMFnDataString, value=id, locked=True)

		return self

	@override(check_signature=False)
	def serializeFromScene(self) -> list[dict]:
		"""
		Serializes current node into a dictionary compatible with JSON.

		:return: JSON compatible dictionary.
		:rtype: list[dict]
		"""

		skip = (consts.CRIT_ID_ATTR, 'id')
		return [plugs.serialize_plug(attr.plug()) for attr in self.iterateExtraAttributes(skip=skip)]

	def id(self) -> str:
		"""
		Returns the ID of the settings node.

		:return: settings node ID.
		:rtype: str
		"""

		id_attr = self.attribute(consts.CRIT_ID_ATTR)
		return id_attr.value() if id_attr is not None else ''


class ControlNode(api.DagNode):
	"""
	Wrapper class for CRIT control nodes.
	"""

	@override(check_signature=False)
	def create(self, **kwargs: dict):
		"""
		Creates control with given arguments.

		:param dict kwargs: dictionary with arguments to create control with.
			{
				'color': (1.0, 1.0, 1.0),
				consts.CRIT_ID_ATTR: 'ctrl',
				'name': 'myCtrl',
				'translate': [0.0, 0.0, 0.0] or api.MVector
				'rotate': [0.0, 0.0, 0.0]		# radians
				'rotateOrder': 0
				'shape': 'circle'
			}
		:return: control node instance.
		:rtype: ControlNode
		:raises SystemError: if a node cannot be deserialized from given arguments.
		"""

		shape = kwargs.get('shape')
		parent = kwargs.get('parent')
		kwargs['type'] = kwargs.get('type', 'critPinLocator')
		kwargs['name'] = kwargs.get('name', 'Control')
		kwargs['parent'] = None

		try:
			n = om_nodes.deserialize_node(kwargs)[0]
		except SystemError:
			logger.error('Failed to deserialize node: {} from structure'.format(
				kwargs['name']), exc_info=True, extra={'data': kwargs})
			raise

		self.setObject(n)

		with api.lock_state_attr_context(
				self, ['rotateOrder'] + api.LOCAL_TRANSFORM_ATTRS + ['translate', 'rotate', 'scale'], state=False):
			self.setRotationOrder(kwargs.get('rotateOrder', api.consts.kRotateOrder_XYZ))
			world_matrix = kwargs.get('worldMatrix')
			if world_matrix is None:
				self.setTranslation(api.Vector(kwargs.get('translate', (0.0, 0.0, 0.0))), space=api.kWorldSpace)
				self.setRotation(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)), space=api.kWorldSpace)
				self.setScale(kwargs.get('scale', (1.0, 1.0, 1.0)))
			else:
				self.setWorldMatrix(api.Matrix(world_matrix))
			if parent is not None:
				self.setParent(parent, maintain_offset=True)

		if shape:
			if helpers.is_string(shape):
				self.add_shape_from_lib(shape, replace=True)
				color = kwargs.get('color')
				if color:
					self.setShapeColor(color, shape_index=-1)
			else:
				self.add_shape_from_data(shape, space=api.kWorldSpace, replace=True)
		self.addAttribute(
			consts.CRIT_ID_ATTR, api.kMFnDataString, value=kwargs.get('id', kwargs['name']), default='', locked=True)

		child_highlighting = kwargs.get('selectionChildHighlighting')
		if child_highlighting is not None:
			self.attribute('selectionChildHighlighting').set(child_highlighting)

		rotate_order = self.rotateOrder
		rotate_order.show()
		rotate_order.setKeyable(True)

		return self

	@override(check_signature=False)
	def setParent(
			self, parent: api.OpenMaya.MObject | api.DagNode, use_srt: bool = True,
			maintain_offset: bool = True) -> api.OpenMaya.MDagModifier | None:
		"""
		Overrides setParent to set the control parent node.

		:param OpenMaya.MObject or api.DagNode parent: new parent node for the guide.
		:param bool use_srt: whether the SRT will be parented instead of the pivot node.
		:param bool maintain_offset: whether to maintain the current world transform after the parenting.
		:return: True if the set parent operation was successful; False otherwise.
		:rtype: bool
		"""

		if use_srt:
			srt = self.srt()
			if srt is not None:
				srt.setParent(parent if parent is not None else None, maintain_offset=maintain_offset)
				return

		return super().setParent(parent, maintain_offset=maintain_offset)

	@override(check_signature=False)
	def serializeFromScene(
			self, skip_attributes: tuple = (), include_connections: bool = True, include_attributes: tuple = (),
			extra_attributes_only: bool = True, use_short_names: bool = True, include_namespace: bool = True) -> dict:
		"""
		Serializes current node instance and returns a JSON compatible dictionary with the node data.

		:param set(str) or None skip_attributes: list of attribute names to skip serialization of.
		:param bool include_connections: whether to find and serialize all connections where the destination is this
			node instance.
		:param set(str) or None include_attributes: list of attribute names to serialize.
		:param bool extra_attributes_only: whether only extra attributes will be serialized.
		:param bool use_short_names: whether to use short name of nodes.
		:param bool include_namespace: whether to include namespace as part of the node name.
		:return: serialized node data.
		:rtype: dict
		"""

		if self._handle is None:
			return dict()

		base_data = super(ControlNode, self).serializeFromScene(
			skip_attributes=skip_attributes, include_connections=include_connections,
			include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
			use_short_names=use_short_names, include_namespace=include_namespace)
		base_data.update({
			'id': self.attribute(consts.CRIT_ID_ATTR).value(),
			'name': base_data['name'].replace('_guide', ''),
			'shape': curves.serialize_transform_curve(self.object(), space=api.kObjectSpace),
			consts.CRIT_ID_ATTR: 'control'
		})

		return base_data

	@override
	def delete(self, mod: api.OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
		"""
		Deletes the node from the scene.

		:param OpenMaya.MDGModifier mod: modifier to add the delete operation into.
		:param bool apply: whether to apply the modifier immediately.
		:return: True if the node deletion was successful; False otherwise.
		:raises RuntimeError: if deletion operation fails.
		:rtype: bool
		"""

		controller_tag = self.controller_tag()
		if controller_tag:
			controller_tag.delete(mod=mod, apply=apply)

		return super().delete(mod=mod, apply=apply)

	def id(self) -> str:
		"""
		Returns the ID for this control.

		:return: ID as a string.
		:rtype: str
		"""

		id_attr = self.attribute(consts.CRIT_ID_ATTR)
		return id_attr.value() if id_attr is not None else ''

	def controller_tag(self) -> api.DGNode | None:
		"""
		Returns the attached controller tag for this control
		.
		:return: control controller tag.
		:rtype: api.DGNode or None
		"""

		for dest in self.attribute('message').destinations():
			node = dest.node()
			if node.apiType() == api.kControllerTag:
				return node

		return None

	def add_controller_tag(
			self, name: str, parent: ControlNode | None = None, visibility_plug: api.Plug | None = None) -> api.DGNode:
		"""
		Creates and attaches a new Maya kControllerTag node into this control.

		:param str name: name of the newly created controller tag.
		:param ControlNode parent: optional controller tag control parent.
		:param api.Plug visibility_plug: visibility plug to connect to.
		:return: newly created controller tag instance.
		:rtype: api.DGNode
		"""

		parent = parent.controller_tag() if parent is not None else None
		return api.factory.create_controller_tag(self, name=name, parent=parent, visibility_plug=visibility_plug or None)

	def add_shape_from_lib(
			self, shape_name: str, replace: bool = False,
			maintain_colors: bool = False) -> tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]:
		"""
		Adds a new CV shape with given name from the library of shapes.

		:param str shape_name: name of the CV shape to add from library.
		:param bool replace: whether to remove already existing CV shapes.
		:param bool maintain_colors: whether to maintain the color of the actual CV shapes.
		:return: tuple containing the control node instance and the created shape instances.
		:rtype: tuple[ControlNode or None, list[api.OpenMaya.MObject or api.DagNode]]
		"""

		if shape_name not in curves_library.names():
			return None, list()

		color_data = dict()
		if maintain_colors:
			for shape in self.iterateShapes():
				color_data = om_nodes.node_color_data(shape.object())
				break

		if replace:
			self.deleteShapeNodes()

		shapes = list(map(api.node_by_object, curves_library.load_and_create_from_lib(
			shape_name, parent=self.object())[1]))
		if maintain_colors:
			for shape in shapes:
				om_nodes.set_node_color(
					shape.object(), color_data.get('overrideColorRGB'), outliner_color=color_data.get('outlinerColor'),
					use_outliner_color=color_data.get('useOutlinerColor', False))

		return self, shapes

	def add_shape_from_data(
			self, shape_data: dict, space: api.OpenMaya.MSpace = api.kObjectSpace, replace: bool = False,
			maintain_colors: bool = False) -> tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]:
		"""
		Adds a new CV shape based on the given data.

		:param dict shape_data: shape data as a dictionary.
		:param api.OpenMaya.MSpace space: coordinates we want to create new curve in.
		:param bool replace: whether to replace already existing control shapes.
		:param bool maintain_colors: whether to maintain colors based on already existing shape colors.
		:return: tuple containing the control node instance and the created shape instances.
		:rtype: tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]
		"""

		color_data = dict()
		if maintain_colors:
			for shape in self.iterateShapes():
				color_data = om_nodes.node_color_data(shape.object())

		if replace:
			self.deleteShapeNodes()

		shapes = list(map(api.node_by_object, curves.create_curve_shape(
			shape_data, parent=self.object(), space=space)[1]))
		if maintain_colors:
			for shape in shapes:
				om_nodes.set_node_color(
					shape.object(), color_data.get('overrideColorRGB'),
					outliner_color=color_data.get('outlinerColor'),
					use_outliner_color=color_data.get('useOutlinerColor', False))

		return self, shapes

	def srt(self, index: int = 0) -> api.DagNode | None:
		"""
		Returns the SRT (Scale-Rotate-Translate) node at given depth index from top to bottom.

		:param int index: SRT index to get.
		:return: SRT group at given index.
		:rtype: api.DagNode or None
		"""

		for destination in self.attribute('message').destinations():
			node = destination.node()
			if not base.is_meta_node(node):
				continue
			control_element = destination.parent()
			srt_array = control_element[2]
			if index not in srt_array.getExistingArrayAttributeIndices():
				continue
			srt_element = srt_array.element(index)
			source_node = srt_element.sourceNode()
			if source_node is not None:
				return source_node

		return None

	def iterate_srts(self) -> Iterator[api.DagNode]:
		"""
		Generator function that iterates over all SRT (Scale-Rotate-Translate) nodes of this control instance.

		:return: itearted srts nodes.
		:rtype: Iterator[api.DagNode]
		"""

		for destination in self.attribute('message').destinations():
			node = destination.node()
			if not base.is_meta_node(node):
				continue
			control_element = destination.parent()
			for srt_element in control_element[2]:
				source = srt_element.sourceNode()
				if source is not None:
					yield source


class Guide(ControlNode):
	"""
	Wrapper class for CRIT guide nodes.
	"""

	DEFAULT_PIVOT_SHAPE_MULTIPLIER = 0.25
	ATTRIBUTES_TO_SKIP = (
		consts.CRIT_ID_ATTR, api.TP_CONSTRAINTS_ATTR_NAME, consts.CRIT_GUIDE_SHAPE_ATTR, consts.CRIT_IS_GUIDE_ATTR,
		consts.CRIT_PIVOT_SHAPE_ATTR, consts.CRIT_PIVOT_COLOR_ATTR, consts.CRIT_GUIDE_SNAP_PIVOT_ATTR,
		consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR
	)

	@staticmethod
	def is_guide(node: api.DGNode) -> bool:
		"""
		Returns whether given node is a valid guide node.

		:param tp.maya.api.DGNode node: node to check.
		:return: True if given node is a valid guide node; False otherwise.
		:rtype: bool
		"""

		return node.hasAttribute(consts.CRIT_IS_GUIDE_ATTR)

	@staticmethod
	def set_guides_world_matrix(guides: list[Guide], matrices: list[api.Matrix], skip_locked_transforms: bool = True):
		"""
		Sets the world matrix of the given guide nodes.

		:param list(Guide) guides: list of guides to set world matrix of.
		:param list(api.Matrix) matrices: list of matrices to set.
		:param bool skip_locked_transforms: whether to skip locked transforms.
		"""

		assert len(guides) == len(matrices), 'Guides and matrices list must be same length'

		for guide, matrix in zip(guides, matrices):
			srt = guide.srt()
			children = list(guide.iterateChildren(recursive=False, node_types=(api.kNodeTypes.kTransform,)))
			for child in children:
				child.setParent(None)
			shape_node = guide.shape_node()
			if shape_node:
				shape_transform = shape_node.worldMatrix()

			parent = guide.parent()
			guide.setParent(None, use_srt=False)
			if srt:
				srt.resetTransform(scale=False)

			if not skip_locked_transforms:
				with api.lock_state_attr_context(guide, api.LOCAL_TRANSFORM_ATTRS, False):
					guide.setWorldMatrix(matrix)
					guide.setParent(parent, use_srt=False)
			else:
				guide.setWorldMatrix(matrix)
				guide.setParent(parent, use_srt=False)

			for child in children:
				child.setParent(guide)

			if shape_node:
				shape_node.setMatrix(shape_transform * shape_node.offsetParentMatrix.value().inverse())

	@override(check_signature=False)
	def create(self, **settings: dict) -> Guide:
		"""
		Creates the MFnSet and sets this instance MObject to the new node.

		:param dict settings: name for the asset container node.
		:return: guide node instance.
		:rtype: Guide
		"""

		# settings['type'] = 'critPinLocator'

		guide_data = dict()
		guide_data.update(settings)

		color = guide_data.get('pivotColor', consts.DEFAULT_GUIDE_PIVOT_COLOR)
		guide_data['color'] = color
		new_shape = guide_data.get('shape')

		attrs = guide_data.get('attributes', list())
		requires_pivot_shape = guide_data.get(consts.CRIT_REQUIRES_PIVOT_SHAPE_ATTR, True)
		if requires_pivot_shape:
			pivot_shape = guide_data.get(consts.CRIT_PIVOT_SHAPE_ATTR) or 0
			guide_data['shape'] = None
			attrs.append(dict(name=consts.CRIT_PIVOT_SHAPE_ATTR, value=pivot_shape, type=api.attributetypes.kMFnNumericInt))
			attrs.append(dict(name=consts.CRIT_PIVOT_COLOR_ATTR, value=color, type=api.attributetypes.kMFnNumeric3Float))
		guide_data['attributes'] = self._merge_user_guide_attributes(guide_data, attrs)

		super().create(**guide_data)

		cv_scale = self.DEFAULT_PIVOT_SHAPE_MULTIPLIER
		snap_pivot = api.factory.create_dag_node('_'.join((self.name(include_namespace=False), 'pick')), 'locator', parent=self)
		snap_pivot.message.connect(self.attribute(consts.CRIT_GUIDE_SNAP_PIVOT_ATTR))
		if color:
			self.setShapeColor(color)
		self.scale_pivot_components(cv_scale, cv_scale, cv_scale)
		snap_pivot.attribute('localScale').set(api.Vector(0.001, 0.001, 0.001))
		self._track_shapes(list(self.iterateShapes()) + list(snap_pivot.iterateShapes()), replace=True)

		shape_node = helpers.first_in_list([shape for shape in self.shapes() if shape.typeName == 'critPinLocator'])
		if shape_node:
			shape_node.shape.set(pivot_shape)
			shape_node.color.set(color)
			self.connect(consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR, shape_node.attribute('drawGizmo'))
			shape_node.attribute('drawShape').set(requires_pivot_shape)
			if not requires_pivot_shape:
				shape_node.attribute('drawShape').lock(True)

		if new_shape:
			shape_transform = guide_data.copy()
			if attrs:
				shape_transform['attributes'] = list()
			shape_transform.update(guide_data.get('shapeTransform', dict()))
			shape_transform['shape'] = new_shape
			shape_transform['name'] = guide_data.get('name', 'CRIT_RENAME')
			shape_transform['color'] = settings.get('color')
			self._create_shape_transform(shape_transform)

		return self

	@override(check_signature=False)
	def setParent(
			self, parent: api.OpenMaya.MObject | api.DagNode, shape_parent: api.DagNode | None = None,
			use_srt: bool = True, maintain_offset: bool = True) -> api.OpenMaya.MDagModifier | None:
		"""
		Overrides setParent to set the control parent node.

		:param OpenMaya.MObject or api.DagNode parent: new parent node for the guide.
		:param api.DagNode shape_parent: shape parent.
		:param bool use_srt: whether the SRT will be parented instead of the pivot node.
		:param bool maintain_offset: whether to maintain the current world transform after the parenting.
		:return: True if the set parent operation was successful; False otherwise.
		:rtype: bool
		"""

		if shape_parent is not None:
			self.set_shape_parent(shape_parent)

		return super().setParent(parent, maintain_offset=maintain_offset, use_srt=use_srt)

	@override(check_signature=False)
	def serializeFromScene(
			self, skip_attributes: tuple = (), include_connections: bool = True, include_attributes: tuple = (),
			extra_attributes_only: bool = True, use_short_names: bool = True, include_namespace: bool = True) -> dict:
		"""
		Serializes current node instance and returns a JSON compatible dictionary with the node data.

		:param set(str) or None skip_attributes: list of attribute names to skip serialization of.
		:param bool include_connections: whether to find and serialize all connections where the destination is this
			node instance.
		:param set(str) or None include_attributes: list of attribute names to serialize.
		:param bool extra_attributes_only: whether only extra attributes will be serialized.
		:param bool use_short_names: whether to use short name of nodes.
		:param bool include_namespace: whether to include namespace as part of the node name.
		:return: serialized node data.
		:rtype: dict
		"""

		if not self.exists():
			return dict()

		attributes_to_skip = list(skip_attributes) + list(self.ATTRIBUTES_TO_SKIP)
		base_data = super(Guide, self).serializeFromScene(
			skip_attributes=attributes_to_skip, include_connections=include_connections,
			include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
			use_short_names=use_short_names, include_namespace=include_namespace)
		children = [child.serializeFromScene(
			skip_attributes=attributes_to_skip, include_connections=include_connections,
			include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
			use_short_names=use_short_names, include_namespace=include_namespace) for child in self.iterate_child_guides()]
		srts = [srt.serializeFromScene(
			skip_attributes=attributes_to_skip, include_connections=include_connections,
			include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
			use_short_names=use_short_names, include_namespace=include_namespace) for srt in self.iterate_srts()]

		shape = self.shape_node()
		shape_translation, shape_rotation, shape_scale = list(), list(), list()
		if shape:
			shape_translation, shape_rotation, shape_scale = shape.decompose()

		_, parent_id = self.guide_parent()
		base_data.update({
			'id': self.id(),
			'children': children,
			'srts': srts,
			'shape': dict() if not shape else curves.serialize_transform_curve(shape.object(), space=api.kWorldSpace),
			'pivotShape': self.attribute(consts.CRIT_PIVOT_SHAPE_ATTR).value(),
			'pivotColor': plugs.python_type_from_plug_value(self.attribute(consts.CRIT_PIVOT_COLOR_ATTR)),
			'parent': parent_id,
			'shapeTransform': {'translate': list(shape_translation), 'rotate': list(shape_rotation), 'scale': list(shape_scale)},
			'critType': 'guide'
		})

		return base_data

	def delete_shape_transform(self) -> bool:
		"""
		Deletes shape transform for this guide.

		:return: True if delete shape transform operation was successful; False otherwise.
		:rtype: bool
		"""

		shape_node = self.shape_node()
		if shape_node is not None and shape_node.exists():
			return shape_node.delete()

		return False

	@api.lock_node_context
	@override(check_signature=False)
	def delete(self) -> bool:
		"""
		Deletes the guide from the scene.

		:rtype: bool
		"""

		self.delete_shape_transform()

		root_str = self.srt(0)
		if root_str:
			controller_tag = self.controller_tag()
			if controller_tag:
				controller_tag.delete()
			return root_str.delete()

		return super().delete()

	def is_root(self) -> bool:
		"""
		Returns this guide is a root one.

		:return: True if this guide is a root guide; False otherwise.
		:rtype: bool
		"""

		return self.guide_parent()[0] is None

	def guide_parent(self) -> tuple[Guide | None, str | None]:
		"""
		Returns the first parent guide and its ID.

		:return: tuple with the parent guide for this guide instance and its ID.
		:rtype: tuple[Guide or None, str or None]
		"""

		for parent in self.iterateParents():
			if parent.hasAttribute(consts.CRIT_IS_GUIDE_ATTR):
				return Guide(parent.object()), parent.attribute(consts.CRIT_ID_ATTR).value()

		return None, None

	def iterate_child_guides(self, recursive: bool = False) -> Iterator[Guide]:
		"""
		Generator function that iterates over all immediate child guides.

		:param bool recursive: whether to recursively iterate children guides.
		:return: iterated children guides.
		:rtype: Iterator[Guide]
		"""

		return self._iterate_child_guides(self, recursive=recursive)

	def shape_node(self):
		"""
		Returns the control shape guide node.

		:return: control shape node instance.
		:rtype: ControlNode
		"""

		for dest in self.attribute(consts.CRIT_GUIDE_SHAPE_ATTR).destinations():
			return ControlNode(dest.node().object())

	def set_shape_parent(self, parent: api.DagNode) -> bool:
		"""
		Sets the parent of the separate shape transform node.

		:param api.DagNode parent: new parent node.
		:return: True if the set shape parent operation was successful; False otherwise.
		:rtype: bool
		"""

		shape = self.shape_node()
		if shape is not None:
			shape.setParent(parent, maintain_offset=True)
			return True

		return False

	def snap_pivot(self) -> api.DagNode:
		"""
		Returns the locator shape node which is used to interactive viewport snapping.

		:return: snap pivot locator shape instance.
		:rtype: api.DagNode
		"""

		return self.sourceNodeByName(consts.CRIT_GUIDE_SNAP_PIVOT_ATTR)

	def scale_pivot_components(self, x: int | float, y: int | float, z: int | float):
		"""
		Scales pick pivot CV components with given X, Y, Z values.

		:param int or float x: pivot scale in X axis.
		:param int or float y: pivot scale in Y axis.
		:param int or float z: pivot scale in Z axis.
		"""

		if not self.exists():
			return

		nurbs_shapes = list()
		for shape in self.shapes():
			if shape.typeName == 'critPinLocator':
				continue
			if shape.hasFn(api.kNodeTypes.kLocator):
				shape.localScale.set(api.Vector(x, y, z))
				continue
			nurbs_shapes.append(shape.fullPathName() + '.cv[*]')
		if nurbs_shapes:
			cmds.scale(x, y, z, nurbs_shapes)

	@classmethod
	def _iterate_child_guides(cls, guide, recursive=False):
		"""
		Internal function that iterates over given guide child guides.

		:param Guide guide: guide to iterate children of.
		:param bool recursive: whether to recursively iterate guides.
		:return: iterated child guides.
		:rtype: generator(Guide)
		"""

		if not recursive:
			for child in guide.iterateChildren(recursive=False, node_types=(api.kTransform,)):
				if cls.is_guide(child):
					yield cls(child.object())
				else:
					for _child in cls._iterate_child_guides(child):
						yield _child
		else:
			for child in guide.iterateChildren(recursive=recursive, node_types=(api.kTransform,)):
				if cls.is_guide(child):
					yield cls(child.object())

	@staticmethod
	def _merge_user_guide_attributes(settings: dict, user_attribute: list[dict] | None = None):
		"""
		Internal function that handle the merge of the guide attributes with the given guide user attributes.

		:param dict settings: dictionary containing guide attribute settings.
		:param list(dict) user_attribute: list containing guide user attribute settings.
		:return:
		"""

		user_attributes = user_attribute or list()

		data = OrderedDict(
			(
				(consts.CRIT_ID_ATTR, dict(
					name=consts.CRIT_ID_ATTR, type=api.kMFnDataString, default='',
					channelBox=False, keyable=False, locked=True)),
				(consts.CRIT_IS_GUIDE_ATTR, dict(
					name=consts.CRIT_IS_GUIDE_ATTR, type=api.kMFnNumericBoolean, default=True,
					value=True, channelBox=False, keyable=False, locked=True)),
				(consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR, dict(
					name=consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR, type=api.kMFnNumericBoolean, default=False,
					channelBox=True, keyable=False, locked=False)),
				(consts.CRIT_AUTO_ALIGN_ATTR, dict(
					name=consts.CRIT_AUTO_ALIGN_ATTR, type=api.kMFnNumericBoolean, default=True,
					channelBox=True, keyable=False, locked=False)),
				(consts.CRIT_MIRROR_ATTR, dict(
					name=consts.CRIT_MIRROR_ATTR, type=api.kMFnNumericBoolean, default=True,
					channelBox=True, keyable=False, locked=False)),
				(consts.CRIT_MIRROR_BEHAVIOUR_ATTR, dict(
					name=consts.CRIT_MIRROR_BEHAVIOUR_ATTR, type=api.kMFnkEnumAttribute, enums=consts.MIRROR_BEHAVIOURS_TYPES,
					keyable=False, channelBox=True, default=0, value=0)),
				(consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR, dict(
					name=consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR, type=api.kMFnNumeric3Float, default=consts.DEFAULT_UP_VECTOR,
					channelBox=True, keyable=False, locked=False)),
				(consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR, dict(
					name=consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR, type=api.kMFnNumeric3Float, default=consts.DEFAULT_AIM_VECTOR,
					channelBox=True, keyable=False, locked=False)),
				(consts.CRIT_PIVOT_SHAPE_ATTR, dict(
					name=consts.CRIT_PIVOT_SHAPE_ATTR, type=api.kMFnNumericInt,
					channelBox=False, keyable=False, locked=False)),
				(consts.CRIT_PIVOT_COLOR_ATTR, dict(
					name=consts.CRIT_PIVOT_COLOR_ATTR, type=api.kMFnNumeric3Float,
					channelBox=False, keyable=False, locked=False)),
				(consts.CRIT_GUIDE_SHAPE_ATTR, dict(
					name=consts.CRIT_GUIDE_SHAPE_ATTR, type=api.kMFnMessageAttribute)),
				(consts.CRIT_GUIDE_SNAP_PIVOT_ATTR, dict(
					name=consts.CRIT_GUIDE_SNAP_PIVOT_ATTR, type=api.kMFnMessageAttribute)),
				(consts.CRIT_GUIDE_SHAPE_PRIMARY_ATTR, dict(
					name=consts.CRIT_GUIDE_SHAPE_PRIMARY_ATTR, type=api.kMFnMessageAttribute, isArray=True))
			)
		)
		data[consts.CRIT_ID_ATTR]['value'] = settings.get('id', 'GUIDE_RENAME')
		data[consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR]['value'] = settings.get(consts.CRIT_DISPLAY_AXIS_SHAPE_ATTR, False)
		data[consts.CRIT_AUTO_ALIGN_ATTR]['value'] = settings.get(consts.CRIT_AUTO_ALIGN_ATTR, True)
		data[consts.CRIT_MIRROR_ATTR]['value'] = settings.get(consts.CRIT_MIRROR_ATTR, True)
		data[consts.CRIT_MIRROR_BEHAVIOUR_ATTR]['value'] = settings.get(consts.CRIT_MIRROR_BEHAVIOUR_ATTR, 0)
		data[consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR]['value'] = settings.get(
			consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR, consts.DEFAULT_UP_VECTOR)
		data[consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR]['value'] = settings.get(
			consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR, consts.DEFAULT_AIM_VECTOR)
		data[consts.CRIT_PIVOT_SHAPE_ATTR]['value'] = settings.get(consts.CRIT_PIVOT_SHAPE_ATTR, '')
		data[consts.CRIT_PIVOT_COLOR_ATTR]['value'] = settings.get(consts.CRIT_PIVOT_COLOR_ATTR, (0, 0, 0))

		for user_attr in user_attributes:
			name = user_attr['name']
			if name in data:
				data[name]['value'] = user_attr.get('value')
			else:
				data[name] = user_attr

		return data.values()

	def _track_shapes(self, shapes: list[api.DagNode], replace: bool = False):
		"""
		Internal function that connects each one of the shapes for the guide into the shape primary attribute.

		:param list[api.DagNode] shapes: list of shape sto connect.
		:param bool replace: whether to replace shapes.
		"""

		attr = self.attribute(consts.CRIT_GUIDE_SHAPE_PRIMARY_ATTR)
		if replace:
			modifier = api.DGModifier()
			for i in attr:
				i.delete(mod=modifier, apply=True)
			modifier.doIt()

		for shape in shapes:
			shape.message.connect(attr.nextAvailableDestElementPlug())

	def _create_shape_transform(self, settings: dict):
		"""
		Internal function that creates a new shape transform for this guide.

		:param dict settings: shape data
		:return: newly created shape control instance.
		:rtype: ControlNode
		:raises ValueError: if shape transform node already exists.
		"""

		current_shape_node = self.shape_node()
		if current_shape_node:
			raise ValueError('Shape transform node already exists')

		name = '_'.join([settings['name'], 'shape'])
		shape_control = ControlNode()
		transform_info = settings
		transform_info['name'] = name
		transform_info['type'] = 'transform'
		transform_info['parent'] = None
		transform_info['shape'] = settings.get('shape')
		shape_control.create(**transform_info)
		self._connect_pivot_to_shape(shape_control)

		return shape_control

	def _connect_pivot_to_shape(self, shape_node):
		"""
		Internal function that connects given shape node to the pivot shape.

		:param DagNode shape_node: shape node to connect.
		"""

		shape_pivot_attr = shape_node.addAttribute(consts.CRIT_PIVOT_NODE_ATTR, api.attributetypes.kMFnMessageAttribute)
		self.attribute(consts.CRIT_GUIDE_SHAPE_ATTR).connect(shape_pivot_attr)
		self.rotateOrder.connect(shape_node.rotateOrder)
		api.build_constraint(
			shape_node, {'targets': ((self.fullPathName(partial_name=True, include_namespace=False), self),)},
			constraint_type='matrix', track=False, maintainOffset=True)
