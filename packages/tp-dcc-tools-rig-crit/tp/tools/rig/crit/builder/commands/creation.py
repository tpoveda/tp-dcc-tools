from __future__ import annotations

import typing

from overrides import override

from tp.commands import crit
from tp.tools.rig.crit.builder.core import command, utils

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.rig import Rig
	from tp.libs.rig.crit.core.component import Component
	from tp.libs.rig.crit.descriptors.component import ComponentDescriptor


class CreateRigUiCommand(command.CritUiCommand):

	ID = 'createRig'
	UI_DATA = {'icon': 'add', 'label': 'Create rig instance'}

	@override(check_signature=False)
	def execute(self, name: str) -> Rig | None:
		"""
		Creates a new rig instance.

		:param str name: name of the rig.
		:return: newly created rig instance.
		:rtype: Rig or None
		"""

		success = utils.check_scene_units(parent=self._ui_interface.builder())
		if not success:
			return None

		new_rig = crit.create_rig(name=name)
		self.request_refresh(False)

		return new_rig


class DeleteRigCommand(command.CritUiCommand):

	ID = 'deleteRig'
	UI_DATA = {'icon': 'trash', 'label': 'Delete rig instance'}

	@override(check_signature=False)
	def execute(self, rig: Rig | None = None):
		"""
		Deletes given rig instance.

		:param Rig or None rig: rig instance to delete.
		"""

		if not self._rig_model:
			return

		crit.delete_rig(rig=rig or self.rig_model.rig)
		self.request_refresh(False)


class CreateComponentUiCommand(command.CritUiCommand):

	ID = 'createComponent'
	UI_DATA = {'icon': 'add', 'label': 'Create component'}

	@override(check_signature=False)
	def execute(
			self, component_type: str, name: str, side: str,
			descriptor: ComponentDescriptor | None = None) -> Component | None:
		"""
		Creates a new component instance.

		:param str component_type: type of the component to create.
		:param str name: name of the component to create.
		:param str side: side of the component to create.
		:param ComponentDescriptor descriptor: optional component descriptor to use.
		:return: newly created component.
		:rtype: Component or None
		"""

		if not self._rig_model:
			return None

		success = utils.check_scene_units(parent=self._ui_interface.builder())
		if not success:
			return None

		name = descriptor.get('name', name) if descriptor is not None else name
		side = descriptor.get('side', side) if descriptor is not None else side

		components_to_create = {'type': component_type, 'name': name, 'side': side, 'descriptor': descriptor}
		components = crit.create_components(self._rig_model.rig, components=[components_to_create], build_guides=True)
		self.request_refresh(False)

		return components[0] if components else None


class DuplicateComponentsUiCommand(command.CritUiCommand):

	ID = 'duplicateComponents'
	UI_DATA = {'icon': 'clone', 'label': 'Duplicate Selected Components'}

	@override(check_signature=False)
	def execute(self):
		"""
		Duplicates components that are currently selected within components tree widget.
		"""

		if not self._rig_model:
			return

		component_info = []
		for selected_component_model in self._selected_component_models:
			selected_component = selected_component_model.component
			component_info.append(
				{'component': selected_component, 'name': selected_component.name(), 'side': selected_component.side()})

		current_rig = self._rig_model.rig
		current_rig.clear_components_cache()
		crit.duplicate_components(current_rig, sources=component_info)

		self.request_refresh(False)


class DeleteComponentUiCommand(command.CritUiCommand):

	ID = 'deleteComponent'
	UI_DATA = {'icon': 'trash', 'label': 'Delete Components'}

	@override(check_signature=False)
	def execute(self):
		"""
		Deletes current selected components.
		"""

		if not self._rig_model:
			return

		selection = self.selected_component_models
		if not selection:
			return

		current_rig = self._rig_model.rig
		current_rig.clear_components_cache()
		crit.delete_components(current_rig, [component_model.component for component_model in selection])
		self.request_refresh(False)


class DeleteAllComponentsUiCommand(command.CritUiCommand):

	ID = 'deleteAllComponents'
	UI_DATA = {'icon': 'trash', 'label': 'Delete All Components'}

	@override(check_signature=False)
	def execute(self):
		"""
		Deletes all components of current active rig.
		"""

		current_rig = self._rig_model.rig
		current_rig.clear_components_cache()
		components = self._rig_model.rig.components()
		if not components:
			return

		crit.delete_components(current_rig, components)
