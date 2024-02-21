from __future__ import annotations

import typing

from tp.core import log
from tp.common.qt import api as qt

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.graph import NodeGraph
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow

logger = log.tpLogger


class EditMenu(qt.QMenu):
    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__('Edit', parent=parent or main_window)

        self._main_window = main_window
        self._workspace_widget = main_window.workspace_widget

        self._setup_actions()
        self._setup_shortcuts()
        self._populate()
        self._setup_signals()

        self.setTearOffEnabled(True)

    @property
    def graph(self) -> NodeGraph | None:
        editor = self._main_window.current_editor
        if not editor:
            return None
        return editor.graphics_scene.graph

    def _setup_actions(self):
        """
        Internal function that creates all menu actions.
        """

        self._rename_selected_node_action = qt.QAction('Rename Selected Node', parent=self)
        self._regenerate_uuids_action = qt.QAction('Regenerate UUIDs', parent=self)
        self._undo_action = qt.QAction('&Undo', parent=self)
        self._redo_action = qt.QAction('&Redo', parent=self)
        self._copy_action = qt.QAction('&Copy', parent=self)
        self._cut_action = qt.QAction('&Cut', parent=self)
        self._paste_action = qt.QAction('&Paste', parent=self)
        self._delete_action = qt.QAction('&Delete', parent=self)

    def _setup_shortcuts(self):
        """
        Internal function that setup all action shortcuts
        """

        self._rename_selected_node_action.setShortcut('F2')
        self._undo_action.setShortcut('Ctrl+Z')
        self._redo_action.setShortcut('Ctrl+Y')
        self._copy_action.setShortcut('Ctrl+C')
        self._cut_action.setShortcut('Ctrl+X')
        self._paste_action.setShortcut('Ctrl+V')
        self._delete_action.setShortcut('Del')

    def _populate(self):
        """
        Internal function that populates sub-menus and menu itself.
        """

        self.addAction(self._rename_selected_node_action)
        self.addAction(self._regenerate_uuids_action)
        self.addSeparator()
        self.addAction(self._undo_action)
        self.addAction(self._redo_action)
        self.addSeparator()
        self.addAction(self._copy_action)
        self.addAction(self._cut_action)
        self.addAction(self._paste_action)
        self.addSeparator()
        self.addAction(self._delete_action)

    def _setup_signals(self):
        """
        Internal function that setup menu actions signal connections.
        """

        self._main_window.mdi_area.subWindowActivated.connect(self._update_actions_state)
        self.aboutToShow.connect(self._update_actions_state)
        self._rename_selected_node_action.triggered.connect(self._on_rename_selected_node_action_triggered)
        self._regenerate_uuids_action.triggered.connect(self._on_regenerate_uuids_action_triggered)
        self._undo_action.triggered.connect(self._on_undo_action_triggered)
        self._redo_action.triggered.connect(self._on_redo_action_triggered)
        self._copy_action.triggered.connect(self._on_copy_action_triggered)
        self._cut_action.triggered.connect(self._on_cut_action_triggered)
        self._paste_action.triggered.connect(self._on_paste_action_triggered)
        self._delete_action.triggered.connect(self._on_delete_action_triggered)

    def _update_actions_state(self):
        """
        Internal function that updates enable status of menu actions.
        """

        is_graph_set = self.graph is not None
        self._rename_selected_node_action.setEnabled(is_graph_set)
        self._regenerate_uuids_action.setEnabled(is_graph_set)
        self._undo_action.setEnabled(is_graph_set)
        self._redo_action.setEnabled(is_graph_set)
        self._copy_action.setEnabled(is_graph_set)
        self._cut_action.setEnabled(is_graph_set)
        self._paste_action.setEnabled(is_graph_set)
        self._delete_action.setEnabled(is_graph_set)

    def _on_rename_selected_node_action_triggered(self):
        """
        Internal callback function that is called each time Rename Selected Node action is triggered by the user.
        """

        if self.graph is None:
            return

        try:
            self.graph.rename_selected_node()
        except Exception:
            logger.exception('Node rename exception', exc_info=True)

    def _on_regenerate_uuids_action_triggered(self):
        """
        Internal callback function that is called each time Regenerate UUIDs action is triggered by the user.
        """

        if self.graph is None:
            return

        try:
            self.graph.regenerate_uuids()
        except Exception:
            logger.exception('Regenerate UUIDs exception', exc_info=True)

    def _on_undo_action_triggered(self):
        """
        Internal callback function that is called each time Undo action is triggered by the user.
        """

        if self.graph is None:
            return

        try:
            self.graph.history.undo()
            self._main_window.refresh_variables()
        except Exception:
            logger.exception('Undo exception', exc_info=True)

    def _on_redo_action_triggered(self):
        """
        Internal callback function that is called each time Redo action is triggered by the user.
        """

        if self.graph is None:
            return

        try:
            self.graph.history.redo()
            self._main_window.refresh_variables()
        except Exception:
            logger.exception('Redo exception', exc_info=True)

    def _on_copy_action_triggered(self):
        """
        Internal callback function that is called each time Copy action is triggered by the user.
        """

        if self.graph is None:
            return

        self.graph.copy_selected()

    def _on_cut_action_triggered(self):
        """
        Internal callback function that is called each time Cut action is triggered by the user.
        """

        if self.graph is None:
            return

        self.graph.cut_selected()

    def _on_paste_action_triggered(self):
        """
        Internal callback function that is called each time Paste action is triggered by the user.
        """

        if self.graph is None:
            return

        self.graph.paste_from_clipboard()

    def _on_delete_action_triggered(self):
        """
        Internal callback function that is called each time Delete action is triggered by the user.
        """

        if self.graph is None:
            return

        self.graph.delete_selected()
