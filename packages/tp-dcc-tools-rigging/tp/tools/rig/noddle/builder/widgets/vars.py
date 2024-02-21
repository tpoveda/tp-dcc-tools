from __future__ import annotations

import json
import typing
from typing import Union

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.common.resources import api as resources
from tp.common.nodegraph import registers

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.vars import SceneVars
    from tp.common.nodegraph.core.graph import NodeGraph
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow
    from tp.tools.rig.noddle.builder.widgets.attributeseditor import AttributesEditor

logger = log.tpLogger


class SceneVarsWidget(qt.QWidget):

    JSON_DATA_ROLE = qt.Qt.UserRole + 1

    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__(parent=parent or main_window)

        self._main_window = main_window

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

    @property
    def variables_list_widget(self):
        return self._variables_list_widget

    @property
    def scene_vars(self) -> SceneVars | None:
        return self._main_window.current_editor.vars if self._main_window.current_editor else None

    @property
    def attributes_editor(self) -> AttributesEditor:
        return self._main_window.attributes_editor

    def refresh(self):
        """
        Refreshes list of variable widgets.
        """

        self._variables_list_widget.populate()

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        self._variables_list_widget = VarsListWidget(self)
        self._add_variable_button = qt.base_button(icon=resources.icon('add'), parent=self)
        self._delete_variable_button = qt.base_button(icon=resources.icon('delete'), parent=self)

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        main_layout = qt.vertical_layout(spacing=0, margins=(0, 0, 0, 0))
        self.setLayout(main_layout)

        buttons_layout = qt.horizontal_layout(spacing=2, margins=(0, 0, 0, 0))
        buttons_layout.addWidget(self._add_variable_button)
        buttons_layout.addWidget(self._delete_variable_button)

        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(self._variables_list_widget)

    def _setup_signals(self):
        """
        Internal function that connects all signals for this graph.
        """

        self._add_variable_button.clicked.connect(self._on_add_variable_button_clicked)
        self._delete_variable_button.clicked.connect(self._on_delete_variable_button_clicked)

    def _on_add_variable_button_clicked(self):
        """
        Internal callback function that is called each time user clicks Add Variable button.
        Adds a new variable.
        """

        if not self.scene_vars:
            return

        self.scene_vars.add_new_variable('variable')
        self.refresh()

    def _on_delete_variable_button_clicked(self):
        """
        Internal callback function that is called each time user clicks Delete Variable button.
        Deletes an existing variable.
        """

        selected_items = self._variables_list_widget.selectedItems()
        if not selected_items:
            return

        try:
            var_name = selected_items[-1].data(VarsListWidget.JSON_DATA_ROLE)['var_name']
            if not self.scene_vars:
                logger.error(f'Scene Variables is {self.scene_vars}, cannot delete variable')
                return
            self.scene_vars.delete_variable(var_name)
            self.refresh()
            self.attributes_editor.update_current_variable_widget(None)
        except Exception:
            logger.exception('Delete selected variable exception', exc_info=True)


class VarsListWidget(qt.QListWidget):

    variableRenamed = qt.Signal(qt.QListWidgetItem)

    PIXMAP_ROLE = qt.Qt.UserRole
    JSON_DATA_ROLE = qt.Qt.UserRole + 1

    def __init__(self, vars_widget: SceneVarsWidget, parent: qt.QWidget | None = None):
        super().__init__(parent=parent or vars_widget)

        self._vars_widget = vars_widget

        self.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)

        self._setup_signals()

    @property
    def scene_vars(self) -> SceneVars | None:
        return self._vars_widget.scene_vars

    @override
    def startDrag(self, supportedActions: Union[qt.Qt.DropActions, qt.Qt.DropAction]) -> None:
        try:
            item = self.currentItem()
            json_data = item.data(VarsListWidget.JSON_DATA_ROLE)
            item_data = qt.QByteArray()
            data_stream = qt.QDataStream(item_data, qt.QIODevice.WriteOnly)
            data_stream.writeQString(json.dumps(json_data))
            mime_data = qt.QMimeData()
            mime_data.setData('noddle/x-vars_item', item_data)
            drag = qt.QDrag(self)
            drag.setMimeData(mime_data)
            # drag.setHotSpot(QtCore.QPoint(pixmap.width() / 2, pixmap.height() / 2))
            # drag.setPixmap(pixmap)
            drag.exec_(qt.Qt.MoveAction)
        except Exception:
            logger.exception('Vars drag exception', exc_info=True)

    def populate(self):
        """
        Fills list widget with all available variables.
        """

        self.clear()
        if not self.scene_vars or not self.scene_vars.vars:
            return

        for var_name in self.scene_vars.vars.keys():
            new_item = qt.QListWidgetItem()
            new_item.setFlags(
                qt.Qt.ItemIsEnabled | qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEditable | qt.Qt.ItemIsDragEnabled)
            new_item.setText(var_name)
            json_data = {'var_name': var_name}
            new_item.setData(VarsListWidget.JSON_DATA_ROLE, json_data)
            self.addItem(new_item)

    def _setup_signals(self):
        """
        Internal function that connects all signals for this graph.
        """

        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemChanged.connect(self._on_item_changed)
        self.variableRenamed.connect(self._vars_widget.attributes_editor.update_current_variable_widget)

    def _on_item_double_clicked(self, item: qt.QListWidgetItem):
        """
        Internal callback function that is called each time user double-clicks on a variable item.
        Enters variable edit mode.

        :param qt.QListWidgetItem item: double-clicked item.
        """

        self.editItem(item)

    def _on_item_changed(self, item: qt.QListWidgetItem):
        """
        Internal callback function that is called each time item is changed by the user.

        :param qt.QListWidgetItem item: edited item.
        """

        json_data = item.data(VarsListWidget.JSON_DATA_ROLE)
        if not json_data:
            return

        # Handle empty name.
        old_var_name = json_data['var_name']
        if not item.text().strip():
            item.setText(old_var_name)

        if item.text() == old_var_name:
            return

        old_row = self.row(item)
        self.scene_vars.rename_variable(old_var_name, item.text())

        self.populate()
        new_item = self.item(old_row)
        self.variableRenamed.emit(new_item)


class VarAttributeWidget(qt.QGroupBox):

    dataTypeSwitched = qt.Signal(qt.QListWidgetItem, str)

    def __init__(self, list_item: qt.QListWidgetItem, graph: NodeGraph, parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

        self._list_item = list_item
        self._graph = graph
        self._value_widget: qt.QWidget | None = None

        json_data = self._list_item.data(VarsListWidget.JSON_DATA_ROLE)
        self._var_name = json_data['var_name']
        self.setTitle(f'Variable {self._var_name}')

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        var_data_type_name = self._graph.vars.data_type(self._var_name, as_dict=False)
        var_data_type = self._graph.vars.data_type(self._var_name, as_dict=True)
        var_value = self._graph.vars.value(self._var_name)

        self._data_type_combo = qt.combobox()
        types_list = list(registers.DATA_TYPES_REGISTER.keys())
        types_list.sort()
        types_list.remove('EXEC')
        self._data_type_combo.addItems(types_list)
        self._data_type_combo.setCurrentText(var_data_type_name)

        self._value_widget = None
        if var_data_type['class'] in registers.DataType.runtime_types(classes=True):
            self.value_widget = qt.QLineEdit()
            self.value_widget.setText(str(var_value))
            self.value_widget.setEnabled(False)
        elif var_data_type == registers.DataType.NUMERIC:
            self.value_widget = qt.QDoubleSpinBox()
            self.value_widget.setRange(-9999, 9999)
            self.value_widget.setValue(var_value)
        elif var_data_type == registers.DataType.STRING:
            self.value_widget = qt.QLineEdit()
            self.value_widget.setText(var_value)
        elif var_data_type == registers.DataType.BOOLEAN:
            self.value_widget = qt.QCheckBox()
            self.value_widget.setChecked(var_value)
        else:
            logger.warning(f'Missing widget creation for data {var_data_type["class"]}')

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        main_layout = qt.form_layout()
        self.setLayout(main_layout)

        main_layout.addRow('Type:', self._data_type_combo)
        if self._value_widget:
            main_layout.addRow('Value:', self._value_widget)

    def _setup_signals(self):
        """
        Internal function that connects all signals for this graph.
        """

        self._data_type_combo.currentTextChanged.connect(self._on_data_type_combo_current_text_changed)
        if self._value_widget is not None:
            if isinstance(self._value_widget, qt.QLineEdit):
                self._value_widget.textChanged.connect(lambda text: self._graph.vars.set_value(self._var_name, text))
            elif isinstance(self._value_widget, qt.QAbstractSpinBox):
                self._value_widget.valueChanged.connect(lambda value: self._graph.vars.set_value(self._var_name, value))
            elif isinstance(self._value_widget, qt.QCheckBox):
                self._value_widget.toggled.connect(lambda state: self._graph.vars.set_value(self._var_name, state))

    def _on_data_type_combo_current_text_changed(self, type_name: str):
        """
        Internal callback function that is called each time data type combo box changes.

        :param str type_name: type name.
        """

        self._graph.vars.set_data_type(self._var_name, type_name)
        self.dataTypeSwitched.emit(self._list_item, self._var_name)
