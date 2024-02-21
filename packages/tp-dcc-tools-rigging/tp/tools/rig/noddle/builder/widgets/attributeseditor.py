from __future__ import annotations

import typing

from tp.common.qt import api as qt
from tp.tools.rig.noddle.builder.widgets import vars

if typing.TYPE_CHECKING:
    from tp.tools.rig.noddle.builder.editor import NodeEditor
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow


class AttributesEditor(qt.QWidget):
    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__(parent=parent or main_window)

        self._main_window = main_window
        self._current_widget: qt.QWidget | None = None

        self.setMinimumWidth(250)

        self.main_layout = qt.vertical_layout(margins=(0, 0, 0, 0))
        self.setLayout(self.main_layout)

    @property
    def current_editor(self) -> NodeEditor | None:
        return self._main_window.current_editor

    @property
    def current_widget(self) -> qt.QWidget | None:
        return self._current_widget

    @current_widget.setter
    def current_widget(self, widget: qt.QWidget):
        self._current_widget = widget
        self.main_layout.addWidget(self._current_widget)
        self._current_widget.show()

    def update_current_node_widget(self):
        self.clear()
        if not self.current_editor:
            return
        selected = self.current_editor.selected_nodes
        if not selected:
            return

        node = selected[-1]
        try:
            widget = node.attributes_widget()
        except AttributeError:
            return
        if widget:
            self.current_widget = widget

    def update_current_variable_widget(self, list_item: qt.QListWidgetItem | None):
        self.clear()
        if not list_item or not self.current_editor:
            return
        variable_widget = vars.VarAttributeWidget(list_item, self.current_editor)
        self.current_widget = variable_widget
        variable_widget.dataTypeSwitched.connect(self.update_current_variable_widget)

    def clear(self):
        """
        Clears attribute editor widgets.
        """

        if not self.current_widget:
            return

        self.main_layout.removeWidget(self.current_widget)
        self.current_widget.close()
        self.current_widget.deleteLater()
        self._current_widget = None
