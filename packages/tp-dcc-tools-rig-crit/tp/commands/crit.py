from __future__ import annotations

import typing
from typing import List, Dict

from tp.core import dcc, command
from tp.maya.cmds import contexts

if typing.TYPE_CHECKING:
	from tp.maya.api import DagNode
	from tp.libs.rig.crit.core.rig import Rig
	from tp.libs.rig.crit.core.component import Component
	from tp.libs.rig.crit.meta.nodes import Guide


def create_rig(name: str | None = None, namespace: str | None = None) -> Rig:
	"""
	Creates a new rig instance or returns an existing one.

	:param str name: name of the rig. If not given, a new one will be generated.
	:param str namespace: optional rig namespace.
	:return: newly created rig.
	:rtype: Rig
	"""

	if dcc.is_maya():
		with contexts.disable_node_editor_add_node_context():
			return command.execute('crit.rig.create', **locals())

	return command.execute('crit.rig.create', **locals())


def update_rig_configuration(rig: Rig, settings: Dict):
	"""
	Updates given rig configuration with the given settings.

	:param Rig rig: rig instance to update configuration of.
	:param Dict settings: dictionary containing the setting keys and values.
	"""

	command.execute('crit.rig.configuration.update', **locals())


def rename_rig(rig: Rig, name: str) -> bool:
	"""
	Renames given rig to the given name.

	:param Rig rig: rig instance to rename.
	:param str name: new rig name.
	:return: True if the rename rig command was executed successfully; False otherwise.
	:rtype: bool
	"""

	return command.execute('crit.rig.rename', **locals())


def delete_rig(rig: Rig) -> bool:
	"""
	Deletes given rig instance.

	:param Rig rig: rig instance to delete.
	:return: True if the delete rig command was executed successfully; False otherwise.
	:rtype: bool
	"""

	return command.execute('crit.rig.delete', **locals())


def create_components(
		rig: Rig, components: List[Dict], build_guides: bool = False, build_rigs: bool = False,
		parent_node: DagNode | None = None) -> List[Component]:
	"""
	Creates components under the given rig.

	:param Rig rig: rig we want to create components for.
	:param List[Dict] components: list with the data of the components to create. e.g:
		[
			{'type': 'root', 'name': 'Root', 'side': 'left', 'descriptor': None},
			{'type': 'fkspine', 'name': 'Spine', 'side': 'right', 'descriptor': None},
		]
	:param bool build_guides: whether component guides should be built.
	:param bool build_rigs: whether component rigs should be built.
	:param DagNode or None parent_node: optional component root node parent node.
	:return: list of created components.
	:rtype: List[Component]
	"""

	if dcc.is_maya():
		with contexts.disable_node_editor_add_node_context():
			return command.execute('crit.rig.create.components', **locals())

	return command.execute('crit.rig.create.components', **locals())


def duplicate_components(rig: Rig, components: List[Dict]):
	"""
	Duplicates given rig with the given component data.

	:param Rig rig: rig we want to duplicate components of.
	:param List[Dict] components: component data to duplicate. e.g:
		[
			{'component': Component, 'name': 'root', 'side': 'center'},
			{'component': Component, 'name': 'arm', 'side': 'left'},
		]
	:return:
	"""

	if dcc.is_maya():
		with contexts.disable_node_editor_add_node_context():
			return command.execute('crit.component.duplicate', **locals())

	return command.execute('crit.component.duplicate', **locals())


def rename_component(component: Component, name: str):
	"""
	Renames given component with the new name, exluding the side label.

	:param Component component: component instance to rename.
	:param str name: new component name.
	"""

	command.execute('crit.component.rename', **locals())


def set_component_side(component: Component, side: str):
	"""
	Sets the given component instance side.

	:param Component component: component instance to set side of.
	:param str side: new component side.
	"""

	command.execute('crit.component.rename.side', **locals())


def parent_selected_components() -> bool:
	"""
	Parents currently selected components (selected guides).

	:return: True if parent selected components was successful; False otherwise.
	:rtype: bool
	"""

	return command.execute('crit.component.parent.selectionAdd')


def unparent_selected_components() -> bool:
	"""
	Unparent currently selected components (selected guides).

	:return: True if unparent selected components was successful; False otherwise.
	:rtype: bool
	"""

	return command.execute('crit.component.parent.removeAll')


def select_components_guides(components: List[Component]):
	"""
	Selects all guides of given component instances.

	:param List[Component] components: components with guide pivots to select.
	"""

	command.execute('crit.component.guide.select', components=components)


def select_components_root_guide(components: List[Component]):
	"""
	Selects all root guide of given component instances.

	:param List[Component] components: components with guide pivots to select.
	"""

	command.execute('crit.component.guide.select.root', components=components)


def select_component_guide_shapes(guides: List[Guide]):
	"""
	Select all shapes of given guides.

	:param List[Guide] guides: list of guides whose shapes we want to select.
	"""

	command.execute('crit.component.guide.select.shapes', guides=guides)


def select_all_component_guide_shapes(components: List[Component]):
	"""
	Select all shapes of given guides.

	:param List[Component] components: components with guide pivots to select.
	"""

	command.execute('crit.component.guide.select.shapes.all', components=components)


def delete_components(rig: Rig, components: List[Component], children: bool = True):
	"""
	Deletes given components from rig.

	:param Rig rig: rig we want to delete components of.
	:param List[Component] components: list of component instances to delete.
	:param bool children: whether recursively delete all connected child components.
	:return:
	"""

	command_id = 'crit.component.delete'

	def _repeat_delete_components():

		from tp.libs.rig.crit import api as crit
		selected_components = crit.components_from_selected()
		if not selected_components:
			return
		rig_instance = None
		selected_components = list(selected_components.keys())
		for component in selected_components:
			rig_instance = component.rig
			break
		command.execute(command_id, rig=rig_instance, components=selected_components, children=children)

	result = command.execute(command_id, rig=rig, components=components, children=children)
	if dcc.is_maya():
		from tp.maya.cmds import helpers
		helpers.create_repeat_command_for_function(_repeat_delete_components)

	return result


def auto_align_guides(components: List[Component]):
	"""
	Realign all given component guides by realigning the rotations using the guide settings for auto align feature.

	:param List[Component] components: list of components whose guides we want to align.
	"""

	command.execute('crit.component.guide.align.all', **locals())