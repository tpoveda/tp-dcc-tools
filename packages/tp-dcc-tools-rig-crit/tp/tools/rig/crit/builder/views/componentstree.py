from __future__ import annotations

import typing
from functools import partial
from typing import Tuple, List, Dict, Callable, Iterator

from overrides import override

from tp.core import log
from tp.commands import crit
from tp.common.qt import api as qt
from tp.common.python import strings
from tp.maya.api import attributetypes
from tp.preferences.interfaces import core
from tp.common.resources import api as resources

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core.component import Component
from tp.libs.rig.crit.meta.nodes import Guide
from tp.tools.rig.crit.builder.widgets import treewidget

if typing.TYPE_CHECKING:
    from tp.common.python.helpers import ObjectDict
    from tp.libs.rig.crit.core.managers import ComponentsManager
    from tp.tools.rig.crit.builder.core.command import CritUiCommand
    from tp.tools.rig.crit.builder.controller import CritBuilderController
    from tp.tools.rig.crit.builder.managers.components import ComponentsModelManager
    from tp.tools.rig.crit.builder.models.rig import RigModel
    from tp.tools.rig.crit.builder.models.component import ComponentModel

logger = log.rigLogger


class ComponentsTreeView(treewidget.TreeWidgetFrame):
    """
    Main view to show components. Is composed by:
    ComponentsTreeView
        SearchBar
        ComponentTreeWidget
            List(TreeWidgetItem)
    """

    def __init__(
            self, components_manager: ComponentsManager | None = None,
            components_model_manager: ComponentsModelManager | None = None,
            controller: CritBuilderController | None = None,
            parent: qt.QWidget | None = None):
        super().__init__(title='COMPONENTS', parent=parent)

        self._theme_prefs = core.theme_preference_interface()
        self._components_model_manager = components_model_manager
        self._controller = controller
        self._ui_interface = self._controller.ui_interface

        self._highlight_button = qt.base_button(parent=parent)
        self._select_in_scene_button = qt.base_button(parent=parent)
        self._group_button = qt.base_button(parent=parent)
        self._menu_button = qt.base_button(parent=parent)

        self.setup_ui(ComponentsTreeWidget(
            components_manager=components_manager, components_model_manager=components_model_manager,
            controller=controller, parent=self))
        self.setup_signals()

    @override
    def setup_ui(self, tree_widget: qt.QTreeWidget):
        super().setup_ui(tree_widget=tree_widget)
        self.setContentsMargins(0, 0, 0, 0)

    @override
    def setup_toolbar(self) -> qt.QHBoxLayout:
        result = super().setup_toolbar()

        highlight_ui_command = self._controller.ui_commands_manager.plugin(
            'highlightFromScene')(logger, ui_interface=self._ui_interface)
        select_in_scene_ui_command = self._controller.ui_commands_manager.plugin(
            'selectInScene')(logger, ui_interface=self._ui_interface)
        highlight_ui_command_data = highlight_ui_command.UI_DATA
        select_in_scene_ui_command_data = select_in_scene_ui_command.UI_DATA

        icon_size = 16
        foreground_color = self._theme_prefs.MAIN_FOREGROUND_COLOR
        self._highlight_button.set_icon(
            highlight_ui_command_data['icon'], colors=highlight_ui_command_data['iconColor'], size=icon_size)
        self._select_in_scene_button.set_icon(
            select_in_scene_ui_command_data['icon'], colors=select_in_scene_ui_command_data['iconColor'],
            size=icon_size)
        self._group_button.set_icon('add_folder', colors=foreground_color, size=icon_size)
        self._menu_button.set_icon('menu_dots', colors=foreground_color, size=icon_size)
        self._menu_button.menu_align = qt.Qt.AlignRight
        self._group_button.hide()

        self._toolbar_layout.addWidget(self._highlight_button)
        self._toolbar_layout.addWidget(self._select_in_scene_button)
        self._toolbar_layout.addWidget(self._group_button)
        self._toolbar_layout.addWidget(self._menu_button)

        actions = self.menu_actions()
        for command_ui, command_ui_type, variant_id in self._controller.ui_commands_manager.iterate_ui_commands_from_ids(
                actions):
            if command_ui_type == 'PLUGIN':
                new_command_ui = command_ui(logger, ui_interface=self._ui_interface)
                self._add_menu_action_ui_command(new_command_ui, variant_id)
            elif command_ui_type == 'SEPARATOR':
                self._menu_button.add_separator()

        return result

    def menu_actions(self) -> List[str]:
        """
        Returns a list of command UI action IDs that will be added into the components tree widget context menu.

        :return: list of command UI IDs.
        :rtype: List[str]
        """

        return [
            'selectInScene', 'highlightFromScene', 'minimizeAllComponents', 'maximizeAllComponents',
            'selectAllComponents', 'invertSelectedComponents', '---',
            'duplicateComponents', 'mirrorComponents', 'mirrorComponents:all', '---',
            'deleteAllComponents']

    def apply_rig(self, rig_model: RigModel):
        """
        Applies given rig model instance and fills tree widget.

        :param RigModel rig_model: rig model instance.
        """

        self.setUpdatesEnabled(False)
        try:
            for component_model in rig_model.component_models:
                self.add_component(component_model)
            self._tree_widget.clearSelection()
        finally:
            self.setUpdatesEnabled(True)

    def add_component(self, component_model: ComponentModel, group=None):
        """
        Adds given component model instance into the tree widget.

        :param ComponentModel component_model: component model instance.
        :param group:
        """

        self._tree_widget.add_component(component_model, group=group)

    def sync(self):
        """
        Syncs tree widget with the current model.
        """

        self._tree_widget.sync()

    def clear(self):
        """
        Clears out the tree widget.
        """

        self._tree_widget.clear()

    def _add_menu_action_ui_command(self, ui_command: CritUiCommand, variant_id: str | None = None):
        """
        Internal function that adds a UI command as a menu action.

        :param  CritUiCommand ui_command: UI command instance to add into the menu.
        :param str or None variant_id: optional command UI variant to use.
        """

        ui_data = ui_command.UI_DATA
        ui_command_label = ui_data['label']
        ui_command_icon = ui_data['icon']
        if variant_id:
            try:
                variant = [x for x in ui_command.variants() if x['id'] == variant_id][0]
                ui_command_label = variant['name']
                ui_command_icon = variant['icon']
            except Exception:
                raise Exception(F'Variant ID "{variant_id}" does not exist for "{ui_command}"')

        new_action = self._menu_button.addAction(ui_command_label, action_icon=ui_command.icon(), connect=None)
        new_action.setProperty('ui_command', ui_command)
        new_action.setProperty('variant', variant_id)

        ui_command.refreshRequested.connect(self.sync)

        try:
            action_icon = resources.icon(ui_command_icon)
            new_action.setIcon(action_icon)
        except AttributeError:
            pass

        new_action.triggered.connect(partial(self._execute_ui_command, ui_command, variant_id))

    def _execute_ui_command(self, ui_command: CritUiCommand, variant_id: str | None):
        """
        Internal function that executes the given UI command instance.

        :param CritUiCommand ui_command: UI command instance to execute.
        :param str or None variant_id: optional UI command variant to execute.
        """

        ui_command.set_selected(self._controller.selection_model)
        ui_command.component_model = None
        if len(self._controller.selection_model.component_models) > 0:
            ui_command.component_model = self._controller.selection_model.component_models[0]
        ui_command.process(variant_id)


class ComponentsTreeWidget(qt.GroupedTreeWidget):

    class ComponentWidget(qt.StackItem):
        """
        Stacked widget that represents a component within Components tree widget.
        """

        syncRequested = qt.Signal(bool)
        componentRenamed = qt.Signal(str, str)

        class SideNameWidget(qt.QWidget):

            renamed = qt.Signal(str)

            def __init__(
                    self, model: ComponentModel, show_label: bool = True, show_arrow: bool = True,
                    parent: ComponentsTreeWidget.ComponentWidget | None = None):
                super().__init__(parent)

                self._model = model
                self._show_label = show_label

                self._setup_ui()
                self._setup_signals()

                style_sheet = """
                QComboBox {
                    background-color: #30000000;
                }
                QComboBox:hover {
                    background-color: #88111111;
                }
                QComboBox::drop-down {
                    background-color: transparent;
                    border-left: 0px solid #33FF1111;
                }
                QComboBox::drop-down:pressed {
                    background-color: #8871a0d0;
                }

                QComboBox:pressed {
                    background-color: #8871a0d0;
                }
                """

                hide_arrow_style_sheet = """
                QComboBox::down-arrow { image: none; }
                """

                if not show_arrow:
                    style_sheet += hide_arrow_style_sheet

                self.setStyleSheet(style_sheet)

            def _setup_ui(self):
                """
                Internal function that setup widget UI.
                """

                main_layout = qt.horizontal_layout(parent=self)
                self._side_combo_box = qt.ComboBoxRegularWidget(
                    label='Side', items=[], label_ratio=4, box_ratio=16, sort_alphabetically=True,
                    support_middle_mouse_scroll=False, parent=self)
                self._side_combo_box.setFocusPolicy(qt.Qt.StrongFocus)
                self._update_combo()
                main_layout.addWidget(self._side_combo_box)
                if not self._show_label:
                    self._side_combo_box.label.hide()

            def _setup_signals(self):
                """
                Internal function that setup widget signal connections.
                """

                self._side_combo_box.itemChanged.connect(self._on_side_combo_box_item_changed)

            def _update_combo(self):
                """
                Internal function that updates side combo box items.
                """

                with qt.block_signals(self._side_combo_box):
                    naming_manager = self._model.component.naming_manager()
                    side_token = naming_manager.token('side')
                    sides = sorted(list([i.name for i in side_token.iterate_key_values()]))
                    side = side_token.value_for_key(self._model.side)
                    self._side_combo_box.clear()
                    self._side_combo_box.addItems(sides)
                    self._side_combo_box.set_to_text(side, qt.Qt.MatchFixedString | qt.Qt.MatchCaseSensitive)

            def _on_side_combo_box_item_changed(self, event: qt.ComboBoxRegularWidget.ComboItemChangedEvent):
                """
                Internal callback function that is called each time side com box widget items are changed.

                :param qt.ComboBoxRegularWidget.ComboItemChangedEvent event: item changed event.
                """

                side = str(self._model.component.naming_manager().token('side').value_for_key(event.text))
                self.renamed.emit(side)

        class ParentWidget(qt.QWidget):

            parentChanged = qt.Signal(Component, Guide)

            def __init__(
                    self, rig_model: RigModel | None = None, component_model: ComponentModel | None = None,
                    parent: ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget | None = None):
                super().__init__(parent)

                self._rig_model = rig_model
                self._component_model = component_model
                self._current_parent = None, None				# type: Tuple[Component, Guide]
                self._item_data = []							# type: List[List[Component, Guide]]

                main_layout = qt.horizontal_layout(parent=self)
                self._parent_combo = qt.ComboBoxRegularWidget(
                    label='Parent', box_ratio=16, label_ratio=4, support_middle_mouse_scroll=False, parent=self)
                self._parent_combo.setFixedHeight(qt.dpi_scale(21))
                main_layout.addWidget(self._parent_combo)
                self.setLayout(main_layout)

                self._setup_ui()
                self._setup_signals()

            @staticmethod
            def _item_name(component: Component, guide: Guide) -> str:
                """
                Internal static function that returns a valid parent item name.

                :param Component component: component instance.
                :param Guide guide: current guide instance.
                :return: item name.
                :rtype: str
                """

                return f'[{component.name()} {component.side()}] {guide.name(include_namespace=False)}'

            def is_current_parent(self, component: Component, guide: Guide) -> bool:
                """
                Returns whether current parent matches the given component and guide.

                :param Component component: component instance.
                :param Guide guide: current guide instance.
                :return: True if given component and guide matches current parent.
                :rtype: bool
                """

                if self._current_parent[0] is not None:
                    return self._current_parent == (component, guide)

                return False

            def update_combo(self):
                """
                Updates parent combo box contents.
                """

                with qt.block_signals(self._parent_combo):
                    self._parent_combo.clear()
                    self._item_data = [[None, None]]
                    self._parent_combo.add_item('')

                    if not self._rig_model:
                        return

                    self._current_parent = self._component_model.component.component_parent_guide()
                    combo_set = False

                    rig = self._rig_model.rig
                    for component in rig.components():
                        if component == self._component_model.component:
                            continue
                        guide_layer = component.guide_layer()
                        if not guide_layer:
                            continue
                        for guide in guide_layer.iterate_guides(include_root=False):
                            self._parent_combo.add_item(self._item_name(component, guide))
                            self._item_data.append([component, guide])
                            if self.is_current_parent(component, guide) and not combo_set:
                                combo_set = True
                                self._parent_combo.setCurrentIndex(self._parent_combo.count() - 1)

            def _setup_ui(self):
                """
                Internal function that setups component settings widgets.
                """

                self.update_combo()

            def _setup_signals(self):
                """
                Internal function that setups component settings signal connections.
                """

                self._parent_combo.itemChanged.connect(self._on_parent_combo_current_index_changed)

            def _on_parent_combo_current_index_changed(self, event: qt.ComboBoxRegularWidget.ComboItemChangedEvent):
                """
                Internal callback function that is called each time parent combo item changes.

                :param qt.ComboBoxRegularWidget.ComboItemChangedEvent event: combo item changed event.
                """

                data = self._item_data[self._parent_combo.current_index()]
                self.parentChanged.emit(data[0], data[1])
                self._current_parent = data[0], data[1]

        class ComponentSettingWidget(qt.QFrame):

            SHOW_SPACE_SWITCHING = True

            def __init__(
                    self, component_widget: ComponentsTreeWidget.ComponentWidget, component_model: ComponentModel,
                    parent: qt.QWidget | None = None):
                super().__init__(parent)

                self._component_model = component_model
                self._component_widget = component_widget
                self._rig_model = component_model.rig_model
                self._settings_widgets = []							# type: List[Tuple[Dict, qt.QWidget]]
                self._space_switch_layout_created = False
                self._naming_layout_created = False

                self._main_layout = qt.vertical_layout(margins=(6, 8, 6, 8), parent=self)
                self.setLayout(self._main_layout)

                self._parent_widget = ComponentsTreeWidget.ComponentWidget.ParentWidget(
                    rig_model=self._rig_model, component_model=self._component_model, parent=self)

                self._main_layout.addWidget(self._parent_widget)

                orient_setting = self._component_model.component.descriptor.guide_layer.guide_setting('manualOrient')
                manual_orient_widget = self.create_boolean_widget(
                    self, orient_setting, 'Manual Orient', self._main_layout, self._on_setting_checkbox_changed)
                self._settings_widgets.append((orient_setting, manual_orient_widget))

                self._setup_ui()
                self._setup_signals()

            @staticmethod
            def create_boolean_widget(
                    component_settings_widget: ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget,
                    setting: ObjectDict, name: str, layout: qt.QVBoxLayout, signal_fn: Callable) -> qt.BaseCheckBoxWidget:
                """
                Function that creates a new boolean setting widget.

                :param ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget component_settings_widget: component
                    settings widget.
                :param ObjectDict setting: setting dictionary. e.g:
                    {
                        'name': 'manualOrient', 'value': False, 'isArray': False, 'locked': False, 'default': False,
                        'channelBox': True, 'keyable': False, 'type': 0
                    }
                :param str name: setting display name.
                :param qt.QVBoxLayout layout: layout setting widget will be added into.
                :param Callable signal_fn: function to call when checkbox is checked.
                :return: newly created boolean widget.
                :rtype: qt.BaseCheckBoxWidget
                """

                checkbox = qt.checkbox_widget(
                    text=name, checked=setting.value, box_ratio=16, label_ratio=4, right=True,
                    parent=component_settings_widget)
                layout.addWidget(checkbox)
                checkbox.stateChanged.connect(partial(signal_fn, checkbox, setting))

                return checkbox

            @staticmethod
            def create_enum_widget(
                    component_settings_widget: ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget,
                    setting: ObjectDict, name: str, layout: qt.QVBoxLayout, items: List[str] | None,
                    signal_fn: Callable) -> qt.ComboBoxRegularWidget:
                """
                Function that creates a new enum setting widget.

                :param ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget component_settings_widget: component
                    settings widget.
                :param ObjectDict setting: setting dictionary. e.g:
                    {
                        'name': 'manualOrient', 'value': False, 'isArray': False, 'locked': False, 'default': False,
                        'channelBox': True, 'keyable': False, 'type': 0
                    }
                :param str name: setting display name.
                :param qt.QVBoxLayout layout: layout setting widget will be added into.
                :param List[str] items: list of item names.
                :param Callable signal_fn: function to call when checkbox is checked.
                :return: newly created enum widget.
                :rtype: qt.ComboBoxRegularWidget
                """

                items = items or setting.get('enums', [])
                combo = qt.ComboBoxRegularWidget(
                    label=name, items=[strings.title_case(it) for it in items], item_data=items, set_index=setting.value,
                    box_ratio=16, label_ratio=4, support_middle_mouse_scroll=False, parent=component_settings_widget)
                combo.itemChanged.connect(lambda value, w=combo, s=setting: signal_fn(value, w, s))
                layout.addWidget(combo)

                return combo

            def refresh_ui(self):
                """
                Refreshes settings widgets based on component model.
                """

                self._parent_widget.update_combo()

            def _setup_ui(self):
                """
                Internal function that setups component settings widgets.
                """

                for i, setting in enumerate(self._component_model.component.descriptor.guide_layer.settings):
                    if setting.name == 'manualOrient':
                        continue
                    name = strings.title_case(setting.name)
                    setting_type = setting.type
                    if setting_type == attributetypes.kMFnNumericBoolean:
                        widget = self.create_boolean_widget(
                            self, setting, name, self._main_layout, self._on_setting_checkbox_changed)
                        self._settings_widgets.append((setting, widget))
                    elif setting_type == attributetypes.kMFnkEnumAttribute:
                        widget = self.create_enum_widget(
                            self, setting, name, self._main_layout, None, self._on_enum_changed)
                        self._settings_widgets.append((setting, widget))
                    else:
                        logger.warning(
                            f'Setting {name} of type '
                            f'{attributetypes._TYPE_TO_STRING.get(setting_type, f"missing type: {setting_type}")} '
                            f'is not yet implemented!')

            def _setup_signals(self):
                """
                Internal function that setups component settings signal connections.
                """

                pass

            def _on_setting_checkbox_changed(self, widget: qt.QWidget, setting: ObjectDict, value: bool):
                """
                Internal callback function that is called each time a setting checkbox is toggled by the user.

                :param qt.QWidget widget: setting widget modified by the user.
                :param ObjectDict setting: attribute setting. e.g:
                    {
                        'name': 'manualOrient', 'value': False, 'isArray': False, 'locked': False, 'default': False,
                        'channelBox': True, 'keyable': False, 'type': 0
                    }
                :param bool value: new value.
                """

                crit.update_guide_settings(self._component_model.component, {setting.name: value})

            def _on_enum_changed(
                    self, event: qt.ComboBoxRegularWidget.ComboItemChangedEvent, widget: qt.ComboBoxRegularWidget,
                    setting: ObjectDict):
                """
                Internal callback function that is called each time a setting enum is changed by the user.

                :param qt.ComboBoxRegularWidget.ComboItemChangedEvent event: combo item changed event.
                :param qt.ComboBoxRegularWidget widget: setting widget modified by the user.
                :param ObjectDict setting: attribute setting. e.g:
                    {
                        'name': 'manualOrient', 'value': False, 'isArray': False, 'locked': False, 'default': False,
                        'channelBox': True, 'keyable': False, 'type': 0
                    }
                """

                crit.update_guide_settings(self._component_model.component, {setting.name: event.index})

        def __init__(
                self, component_model: ComponentModel, controller: CritBuilderController | None = None,
                parent: ComponentsTreeWidget | None = None):

            self._model = component_model
            self._tree = parent
            self._controller = controller
            self._title_default_object_name = ''
            self._theme_pref = core.theme_preference_interface()
            self._main_frame = None  			# type: qt.QFrame
            self._context_menu = None  			# type: qt.QMenu
            self._component_menu = None  		# type: qt.IconMenuButton
            self._ui_commands = []				# type: List[CritUiCommand]
            self._component_settings = None		# type: ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget

            super().__init__(
                title=component_model.name, icon=component_model.icon, collapsed=False, start_hidden=False,
                shift_arrows_enabled=False, delete_button_enabled=True, item_icon_size=14, parent=parent)

            self.toggleExpandRequested.connect(self._on_toggle_expand_requested)

        @property
        def model(self) -> ComponentModel:
            return self._model

        @property
        def component_type(self) -> str:
            return self._model.component_type

        @property
        def name(self) -> str:
            return self._model.name

        @override
        def mousePressEvent(self, event: qt.QMouseEvent) -> None:
            event.ignore()

        @override
        def mouseReleaseEvent(self, event: qt.QMouseEvent) -> None:
            event.ignore()

        @override
        def setup_ui(self):
            super().setup_ui()

            self._title_default_object_name = self._title_frame.objectName()

            color = self._theme_pref.STACK_ITEM_HEADER_FOREGROUND

            self._main_frame = qt.QFrame(parent=self)
            self._component_menu = qt.IconMenuButton(parent=self)
            self._component_menu.set_icon('menu_dots', colors=color, size=15)
            self._component_menu.menuAboutToShow.connect(self._on_component_menu_about_to_show)
            self._component_menu.setMenu(self._setup_context_menu())

            self._side_combo = ComponentsTreeWidget.ComponentWidget.SideNameWidget(
                self._model, show_label=False, show_arrow=False, parent=self)
            self._side_combo.setMinimumWidth(50)

            self._rig_mode_warning_label = qt.icon_label(
                icon=resources.icon('warning', color=(220, 210, 0)),
                text='Edits can only be made in Guides mode.', enable_menu=False, parent=self)
            font = self._rig_mode_warning_label.font()
            font.setItalic(True)
            font.setBold(True)
            self._rig_mode_warning_label.setFont(font)
            self._rig_mode_warning_label.label.setEnabled(False)

            self._contents_layout.addWidget(self._rig_mode_warning_label)
            self._contents_layout.addWidget(self._main_frame)

            self._title_frame.extras_layout.setSpacing(0)
            self._title_frame.extras_layout.addWidget(self._component_menu)
            self._title_frame.delete_button.setIconSize(qt.QSize(12, 12))
            self._title_frame.horizontal_layout.insertWidget(4, self._side_combo)

            self.toggle_contents()

            self._refresh_ui_from_rig_mode(self._controller.rig_mode())

        @override
        def setup_signals(self):
            super().setup_signals()

            self._side_combo.renamed.connect(self._on_side_renamed)
            self._title_frame.line_edit.editingFinished.connect(self._on_line_edit_editing_finished)
            self.syncRequested.connect(self.sync)

        def sync(self):
            """
            Synchronizes the contents of this widget based on the applied rig model.
            """

            logger.debug('Syncing UI with the scene')
            self._widget_hide(self._model.is_hidden())
            self._tree._update_selection_colors()
            self._update_ui_command_icons()
            if self._collapsed:
                return
            self._component_settings.refresh_ui()

        def refresh_ui(self):
            """
            Refreshes component settings UI from the component model.
            """

            if self._collapsed:
                return

            if self._component_settings is not None:
                self._component_settings.refresh_ui()

        def _widget_hide(self, hide: bool):
            """
            Internal function that handles the visual behaviour to show/hide the component widget.

            :param bool hide: whether to show/hide component widget.
            """

            self._title_frame.setObjectName('diagonalBG' if hide else self._title_default_object_name)
            self._title_frame.setStyle(self._title_frame.style())

        def _setup_context_menu(self) -> qt.QMenu:
            """
            Internal function that setup contextual menu.

            :return: context menu instance.
            :rtype: qt.QMenu
            """

            if self._context_menu:
                return self._context_menu

            self._context_menu = qt.searchable_menu(parent=self)
            self._context_menu.set_search_visible(False)
            for ui_command, ui_command_type, _ in self._controller.ui_commands_manager.iterate_ui_commands_from_ids(self._model.menu_actions()):
                if ui_command_type == 'PLUGIN':
                    new_ui_command = ui_command(logger, ui_interface=self._controller.ui_interface)
                    self._add_menu_action_ui_command(new_ui_command, self._context_menu)
                elif ui_command_type == 'SEPARATOR':
                    self._context_menu.addSeparator()
            self._context_menu.setToolTipsVisible(True)

            return self._context_menu

        def _add_menu_action_ui_command(self, ui_command: CritUiCommand, menu: qt.QMenu):
            """
            Internal function that adds the given Crit UI command into the given Qt QMenu instance.

            :param CritUiCommand ui_command: CRIT UI command to add into the given menu.
            :param qt.QMenu menu: Qt menu instance.
            """

            ui_data = ui_command.UI_DATA
            action = qt.QAction(parent=self)
            action.setText(ui_data['label'])
            action.setProperty('ui_command', ui_command)
            try:
                icon = resources.icon(ui_data['icon'])
                action.setIcon(icon)
            except AttributeError:
                pass
            menu.addAction(action)
            action.triggered.connect(partial(self._on_ui_command_action_triggered, ui_command))

            ui_command.refreshRequested.connect(self.syncRequested.emit)
            ui_command.attached_widget = action

            self._ui_commands.append(ui_command)

        def _refresh_ui_from_rig_mode(self, rig_mode: int):
            """
            Internal function that refreshes UI based on given rig mode.

            :param int rig_mode: current rig mode state.
            """

            if rig_mode == consts.GUIDES_STATE:
                self._main_frame.setEnabled(True)
                self._rig_mode_warning_label.setVisible(False)
            else:
                self._main_frame.setEnabled(False)
                self._rig_mode_warning_label.setVisible(True)

        def _init_settings_widget(self) -> ComponentSettingWidget | None:
            """
            Internal function that creates the component settings widget instance for this widget.

            :return: component settings widget.
            :rtype: ComponentSettingWidget or None
            """

            settings_layout = qt.horizontal_layout(parent=self._main_frame)
            self._component_settings = self._model.create_widget(component_widget=self, parent_widget=self)
            if not self._component_settings:
                logger.warning('No custom widget supplied by component model')
                return None

            settings_layout.addWidget(self._component_settings)

            return self._component_settings

        def _update_ui_command_icons(self):
            """
            Internal function that updates command UI icons.
            """

            pass

        def _on_toggle_expand_requested(self, collapsed: bool):
            """
            Internal callback function that is called each time toggleExpandRequested signal is emitted.

            :param bool collapsed: whether contents are collapsed or expanded.
            """

            if collapsed:
                return

            if self._component_settings is None:
                self._component_settings = self._init_settings_widget()
                self._component_settings.refresh_ui()
            else:
                self._component_settings.refresh_ui()

        def _on_component_menu_about_to_show(self):
            """
            Internal callback function that is called each time Component Menu is going to be visible.
            """

            self._update_ui_command_icons()

        def _on_side_renamed(self, new_side: str):
            """
            Intenral callback function that is called each time side text is renamed.

            :param str new_side: new side.
            """

            self._controller.execute_ui_command(
                'setComponentSide', args={'component_model': self._model, 'side': new_side})

        def _on_line_edit_editing_finished(self):
            """
            Internal callback function that is called when component name line edit is edited.
            """

            before = self._model.name
            after = str(self.sender().text())
            self._model.name = after
            self.componentRenamed.emit(before, after)

        def _on_ui_command_action_triggered(self, ui_command: CritUiCommand, variant_id: str | None = None):
            """
            Internal callback function that is called when a CRIT UI command action is triggered by the user.

            :param CritUiCommand ui_command: CRIT UI command to execute.
            """

            ui_command.set_selected(self._controller.selection_model)
            ui_command.component_model = self._model
            try:
                ui_command.process(variant_id)
            finally:
                qt.single_shot_timer(self.sync)

    def __init__(
            self, components_manager: ComponentsManager | None = None,
            components_model_manager: ComponentsModelManager | None = None,
            controller: CritBuilderController | None = None,
            parent: qt.QWidget | None = None):

        self._components_manager = components_manager
        self._components_model_manager = components_model_manager
        self._controller = controller
        self._header_item = qt.QTreeWidgetItem(['Component'])

        super().__init__(allow_sub_groups=True, parent=parent)

    @override
    def setItemWidget(self, item: qt.QTreeWidgetItem, column: int, widget: qt.QWidget) -> None:

        if isinstance(widget, ComponentsTreeWidget.ComponentWidget):
            self._setup_component_widget_connections(widget, item)

        super().setItemWidget(item, column, widget)

    @override
    def _on_tree_selection_changed(self):

        super()._on_tree_selection_changed()

        component_models = []
        for it in self.selectedItems():
            item_widget = self._item_widget(it)
            if self._item_type(it) == self.ITEM_TYPE_WIDGET and item_widget is not None:
                component_models.append(item_widget.model)

        self._update_selection_colors()
        self._controller.set_selected_components(component_models)

    def sync(self):
        """
        Synchronizes the contents of this tree widget based on the applied rig model.
        """

        for item in self.item_widgets(item_type=self.ITEM_TYPE_WIDGET):
            item.sync()

    def tree_items(self) -> List[qt.GroupedTreeWidget.TreeWidgetItem]:
        """
        Returns a list of tree widget items within this tree widget.

        :return: list of tree widget items.
        :rtype: List[qt.GroupedTreeWidget.TreeWidgetItem]
        """

        return list(self.iterator())

    def maximize_all(self):
        """
        Expands all component widgets.
        """

        for tree_item in self.tree_items():
            self._item_widget(tree_item).expand()

    def maximize_selected(self):
        """
        Expands all selected component widgets.
        """

        for tree_item in self.selectedItems():
            self._item_widget(tree_item).expand()

    def minimize_all(self):
        """
        Collapses all component widgets.
        """

        for tree_item in self.tree_items():
            self._item_widget(tree_item).collapse()

    def minimize_selected(self):
        """
        Collapses all selected component widgets.
        """

        for tree_item in self.selectedItems():
            self._item_widget(tree_item).collapse()

    def add_component(
            self, component_model: ComponentModel,
            group: qt.GroupedTreeWidget.GroupWidget | None = None) -> ComponentsTreeWidget.ComponentWidget:
        """
        Adds a component widget to this tree widget based on the given component model.

        :param ComponentModel component_model: component model instance.
        :param qt.GroupedTreeWidget.GroupWidget group: optional parent group widget.
        :return: newly created component widget instance.
        :rtype: ComponentsTreeWidget.ComponentWidget
        """

        component_widget = ComponentsTreeWidget.ComponentWidget(
            component_model=component_model, controller=self._controller, parent=self)
        component_widget.syncRequested.connect(self.sync)
        self.add_component_widget(component_widget, group=group)

        if self.updatesEnabled():
            self.sync()

        return component_widget

    def add_component_widget(
            self, component_widget: ComponentsTreeWidget.ComponentWidget,
            group: qt.GroupedTreeWidget.GroupWidget | None = None):
        """
        Adds given component widget into the tree widget.

        :param ComponentsTreeWidget.ComponentWidget component_widget: component widget instance.
        :param qt.GroupedTreeWidget.GroupWidget group: optional parent group widget.
        """

        new_tree_item = self.add_new_item(
            component_widget.component_type, component_widget, widget_info=hash(component_widget.model),
            item_type=self.ITEM_TYPE_WIDGET)

        if group is not None:
            self.add_to_group(new_tree_item, group)

    def component_widget_by_model(self, component_model: ComponentModel) -> ComponentWidget | None:
        """
        Returns component widget instance that matches given component model.

        :param ComponentModel component_model: compoennt model instance.
        :return: component widget that matches given component model.
        :rtype: ComponentWidget or None
        """

        found_component_widget = None
        for component_widget in self.iterate_component_widgets():
            if component_widget.model == component_model:
                found_component_widget = component_widget
                break

        return found_component_widget

    def iterate_component_widgets(self) -> Iterator[ComponentWidget]:
        """
        Generator function that iterates over all component widgets within tree.

        :return: iterated component widgets.
        :rtype: Iterator[ComponentWidget]
        """

        for it in self.iterator():
            widget = self._item_widget(it)
            if widget:
                yield widget

    def _update_selection_colors(self):
        """
        Internal function that loops through each component widget and set the colors based on selection.
        """

        for i in range(self.invisibleRootItem().childCount()):
            tree_item = self.invisibleRootItem().child(i)
            item_widget = self._item_widget(tree_item)
            if item_widget is not None:
                update_targets = []
                if self._item_type(tree_item) == self.ITEM_TYPE_WIDGET:
                    update_targets = [item_widget.title_frame, item_widget.hider_widget]
                elif self._item_type(tree_item) == self.ITEM_TYPE_GROUP:
                    update_targets = [item_widget.title_frame]
                if tree_item.isSelected():
                    [qt.set_stylesheet_object_name(t, 'selected') for t in update_targets]
                else:
                    [qt.set_stylesheet_object_name(t, '') for t in update_targets]

    def _setup_component_widget_connections(self, widget: ComponentsTreeWidget.ComponentWidget, item: qt.QTreeWidgetItem):
        """
        Internal function that setup signal connections of the given component widget.

        :param ComponentsTreeWidget.ComponentWidget widget: components widget instance.
        :param qt.QTreeWidgetItem item: tree widget item instance.
        """

        widget.minimized.connect(self.refresh)
        widget.maximized.connect(self.refresh)
        widget.componentRenamed.connect(self._on_component_widget_renamed)

    def _on_component_widget_renamed(self):
        """
        Internal callback function that is called each time a component widget componentRenamed signal is emitted.
        Forces the refreshing of the component widget UI.
        """

        for widget in self.iterate_component_widgets():
            print(widget)
