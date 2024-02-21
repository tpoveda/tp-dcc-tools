from __future__ import annotations

from overrides import override

from tp.core import dcc, tool

from tp.tools.rig.skeletor import consts, view


class SkeletorTool(tool.Tool):

    id = consts.TOOL_ID
    creator = 'Tomi Poveda'
    tags = ['skeleton', 'rig']

    @override
    def execute(self, *args, **kwargs):

        win = view.SkeletorView()
        win.show()

        return win
