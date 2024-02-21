from __future__ import annotations

import typing

from tp.common.qt import api as qt
from tp.common.resources import api as resources
from tp.common.nodegraph.core import edge

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.graph import NodeGraph
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow
    from tp.common.nodegraph.core.executor import GraphExecutor


class GraphMenu(qt.QMenu):
    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__('Graph', parent=parent or main_window)

        self._main_window = main_window

        self._setup_actions()
        self._setup_shortcuts()
        self._setup_sub_menus()
        self._populate()
        self._setup_signals()

        self.setTearOffEnabled(True)

    @property
    def executor(self) -> GraphExecutor | None:
        editor = self._main_window.current_editor
        return editor.executor if editor else None

    @property
    def graph(self) -> NodeGraph:
        editor = self._main_window.current_editor
        return editor.graphics_scene.graph if editor else None

    def _setup_actions(self):
        """
        Internal function that creates all menu actions.
        """

        self._edge_type_group = qt.QActionGroup(self)
        self._edge_type_direct_action = qt.QAction('Direct', parent=self)
        self._edge_type_bezier_action = qt.QAction('Bezier', parent=self)
        self._edge_type_square_action = qt.QAction('Square', parent=self)
        self._edge_type_group.addAction(self._edge_type_direct_action)
        self._edge_type_group.addAction(self._edge_type_bezier_action)
        self._edge_type_group.addAction(self._edge_type_square_action)
        self._edge_type_direct_action.setCheckable(True)
        self._edge_type_bezier_action.setCheckable(True)
        self._edge_type_square_action.setCheckable(True)

        self._reset_stepped_execution = qt.QAction('&Reset Stepped Execution', parent=self)
        self._execute_step_action = qt.QAction('&Execute Step', parent=self)
        self._execute_action = qt.QAction(resources.icon('play'), '&Execute', parent=self)

    def _setup_shortcuts(self):
        """
        Internal function that setup all action shortcuts
        """

        self._execute_step_action.setShortcut(qt.QKeySequence(qt.Qt.Key_F6))
        self._execute_action.setShortcut(qt.QKeySequence(qt.Qt.Key_F5))

    def _setup_sub_menus(self):
        """
        Internal function that creates all menu sub-menus.
        """

        self._scene_edge_type_menu = qt.QMenu('Edge Style', parent=self)

    def _populate(self):
        """
        Internal function that populates sub-menus and menu itself.
        """

        self.addMenu(self._scene_edge_type_menu)
        self._scene_edge_type_menu.addAction(self._edge_type_direct_action)
        self._scene_edge_type_menu.addAction(self._edge_type_bezier_action)
        self._scene_edge_type_menu.addAction(self._edge_type_square_action)

        self.addSection('Execution')
        self.addAction(self._reset_stepped_execution)
        self.addAction(self._execute_step_action)
        self.addSeparator()
        self.addAction(self._execute_action)

    def _setup_signals(self):
        """
        Internal function that setup menu actions signal connections.
        """

        self._main_window.mdi_area.subWindowActivated.connect(self._update_actions_state)
        self.aboutToShow.connect(self._update_actions_state)
        self._scene_edge_type_menu.aboutToShow.connect(self._on_scene_edge_type_menu_about_to_show)
        self._edge_type_direct_action.toggled.connect(self._on_edge_type_direct_action_toggled)
        self._edge_type_bezier_action.toggled.connect(self._on_edge_type_bezier_action_toggled)
        self._edge_type_square_action.toggled.connect(self._on_edge_type_square_action_toggled)
        self._reset_stepped_execution.triggered.connect(self._on_reset_stepped_action_triggered)
        self._execute_step_action.triggered.connect(self._on_execute_step_action_triggered)
        self._execute_action.triggered.connect(self._on_execute_action_triggered)

    def _update_actions_state(self):
        """
        Internal function that updates the enable state of actions for this menu.
        """

        is_graph_set = self.graph is not None
        self._scene_edge_type_menu.setEnabled(is_graph_set)
        self._reset_stepped_execution.setEnabled(is_graph_set)
        self._execute_step_action.setEnabled(is_graph_set)
        self._execute_action.setEnabled(is_graph_set)

    def _on_scene_edge_type_menu_about_to_show(self):
        """
        Internal callback function that is called each time Edge Type menu is shown.
        Updates checked status for the actions within this menu.
        """

        if not self._main_window.current_editor:
            self._edge_type_direct_action.setEnabled(False)
            self._edge_type_bezier_action.setEnabled(False)
            self._edge_type_square_action.setEnabled(False)
            return

        self._edge_type_direct_action.setEnabled(True)
        self._edge_type_bezier_action.setEnabled(True)
        self._edge_type_square_action.setEnabled(True)
        if self.graph.edge_type == edge.Edge.Type.DIRECT:
            self._edge_type_direct_action.setChecked(True)
        if self.graph.edge_type == edge.Edge.Type.BEZIER:
            self._edge_type_bezier_action.setChecked(True)
        if self.graph.edge_type == edge.Edge.Type.SQUARE:
            self._edge_type_square_action.setChecked(True)

    def _on_edge_type_direct_action_toggled(self, state: bool):
        """
        Internal callback function that is called each time edge type direct action is toggled by the user.

        :param bool state: check action state.
        """

        if not self._main_window.current_editor or not state:
            return
        self.graph.edge_type = edge.Edge.Type.DIRECT

    def _on_edge_type_bezier_action_toggled(self, state: bool):
        """
        Internal callback function that is called each time edge type bezier action is toggled by the user.

        :param bool state: check action state.
        """

        if not self._main_window.current_editor or not state:
            return
        self.graph.edge_type = edge.Edge.Type.BEZIER

    def _on_edge_type_square_action_toggled(self, state: bool):
        """
        Internal callback function that is called each time edge type square action is toggled by the user.

        :param bool state: check action state.
        """

        if not self._main_window.current_editor or not state:
            return
        self.graph.edge_type = edge.Edge.Type.SQUARE

    def _on_reset_stepped_action_triggered(self):
        """
        Internal callback function that is called each time user triggers Reset Stepped Action.
        """

        if not self.executor:
            return

        self.executor.reset_stepped_execution()

    def _on_execute_step_action_triggered(self):
        """
        Internal callback function that is called each time user triggers Execute Step Action.
        """

        if not self.executor:
            return

        self.executor.execute_step()

    def _on_execute_action_triggered(self):
        """
        Internal callback function that is called each time user triggers Execute Action.
        """

        if not self.executor:
            return

        self.executor.execute_graph()
