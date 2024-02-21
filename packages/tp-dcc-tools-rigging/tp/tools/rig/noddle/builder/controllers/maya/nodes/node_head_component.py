# from __future__ import annotations
#
# from typing import Any, Callable
#
# from overrides import override
#
# from tp.libs.rig.noddle.core import components
# from tp.tools.rig.noddle.builder import api
# from tp.tools.rig.noddle.builder.controllers.maya.nodes import node_fk_component
#
#
# class HeadComponentNode(node_fk_component.FKComponentNode):
#
#     ID = 17
#     IS_EXEC = True
#     ICON = 'skull.png'
#     DEFAULT_TITLE = 'Head'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.HeadComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('head')
#         self.out_self.data_type = api.DataType.HeadComponent
#
#         self.remove_socket('End Control')
#
#         self.in_head_joint_index = self.add_input(api.dt.Numeric, label='Head Index', value=-2)
#
#         self.out_head_hook = self.add_output(
#             api.dt.Numeric, label='Hook Head', value=self.COMPONENT_CLASS.Hooks.HEAD.value)
#         self.out_base_hook = self.add_output(
#             api.dt.Numeric, label='Hook Base', value=self.COMPONENT_CLASS.Hooks.NECK_BASE.value)
#
#     @override
#     def execute(self) -> Any:
#         self._component_instance = self.COMPONENT_CLASS(
#             character=self.in_character.value(),
#             component_name=self.in_name.value(),
#             side=self.in_side.value(),
#             tag=self.in_tag.value(),
#             hook=self.in_hook.value(),
#             start_joint=self.in_start_joint.value(),
#             end_joint=self.in_end_joint.value(),
#             head_joint_index=self.in_head_joint_index.value(),
#             lock_translate=self.in_lock_translate.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'HeadComponent', components.HeadComponent,
#         api.DataType.COMPONENT.get('color'), label='Head Component', default_value=None)
#
#     register_node(HeadComponentNode.ID, HeadComponentNode)
#
#     register_function(
#         HeadComponentNode.COMPONENT_CLASS.add_orient_attribute, api.DataType.HeadComponent,
#         inputs={'Head': api.DataType.HeadComponent}, nice_name='Add Orient Attribute', category='Head Component')
#     register_function(
#         HeadComponentNode.COMPONENT_CLASS.head_hook_index, api.DataType.HeadComponent,
#         inputs={'Head': api.DataType.HeadComponent}, outputs={'Hook Head': api.DataType.NUMERIC},
#         nice_name='Get Head Hook', category='Head Component')
#     register_function(
#         HeadComponentNode.COMPONENT_CLASS.neck_base_hook_index, api.DataType.HeadComponent,
#         inputs={'Head': api.DataType.HeadComponent}, outputs={'Hook Neck': api.DataType.NUMERIC},
#         nice_name='Get Neck Hook', category='Head Component')
