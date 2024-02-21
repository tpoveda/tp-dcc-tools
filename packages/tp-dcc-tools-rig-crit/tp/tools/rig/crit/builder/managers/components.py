from __future__ import annotations

import os
import typing
from typing import Tuple

from tp.common import plugin

from tp.tools.rig.crit.builder.models import component

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.component import Component
	from tp.libs.rig.crit.core.managers import ComponentsManager


class ComponentsModelManager:
	"""
	Manager that handles matching custom component models to CRIT components.
	"""

	MANAGER_ENV = 'CRIT_COMPONENT_MODELS_PATHS'

	def __init__(self, components_manager: ComponentsManager):
		super().__init__()

		self._components_manager = components_manager
		self._models = {}
		self._manager = plugin.PluginFactory(interface=component.ComponentModel, plugin_id='component_type')

	def discover_components(self) -> bool:
		"""
		Searches all component models implementations located within 'CRIT_COMPONENT_MODELS_PATHS' environment variable
		paths.

		:return: True if discover component process was successful; False otherwise.
		:rtype: bool
		"""

		self._models.clear()
		paths = os.environ.get(self.MANAGER_ENV, '').split(os.pathsep)
		if not paths:
			return False

		self._manager.register_paths(paths)
		models = {model.component_type: {'model': model} for model in self._manager.plugins()}
		for crit_type, data in self._components_manager.components.items():
			if crit_type in models:
				models[crit_type].update({'component': data['object'], 'type': crit_type})
			else:
				models[crit_type] = {'component': data['object'], 'model': component.ComponentModel, 'type': crit_type}

		self._models = models

		return True

	def find_component_model(self, component_type: str) -> Tuple[component.ComponentModel, str] | None:
		"""
		Returns a matching component model instance for given component type.

		:param str component_type: component type.
		:return: found component model with given type.
		:rtype: Tuple[component.ComponentModel, str] or None
		"""

		found_model = self._models.get(component_type, {})
		if not found_model:
			return None

		return found_model['model'], found_model['type']

	def find_component(self, component_type: str) -> Component | None:
		"""
		Returns a matching component model instance for given component type.

		:param str component_type: component type.
		:return: found component model with given type.
		:rtype: Component or None
		"""

		found_model = self._models.get(component_type, {})
		return found_model.get('component', None)
