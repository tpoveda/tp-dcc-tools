from __future__ import annotations

import typing

import maya.cmds as cmds

from tp.maya import api
from tp.common.python import helpers
from tp.libs.rig.freeform import consts
from tp.libs.rig.freeform.meta import skeleton as meta_skeleton
from tp.libs.rig.freeform.library.functions import skeleton, character

if typing.TYPE_CHECKING:
	from tp.libs.rig.freeform.meta.character import FreeformCharacter


def freeze_xform_rig(character_node: FreeformCharacter):
	"""
	Duplicates the skeleton, freezes all transforms, characterizes the new skeleton and saves a temporary character
	YAML file with all the zeroed joint values in it.

	:param FreeformCharacter character_node: character meta node instance.
	"""

	character_joints = character_node.upstream(meta_skeleton.FreeformJoints)

	joints = character_joints.joints()
	joint_names = [jnt.fullPathName() for jnt in joints]
	root = skeleton.root_joint(helpers.first_in_list(joints))

	new_skeleton = [api.node_by_name(jnt) for jnt in cmds.duplicate(joint_names, parentOnly=True, fullPath=True)]
	new_root = skeleton.root_joint(helpers.first_in_list(new_skeleton))
	new_root.setParent(None)
	new_root.rename(root.name(include_namespace=False))

	for jnt in new_skeleton:
		jnt.setLockStateOnAttributes(consts.TRANSFORM_ATTRS, state=False)
		jnt.attribute('translate').set(jnt.attribute(consts.BIND_TRANSLATE_ATTR).value())
		jnt.attribute('rotate').set(jnt.attribute(consts.BIND_ROTATE_ATTR).value())

	constraints_to_delete = cmds.listRelatives(new_root.fullPathName(), ad=True, type='constraint')
	if constraints_to_delete:
		cmds.delete(constraints_to_delete)
	cmds.makeIdentity([jnt.fullPathName() for jnt in new_skeleton], apply=True)

	new_character_node = character.characterize_skeleton(
		new_root, name='ZeroTemp', update_ui=False, freeze_skeleton=False)

	new_character_node.delete()
