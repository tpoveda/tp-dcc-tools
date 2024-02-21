# from __future__ import annotations
#
# from typing import Any, Callable
#
# from overrides import override
#
# from tp.libs.rig.noddle.core import components
# from tp.tools.rig.noddle.builder import api
#
#
# class FKComponentNode(api.AnimComponentNode):
#
#     ID = 16
#     IS_EXEC = True
#     ICON = 'fk.png'
#     DEFAULT_TITLE = 'FK'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.FKComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('fk_component')
#         self.out_self.data_type = api.DataType.FKComponent
#
#         self.in_start_joint = self.add_input(api.dt.String, label='Start Joint', value=None)
#         self.in_end_joint = self.add_input(api.dt.String, label='End Joint', value=None)
#         self.in_add_end_control = self.add_input(api.dt.Boolean, label='End Control', value=True)
#         self.in_lock_translate = self.add_input(api.dt.Boolean, label='Lock Translation', value=True)
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
#             add_end_control=self.in_add_end_control.value(),
#             lock_translate=self.in_lock_translate.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'FKComponent', components.FKComponent,
#         api.DataType.COMPONENT.get('color'), label='FK Component', default_value=None)
#
#     register_node(FKComponentNode.ID, FKComponentNode)
#
#     register_function(
#         FKComponentNode.COMPONENT_CLASS.add_auto_aim, api.DataType.FKComponent,
#         inputs={
#             'FK Component': api.DataType.FKComponent,
#             'Follow Control': api.DataType.CONTROL,
#             'Is Mirrored': api.DataType.BOOLEAN,
#             'Default Blend': api.DataType.NUMERIC},
#         default_values=[None, None, False, 0.5], nice_name='Add Auto Aim', category='FK Component')
