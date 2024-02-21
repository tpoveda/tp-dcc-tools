from __future__ import annotations

import os
import sys
import typing
import subprocess
from functools import partial

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.preferences.interfaces import noddle
from tp.common.resources import api as resources
from tp.libs.rig.noddle.core import asset, project
from tp.tools.rig.noddle.builder.widgets import shared

if typing.TYPE_CHECKING:
    from tp.tools.rig.noddle.builder.controller import NoddleController

logger = log.rigLogger


class WorkspaceWidget(qt.QWidget):

    LABEL = 'Workspace'

    def __init__(self, controller: NoddleController, parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

        self._controller = controller

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

        self.setMinimumWidth(315)

    @property
    def project_group(self) -> ProjectGroup:
        return self._project_group

    @override
    def showEvent(self, event: qt.QShowEvent) -> None:
        super().showEvent(event)
        self.update_data()

    def update_data(self):
        """
        Function that updates groups data.
        """

        self._project_group.update_project()
        self._asset_group.update_asset_data()

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        self._scroll_widget = shared.ScrollWidget(parent=self)
        self._project_group = ProjectGroup(parent=self)
        self._asset_group = AssetGroup(controller=self._controller, parent=self)
        self._scroll_widget.add_widget(self._project_group)
        self._scroll_widget.add_widget(self._asset_group)
        self._scroll_widget.content_layout.addStretch()

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        self._main_layout = qt.vertical_layout(margins=(0, 0, 0, 0))
        self.setLayout(self._main_layout)

        self._main_layout.addWidget(self._scroll_widget)

    def _setup_signals(self):
        """
        Internal function that creates all signal connections.
        """

        self._project_group.projectChanged.connect(self._on_project_changed)
        self._project_group.exit_button.clicked.connect(self._asset_group.reset_asset_data)

    def _on_project_changed(self, current_project: project.Project | None):
        """
        Internal callback function that is called each time project is changed by the user.

        :param project.Project or None current_project: active project.
        """

        self._asset_group.setDisabled(current_project is None)
        self._asset_group.update_asset_data()
        self._asset_group.update_asset_completion()


class ProjectGroup(qt.QGroupBox):

    projectChanged = qt.Signal(project.Project)

    def __init__(self, title: str = 'Project', parent: qt.QWidget | None = None):
        super().__init__(title, parent=parent)

        self._prefs = noddle.noddle_interface()

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

    @property
    def exit_button(self) -> qt.QPushButton:
        return self._exit_button

    def set_project(self, project_path: str):
        """
        Sets current active Noddle project.

        :param str project_path: absolute path pointing to noddle project directory.
        """

        active_project = project.Project.set(project_path)
        self.projectChanged.emit(active_project)

    def update_project(self):
        current_project = project.Project.get()
        if not current_project:
            self._name_line_edit.setText('Not set')
            return

        self._name_line_edit.setText(current_project.name)
        self._name_line_edit.setToolTip(current_project.path)

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        self._current_label = qt.label('Current:', parent=self)
        self._name_line_edit = qt.line_edit(read_only=True, parent=self)
        self._set_button = qt.base_button(icon=resources.icon('folder'), tooltip='Set existing project.', parent=self)
        self._create_button = qt.base_button(icon=resources.icon('plus'), tooltip='Create new project.', parent=self)
        self._exit_button = qt.base_button(icon=resources.icon('exit'), tooltip='Exit Noddle workspace.', parent=self)

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        self._main_layout = qt.horizontal_layout(margins=(0, 0, 0, 0))
        self.setLayout(self._main_layout)

        self._main_layout.addWidget(self._current_label)
        self._main_layout.addWidget(self._name_line_edit)
        self._main_layout.addWidget(self._create_button)
        self._main_layout.addWidget(self._set_button)
        self._main_layout.addWidget(self._exit_button)

    def _setup_signals(self):
        """
        Internal function that creates all signal connections.
        """

        self._create_button.clicked.connect(self._on_create_button_clicked)
        self._set_button.clicked.connect(self._on_set_button_clicked)
        self._exit_button.clicked.connect(self._on_exit_button_clicked)
        self.projectChanged.connect(self._on_project_changed)

    def _on_create_button_clicked(self):
        """
        Internal callback function that is called each time Create button is clicked by the user.
        """

        prev_project_path = self._prefs.previous_project()
        logger.debug(f'Previous project: {prev_project_path}')
        root_dir = os.path.dirname(prev_project_path) if os.path.isdir(prev_project_path) else ''
        path = qt.QFileDialog.getExistingDirectory(None, 'Create Noddle project', root_dir)
        if not path:
            return
        new_project = project.Project.create(path)
        self.projectChanged.emit(new_project)

    def _on_set_button_clicked(self):
        """
        Internal callback function that is called each time Set button is clicked by the user.
        """

        prev_project_path = self._prefs.previous_project()
        logger.debug(f'Previous project: {prev_project_path}')
        root_dir = os.path.dirname(prev_project_path) if os.path.isdir(prev_project_path) else ''
        path = qt.QFileDialog.getExistingDirectory(None, 'Set Noddle project', root_dir)
        if not path:
            return
        self.set_project(path)

    def _on_exit_button_clicked(self):
        """
        Internal callback function that is called each time Exit button is clicked by the user.
        Exists current active Noddle project.
        """

        project.Project.exit()
        self.projectChanged.emit(None)

    def _on_project_changed(self):
        """
        Internal callback function that is called each time Noddle active project is changed.
        """

        self.update_project()


class AssetGroup(qt.QGroupBox):

    assetChanged = qt.Signal(object)

    def __init__(self, controller: NoddleController, title: str = 'Asset', parent: qt.QWidget | None = None):
        super().__init__(title, parent=parent)

        self._controller = controller
        self._prefs = noddle.noddle_interface()
        self._asset_types = self._prefs.asset_types() or ['character']

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

        self.setContextMenuPolicy(qt.Qt.CustomContextMenu)

    @override
    def keyPressEvent(self, event: qt.QKeyEvent):
        super().keyPressEvent(event)
        if event.key() == qt.Qt.Key_Enter:
            self._set_asset()

    def update_asset_data(self):
        """
        Updates asset data.
        """

        current_project = project.Project.get()
        current_asset = asset.Asset.get()
        if not current_project or not current_asset:
            self.reset_asset_data()
            return

        self._asset_name_line_edit.setText(current_asset.name)
        self._asset_type_combo.setCurrentText(current_asset.type)
        self._model_path_widget.line_edit.setText(current_asset.model_path)
        self._rig_path_widget.line_edit.setText(current_asset.latest_rig_path)
        self._file_system.setRootPath(current_asset.path)
        self._file_tree.setRootIndex(self._file_system.index(current_asset.path))

    def update_asset_completion(self):
        """
        Updates asset completion.
        """

        current_project = project.Project.get()
        if not current_project:
            self._asset_name_line_edit.setCompleter(None)
            return

        project_meta = current_project.meta_data
        asset_list = project_meta.get(f'{self._asset_type_combo.currentText()}s', [])
        if not asset_list:
            self._asset_name_line_edit.setCompleter(None)
            return

        completer = qt.QCompleter(asset_list)
        completer.setCaseSensitivity(qt.Qt.CaseInsensitive)
        self._asset_name_line_edit.setCompleter(completer)

    def reset_asset_data(self):
        """
        Resets asset data.
        """
        current_project = project.Project.get()
        root_path = current_project.path if current_project else '~'

        self._asset_name_line_edit.clear()
        self._model_path_widget.line_edit.clear()
        self._rig_path_widget.line_edit.clear()
        self._file_system.setRootPath(root_path)
        self._file_tree.setRootIndex(self._file_system.index(root_path))

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        self._asset_type_combo = qt.combobox(items=self._asset_types, parent=self)
        self._asset_name_line_edit = qt.line_edit(placeholder_text='Name', parent=self)
        self._file_system =  qt.QFileSystemModel()
        self._file_system.setNameFilterDisables(False)
        self._file_tree = qt.QTreeView(parent=self)
        self._file_tree.setModel(self._file_system)
        self._file_tree.hideColumn(1)
        self._file_tree.hideColumn(2)
        self._file_tree.setColumnWidth(0, 200)
        self._file_tree.setMinimumWidth(200)
        self._file_tree.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self._model_path_widget = shared.PathWidget(
            mode=shared.PathWidget.Mode.EXISTING_FILE, label_text='Model file: ', dialog_label='Select model file',
            parent=self)
        self._rig_path_widget = shared.PathWidget(
            mode=shared.PathWidget.Mode.EXISTING_FILE, label_text='Latest rig: ', parent=self)
        self._rig_path_widget.browse_button.hide()
        self._model_open_button = qt.base_button(icon=resources.icon('open'), parent=self)
        self._model_reference_button = qt.base_button(icon=resources.icon('reference'), parent=self)
        self._model_path_widget.add_widget(self._model_open_button)
        self._model_path_widget.add_widget(self._model_reference_button)
        self._rig_open_button = qt.base_button(icon=resources.icon('open'), parent=self)
        self._rig_reference_button = qt.base_button(icon=resources.icon('reference'), parent=self)
        self._rig_path_widget.add_widget(self._rig_open_button)
        self._rig_path_widget.add_widget(self._rig_reference_button)

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        self._main_layout = qt.vertical_layout(margins=(0, 0, 0, 0))
        self.setLayout(self._main_layout)

        self._basic_info_layout = qt.horizontal_layout(margins=(0, 0, 0, 0))
        self._basic_info_layout.addWidget(self._asset_type_combo)
        self._basic_info_layout.addWidget(self._asset_name_line_edit)

        self._main_layout.addLayout(self._basic_info_layout)
        self._main_layout.addWidget(self._file_tree)
        self._main_layout.addWidget(self._model_path_widget)
        self._main_layout.addWidget(self._rig_path_widget)

    def _setup_signals(self):
        """
        Internal function that creates all signal connections.
        """

        self._file_tree.doubleClicked.connect(self._on_file_tree_double_clicked)
        self._asset_name_line_edit.returnPressed.connect(self._on_asset_name_line_edit_return_pressed)
        self._asset_type_combo.currentIndexChanged.connect(self.update_asset_completion)
        self._model_path_widget.line_edit.textChanged.connect(self._on_model_path_line_edit_changed)
        self._model_open_button.clicked.connect(partial(self._open_asset_file, 'model'))
        self._model_reference_button.clicked.connect(partial(self._open_asset_file, 'model', reference=True))
        self._rig_open_button.clicked.connect(partial(self._open_asset_file, 'rig'))
        self._rig_reference_button.clicked.connect(partial(self._open_asset_file, 'rig', reference=True))
        self._file_tree.customContextMenuRequested.connect(self._on_files_tree_custom_context_menu_requested)
        self.assetChanged.connect(self.update_asset_data)

    def _on_file_tree_double_clicked(self, index: qt.QModelIndex):
        """
        Internal callback function that is called each time file tree is double-clicked by the user.

        :param qt.QModelIndex index: index of the item within model.
        """

        if self._file_system.isDir(index):
            return

        path = os.path.normpath(self._file_system.filePath(index))
        dcc_file_extensions = self._controller.execute('file_extensions').get('ReturnValue', [])
        if dcc_file_extensions and any([path.endswith(ext) for ext in dcc_file_extensions]):
            self._controller.open_file(path, force=True)
        else:
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.call([opener, path])

    def _open_asset_file(self, file_type: str, reference: bool = False):
        """
        Internal function that opens file of given type.

        :param str file_type: file type to open ('model', 'rig')
        :param bool reference: whether to reference file or just open it.
        """

        file_path = ''
        if file_type == 'model':
            file_path = self._model_path_widget.line_edit.text()
        elif file_type == 'rig':
            file_path = self._rig_path_widget.line_edit.text()
        if not file_path or not os.path.isfile(file_path):
            logger.warning(f'Invalid file path: "{file_path}"')
            return

        if reference:
            self._controller.reference_file(file_path)
        else:
            self._controller.open_file(file_path, force=True)

    def _set_asset(self):
        """
        Internal function that sets active asset.
        """

        current_project = project.Project.get()
        asset_name = self._asset_name_line_edit.text()
        if not current_project or not asset_name:
            return
        asset_type = self._asset_type_combo.currentText().lower()
        asset_path = os.path.normpath(os.path.join(current_project.path, f'{asset_type}s', asset_name))
        if not os.path.isdir(asset_path):
            reply = qt.QMessageBox.question(self, 'Missing asset', f'Asset {asset_name} does not exist. Create it?')
            if not reply == qt.QMessageBox.Yes:
                return
        new_asset = asset.Asset(current_project, asset_name, asset_type)
        self.assetChanged.emit(new_asset)

    def _on_asset_name_line_edit_return_pressed(self):
        """
        Internal callback function that is called each time asset name line edit changes are accepted by the user.
        """

        self._set_asset()

    def _on_model_path_line_edit_changed(self):
        """
        Internal callback function that is called each time model path widget line edit is changed by the user.
        """

        current_asset = asset.Asset.get()
        if not current_asset:
            return
        if self._model_path_widget.line_edit.text() == current_asset.model_path:
            return
        current_asset.set_data('model', self._model_path_widget.line_edit.text())
        logger.info(f'Set asset model to: "{self._model_path_widget.line_edit.text()}"')

    def _on_files_tree_custom_context_menu_requested(self, pos: qt.QPoint):
        """
        Internal callback function that is called each time files tree context menu is requested by the user.

        :param qt.QPoint pos: global menu position.
        """

        def _revel_in_explorer(_index: qt.QModelIndex):
            path = self._file_system.filePath(_index)
            if os.path.isfile(path):
                path = os.path.dirname(path)
            qt.QDesktopServices.openUrl(qt.QUrl.fromLocalFile(path))

        context_menu = qt.QMenu('File menu', self)
        open_action = qt.QAction('Open', self)
        reveal_action = qt.QAction('Reveal in explorer', self)
        open_action.triggered.connect(partial(self._on_file_tree_double_clicked, self._file_tree.currentIndex()))
        reveal_action.triggered.connect(partial(_revel_in_explorer, self._file_tree.currentIndex()))
        context_menu.addAction(open_action)
        context_menu.addAction(reveal_action)
        context_menu.exec_(self._file_tree.mapToGlobal(pos))
