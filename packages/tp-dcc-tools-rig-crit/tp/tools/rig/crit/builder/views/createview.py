from __future__ import annotations

import typing

from tp.common.qt import api as qt

from tp.tools.rig.crit.builder.managers import components
from tp.tools.rig.crit.builder.views import componentstree, componentsoutliner

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.managers import ComponentsManager
	from tp.libs.rig.crit.descriptors.component import ComponentDescriptor
	from tp.tools.rig.crit.builder.interface import CritUiInterface
	from tp.tools.rig.crit.builder.models.rig import RigModel
	from tp.tools.rig.crit.builder.ui import CritBuilderWindow
	from tp.tools.rig.crit.builder.controller import CritBuilderController


class CreateView(qt.QWidget):

	def __init__(
			self, components_manager: ComponentsManager, controller: CritBuilderController,
			ui_interface: CritUiInterface, theme_prefs, parent: CritBuilderWindow | None = None):
		super().__init__(parent)

		self._components_manager = components_manager
		self._controller = controller
		self._ui_interface = ui_interface
		self._theme_prefs = theme_prefs
		self._crit_builder = parent
		self._components_model_manager = components.ComponentsModelManager(self._components_manager)
		self._components_model_manager.discover_components()

		# self._components_tree_view = componentstree.ComponentsTreeView(
		# 	components_manager=components_manager, components_model_manager=self._components_model_manager,
		# 	controller=self._controller, parent=self)
		# self._ui_interface.set_components_tree(self._components_tree_view.tree_widget)

		self._components_outliner = componentsoutliner.ComponentsOutliner(controller=controller, parent=self)
		self._ui_interface.set_components_tree(self._components_outliner.tree_widget)

		self._setup_ui()

	def apply_rig(self, rig_model: RigModel):
		"""
		Applies the given rig model to the component stack.

		:param RigModel rig_model: rig model instance.
		"""

		self._components_outliner.clear()
		self._components_outliner.apply_rig(rig_model)
		# Sync is already handled within apply_rig function.
		# self._components_outliner.sync()

	def clear_tree(self):
		"""
		Clears all the tree nodes in the tree widget.
		"""

		pass
		# self._components_tree_view.tree_widget.clear()

	def create_component(self, component_id: str, descriptor: ComponentDescriptor | None = None):
		"""
		Creates a new component.

		:param str component_id: ID of the component to create.
		:param ComponentDescriptor descriptor: optional component descriptor to use.
		:raises ValueError: if component creation fails.
		"""

		if not self._controller.current_rig_exists():
			self._controller.add_rig(set_current=True)

		component_model = self._controller.add_component(component_id, descriptor=descriptor)
		if component_model is None:
			raise ValueError(f'Was not possible to add component of type "{component_id}"')

	def _setup_ui(self):
		"""
		Internal function that setups create view UI.
		"""

		main_layout = qt.vertical_layout(margins=(0, 0, 0, 0))
		self.setLayout(main_layout)

		toolbar_layout = qt.horizontal_layout(margins=(0, 0, 0, 0))
		splitter = qt.QSplitter(self.parent())
		splitter.setHandleWidth(qt.dpi_scale(3))
		toolbar_layout.addWidget(splitter)

		main_layout.addLayout(toolbar_layout)
		main_layout.addWidget(self._components_outliner)
