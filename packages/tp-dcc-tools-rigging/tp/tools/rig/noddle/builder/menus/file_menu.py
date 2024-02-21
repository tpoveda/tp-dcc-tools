from __future__ import annotations

import os
import typing
from functools import partial

from tp.core import dcc
from tp.common.qt import api as qt
from tp.common.resources import api as resources
from tp.preferences.interfaces import noddle
from tp.libs.rig.noddle.core import asset

if typing.TYPE_CHECKING:
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow


class FileMenu(qt.QMenu):
    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__('File', parent=parent or main_window)

        self._main_window = main_window
        self._workspace_widget = main_window.workspace_widget
        self._prefs = noddle.noddle_interface()

        self._setup_actions()
        self._setup_shortcuts()
        self._setup_sub_menus()
        self._populate()
        self._setup_signals()

        self.setTearOffEnabled(True)

    def _setup_actions(self):
        """
        Internal function that creates all menu actions.
        """

        self._new_build_action = qt.QAction('New Build', parent=self)
        self._open_build_file_action = qt.QAction('Open Build...', parent=self)
        self._open_build_tab_action = qt.QAction('Open Build as Tab...', parent=self)
        self._save_build_action = qt.QAction('Save Build', parent=self)
        self._save_build_as_action = qt.QAction('Save Build As...', parent=self)
        self._save_skeleton_as_action = qt.QAction('Save Skeleton As...', parent=self)
        self._save_new_skeleton_action = qt.QAction('Increment and Save', parent=self)
        self._save_rig_as_action = qt.QAction('Save Rig As...', parent=self)
        self._model_reference_action = qt.QAction(resources.icon('reference'), 'Reference model', parent=self)
        self._clear_references_action = qt.QAction(resources.icon('trash'), 'Clear all references', parent=self)

    def _setup_shortcuts(self):
        """
        Internal function that setup all action shortcuts
        """

        self._new_build_action.setShortcut('Ctrl+N')
        self._open_build_file_action.setShortcut('Ctrl+O')
        self._open_build_tab_action.setShortcut('Ctrl+Shift+O')
        self._save_build_action.setShortcut('Ctrl+S')
        self._save_build_as_action.setShortcut('Ctrl+Shift+S')

    def _setup_sub_menus(self):
        """
        Internal function that creates all menu sub-menus.
        """

        self._recent_projects_menu = qt.QMenu('Recent projects', parent=self)

    def _populate(self):
        """
        Internal function that populates sub-menus and menu itself.
        """

        self.addSection('Project')
        self.addMenu(self._recent_projects_menu)
        self.addSection('Build graph')
        self.addAction(self._new_build_action)
        self.addAction(self._open_build_file_action)
        self.addAction(self._open_build_tab_action)
        self.addAction(self._save_build_action)
        self.addAction(self._save_build_as_action)
        self.addSection('Skeleton')
        self.addAction(self._save_skeleton_as_action)
        self.addAction(self._save_new_skeleton_action)
        self.addSection('Rig')
        self.addAction(self._save_rig_as_action)
        self.addSection('Asset')
        self.addAction(self._model_reference_action)
        self.addAction(self._clear_references_action)

    def _setup_signals(self):
        """
        Internal function that setup menu actions signal connections.
        """

        self.aboutToShow.connect(self._on_about_show)
        self._main_window.mdi_area.subWindowActivated.connect(self._update_actions_state)
        self._new_build_action.triggered.connect(self._main_window.new_build)
        self._open_build_file_action.triggered.connect(self._main_window.open_build)
        self._open_build_tab_action.triggered.connect(self._main_window.open_build_tabbed)
        self._save_build_action.triggered.connect(self._main_window.save_build)
        self._save_build_as_action.triggered.connect(self._main_window.save_build_as)
        self._save_skeleton_as_action.triggered.connect(partial(self._main_window.controller.save_file_as, 'skeleton'))
        self._save_new_skeleton_action.triggered.connect(self._save_new_skeleton_action_triggered)
        self._save_rig_as_action.triggered.connect(partial(self._main_window.controller.save_file_as, 'rig'))
        self._model_reference_action.triggered.connect(self._main_window.controller.reference_model)
        self._clear_references_action.triggered.connect(self._main_window.controller.clear_all_references)

    def _update_actions_state(self):
        """
        Updates actions enable state.
        """

        is_asset_set = True if asset.Asset.get() is not None else False
        is_current_editor = self._main_window.current_editor is not None
        self._model_reference_action.setEnabled(is_asset_set)
        self._save_skeleton_as_action.setEnabled(is_asset_set)
        self._save_new_skeleton_action.setEnabled(is_asset_set)
        self._save_rig_as_action.setEnabled(is_asset_set)
        self._open_build_file_action.setEnabled(is_asset_set)
        self._open_build_tab_action.setEnabled(is_asset_set)
        self._save_build_action.setEnabled(is_asset_set and is_current_editor)
        self._save_build_as_action.setEnabled(is_asset_set and is_current_editor)

    def _on_about_show(self):
        """
        Internal callback function that is called when menu is going to be shown.
        """

        projects_data = self._prefs.recent_projects_queue()
        self._recent_projects_menu.clear()
        for project in projects_data:
            if not os.path.isdir(project[1]):
                continue
            project_action = qt.QAction(project[0], parent=self)
            project_action.setToolTip(project[1])
            project_action.triggered.connect(partial(self._workspace_widget.project_group.set_project, project[1]))
            self._recent_projects_menu.addAction(project_action)

        self._update_actions_state()

    def _save_new_skeleton_action_triggered(self):
        """
        Internal callback function that is called each time New Skeleton action is triggered by the user.
        """

        self._main_window.client.increment_save_file(file_type='skeleton')
        self._workspace_widget.update_data()
