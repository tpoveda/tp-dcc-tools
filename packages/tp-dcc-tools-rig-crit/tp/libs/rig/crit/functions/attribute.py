from __future__ import annotations

import maya.cmds as cmds


class Attribute:
	def __init__(
			self, add: bool = True, type: str | None = None, node: str | None = None, name: str | None = None,
			min: int | float | None = None, max: int | float | None = None, value: int | float | bool | str | None = None,
			keyable: bool | None = None, lock: bool = False):
		self.type = type
		self.node = node
		self.name = name
		self.min = min
		self.max = max
		self.value = value
		self.keyable = keyable
		self.lock = lock
		self.attr = ''
		self.has_min_value = False if self.min is None else True
		self.has_max_value = False if self.max is None else True

		if add:
			if not self.type:
				raise RuntimeError('Must provide attribute type when adding attributes.')
			self.add()

	def add(self):
		"""
		Adds current attribute into wrapped node.
		"""

		self.attr = f'{self.node}.{self.name}'
		type_dict = {
			'bool': self.add_bool,
			'double': self.add_double,
			'string': self.add_string
		}
		type_dict[self.type]()

		self.value = self.children_name if self.type == 'plug' else cmds.getAttr(self.attr)

	def add_bool(self):
		"""
		Adds boolean attribute into wrapped node.
		"""

		cmds.addAttr(self.node, attributeType='bool', defaultValue=self.value, keyable=self.keyable, longName=self.name)

	def add_double(self):
		"""
		Adds double attribute into wrapped node.
		"""

		cmds.addAttr(
			self.node, attributeType='double', hasMinValue=self.has_min_value, hasMaxValue=self.has_max_value,
			defaultValue=self.value, keyable=self.keyable, longName=self.name)
		if self.has_min_value:
			cmds.addAttr(self.attr, edit=True, min=self.min)
		if self.has_max_value:
			cmds.addAttr(self.attr, edit=True, max=self.max)

	def add_string(self):
		"""
		Adds string attribute into wrapped node.
		"""

		cmds.addAttr(self.node, longName=self.name, dataType='string')
		cmds.setAttr(self.attr, self.value, type='string')

	def lock_and_hide(
			self, node: str | None = None, translate: bool | str = True, rotate: bool | str = True,
			scale: bool | str = True, visibility: bool = True, attribute_list: list[str] | None = None):
		"""
		Locks and hides current attribute within current node or given one.

		:param str or None node: optional node to lock and hide attributes of.
		:param bool or str translate: whether to lock and hide all translation channels or specific ones ('X', 'XY, ...).
		:param bool or str rotate: whether to lock and hide all rotation channels or specific ones ('X', 'XY, ...).
		:param bool or str scale: whether to lock and hide all scale channels or specific ones ('X', 'XY, ...).
		:param bool visibility: whether to lock and hide visibility channel.
		:param list[str] attribute_list: optional list of attributes to lock and hide.
		"""

		node = node or self.node
		for axis in 'XYZ':
			if translate:
				if isinstance(translate, str) and axis not in translate:
					continue
				else:
					pass
				cmds.setAttr(f'{node}.translate{axis}', lock=True)
				cmds.setAttr(f'{node}.translate{axis}', keyable=False)
			if rotate:
				if isinstance(rotate, str) and axis not in rotate:
					continue
				else:
					pass
				cmds.setAttr(f'{node}.rotate{axis}', lock=True)
				cmds.setAttr(f'{node}.rotate{axis}', keyable=False)
			if scale:
				if isinstance(scale, str) and axis not in scale:
					continue
				else:
					pass
				cmds.setAttr(f'{node}.scale{axis}', lock=True)
				cmds.setAttr(f'{node}.scale{axis}', keyable=False)
		if visibility:
			cmds.setAttr(f'{node}.visibility', lock=True)
			cmds.setAttr(f'{node}.visibility', keyable=False)
		if attribute_list:
			for attr in attribute_list:
				cmds.setAttr(f'{node}.{attr}', lock=True)
				cmds.setAttr(f'{node}.{attr}', keyable=False)
