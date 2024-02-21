from __future__ import annotations

import typing

import maya.cmds as cmds

from tp.maya import api
from tp.common.python import helpers
from tp.common.qt import api as qt

from tp.libs.rig.freeform import api as freeform

if typing.TYPE_CHECKING:
	from tp.tools.rig.freeform.regionseditor.model import FreeformRegionsEditorModel, RegionEvent


class FreeformController(qt.QObject):

	def pick_node(self, selection_name: str):
		"""
		Pick node from current selected node.

		:param selection_name: whether to select "root" or "end" joint.
		"""

		model = self.sender()			# type: FreeformRegionsEditorModel
		selection = helpers.first_in_list(api.selected())
		if selection:
			if selection_name == 'root':
				model.root = selection.name(include_namespace=False)
			elif selection_name == 'end':
				model.end = selection.name(include_namespace=False)

	def add_region(self, event: RegionEvent):
		"""
		Adds new region.

		:param RegionEvent event: region event.
		"""

		selection = api.selected()
		root_joint = api.node_by_name(event.region.root) if cmds.objExists(event.region.root) else None
		end_joint = api.node_by_name(event.region.end) if cmds.objExists(event.region.end) else None
		if not root_joint or not end_joint:
			cmds.confirmDialog(
				title='Cannot Add Markup', message='Root or End joints not found', button=['OK'], defaultButton='OK',
				cancelButton='OK', dismissString='OK')
			return

		event.success, dialog_message = freeform.create_region(
			root_joint, end_joint, side=event.region.side, region=event.region.name, group=event.region.group,
			com_object=event.region.com_object, com_region=event.region.com_region, com_weight=event.region.com_weight)
		if not event.success:
			cmds.confirmDialog(
				title='Cannot add region markup', message=dialog_message,
				button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK')

		api.select(selection)

	def change_root(self, event: RegionEvent):
		"""
		Checks whether the root region defined within event is valid.

		:param RegionEvent event: region event.
		"""

		old_root = api.node_by_name(event.region.root) if cmds.objExists(event.region.root) else None
		end_joint = api.node_by_name(event.region.end) if cmds.objExists(event.region.end) else None
		new_root = api.node_by_name(event.value) if cmds.objExists(event.value) else None

		event.success = freeform.change_region_root_joint(
			event.region.side, event.region.name, old_root, new_root, end_joint)
		if not event.success:
			cmds.confirmDialog(
				title='Cannot change markup', message='Root and End joints cannot create a joint chain',
				button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK')
			return

	def change_end(self, event: RegionEvent):
		"""
		Checks whether the end region defined within event is valid.

		:param RegionEvent event: region event.
		"""

		root_joint = api.node_by_name(event.region.root) if cmds.objExists(event.region.root) else None
		old_end = api.node_by_name(event.region.end) if cmds.objExists(event.region.end) else None
		new_end = api.node_by_name(event.value) if cmds.objExists(event.value) else None

		event.success = freeform.change_region_end_joint(
			event.region.side, event.region.name, root_joint, old_end, new_end)
		if not event.success:
			cmds.confirmDialog(
				title='Cannot change markup', message='Root and End joints cannot create a joint chain',
				button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK')
			return
