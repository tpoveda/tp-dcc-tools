from __future__ import annotations

import typing

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.common.nodegraph.core import graph
from tp.libs.rig.noddle.core import asset

logger = log.rigLogger

if typing.TYPE_CHECKING:
    from tp.tools.rig.noddle.builder.controller import NoddleController


class NodeEditor(graph.NodeGraph):
    def __init__(self, controller: NoddleController, parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

        self._controller = controller

    @property
    def controller(self) -> NoddleController:
        return self._controller

    @override
    def save_build_as(self) -> bool:
        """
        Saves current build graph into disk in a new file.

        :return: True if save operation was successful; False otherwise.
        :rtype: bool
        """

        if not asset.Asset.get():
            logger.warning('Asset is not set')
            return False

        rig_filter = 'Rig Build (*.rig)'
        file_path = qt.QFileDialog.getSaveFileName(
            None, 'Save build graph to file', asset.Asset.get().new_build_path, rig_filter)[0]
        if not file_path:
            return False
        self.save_to_file(file_path)
        return True

    @override
    def open_build(self) -> bool:
        """
        Opens a build for the active asset.

        :return: True if build was opened successfully; False otherwise.
        :rtype: bool
        """

        if not asset.Asset.get():
            logger.warning('Asset is not set!')
            return False
        if not self.maybe_save():
            return False

        rig_filter = 'Rig Build (*.rig)'
        file_path = qt.QFileDialog.getOpenFileName(None, 'Open rig build scene', asset.Asset.get().build, rig_filter)[0]
        if not file_path:
            return False

        self.load_from_file(file_path)

        return True

    def save_build(self):
        """
        Saves current build graph into disk.

        :return: True if save operation was successful; False otherwise.
        :rtype: bool
        """

        if not asset.Asset.get():
            logger.warning('Asset is not set')
            return False

        return super().save_build()
