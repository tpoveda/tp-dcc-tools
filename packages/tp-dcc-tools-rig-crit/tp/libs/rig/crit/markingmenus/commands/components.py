from __future__ import annotations

from typing import Dict

from overrides import override

from tp.core import log
from tp.maya.libs.triggers import markingmenu
from tp.commands import crit

logger = log.rigLogger


class DeleteSelectedComponentMarkingMenuCommand(markingmenu.MarkingMenuCommand):

    ID = 'critDeleteComponent'

    @staticmethod
    @override
    def ui_data(arguments: Dict) -> Dict:
        return {
            'icon': 'trash',
            'label': 'Delete',
            'bold': False,
            'italic': False,
            'optionBox': False
        }

    @override
    def execute(self, arguments: Dict):
        components = arguments.get('components')
        rig = arguments.get('rig')
        msg = ','.join('_'.join([comp.name(), comp.side()]) for comp in components)
        crit.delete_components(rig, components)
        logger.info(f'Completed deleting components: {msg}')
