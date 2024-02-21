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
# class FootComponentNode(api.AnimComponentNode):
#
#     ID = 10
#     IS_EXEC = True
#     ICON = None
#     DEFAULT_TITLE = 'Foot'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.FootComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('foot')
#         self.in_tag.set_value('body')
#
#         self.in_meta_parent.data_type = api.DataType.FKIKComponent
#         self.out_self.data_type = api.DataType.FootComponent
#
#         self.in_start_joint = self.add_input(api.dt.String, label='Start Joint', value=None)
#         self.in_end_joint = self.add_input(api.dt.String, label='End Joint', value=None)
#         self.in_rv_chain = self.add_input(api.dt.String, label='Reverse Chain', value=None)
#         self.in_foot_locator_group = self.add_input(api.dt.String, label='Foot Locators', value=None)
#         self.in_roll_axis = self.add_input(api.dt.String, label='Rotate Axis', value='ry')
#
#         self.mark_inputs_as_required(
#             [self.in_meta_parent, self.in_start_joint, self.in_end_joint, self.in_rv_chain, self.in_foot_locator_group,
#              self.in_roll_axis])
#
#     @override
#     def execute(self) -> Any:
#         self._component_instance = self.COMPONENT_CLASS(
#             character=self.in_character.value(),
#             component_name=self.in_name.value(),
#             side=self.in_side.value(),
#             tag=self.in_tag.value(),
#             start_joint=self.in_start_joint.value(),
#             end_joint=self.in_end_joint.value(),
#             rv_chain=self.in_rv_chain.value(),
#             foot_locators_group=self.in_foot_locator_group.value(),
#             roll_axis=self.in_roll_axis.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'FootComponent', components.FootComponent,
#         api.DataType.COMPONENT.get('color'), label='Foot', default_value=None)
#
#     register_node(FootComponentNode.ID, FootComponentNode)
#
#     register_function(
#         FootComponentNode.COMPONENT_CLASS.roll_axis, api.DataType.FootComponent,
#         inputs={'Foot': api.DataType.FootComponent}, outputs={'Roll Axis': api.dt.String},
#         nice_name='Get Roll Axis', category='Foot Component')
#     register_function(
#         FootComponentNode.COMPONENT_CLASS.fk_control, api.DataType.FootComponent,
#         inputs={'Foot': api.DataType.FootComponent}, outputs={'Control': api.DataType.CONTROL},
#         nice_name='Get FK Control', category='Foot Component')
