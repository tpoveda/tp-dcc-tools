from __future__ import annotations

import typing
from typing import Callable

from overrides import override

from tp.common.qt import api as qt
from tp.preferences.interfaces import core
from tp.common.resources import api as resources
from tp.common.resources import icon
from tp.common.qt.widgets import groupedtreewidget

from tp.tools.rig.crit.builder.views import editor
from tp.tools.rig.crit.builder.widgets import treewidget

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.managers import ComponentsManager
	from tp.tools.rig.crit.builder.managers.components import ComponentsModelManager
	from tp.tools.rig.crit.builder.views.createview import CreateView


class ComponentsLibraryEditor(editor.EditorView):

	ID = 'ComponentsLibrary'
	NAME = 'Components Library'
	TOOLTIP = 'Allows to add new rig components into a CRIT rig'
	DEFAULT_DOCK_AREA = qt.Qt.LeftDockWidgetArea
	IS_SINGLETON = True

	def __init__(self, parent: qt.QWidget | None = None):
		super().__init__(parent)

		self._create_view = None							# type: CreateView
		self._components_manager = None						# type: ComponentsManager
		self._components_model_manager = None				# type: ComponentsModelManager
		self._components_library_widget = None				# type: ComponentsLibraryWidget

	@override(check_signature=False)
	def show(
			self, create_view: CreateView, components_manager: ComponentsManager,
			components_model_manager: ComponentsModelManager) -> None:

		self._create_view = create_view
		self._components_manager = components_manager
		self._components_model_manager = components_model_manager

		if not self._components_library_widget:
			self._components_library_widget = ComponentsLibraryWidget(
				components_manager=components_manager,
				components_model_manager=components_model_manager, parent=create_view)
			self.setWidget(self._components_library_widget)


class ComponentsLibraryWidget(treewidget.TreeWidgetFrame):
	"""
	Component Library tree widget that shows the list of component current available for the user.
	When an element of the tree is clicked, a new component is created and added to the components tree view.
	"""

	def __init__(
			self, components_manager: ComponentsManager | None = None,
			components_model_manager: ComponentsModelManager | None = None, locked: bool = False,
			parent: CreateView | None = None):
		super().__init__(title='COMPONENTS', parent=parent)

		self._theme_pref = core.theme_preference_interface()
		self._theme_pref.updated.connect(self._on_update_theme)

		self._menu_button = qt.IconMenuButton(parent=parent)
		components_tree_widget = ComponentsLibraryTreeWidget(
			components_manager, components_model_manager, locked, parent)
		components_tree_widget.set_drag_drop_enabled(False)

		self.setup_ui(components_tree_widget)
		self.setup_signals()

	@override
	def setup_toolbar(self) -> qt.QHBoxLayout:
		toolbar_layout = super().setup_toolbar()

		self._menu_button.setFixedHeight(20)
		self._menu_button.set_icon('menu_dots', colors=self._theme_pref.MAIN_FOREGROUND_COLOR, size=16)
		toolbar_layout.addWidget(self._menu_button)
		self._menu_button.hide()

		self._menu_button.addAction(
			'Add Group', connect=self._on_add_group_action_triggered, action_icon=resources.icon('folder'))
		self._menu_button.addAction(
			'Delete Group', connect=self._on_delete_group_action_triggered, action_icon=resources.icon('trash'))

		return toolbar_layout

	def _on_update_theme(self, event: 'ThemeUpdateEvent'):
		"""
		Internal callback function that is called when theme is updated.

		:param ThemeUpdateEvent event: theme event.
		"""

		self._menu_button.set_icon('menu_dots', colors=event.theme_dict.MAIN_FOREGROUND_COLOR, size=16)

	def _on_add_group_action_triggered(self):
		"""
		Internal callback function that is called when Add Group action is clicked by the user.
		"""

		self.add_group()

	def _on_delete_group_action_triggered(self):
		"""
		Internal callback function that is called when Delete Group action is clicked by the user.
		"""

		self.delete_group()


class ComponentsLibraryTreeWidget(groupedtreewidget.GroupedTreeWidget):
	"""
	Custom tree widget that contains the list of components that we can add to the rig.
	"""

	class ComponentItemWidget(groupedtreewidget.GroupedTreeWidget.ItemWidgetLabel):
		def __init__(
				self, name: str, components_model_manager: ComponentsModelManager, action_event: Callable | None = None,
				parent: qt.QWidget | None = None):

			self._components_model_manager = components_model_manager
			self._icon = None													# type: qt.QIcon
			self._theme_pref = core.theme_preference_interface()

			super().__init__(name, parent=parent)

			self.setText('')
			self.connect_event(action_event)

		@property
		def icon(self) -> qt.QIcon:
			return self._icon

		@override
		def _setup_ui(self):
			super()._setup_ui()

			component_color = self._theme_pref.CRIT_COMPONENT_COLOR
			background_icon = resources.icon('rounded_square_filled')
			component_icon = resources.icon(self.component_icon())
			self._icon = icon.colorize_layered_icon(
				[background_icon, component_icon], size=qt.dpi_scale(16), colors=[component_color], scaling=[1, 0.7])

		def component_icon(self) -> str:
			"""
			Returns the icon name of the associated component.

			:return: component icon name.
			:rtype: str
			"""

			return self._components_model_manager.find_component(self._name).ICON

	def __init__(
			self, components_manager: ComponentsManager | None = None,
			components_model_manager: ComponentsModelManager | None = None, locked: bool = False,
			parent: CreateView | None = None):

		self._create_view = parent
		self._components_manager = components_manager
		self._components_model_manager = components_model_manager

		super().__init__(locked=locked, parent=parent)

		self.setRootIsDecorated(True)

	@override
	def _setup_ui(self):

		self.setSortingEnabled(False)

		super()._setup_ui()

		components = []
		for name, data in self._components_manager.components.items():
			components.append((name, data['object'].BETA_VERSION))

		for [name, is_beta] in components:
			component_item_widget = ComponentsLibraryTreeWidget.ComponentItemWidget(
				name, components_model_manager=self._components_model_manager,
				action_event=self._on_double_clicked_component_item, parent=self)
			new_name = name.replace('component', '')
			if is_beta:
				new_name += 'Beta'
			self.add_new_item(new_name, component_item_widget, icon=component_item_widget.icon, widget_info=name)

		self.setCurrentItem(None)
		self.setSortingEnabled(True)
		self.sortItems(0, qt.Qt.AscendingOrder)

	def _on_double_clicked_component_item(self):
		"""
		Internal callback function that is called when a component tree item widget is double-clicked by the user.
		"""

		self._create_view.create_component(self.sender().name.replace('Beta', ''))
