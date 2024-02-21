from __future__ import annotations

import typing

from tp.core import dcc, command
from tp.maya.cmds import contexts

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.rig import Rig


def build_guide_controls(rig: Rig):

    with contexts.undo_chunk_context('BuildNoddleGuideControls'), contexts.disable_node_editor_add_node_context():

        command.execute('noddle.rig.guides.build.controls', rig=rig)
        if rig.skeleton_layer():
            pass
