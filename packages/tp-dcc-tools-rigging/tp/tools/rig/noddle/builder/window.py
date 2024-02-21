from __future__ import annotations

import typing

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.common.nodegraph.widgets import palette
from tp.common.resources import api as resources

from tp.tools.rig.noddle.builder import editor
from tp.tools.rig.noddle.builder.widgets import workspace, history, vars, attributeseditor
from tp.tools.rig.noddle.builder.menus import file_menu, edit_menu, graph_menu, skin_menu


logger = log.rigLogger

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.graph import NodeGraph
    from tp.tools.rig.noddle.builder.controller import NoddleController


class NoddleBuilderWindow(qt.FramelessWindow):

    def __init__(self,controller: NoddleController,  parent: qt.QWidget | None = None):

        self._controller = controller
        self._window_title = 'Noddle Builder v0.0.1'
        self._editor_map: dict[qt.QMdiSubWindow, editor.NodeEditor] = {}

        super().__init__(title=self._window_title, parent=parent)

    @property
    def controller(self) -> NoddleController:
        return self._controller

    @property
    def workspace_widget(self) -> workspace.WorkspaceWidget:
        return self._workspace_widget

    @property
    def mdi_area(self) -> qt.QMdiArea:
        return self._mdi_area

    @property
    def current_window(self) -> qt.QMdiSubWindow:
        return self._mdi_area.currentSubWindow()

    @property
    def current_editor(self) -> NodeGraph | None:
        return self._editor_map.get(self.current_window, None) if self.current_window else None

    @property
    def attributes_editor(self) -> attributeseditor.AttributesEditor:
        return self._attributes_editor

    @override
    def setup_widgets(self):
        super().setup_widgets()

        self._main_window = qt.QMainWindow(parent=self)
        self._main_window.setTabPosition(qt.Qt.RightDockWidgetArea, qt.QTabWidget.East)
        self._main_window.setTabPosition(qt.Qt.LeftDockWidgetArea, qt.QTabWidget.North)
        self._window_main_layout = qt.vertical_layout(spacing=0, margins=(0, 0, 0, 0))
        self._window_main_widget = qt.widget(self._window_main_layout, parent=self)
        self._main_window.setCentralWidget(self._window_main_widget)

        self._workspace_widget = workspace.WorkspaceWidget(controller=self._controller, parent=self)
        self._workspace_dock = qt.QDockWidget(self._workspace_widget.LABEL)
        self._workspace_dock.setWidget(self._workspace_widget)
        self._workspace_dock.setAllowedAreas(qt.Qt.RightDockWidgetArea)

        self._attributes_editor = attributeseditor.AttributesEditor(self)
        self._attributes_editor_dock = qt.QDockWidget('Attributes')
        self._attributes_editor_dock.setWidget(self._attributes_editor)
        self._attributes_editor_dock.setAllowedAreas(qt.Qt.RightDockWidgetArea)

        self._history_widget = history.SceneHistoryWidget(self)
        self._history_dock = qt.QDockWidget('History')
        self._history_dock.setWidget(self._history_widget)
        self._history_dock.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)

        self._nodes_palette = palette.NodesPalette(parent=self)
        self._nodes_palette_dock = qt.QDockWidget('Nodes Palette')
        self._nodes_palette_dock.setWidget(self._nodes_palette)
        self._nodes_palette_dock.setAllowedAreas(qt.Qt.LeftDockWidgetArea)

        self._vars_widget = vars.SceneVarsWidget(self)
        self._vars_dock = qt.QDockWidget('Variables')
        self._vars_dock.setWidget(self._vars_widget)
        self._vars_dock.setAllowedAreas(qt.Qt.LeftDockWidgetArea)

        self._mdi_area = qt.QMdiArea(parent=self)
        self._mdi_area.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        self._mdi_area.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        self._mdi_area.setViewMode(qt.QMdiArea.TabbedView)
        self._mdi_area.setDocumentMode(True)
        self._mdi_area.setTabsClosable(True)
        self._mdi_area.setTabsMovable(True)

        self._main_window.addDockWidget(qt.Qt.LeftDockWidgetArea, self._nodes_palette_dock)
        self._main_window.addDockWidget(qt.Qt.LeftDockWidgetArea, self._vars_dock)
        self._main_window.addDockWidget(qt.Qt.RightDockWidgetArea, self._attributes_editor_dock)
        self._main_window.addDockWidget(qt.Qt.RightDockWidgetArea, self._workspace_dock)
        self._main_window.tabifyDockWidget(self._attributes_editor_dock, self._workspace_dock)
        self._attributes_editor_dock.raise_()
        self._main_window.addDockWidget(qt.Qt.RightDockWidgetArea, self._history_dock)

        self._window_main_layout.addWidget(self._mdi_area)

        self._setup_menubar()

    @override
    def setup_layouts(self):
        super().setup_layouts()

        main_layout = self.set_main_layout(qt.vertical_layout(spacing=0, margins=(0, 0, 0, 0)))
        main_layout.addWidget(self._main_window)

    @override
    def setup_signals(self):
        super().setup_signals()

        self._update_button.clicked.connect(self._on_update_button_clicked)
        self._mdi_area.subWindowActivated.connect(self._on_mdi_area_sub_window_activated)
        self._vars_widget.variables_list_widget.itemClicked.connect(
            self._attributes_editor.update_current_variable_widget)

    def find_mdi_child_by_widget(self, widget: qt.QWidget) -> qt.QMdiSubWindow | None:
        """
        Returns the MDI sub window instance that matches given graph file name.

        :param qt.QWidget: widget of the MDI sub window we are looking for.
        :return: found mdi area sub window.
        :rtype: qt.QMdiSubWindow or None
        """

        found_mdi_child: qt.QMdiSubWindow | None = None
        for sub_window in self._mdi_area.subWindowList():
            sub_window_widget = sub_window.widget()
            if not sub_window_widget or sub_window_widget != widget:
                continue
            found_mdi_child = sub_window
            break

        return found_mdi_child

    def find_mdi_child_by_filename(self, file_name: str) -> qt.QMdiSubWindow | None:
        """
        Returns the MDI sub window instance that matches given graph file name.

        :param str file_name: graph file name to find mdi area sub window from.
        :return: found mdi area sub window.
        :rtype: qt.QMdiSubWindow or None
        """

        found_mdi_child: qt.QMdiSubWindow | None = None
        for sub_window in self._mdi_area.subWindowList():
            node_graph = self._editor_map.get(sub_window, None)
            if not node_graph:
                continue
            if node_graph.file_name == file_name:
                found_mdi_child = sub_window
                break

        return found_mdi_child

    def new_build(self):
        """
        Creates a new build graph.
        """

        try:
            sub_window = self._create_mdi_child()
            sub_window.show()
        except Exception:
            logger.exception('Failed to create new build', exc_info=True)

    def open_build(self):
        """
        Opens build file.
        """

        sub_window = self.current_window or self._create_mdi_child()
        self._editor_map[sub_window].open_build()

    def open_build_tabbed(self):
        """
        Opens build file in a new tab.
        """

        sub_window = self._create_mdi_child()
        res = self._editor_map[sub_window].open_build()
        if not res:
            self.mdi_area.removeSubWindow(sub_window)

    def save_build(self):
        """
        Saves current build into disk.
        """

        if not self.current_editor:
            return

        self.current_editor.save_build()

    def save_build_as(self):
        """
        Saves current build into disk in a new file.
        """

        if not self.current_editor:
            return

        self.current_editor.save_build_as()

    def refresh_variables(self):
        """
        Refreshes variables widget.
        """

        self._vars_widget.refresh()

    def _setup_menubar(self):
        """
        Internal function that setup menubar.
        """

        self._menubar = qt.QMenuBar(parent=self._main_window)
        self._main_window.setMenuBar(self._menubar)

        self._update_button = qt.base_button(icon=resources.icon('refresh'))
        self._menubar.setCornerWidget(self._update_button, qt.Qt.TopRightCorner)

        self._file_menu = file_menu.FileMenu(self)
        self._edit_menu = edit_menu.EditMenu(self)
        self._graph_menu = graph_menu.GraphMenu(self)
        self._skin_menu = skin_menu.SkinMenu(self)

        self._menubar.addMenu(self._file_menu)
        self._menubar.addMenu(self._edit_menu)
        self._menubar.addMenu(self._graph_menu)
        self._menubar.addMenu(self._skin_menu)

    def _create_mdi_child(self):
        """
        Internal function that creates a new node editor.
        """

        new_editor = editor.NodeEditor(controller=self._controller, parent=self)
        new_editor_widget = new_editor.widget()
        sub_window = self._mdi_area.addSubWindow(new_editor_widget)
        self._editor_map[sub_window] = new_editor
        new_editor.fileNameChanged.connect(self._update_title)
        new_editor.modified.connect(self._update_title)
        new_editor.itemSelected.connect(self._attributes_editor.update_current_node_widget)
        new_editor.itemsDeselected.connect(self._attributes_editor.clear)
        new_editor.fileLoadFinished.connect(self._vars_widget.refresh)
        new_editor_widget.aboutToClose.connect(self._on_sub_window_close)

        return sub_window

    def _update_title(self):
        """
        Internal function that updates window title.
        """

        if not self.current_editor:
            self.setWindowTitle(self._window_title)
            return

        self.setWindowTitle(f'{self._window_title} - {self.current_editor.user_friendly_title}')

    def _on_update_button_clicked(self):
        """
        Internal callback function that is called each time Update button is clicked by the user.
        """

        # self._workspace_widget.update_data()
        self._nodes_palette.update_nodes_tree()

    def _on_mdi_area_sub_window_activated(self):
        """
        Internal callback function that is called each time MDI area sub window is activated.
        """

        self._update_title()
        self._history_widget.update_history_connection()
        self._vars_widget.refresh()

    def _on_sub_window_close(self, widget: qt.QWidget, event: qt.QCloseEvent):
        """
        Internal callback function that is called each time sub window is closed by the user.

        :param qt.QWidget widget: widget sub window was parent of.
        :param qt.QCloseEvent event: Qt close event.
        """

        existing = self.find_mdi_child_by_widget(widget)
        self._mdi_area.setActiveSubWindow(existing)
        if self.current_editor.maybe_save():
            event.accept()
            self._attributes_editor.clear()
        else:
            event.ignore()
