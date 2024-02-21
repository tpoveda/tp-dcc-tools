from __future__ import annotations

import typing

from overrides import override

from tp.maya import api
from tp.maya.meta import base, utils

from tp.libs.rig.freeform import consts
from tp.libs.rig.freeform.utils import scene

if typing.TYPE_CHECKING:
	from tp.libs.rig.freeform.meta.skeleton import FreeformJoints


class FreeformCharacter(base.DependentNode):
	"""
	Character node that is the start point of a character graph.
	"""

	ID = consts.CHARACTER_TYPE
	DEPENDENT_NODE_CLASS = base.Core

	def __init__(
			self, node: api.OpenMaya.MObject | None = None, name: str | None = None,
			parent: api.OpenMaya.MObject | None = None, init_defaults: bool = True, lock: bool = False,
			mod: api.OpenMaya.MDGModifier | None = None):
		super().__init__(node=node, name=name, init_defaults=init_defaults, lock=lock, mod=mod, parent=parent)

		if self.attribute('scalar') == 0.0:
			self.attribute('scalar').set(1.0)

	@override
	def meta_attributes(self) -> list[dict]:
		attrs = super().meta_attributes()

		attrs.extend(
			(
				dict(name=consts.VERSION_ATTR, type=api.kMFnNumericShort),
				dict(name=consts.CHARACTER_NAME_ATTR, type=api.kMFnDataString),
				dict(name=consts.ROOT_PATH_ATTR, type=api.kMFnDataString),
				dict(name=consts.SUB_PATHS_ATTR, type=api.kMFnDataString),
				dict(name=consts.RIG_FILE_PATH_ATTR, type=api.kMFnDataString),
				dict(name=consts.SETTINGS_FILE_PATH_ATTR, type=api.kMFnDataString),
				dict(name=consts.COLOR_SET_ATTR, type=api.kMFnDataString),
				dict(name=consts.SCALAR_ATTR, type=api.kMFnNumericFloat),
				dict(name=consts.ROOT_TRANSFORM_ATTR, type=api.kMFnMessageAttribute),
			)
		)

		return attrs

	@override(check_signature=False)
	def setup(
			self, version: int = 1, root_path: str = '', sub_paths: str = '', rig_file_path: str = '',
			settings_file_path: str = '', color_set: str = '', scalar: float = 1.0):

		self.attribute(consts.VERSION_ATTR).set(version)
		self.attribute(consts.CHARACTER_NAME_ATTR).set(self.fullPathName(partial_name=True, include_namespace=False))
		self.attribute(consts.ROOT_PATH_ATTR).set(root_path)
		self.attribute(consts.SUB_PATHS_ATTR).set(sub_paths)
		self.attribute(consts.RIG_FILE_PATH_ATTR).set(rig_file_path)
		self.attribute(consts.SETTINGS_FILE_PATH_ATTR).set(settings_file_path)
		self.attribute(consts.COLOR_SET_ATTR).set(color_set)
		self.attribute(consts.SCALAR_ATTR).set(scalar)
		self.create_transform(f'{self.fullPathName(partial_name=True, include_namespace=False)}_Character')

	@override(check_signature=False)
	def delete(
			self, move_namespace: str | None = None, mod: api.OpenMaya.MDGModifier | None = None,
			apply: bool = True) -> bool:

		utils.delete_network(self, delete_root_node=False)

		character_group = self.root_transform()
		namespace = character_group.namespace()
		character_group.delete()
		if namespace:
			pass

		super().delete(mod=mod, apply=apply)

		scene.clean_scene()

	def root_transform(self) -> api.DagNode | None:
		"""
		Returns the root transform node for this component instance.

		:return: root transform instance.
		:rtype: api.DagNode or None
		"""

		return self.sourceNodeByName(consts.ROOT_TRANSFORM_ATTR)

	def create_transform(self, name: str) -> api.DagNode:
		"""
		Creates the transform node within Maya scene linked to this meta node.

		:param str name: name of the transform node.
		:return: newly created transform node.
		:rtype: api.DagNode
		"""

		root_transform = api.factory.create_dag_node(name=name, node_type='transform')
		root_transform.setLockStateOnAttributes(consts.TRANSFORM_ATTRS)
		root_transform.showHideAttributes(('translate', 'rotate', 'scale'))
		self.connect_to(consts.ROOT_TRANSFORM_ATTR, root_transform)
		# root_transform.lock(True)

		return root_transform

	def joints(self) -> FreeformJoints:
		"""
		Returns joints meta node instance connected this character.

		:return: joints meta node instance.
		:rtype: FreeformJoints
		"""

		from tp.libs.rig.freeform.meta import skeleton
		return self.upstream(skeleton.FreeformJoints)
