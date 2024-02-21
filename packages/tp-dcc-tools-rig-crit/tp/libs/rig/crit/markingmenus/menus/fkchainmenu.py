from __future__ import annotations

import typing
from typing import Dict

from overrides import override

from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.markingmenus.menus import defaultguidemenu

if typing.TYPE_CHECKING:
	from tp.maya.libs.triggers.markingmenu import MarkingMenuLayout


class CritFkChainGuideMenu(defaultguidemenu.CritDefaultGuideMenu):

	ID = 'critFkChainGuideMenu'

	@override
	def execute(self, layout: MarkingMenuLayout, arguments: Dict) -> MarkingMenuLayout | None:

		layout = super().execute(layout, arguments)
		if layout is None:
			return layout

		layout['sortOrder'] = 10

		components_manager = crit.Configuration().components_manager()
		fk_component_class = components_manager.find_component_by_type('fkchain')
		for comp, _ in arguments.get('componentToNodes', {}).items():
			if not isinstance(comp, fk_component_class):
				continue
			layout['items']['generic'].insert(0, {
				'type': 'command',
				'id': 'critFkAddGuide',
				'arguments': arguments
			})
			layout['items']['generic'].insert(1, {
				'type': 'command',
				'id': 'critFkSetParentGuide',
				'arguments': arguments
			})
			layout['items']['generic'].insert(2, {'type': 'separator'})
			break

		return layout
