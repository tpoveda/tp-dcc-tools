# from __future__ import annotations
#
# from typing import Any, Callable
#
# from overrides import override
#
# from tp.libs.rig.noddle.core import, character
# from tp.tools.rig.noddle.builder import api
#
#
# class CharacterNode(api.ComponentNode):
#
#     ID = 7
#     IS_EXEC = True
#     ICON = 'bindpose.png'
#     DEFAULT_TITLE = 'Character'
#     CATEGORY = 'Components'
#     UNIQUE = True
#     COMPONENT_CLASS = character.Character
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.out_self.data_type = api.DataType.CHARACTER
#         self.in_name.set_value('character')
#         self.in_tag.set_value('character')
#
#         self.out_root_control = self.add_output(api.DataType.CONTROL, label='Root Control')
#         self.out_deform_rig = self.add_output(api.dt.String, label='Deformation Rig')
#         self.out_control_rig = self.add_output(api.dt.String, label='Control Rig')
#         self.out_geometry_group = self.add_output(api.dt.String, label='Geometry Group')
#
#     def execute(self) -> Any:
#         self.component_instance = self.COMPONENT_CLASS(
#             component_name=self.in_name.value(), tag=self.in_tag.value(), parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self.component_instance)
#         self.out_meta_parent.set_value(
#             self.component_instance.meta_parent().fullPathName() if self.component_instance.meta_parent() else None)
#         self.out_root_control.set_value(self.component_instance.root_control().fullPathName())
#         self.out_deform_rig.set_value(self.component_instance.deformation_rig_group().fullPathName())
#         self.out_control_rig.set_value(self.component_instance.control_rig_group().fullPathName())
#         self.out_geometry_group.set_value(self.component_instance.geometry_group().fullPathName())
#
#
# def add_root_motion(in_character: character.Character, in_follow_control: control.Control, in_root_joint: str) -> str:
#     return in_character.add_root_motion(in_follow_control, in_root_joint).fullPathName()
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_node(CharacterNode.ID, CharacterNode)
#     register_function(
#         CharacterNode.COMPONENT_CLASS.control_rig_group_path, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'Control Rig': api.dt.String},
#         nice_name='Get Control Rig', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.deformation_rig_group_path, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'Deformation Rig': api.dt.String},
#         nice_name='Get Deformation Rig', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.geometry_rig_group_path, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'Geometry Group': api.dt.String},
#         nice_name='Get Geometry Group', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.root_control, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'Root Control': api.DataType.CONTROL},
#         nice_name='Get Root Control', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.world_locator_path, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'World Locator': api.dt.String},
#         nice_name='Get World Locator', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.root_motion_path, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, outputs={'Root Joint': api.dt.String},
#         nice_name='Get Root Joint', category='Character')
#     register_function(
#         add_root_motion, api.DataType.CHARACTER,
#         inputs={
#             'Character': api.DataType.CHARACTER, 'Follow Control': api.DataType.CONTROL, 'Root Joint': api.dt.String},
#         outputs={'Root Joint': api.dt.String}, nice_name='Add Root Motion', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.attach_to_skeleton, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER}, nice_name='Attach To Skeleton', category='Character')
#     register_function(
#         CharacterNode.COMPONENT_CLASS.set_publish_mode, api.DataType.CHARACTER,
#         inputs={'Character': api.DataType.CHARACTER, 'Publish Ready': api.dt.Boolean},
#         nice_name='Set Publish Mode', category='Character')
