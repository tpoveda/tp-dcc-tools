from __future__ import annotations

import typing
from typing import List

from tp.core import log, dcc
from tp.common.python import helpers, strings, path, folder, fileio
from tp.common.qt import api as qt

from tp.libs.rig.crit import api as crit
from tp.tools.rig.crit.builder import controller
from tp.tools.rig.crit.builder.managers import components
from tp.tools.rig.crit.builder.models import selection, rig
from tp.tools.rig.crit.componentseditor.core import template

if typing.TYPE_CHECKING:
	from tp.common.naming.manager import NameManager
	from tp.libs.rig.crit.core.managers import ComponentsManager
	from tp.tools.rig.crit.builder.models.component import ComponentModel

logger = log.rigLogger


def valid_component_name(name: str, components_manager: ComponentsManager) -> str:
	"""
	Returns a valid component name for a new rig component.

	:param str name: component name.
	:param ComponentsManager components_manager: components manager instance to check existence of other components..
	:return: valid module component that does not clash with others already existing modules.
	:rtype: str
	"""

	name = name or 'NewRigComponent'
	# TODO: Check that name do not clash with other component names
	return name.lower().replace(' ', '')


def create_component(
		root_path: str, name: str, side: str, description: str = '', display_name: str = '',
		icon_path: str = '') -> bool:
	"""
	Creates a new rig component in disk within given path.

	:param str root_path: root path where component will be stored.
	:param str name: component name.
	:param str side: component default side.
	:param str description: optional component description.
	:param str display_name: optional component display name.
	:param str icon_path: optional component icon path.
	:return: True if component was created successfully; False otherwise.
	:rtype: bool
	"""

	if not path.is_dir(root_path):
		logger.warning('Given Module Path directory does not exists: "{}"'.format(root_path))
		return False

	display_name = strings.string_to_camel_case(display_name or name)
	component_path = path.join_path(root_path, name)
	if path.is_dir(component_path):
		logger.warning('Given Module Path directory does not exists: "{}"'.format(component_path))
		return False

	if icon_path and not path.is_file(icon_path):
		icon_path = None
	descriptor_template = template.latest_descriptor_template()
	if not descriptor_template:
		logger.warning('Latest Rig Component Descriptor Template was not found!')
		return False
	component_template = template.latest_component_template()
	if not component_template:
		logger.warning('Latest Rig Component Template was not found!')
		return False

	template_data = dict(
		name=name, displayName=display_name, description=description, type='CRIT.{}'.format(name), side=side)
	for template_key, template_value in template_data.items():
		descriptor_template = descriptor_template.replace('{{{' + template_key + '}}}', template_value)

	component_template = component_template.replace('TemplateRigModule', display_name).replace(
		'ID = None', "ID = 'CRIT.{}'".format(name))
	temp_folder = folder.get_temp_folder()
	module_temp_folder = path.join_path(temp_folder, name)
	if path.is_dir(module_temp_folder):
		folder.delete_folder(module_temp_folder)

	version_folder = folder.create_folder('v001', module_temp_folder)
	fileio.create_file('__init__.py', module_temp_folder)
	fileio.create_file('__init__.py', version_folder)
	module_descriptor_file = fileio.create_file('{}.descriptor'.format(name), version_folder)
	module_file = fileio.create_file('{}.py'.format(name), version_folder)

	fileio.write_lines(module_descriptor_file, descriptor_template.split('\n'))
	fileio.write_lines(module_file, component_template.split('\n'))

	if icon_path:
		fileio.copy_file(icon_path, path.join_path(version_folder, 'thumb.png'))

	result = folder.move_folder(module_temp_folder, component_path)

	return result


class CritComponentsEditorController(qt.QObject):

	availableComponentPathsChanged = qt.Signal(list)
	availableSidesChanged = qt.Signal(list)
	availableComponentsChanged = qt.Signal(dict)
	activePathChanged = qt.Signal(str)
	activeComponentChanged = qt.Signal(str)
	activeComponentModelChanged = qt.Signal(object)
	newComponentNameChanged = qt.Signal(str)
	newComponentSideChanged = qt.Signal(str)
	newComponentIconPathChanged = qt.Signal(str)
	newComponentDescriptionChanged = qt.Signal(str)
	newComponentAdded = qt.Signal()
	newComponentModelAdded = qt.Signal()
	startEditingComponent = qt.Signal(bool)

	def __init__(self, components_manager: ComponentsManager, name_manager: NameManager):
		super().__init__()

		self._components_manager = components_manager
		self._name_manager = name_manager
		self._components_models_manager = components.ComponentsModelManager(self._components_manager)
		self._components_models_manager.discover_components()

		self._available_paths = []
		self._available_sides = []
		self._available_components = {}
		self._active_component = ''

		self._active_path = ''
		self._new_component_name = ''
		self._new_component_side = 'M'
		self._new_component_icon_path = ''
		self._new_component_description = ''

		self._current_rig_container = None			# type: controller.RigContainer
		self._active_component_model = None			# type: ComponentModel
		self._selection = selection.SelectionModel()

	@property
	def components_managers(self) -> ComponentsManager:
		return self._components_manager

	@property
	def available_paths(self) -> List[str]:
		return self._available_paths

	@property
	def active_path(self) -> str:
		return self._active_path

	@active_path.setter
	def active_path(self, value: str):
		self._active_path = value
		self.activePathChanged.emit(self._active_path)

	@property
	def active_component(self) -> str:
		return self._active_component

	@active_component.setter
	def active_component(self, value: str):
		self._active_component = value
		self.activeComponentChanged.emit(self._active_component)
		if self._active_component:
			self.edit_rig_component()

	@property
	def new_component_name(self) -> str:
		return self._new_component_name

	@new_component_name.setter
	def new_component_name(self, value: str):
		self._new_component_name = value
		self.newComponentNameChanged.emit(self._new_component_name)

	@property
	def new_component_side(self) -> str:
		return self._new_component_side

	@new_component_side.setter
	def new_component_side(self, value: str):
		self._new_component_side = value
		self.newComponentSideChanged.emit(self._new_component_side)

	@property
	def new_component_icon_path(self) -> str:
		return self._new_component_icon_path

	@new_component_icon_path.setter
	def new_component_icon_path(self, value: str):
		self._new_component_icon_path = value
		self.newComponentIconPathChanged.emit(self._new_component_icon_path)

	@property
	def new_component_description(self) -> str:
		return self._new_component_description

	@new_component_description.setter
	def new_component_description(self, value: str):
		self._new_component_description = value
		self.newComponentDescriptionChanged.emit(self._new_component_description)

	@property
	def module_path(self) -> str:
		if not self._new_component_name or not self._active_path:
			return ''

		return path.join_path(self._active_path, self._new_component_name)

	@property
	def active_component_model(self) -> ComponentModel:
		return self._active_component_model

	@active_component_model.setter
	def active_component_model(self, value: ComponentModel):
		self._active_component_model = value
		self.activeComponentModelChanged.emit(self._active_component_model)

	def clear_creator(self):
		"""
		Clears creator.
		"""

		self.active_path = ''
		self.new_component_name = ''
		self.new_component_side = ''
		self.new_component_icon_path = ''
		self.new_component_description = ''

	def refresh(self):
		"""
		Refreshes all current available components and both components creator and editor.
		"""

		self._available_paths.clear()
		for components_path in self._components_manager.components_paths():
			self._available_paths.append(path.clean_path(components_path))
		self.availableComponentPathsChanged.emit(self._available_paths)

		self._available_sides.clear()
		side_token = self._name_manager.token('side')
		self._available_sides = sorted(list([i.name for i in side_token.iterate_key_values()]))
		self.availableSidesChanged.emit(self._available_sides)

		self.refresh_components()

		if not self._active_path:
			self._active_path = helpers.first_in_list(self._available_paths, default='')
		self.activePathChanged.emit(self._active_path)

	def refresh_components(self):
		"""
		Refreshes all current available components.
		"""

		self._available_components.clear()
		self._components_manager.refresh()
		self._components_models_manager.discover_components()
		for name, component_data in self._components_manager.components.items():
			component_data['icon'] = component_data['object'].ICON
			self._available_components[name] = component_data

		self.availableComponentsChanged.emit(self._available_components)

	def refresh_editor(self):
		"""
		Refreshes components editor.
		"""

		dcc.new_scene(force=True, do_save=False)

		if self._current_rig_container and not self._current_rig_container.rig_exists():
			self._current_rig_container = None
			self.active_component_model = None

		builder_rig = crit.root_by_rig_name('builder')
		if not builder_rig:
			self.add_editor_rig()

		if self._current_rig_container:
			self._selection.rig_model = self._current_rig_container.rig_model

		self._components_models_manager.discover_components()

		self.add_editor_component()

	def add_rig_component(self):
		"""
		Adds rig component.
		"""

		component_name = valid_component_name(self._new_component_name, components_manager=self._components_manager)
		result = create_component(
			root_path=self._active_path, name=component_name, side=self._new_component_side or 'center',
			description=self._new_component_description, display_name=self._new_component_name,
			icon_path=self._new_component_icon_path)
		if not result:
			logger.error('Something went wrong while creating rig component folders and files.')
			return

		self.clear_creator()
		self.refresh_components()

		self.newComponentAdded.emit()

	def edit_rig_component(self):
		"""
		Edits rig component.
		"""

		if not self._active_component:
			logger.warning('No active component to edit.')
			self.startEditingComponent.emit(False)
			return

		component_data = self._components_manager.component_data(self._active_component)
		if not component_data:
			logger.warning('No component data found.')
			self.active_component = ''
			self.startEditingComponent.emit(False)
			return

		self.startEditingComponent.emit(True)

	def add_editor_rig(self) -> rig.RigModel:
		"""
		Adds a new builder rig if it does not already exist within DCC scene.

		:return: rig model instance.
		:rtype: rig.RigModel
		"""

		if self._current_rig_container:
			self._selection.rig_model = self._current_rig_container.rig_model
			return self._current_rig_container.rig_model

		new_rig = crit.create_rig(name='builder')
		rig_model = rig.RigModel(rig=new_rig)
		rig_container = controller.RigContainer(rig_model)
		self._current_rig_container = rig_container

		return rig_model

	def add_editor_component(self) -> ComponentModel | None:
		"""
		Adds a new component to the editor rig into current DCC scene.

		:return: newly created component model.
		:rtype: ComponentModel or None
		"""

		if self._active_component_model:
			logger.warning('A rig component already exist within scene...')
			return None

		if not self._active_component:
			logger.warning('No active component set')
			return None

		model_class, component_type = self._components_models_manager.find_component_model(self._active_component)

		component_name = self._active_component
		if component_name.startswith('CRIT.'):
			component_name = component_type[5:]
		component_data = {'type': component_type, 'name': component_name, 'side': 'C', 'descriptor': None}
		new_component = crit.create_components(
			rig=self._current_rig_container.rig_model.rig, components=[component_data], build_guides=True)
		new_model = model_class()
		new_model.component = new_component
		new_model.rig_model = self._current_rig_container.rig_model
		self.active_component_model = new_model
		self.newComponentModelAdded.emit()

		return new_model
