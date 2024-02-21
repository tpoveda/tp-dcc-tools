from __future__ import annotations

from typing import Any, Callable

from overrides import override

import maya.cmds as cmds
from tp.core import log
from tp.dcc import scene
from tp.maya.cmds import gui
from tp.common.nodegraph import api
from tp.common.nodegraph.nodes import node_graph_inout

from tp.libs.rig.noddle.core import asset
from tp.libs.rig.noddle.functions import assets

logger = log.tpLogger


class GraphInputNodeAsset(node_graph_inout.GraphInputNode):

    ID = 110
    DEFAULT_TITLE = 'Input Asset'
    IS_INPUT = True

    @property
    def out_asset_name(self) -> api.OutputSocket:
        return self._out_asset_name

    @override
    def _setup_sockets(self, reset: bool = True):
        super()._setup_sockets()

        self._out_asset_name = self.add_output(api.dt.String, label='Asset Name', value='')

    @override
    def execute(self) -> Any:
        if not asset.Asset.get():
            logger.error('Asset is not set')
            raise ValueError

        self.out_asset_name.set_value(asset.Asset.get().name)

        scene.Scene().new()
        assets.import_model()
        assets.import_skeleton()


class GraphOutputNodeAsset(node_graph_inout.GraphOutputNode):

    ID = 111
    DEFAULT_TITLE = 'Output Asset'

    @property
    def in_character(self) -> api.InputSocket:
        return self._in_character

    @override
    def _setup_sockets(self, reset: bool = True):
        super()._setup_sockets()

        self._in_character = self.add_input(api.DataType.CHARACTER, label='Character')
        self.mark_input_as_required(self._in_character)

    @override
    def execute(self) -> Any:
        try:
            self.in_character.value().save_bind_pose()
            gui.switch_xray_joints()
            cmds.viewFit(self.in_character.value().root_control().group.fullPathName())
            self.in_character.value().geometry_group().overrideEnabled.set(True)
            self.in_character.value().geometry_group().overrideColor.set(True)
            return 0
        except Exception:
            logger.exception(f'Failed to exec {self.title} node', exc_info=True)
            return 1


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
    register_node(GraphInputNodeAsset.ID, GraphInputNodeAsset)
    register_node(GraphOutputNodeAsset.ID, GraphOutputNodeAsset)
