from __future__ import annotations

import os
import inspect

from overrides import override

import maya.cmds as cmds
import maya.mel as mel

from tp.common.qt import api as qt
from tp.common.nodegraph import registers
from tp.tools.rig.noddle.builder.controllers import abstract
from tp.libs.rig.noddle.core import nodes, component, animcomponent, rig
from tp.libs.rig.noddle.io import skin


class MayaNoddleController(abstract.AbstractNoddleController):

    @override
    def open_file(self, file_path: str, force: bool = False) -> bool:
        """
        Open file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :param bool force: whether to force the opening of the file.
        :return: True if file was opened successfully; False otherwise.
        :rtype: bool
        """

        cmds.file(file_path, open=True, force=force)
        return True

    @override
    def reference_file(self, file_path: str) -> bool:
        """
        References file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :return: True if file was referenced successfully; False otherwise.
        :rtype: bool
        """

        cmds.file(file_path, reference=True)
        return True

    def nodes_paths(self) -> list[str]:
        root_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        return [os.path.join(root_path, 'nodes')]

    @override
    def load_data_types(self):
        if not registers.DataType.is_type_registered('CONTROL'):
            registers.DataType.register_data_type(
                'CONTROL', nodes.ControlNode, qt.QColor("#2BB12D"), label='Color', default_value=None)
        if not registers.DataType.is_type_registered('COMPONENT'):
            registers.DataType.register_data_type(
                'COMPONENT', component.Component, qt.QColor("#6495ED"), label='Component', default_value=None)
        if not registers.DataType.is_type_registered('ANIM_COMPONENT'):
            registers.DataType.register_data_type(
                'ANIM_COMPONENT', animcomponent.AnimComponent, qt.QColor("#6495ED"), label='AnimComponent',
                default_value=None)
        if not registers.DataType.is_type_registered('RIG'):
            registers.DataType.register_data_type(
                'RIG', rig.Rig, qt.QColor("#5767FF"), label='Character', default_value=None)

    @override
    def reference_model(self):
        pass

    @override
    def clear_all_references(self):
        pass

    @override
    def increment_save_file(self, file_type):
        pass

    @override
    def save_file_as(self, file_type):
        pass

    @override
    def bind_skin(self):
        mel.eval('SmoothBindSkinOptions;')

    @override
    def detach_skin(self):
        mel.eval('DetachSkinOptions;')

    @override
    def mirror_skin_weights(self):
        mel.eval('MirrorSkinWeightsOptions;')

    @override
    def copy_skin_weights(self):
        mel.eval('CopySkinWeightsOptions;')

    @override
    def export_asset_weights(self):
        skin.SkinManager.export_all()

    @override
    def import_asset_weights(self):
        skin.SkinManager.import_all()

    @override
    def export_selected_weights(self):
        skin.SkinManager.export_selected()

    @override
    def import_selected_weights(self):
        skin.SkinManager.import_selected()

