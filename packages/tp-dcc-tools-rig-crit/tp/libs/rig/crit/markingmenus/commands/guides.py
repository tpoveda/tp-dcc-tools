from __future__ import annotations

import typing
from typing import Dict

from overrides import override

from tp.core import log
from tp.maya import api
from tp.maya.libs.triggers import markingmenu
from tp.libs.rig.crit import api as crit

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.rig import Rig

logger = log.rigLogger


class ConstraintGuidesMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critConstraintSelectedGuides'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'plug',
			'label': 'Parent',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		success = crit.commands.parent_selected_components()
		if success:
			logger.info('Completed creating constraint for selection')


class RemoveAllConstraintsMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critRemoveAllConstraints'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'plug_disconnect',
			'label': 'Unparent',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		success = crit.commands.unparent_selected_components()
		if success:
			logger.info('Completed removing all constraints from selected components')


class ComponentGuideSelectPivotMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critComponentSelectGuides'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'cursor',
			'label': 'Select Guide Pivots',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		components = arguments.get('components')
		if not components:
			return

		crit.commands.select_components_guides(components)
		logger.info('Completed selecting guide nodes')


class ComponentSelectRootGuideMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critComponentSelectRootGuide'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'hierarchy',
			'label': 'Select Guide Root',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		components = arguments.get('components')
		if not components:
			return

		crit.commands.select_components_root_guide(components)
		logger.info('Completed selecting guide root nodes')


class ComponentSelectGuideShapeMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critComponentGuideSelectShape'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'cursor',
			'label': 'Select Guide Controls',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		selection = arguments.get('nodes', [])
		selected_guides = []
		for node in selection:
			if crit.Guide.is_guide(api.node_by_object(node.object())):
				selected_guides.append(crit.Guide(node.object()))
		if not selected_guides:
			return

		crit.commands.select_component_guide_shapes(guides=selected_guides)
		logger.info(f'Completed selecting guide shapes of guides: {selected_guides}')


class ComponentSelectAllGuideShapesMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critComponentGuideSelectAllShapes'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:
		return {
			'icon': 'cursor',
			'label': 'Select All Guide Controls',
			'bold': False,
			'italic': False,
			'optionBox': False
		}

	@override
	def execute(self, arguments: Dict):
		components = arguments.get('components', None)
		if not components:
			return

		crit.commands.select_all_component_guide_shapes(components=components)
		logger.info('Completed selecting all guide shapes')


class ComponentToggleVisibilityMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critComponentToggleVisibility'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:

		label = arguments.get('visibilityType', 'None')
		_ui_data = {
			'label': f'{label} Visibility',
			'bold': False,
			'italic': False,
			'optionBox': False,
			'checkBox': False
		}

		rig = arguments.get('rig', None)			# type: Rig
		if not rig:
			return {}

		arguments['rig'] = rig
		visibility = False
		visibility_type = arguments.get('visibilityType', '').lower()
		if visibility_type == 'guides':
			visibility = rig.configuration.guide_pivot_visibility
		elif visibility_type == 'controls':
			visibility = rig.configuration.guide_control_visibility

		arguments['toggleChecked'] = visibility
		_ui_data['checkBox'] = visibility

		return _ui_data

	@override
	def execute(self, arguments: Dict):
		visibility_type = arguments.get('visibilityType', '').lower()
		rig = arguments['rig']
		settings = {}
		if visibility_type == 'guides':
			settings = {'guidePivotVisibility': not rig.configuration.guide_pivot_visibility}
		elif visibility_type == 'controls':
			settings = {'guideControlVisibility': not rig.configuration.guide_control_visibility}
		if settings:
			crit.commands.update_rig_configuration(rig, settings)
			logger.info(f'Completed Toggling visibility of {visibility_type}')


class AutoAlignGuidesMarkingMenuCommand(markingmenu.MarkingMenuCommand):

	ID = 'critGuideAutoAlign'

	@staticmethod
	@override
	def ui_data(arguments: Dict) -> Dict:

		arguments.update(
			{'icon': 'target', 'label': 'Align Selected' if not arguments.get('alignAll') else 'Align All',
			 'bold': False, 'italic': False, 'optionBox': False})

		return arguments

	@override
	def execute(self, arguments: Dict):
		components = arguments.get('components')
		if not components:
			return

		if arguments.get('alignAll'):
			crit.commands.auto_align_guides(components=arguments['rig'].components())
		else:
			crit.commands.auto_align_guides(components=components)

		logger.info('Completed align guides')
