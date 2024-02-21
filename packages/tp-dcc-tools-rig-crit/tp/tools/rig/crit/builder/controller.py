from __future__ import annotations

import typing
from typing import List, Dict

from tp.core import log
from tp.common.python import profiler
from tp.common.qt import api as qt

from tp.libs.rig.crit import api as crit
from tp.tools.rig.crit.builder.core import command
from tp.tools.rig.crit.builder.models import selection, rig, component
from tp.tools.rig.crit.builder.managers import components

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.rig import Rig
	from tp.libs.rig.crit.core.component import Component
	from tp.libs.rig.crit.descriptors.component import ComponentDescriptor
	from tp.libs.rig.crit.core.managers import ComponentsManager
	from tp.libs.rig.crit.meta.rig import CritRig
	from tp.tools.rig.crit.builder.ui import CritBuilderWindow
	from tp.tools.rig.crit.builder.interface import CritUiInterface
	from tp.tools.rig.crit.builder.managers.commands import UiCommandsManager
	from tp.tools.rig.crit.builder.managers.editors import EditorsManager

logger = log.rigLogger


class CritBuilderController(qt.QObject):
	"""
	Main controller class for CRIT Builder. Holds the status of rig and component models.

	Builder UI uses this controller to:
		- Find oud what is the current rig and its associated components.
		- Add rigs and components.
		- Modify rigs and components.
		- Delete rigs and components.

	This controller works with rig and component models to modify any data.

	CritBuilderController
		RigContainer (collection of rigs)
			RigModel
			ComponentModels
		SelectionModel (selected components).
	"""

	rigAdded = qt.Signal()
	rigRenamed = qt.Signal()
	rigDeleted = qt.Signal()
	rigsChanged = qt.Signal()
	componentAdded = qt.Signal()
	currentRigContainerChanged = qt.Signal(str)

	def __init__(
			self, components_manager: ComponentsManager, editors_manager: EditorsManager,
			ui_commands_manager: UiCommandsManager, ui_interface: CritUiInterface):
		super().__init__()

		self._components_manager = components_manager
		self._editors_manager = editors_manager
		self._ui_commands_manager = ui_commands_manager
		self._ui_interface = ui_interface
		self._ui_interface.set_controller(self)

		self._rig_containers = []											# type: List[RigContainer]
		self._current_rig_container = None									# type: RigContainer
		self._selection_model = selection.SelectionModel()

		self._components_models_manager = components.ComponentsModelManager(self._components_manager)
		self._components_models_manager.discover_components()

	@property
	def ui_interface(self) -> CritUiInterface:
		return self._ui_interface

	@property
	def components_manager(self) -> ComponentsManager:
		return self._components_manager

	@property
	def editors_manager(self) -> EditorsManager:
		return self._editors_manager

	@property
	def ui_commands_manager(self) -> UiCommandsManager:
		return self._ui_commands_manager

	@property
	def components_models_manager(self) -> components.ComponentsModelManager:
		return self._components_models_manager

	@property
	def current_rig_container(self) -> RigContainer | None:
		return self._current_rig_container

	@property
	def selection_model(self) -> selection.SelectionModel:
		return self._selection_model

	def crit_builder(self) -> CritBuilderWindow | None:
		"""
		Returns CRIT Builder window instance.

		:return: builder window instance.
		:rtype: CritBuilderWindow or None
		"""

		return self._ui_interface.builder() if self._ui_interface else None

	def rig_mode(self) -> int | None:
		"""
		Returns current rig mode.

		:return: rig mode.
		:rtype: int or None
		"""

		if self._current_rig_container is None or not self._current_rig_container.rig_exists():
			return

		return self._current_rig_container.rig_model.rig.build_state()

	def current_rig_exists(self) -> bool:
		"""
		Returns whether a rig container is active and whether the rig within the active rig container exists within
		current scene.

		:return: True if rig exists within scene; False otherwise.
		:rtype: bool
		"""

		return bool(self._current_rig_container is not None and self._current_rig_container.rig_exists())

	def rig_names(self) -> List[str]:
		"""
		Returns all the rig names available within current scene.

		:return: list of rig names.
		:rtype: List[str]
		"""

		return [rig_container.rig_model.name for rig_container in self._rig_containers]

	def add_rig(self, name: str | None = None, set_current: bool = True) -> rig.RigModel | None:
		"""
		Creates a new rig.

		:param str or None name: optional name of the rig.
		:param bool set_current: whether new rig container should be set as the active rig container.
		:return: newly created rig model.
		:rtype: RigModel or None
		"""

		new_rig = self.execute_ui_command('createRig', {'name': name})
		if not new_rig:
			return None

		rig_model = rig.RigModel(rig=new_rig)
		rig_container = RigContainer(rig_model)
		self._rig_containers.append(rig_container)
		if set_current:
			self._current_rig_container = rig_container
		self.rigAdded.emit()

		return rig_model

	def rename_rig(self):
		"""
		Renames current active rig.
		"""

		self.execute_ui_command('renameRig')

	def delete_rig(self, rig_to_delete: rig.RigModel | RigContainer) -> bool:
		"""
		Deletes given rig.

		:param rig.RigModel or RigContainer rig_to_delete: rig model or rig container to delete.
		:return: True if rig was deleted successfully; False otherwise.
		:rtype: bool
		"""

		if isinstance(rig_to_delete, rig.RigModel):
			for rig_container in self._rig_containers:
				if rig_container.rig_model == rig_to_delete:
					self._rig_containers.remove(rig_container)
					rig_to_delete.delete()
					self.rigDeleted.emit()
					return True
		elif isinstance(rig_to_delete, RigContainer):
			for rig_container in self._rig_containers:
				if rig_container == rig_to_delete:
					self._rig_containers.remove(rig_container)
					rig_to_delete.rig_model.delete()
					self.rigDeleted.emit()
					return True

		return False

	def add_component(
			self, component_type: str, component_name: str | None = None, side: str | None = None,
			descriptor: ComponentDescriptor | None = None) -> component.ComponentModel | None:
		"""
		Creates a new component.

		:param str component_type: type of the component to create.
		:param str component_name: name of the component to create.
		:param str side: side of the component to create.
		:param ComponentDescriptor descriptor: optional component descriptor to use.
		:return: newly created component model.
		:rtype: component.ComponentModel or None
		"""

		if not self._current_rig_container:
			return None

		component_model, component_type = self._components_models_manager.find_component_model(component_type)
		if not component_model:
			return None

		new_component = self.execute_ui_command(
			'createComponent',
			dict(component_type=component_type, name=component_name, side=side, descriptor=descriptor))
		new_component_model = component_model(component=new_component, rig_model=self._current_rig_container.rig_model)
		self._current_rig_container.add_component_model(new_component_model)
		self.componentAdded.emit()

		return new_component_model

	def set_selected_components(self, component_models: List[component.ComponentModel]):
		"""
		Sets currently selected component models.

		:param List[component.ComponentModel] component_models: list of selected component models.
		"""

		self._selection_model.component_models = component_models

	def rig_by_name(self, name: str) -> Rig | None:
		"""
		Returns rig instance that matches given name.

		:param str name: name of the rig to get.
		:return: rig instance.
		:rtype: Rig or None
		"""

		found_rig = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model.name == name:
				found_rig = rig_container.rig_model.rig
				break

		return found_rig

	def rig_model_by_name(self, name: str) -> rig.RigModel | None:
		"""
		Returns rig model instance that matches given name.

		:param str name: name of the rig model to get.
		:return: rig model instance.
		:rtype: model.RigModel or None
		"""

		found_rig_model = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model.name == name:
				found_rig_model = rig_container.rig_model
				break

		return found_rig_model

	def needs_refresh(self) -> bool:
		"""
		Returns whether CRIT UIs need to be refreshed.

		:return: True if CRIT Uis need to be refreshed; False otherwise.
		:rtype: bool
		..info:: this function is pretty cheap (O(n) speed for n number of rigs).
		"""

		rig_meta_nodes = list(crit.iterate_scene_rig_meta_nodes())
		if len(rig_meta_nodes) != len(self._rig_containers):
			logger.debug('Number of scene rigs does not much number of UI rigs, CRIT UIs need to be refreshed.')
			return True

		for rig_meta_node in rig_meta_nodes:
			container = self.container_by_rig_meta_node(rig_meta_node)
			if not container:
				logger.debug(
					f'Cannot find matching container for rig meta node "{rig_meta_node}", CRIT UIs need to be refreshed.')
				return True

	def refresh(self):
		"""
		Finds all rigs within current scene updates the internal controller data so UIs can be updated properly.

		..warning:: this is an expensive process, so we should call this function sparingly.
		"""

		self._rig_containers.clear()

		for found_rig in crit.iterate_scene_rigs():
			rig_container = RigContainer(rig.RigModel(found_rig))
			for rig_component in found_rig.iterate_components():
				component_model = self.create_component_model(rig_component, rig_container)
				rig_container.add_component_model(component_model)
			self._rig_containers.append(rig_container)

		if not self._rig_containers:
			self._current_rig_container = RigContainer(None)

		self.rigsChanged.emit()

	def create_component_model(
			self, component_instance: Component, rig_container: RigContainer) -> component.ComponentModel | None:
		"""
		Creates a new component model for given component instance.

		:param Component component_instance: rig component instance.
		:param RigContainer rig_container: rig container that contains the rig given component belongs to.
		:return: newly created component model.
		:rtype: ComponentModel or None
		"""

		if not component_instance:
			return None

		component_type = component_instance.component_type
		model_class, model_type = self._components_models_manager.find_component_model(component_type)
		if not model_class:
			component_model = component.ComponentModel(component_instance, rig_container.rig_model)
			component_model.component_type = model_type
		else:
			component_model = model_class(component_instance, rig_container.rig_model)

		return component_model

	def rig_container_by_model(self, rig_model: rig.RigModel) -> RigContainer | None:
		"""
		Returns the rig container that wraps given rig model.

		:param rig.RigModel rig_model: rig model instance.
		:return: found rig container.
		:rtype: RigContainer or None
		"""

		found_rig_container = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model == rig_model:
				found_rig_container = rig_container
				break

		return found_rig_container

	def rig_container_by_name(self, name: str) -> RigContainer | None:
		"""
		Returns the rig container that wraps rig model with given name.

		:param str name: name of the rig.
		:return: found rig container.
		:rtype: RigContainer or None
		"""

		found_rig_container = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model.name == name:
				found_rig_container = rig_container
				break

		return found_rig_container

	def container_by_rig(self, rig_instance: Rig) -> RigContainer | None:
		"""
		Finds rig container for given rig instance.

		:param Rig rig_instance: rig instance whose container we want to retrieve.
		:return: found rig container.
		:rtype: RigContainer or None
		"""

		found_container = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model.rig == rig_instance:
				found_container = rig_container
				break

		return found_container

	def container_by_rig_meta_node(self, rig_meta_node: CritRig) -> RigContainer | None:
		"""
		Finds rig container for given rig instance.

		:param CritRig rig_meta_node: rig meta node instance whose container we want to retrieve.
		:return: found rig container.
		:rtype: RigContainer or None
		"""

		found_container = None
		for rig_container in self._rig_containers:
			if rig_container.rig_model.meta == rig_meta_node:
				found_container = rig_container
				break

		return found_container

	def set_current_rig_container(self, rig_model: rig.RigModel) -> rig.RigModel:
		"""
		Sets the current active rig container that contains the given rig model.

		:param rig.RigModel rig_model: rig model instance.
		:return: active rig model instance.
		:rtype: rig.RigModel
		"""

		rig_container = self.rig_container_by_model(rig_model)
		self._current_rig_container = rig_container
		self._selection_model.rig_model = self._current_rig_container.rig_model
		self.currentRigContainerChanged.emit(self._current_rig_container.rig_model.name)

		return self._current_rig_container.rig_model

	def set_current_rig_container_by_name(self, rig_name: str) -> rig.RigModel:
		"""
		Sets current active rig container that contains the rig model with given name.

		:param str rig_name: name of the rig whose container we want to set as active.
		:return: active rig model instance.
		:rtype: rig.RigModel
		"""

		rig_container = self.rig_container_by_name(rig_name)
		if rig_container is not None:
			self._current_rig_container = rig_container
			self._selection_model.rig_model = self._current_rig_container.rig_model
			self.currentRigContainerChanged.emit(rig_name)

		return self._current_rig_container.rig_model

	@profiler.fn_timer
	def execute_ui_command(self, command_id: str, args: Dict | None = None):
		"""
		Executes a CRIT UI command.

		:param str command_id: CRIT command ID to execute.
		:param Dict or None args: optional arguments to pass to the command to execute.
		:return:
		"""

		ids = command_id.split('.')
		variant_id = None
		if len(ids) > 1:
			variant_id = ids[1]
			command_id = ids[0]

		found_command = self._ui_commands_manager.plugin(
			command_id)(logger, self._ui_interface)				# type: command.CritUiCommand
		if found_command is None:
			logger.warning(f'CRIT UI Command with ID "{command_id}" not found!')
			return None

		args = args or {}
		if variant_id:
			args['variant'] = variant_id
		found_command.set_selected(self._selection_model)
		logger.info(f'Executing CRIT UI Command: "{found_command.ID}"')
		found_command.refreshRequested.connect(self._ui_interface.refresh_ui)
		return found_command.process(variant_id=variant_id, args=args)


class RigContainer:

	def __init__(self, rig_model: rig.RigModel | None, component_models: Dict[component.ComponentModel] | None = None):
		super().__init__()

		self._rig_model = rig_model
		self._component_models = component_models or {}

	@property
	def rig_model(self) -> rig.RigModel:
		return self._rig_model

	@property
	def component_models(self) -> List[component.ComponentModel] | None:
		return self._component_models

	def rig_exists(self) -> bool:
		"""
		Returns whether this rig container has an associated rig model and whether the rig model is pointing to a valid
		rig within current scene.

		:return: True if rig model exists; False otherwise.
		:rtype: bool
		"""

		return self._rig_model and self._rig_model.exists()

	def add_component_model(self, component_model: component.ComponentModel):
		"""
		Adds given component model into the rig model.

		:param ComponentModel component_model: component model instance.
		"""

		self._component_models[hash(component_model)] = component_model
		self._rig_model.add_component_model(component_model)
