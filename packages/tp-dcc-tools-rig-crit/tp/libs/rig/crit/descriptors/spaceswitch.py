from __future__ import annotations

from typing import List

from tp.maya import api
from tp.common.python import helpers
from tp.libs.rig.crit.descriptors import attributes


def merge_attributes_with_space_switches(
		control_panel_attributes: List[attributes.AttributeDescriptor], space_switches: List[SpaceSwitchDescriptor],
		exclude_active: bool = True):
	"""
	Merges the space switching descriptors with the attribute list to ensure that only those that do not already exist
	are created.

	:param List[AttributeDescriptor] control_panel_attributes: control panel descriptor attributes.
	:param List[SpaceSwitchDescriptor] space_switches: list of space switches for the component to merge.
	:param bool exclude_active: whether the space switches which are set to active should be merged.
	"""

	current_attrs = {i.name: i for i in control_panel_attributes}
	current_attr_labels = list(current_attrs.keys())
	previous_attr_label = current_attr_labels[-1] if current_attr_labels else ''
	space_attr_type = attributes.attribute_class_for_type(api.kMFnkEnumAttribute)

	for space in space_switches:
		pass


class SpaceSwitchDescriptor(helpers.ObjectDict):
	"""
	Class that represents a space switch in its raw form:
		{
			'label': 'ikSpace',
			'driven': 'endIk',
			'type': 'parent',
			'drivers': [
				'label': 'parent',
				'driver': '@{self.inputLayer.upr}'
			]
		}
	"""

	def __init__(self, *args, **kwargs):

		data = {}
		if args:
			data = args[0]
		data.update(kwargs)
		drivers = []
		for driver in data.get('drivers', []):
			drivers.append(SpaceSwitchDriverDescriptor(driver))
		data['drivers'] = drivers
		super().__init__(data)


class SpaceSwitchDriverDescriptor(helpers.ObjectDict):
	"""
	Class that represents a single space switch driver
		{
			'label': 'parent',
			'driver': '@{self.inputLayer.upr}'
		}
	"""

	pass
