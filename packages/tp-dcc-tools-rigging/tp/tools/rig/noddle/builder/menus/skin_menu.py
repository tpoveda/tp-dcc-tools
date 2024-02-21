from __future__ import annotations

import typing

from tp.common.qt import api as qt
from tp.common.resources import api as resources
from tp.libs.rig.noddle.core import asset

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.graph import NodeGraph
    from tp.tools.rig.noddle.builder.controller import NoddleController
    from tp.tools.rig.noddle.builder.window import NoddleBuilderWindow


class SkinMenu(qt.QMenu):
    def __init__(self, main_window: NoddleBuilderWindow, parent: qt.QWidget | None = None):
        super().__init__('Skin', parent=parent or main_window)

        self._main_window = main_window

        self._setup_actions()
        self._populate()
        self._setup_signals()

        self.setTearOffEnabled(True)

    @property
    def controller(self) -> NoddleController:
        return self._main_window.controller

    @property
    def graph(self) -> NodeGraph:
        editor = self._main_window.current_editor
        return editor.graphics_scene.graph if editor else None

    def _setup_actions(self):
        """
        Internal function that creates all menu actions.
        """

        self._bind_skin_action = qt.QAction(resources.icon('smoothSkin'), 'Bind Skin', parent=self)
        self._detach_skin_action = qt.QAction(resources.icon('detachSkin'), 'Detach Skin', parent=self)
        self._mirror_skin_action = qt.QAction(resources.icon('mirrorSkinWeight'), 'Mirror Weights', parent=self)
        self._copy_skin_action = qt.QAction(resources.icon('copySkinWeight'), 'Copy Weights', parent=self)
        self._export_all_action = qt.QAction(resources.icon('save'), 'Export Asset Weights', parent=self)
        self._import_all_action = qt.QAction(resources.icon('import'), 'Import Asset Weights', parent=self)

    def _populate(self):
        """
        Internal function that populates sub-menus and menu itself.
        """

        self.addAction(self._bind_skin_action)
        self.addAction(self._detach_skin_action)
        self.addSection('Weight Maps')
        self.addAction(self._mirror_skin_action)
        self.addAction(self._copy_skin_action)
        self.addSection('Asset')
        self.addAction(self._export_all_action)
        self.addAction(self._import_all_action)

    def _setup_signals(self):
        """
        Internal function that setup menu actions signal connections.
        """

        self.aboutToShow.connect(self._update_actions_state)
        self._bind_skin_action.triggered.connect(self.controller.bind_skin)
        self._detach_skin_action.triggered.connect(self.controller.detach_skin)
        self._mirror_skin_action.triggered.connect(self.controller.mirror_skin_weights)
        self._copy_skin_action.triggered.connect(self.controller.copy_skin_weights)
        self._export_all_action.triggered.connect(self.controller.export_asset_weights)
        self._import_all_action.triggered.connect(self.controller.import_asset_weights)

    def _update_actions_state(self):
        """
        Internal function that updates the enable state of actions for this menu.
        """

        is_asset_set = True if asset.Asset.get() else False
        self._export_all_action.setEnabled(is_asset_set)
        self._import_all_action.setEnabled(is_asset_set)
