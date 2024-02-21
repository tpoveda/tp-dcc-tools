from __future__ import annotations

from overrides import override

from tp.core import tool

from tp.tools.rig.transferskinweights import consts, view


class TransferSkinWeightsTool(tool.Tool):

    id = consts.TOOL_ID
    creator = 'Tomi Poveda'
    tags = ['skin', 'weights', 'transfer']

    @override
    def execute(self, *args, **kwargs):

        win = view.TransferSkinWeightsView()
        win.show()

        return win
