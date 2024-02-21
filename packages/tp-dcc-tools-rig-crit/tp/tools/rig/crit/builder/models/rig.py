from __future__ import annotations

import typing
from typing import List

from tp.commands import crit
from tp.common.python import profiler

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.rig import Rig
	from tp.libs.rig.crit.meta.rig import CritRig
	from tp.tools.rig.crit.builder.models.component import ComponentModel


class RigModel:
	"""
	Class that wraps a rig instance within current scene and can be used to interact with that rig and ensures that
	rig scene and rig data are synced.
	"""

	def __init__(self, rig: Rig | None = None):
		super().__init__()

		self._rig = rig
		self._component_models = []				# type: List[ComponentModel]

	@property
	def rig(self) -> Rig:
		return self._rig

	@property
	def name(self) -> str:
		return self._rig.name()

	@name.setter
	def name(self, value: str):
		crit.rename_rig(self._rig, value)

	@property
	def component_models(self) -> List[ComponentModel]:
		return self._component_models

	@property
	def meta(self) -> CritRig:
		return self._rig.meta

	def exists(self) -> bool:
		"""
		Returns whether rig instance exists within current scene.

		:return: True if rig exists within current scene; False otherwise.
		:rtype: bool
		"""

		return self._rig is not None and self._rig.exists()

	def add_component_model(self, component_model: ComponentModel):
		"""
		Adds given component model into this rig model.

		:param ComponentModel component_model: component model instance to add.
		"""

		self._component_models.append(component_model)

	@profiler.fn_timer
	def delete(self):
		"""
		Deletes rig.
		"""

		crit.delete_rig(self._rig)
