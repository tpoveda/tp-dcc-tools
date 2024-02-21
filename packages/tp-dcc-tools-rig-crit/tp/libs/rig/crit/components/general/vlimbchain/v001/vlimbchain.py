from __future__ import annotations

from typing import List, Dict

from overrides import override

from tp.maya import api
from tp.maya.om import mathlib

from tp.libs.rig.utils.maya import align, skeleton
from tp.libs.rig.crit import api as crit
from tp.libs.rig.crit.core import component

STRETCH_ATTRS = ('stretch', 'maxStretch', 'minStretch', 'upperStretch', 'lowerStretch')


class VChainComponent(component.Component):

	ID = 'vlimbchain'
	DESCRIPTION = 'Component that allow the creation of limbs'

	world_end_rotation = False
	world_end_aim_guide_id = ''
	# used internally to determine if the end guide should hae default alignment behaviour
	_reset_end_guide_alignment = True
	# TODO: flag used to invert the plane normal, this is only required by legs. we should being able to remove this.
	_flip_auto_align_up_vector = True
	ik_control_ids = ('endik', 'upVec')
	fk_control_ids = ('uprfk', 'midfk', 'endfk')
	skeleton_joint_ids = ('upr', 'mid', 'end')

	_space_switch_driven = [
		crit.SpaceSwitchUIDriven(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'endik')), label='End IK'),
		crit.SpaceSwitchUIDriven(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'baseik')), label='Base IK'),
		crit.SpaceSwitchUIDriven(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'upVec')), label='Pole Vector'),
		crit.SpaceSwitchUIDriven(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'uprfk')), label='FK'),
	]
	_space_switch_drivers = [crit.SpaceSwitchUIDriver(**i.serialize()) for i in _space_switch_driven]
	_space_switch_drivers.extend([
		crit.SpaceSwitchUIDriver(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'midfk')), label='Mid FK'),
		crit.SpaceSwitchUIDriver(id=crit.path_as_descriptor_expression(('self', 'rigLayer', 'endfk')), label='End FK'),
	])

	@override
	def id_mapping(self) -> Dict:
		return {
			crit.consts.SKELETON_LAYER_TYPE: {
				'upr': 'upr',
				'mid': 'mid',
				'end': 'end'
			},
			crit.consts.INPUT_LAYER_TYPE: {
				'upr': 'upr',
				'end': 'end',
				'upVec': 'upVec'
			},
			crit.consts.OUTPUT_LAYER_TYPE: {
				'upr': 'upr',
				'mid': 'mid',
				'end': 'end'
			},
			crit.consts.RIG_LAYER_TYPE: {
				'upVec': 'upVec'
			}
		}

	@override
	def set_skeleton_naming(self, naming_manager: crit.NameManager, mod: api.DGModifier):
		component_name, component_side = self.name(), self.side()
		for joint in self.skeleton_layer().iterate_joints():
			joint_name = naming_manager.resolve(
				'skinJointName', {'componentName': component_name, 'side': component_side, 'id': joint.id(), 'type': 'joint'})
			joint.rename(joint_name, maintain_namespace=False, mod=mod, apply=False)
		for input_node in self.input_layer().iterate_inputs():
			input_name = naming_manager.resolve(
				'inputName',
				{'componentName': component_name, 'side': component_side, 'id': input_node.id(), 'type': 'input'})
			input_node.rename(input_name, maintain_namespace=False, mod=mod, apply=False)
		for output_node in self.output_layer().iterate_outputs():
			output_name = naming_manager.resolve(
				'outputName',
				{'componentName': component_name, 'side': component_side, 'id': output_node.id(), 'type': 'output'})
			output_node.rename(output_name, maintain_namespace=False, mod=mod, apply=False)

	@override
	def space_switch_ui_data(self) -> Dict:

		driven = self._space_switch_driven
		drivers = [
			crit.SpaceSwitchUIDriver(id=crit.path_as_descriptor_expression(('self', 'inputLayer', 'upr')), label='Parent Component', internal=True),
			crit.SpaceSwitchUIDriver(id=crit.path_as_descriptor_expression(('self', 'inputLayer', 'world')), label='World Space', internal=True),
		]
		drivers += list(self._space_switch_drivers)

		return {
			'driven': driven,
			'drivers': drivers
		}

	@override(check_signature=False)
	def align_guides(self) -> bool:

		if not self.has_guide():
			return False

		guide_layer = self.guide_layer()
		upper_guide, mid_guide, end_guide, up_vector_guide = guide_layer.find_guides('upr', 'mid', 'end', 'upVec')
		chain_guides = [upper_guide, mid_guide, end_guide]
		positions = [guide.translation() for guide in chain_guides]
		aim_vector = upper_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR).value()
		up_vector = upper_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR).value()
		rotate_axis, _ = mathlib.perpendicular_axis_from_align_vectors(aim_vector, up_vector)
		rotate_axis = api.Vector(mathlib.AXIS_VECTOR_BY_INDEX[rotate_axis])
		if mathlib.is_vector_negative(aim_vector):
			rotate_axis *= -1
		constructed_plane = align.construct_plane_from_positions(positions, chain_guides, rotate_axis=rotate_axis)
		guides, matrices = [], []

		for current_guide, target_guide in align.align_nodes_iterator(chain_guides, constructed_plane, skip_end=True):
			if not current_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_ATTR).asBool():
				continue

			up_vector = current_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR).value() * self._flip_auto_align_up_vector
			aim_vector = current_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR).value()
			rotation = mathlib.look_at(
				current_guide.translation(api.kWorldSpace),
				target_guide.translation(api.kWorldSpace),
				aim_vector=api.Vector(aim_vector),
				up_vector=api.Vector(up_vector),
				world_up_vector=constructed_plane.normal())
			transform = current_guide.transformationMatrix(space=api.kWorldSpace)
			transform.setRotation(rotation)
			matrices.append(transform.asMatrix())
			guides.append(current_guide)

		if end_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_ATTR).asBool():
			if self._reset_end_guide_alignment:
				transform = end_guide.transformationMatrix()
				mid_rotation = mid_guide.rotation(api.kWorldSpace)
				transform.setRotation(mid_rotation)
				matrices.append(transform.asMatrix())
				guides.append(end_guide)
			else:
				up_vector = end_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR).value()
				aim_vector = end_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR).value()
				end_guide.aim_to_child(aim_vector=api.Vector(aim_vector), up_vector=api.Vector(up_vector))

		crit.Guide.set_guides_world_matrix(guides, matrices)

		if not up_vector_guide.attribute(crit.consts.CRIT_AUTO_ALIGN_ATTR).asBool():
			return True

		with api.lock_state_attr_context(
				up_vector_guide, api.LOCAL_TRANSFORM_ATTRS + ['translate', 'rotate', 'scale'], False):
			try:
				new_pos = skeleton.pole_vector_position(*positions)
			except ValueError:
				new_pos = up_vector_guide.translation()
			up_vector_guide.setRotation(api.Quaternion())
			if new_pos != api.Vector():
				up_vector_guide.setTranslation(new_pos, space=api.kWorldSpace)

		return True

	@override
	def setup_inputs(self):
		super().setup_inputs()

		input_layer = self.input_layer()
		root_in, up_vec_in, ik_end_in = input_layer.find_inputs('upr', 'upVec', 'endik')
		guide_layer_descriptor = self.descriptor.guide_layer
		root_in_matrix = guide_layer_descriptor.guide('upr').transformation_matrix(scale=False)
		root_in.setWorldMatrix(root_in_matrix.asMatrix())

		if not self.world_end_rotation:
			ik_end_in_matrix = guide_layer_descriptor.guide('end').transformation_matrix(scale=False)
		else:
			aim_guide, end_guide = guide_layer_descriptor.find_guides(self.world_end_aim_guide_id, 'end')
			rotation = mathlib.look_at(
				api.Vector(end_guide.translate), api.Vector(aim_guide.translate), mathlib.Z_AXIS_VECTOR,
				mathlib.Y_AXIS_VECTOR, constraint_axis=api.Vector(0, 1, 1))
			ik_end_in_matrix = end_guide.transformationMatrix(rotate=False, scale=False)
			ik_end_in_matrix.setRotation(rotation)

		ik_end_in.setWorldMatrix(ik_end_in_matrix.asMatrix())
		up_vec_in_matrix = guide_layer_descriptor.guide('upVec').transformation_matrix(scale=False)
		up_vec_in.setWorldMatrix(up_vec_in_matrix.asMatrix())

	@override(check_signature=False)
	def post_setup_skeleton_layer(self, parent_joint: crit.Joint):

		output_layer = self.output_layer()
		skeleton_layer = self.skeleton_layer()
		ids = list(self.skeleton_joint_ids)
		joints = skeleton_layer.find_joints(*ids)

		for i, (driver, driven_id) in enumerate(zip(joints, ids)):
			if driver is None:
				continue
			driven = output_layer.output_node(driven_id)
			if i == 0:
				# setup world space matrix since we are the root joint for the component
				_, matrix_extra_nodes = api.build_constraint(
					driven,
					drivers={'targets': ((driver.fullPathName(partial_name=True, include_namespace=False), driver),)},
					constraint_type='matrix', maintainOffset=False)
				output_layer.add_extra_nodes(matrix_extra_nodes)
			else:
				driver.attribute('matrix').connect(driven.offsetParentMatrix)
				driven.resetTransform()
			driver.rotateOrder.connect(driven.rotateOrder)

		super().post_setup_skeleton_layer(parent_joint=parent_joint)

	@override(check_signature=False)
	def pre_setup_rig(self, parent_node: crit.Joint | api.DagNode | None = None):

		descriptor = self.descriptor
		rig_layer = descriptor.rig_layer
		has_stretch = descriptor.guide_layer.guide_setting('hasStretch').value
		if not has_stretch:
			rig_layer.delete_setting('controlPanel', STRETCH_ATTRS)
		else:
			orig = self.descriptor.original_descriptor.rig_layer
			last_insert_name = 'ikfk'
			for sett in STRETCH_ATTRS:
				orig_setting = orig.setting('controlPanel', sett)
				if orig_setting:
					rig_layer.insert_setting_by_name('controlPanel', last_insert_name, orig_setting, before=False)
					last_insert_name = orig_setting.name

		super().pre_setup_rig(parent_node=parent_node)

	@override(check_signature=False)
	def setup_rig(self, parent_node: crit.Joint | api.DagNode | None = None):

		descriptor = self.descriptor
		guide_layer_descriptor = descriptor.guide_layer
		component_name, component_side = self.name(), self.side()
		namer = self.naming_manager()
		input_layer = self.input_layer()
		skeleton_layer = self.skeleton_layer()
		rig_layer = self.rig_layer()
		control_panel = self.control_panel()
		ik_guides = guide_layer_descriptor.find_guides('upr', 'mid', 'end')
		up_vec_guide = guide_layer_descriptor.guide('upVec')

		rig_layer_root = rig_layer.root_transform()
		root_in, ik_end_in, up_vec_in = input_layer.find_inputs('upr', 'endik', 'upVec')

		fk_controls = [None] * 3			# type: List[None or crit.ControlNode]
		ik_joints = [None] * 3				# type: List[None or crit.Joint]
		self._ik_controls = {}				# type: Dict[str, crit.ControlNode]
		self._fk_controls = {}				# type: Dict[str, crit.ControlNode]

		blend_attr = control_panel.ikfk
		blend_attr.setFloat(guide_layer_descriptor.guide_setting('ikfk_default').value)

		up_vec_name = namer.resolve(
			'controlName',
			{'componentName': component_name, 'side': component_side, 'system': 'poleVector', 'id':
				up_vec_guide.id, 'type': 'control'})
		up_vec_ik_ctrl = rig_layer.create_control(
			name=up_vec_name, id=up_vec_guide.id, translate=up_vec_guide.translate, rotate=(0.0, 0.0, 0.0, 1.0),
			parent=rig_layer_root, shape=up_vec_guide.shape, rotateOrder=up_vec_guide.rotateOrder,
			selectionChildHighlighting=self.configuration.selection_child_highlighting)
		rig_layer.create_srt_buffer(up_vec_guide.id, '_'.join([up_vec_name, 'srt']))
		self._ik_controls['upvec'] = up_vec_ik_ctrl

		parent_space_rig = api.factory.create_dag_node(
			namer.resolve(
				'object',
				{'componentName': component_name, 'side': component_side, 'section': 'parent_space', 'type': 'transform'}),
			'transform', parent=rig_layer_root)
		parent_space_rig.setWorldMatrix(parent_node.worldMatrix())
		_, matrix_constraint_nodes = api.build_constraint(
			parent_space_rig,
			drivers={'targets': ((root_in.fullPathName(partial_name=True, include_namespace=False), root_in),)},
			constraint_type='matrix', maintainOffset=True)
		rig_layer.add_extra_nodes(matrix_constraint_nodes)
		rig_layer.add_extra_node(parent_space_rig)
