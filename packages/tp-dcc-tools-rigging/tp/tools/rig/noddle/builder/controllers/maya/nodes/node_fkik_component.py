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
# class FKIKComponentNode(api.AnimComponentNode):
#
#     ID = 9
#     IS_EXEC = True
#     ICON = 'fkik.png'
#     DEFAULT_TITLE = 'FKIK'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.FKIKComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('fkik_component')
#         self.out_self.data_type = api.DataType.FKIKComponent
#
#         self.in_start_joint = self.add_input(api.dt.String, label='Start Joint', value=None)
#         self.in_end_joint = self.add_input(api.dt.String, label='End Joint', value=None)
#         self.in_ik_world_orient = self.add_input(api.dt.Boolean, label='IK World Orient', value=False)
#         self.in_default_state = self.add_input(api.dt.Boolean, label='Default to IK', value=True)
#         self.in_param_locator = self.add_input(api.dt.String, label='Param Locator', value=None)
#
#         self.out_hook_start_joint = self.add_output(
#             api.dt.Numeric, label='Hook Start', value=self.COMPONENT_CLASS.Hooks.START_JOINT.value)
#         self.out_hook_end_joint = self.add_output(
#             api.dt.Numeric, label='Hook End', value=self.COMPONENT_CLASS.Hooks.END_JOINT.value)
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
#             ik_world_orient=self.in_ik_world_orient.value(),
#             default_state=self.in_default_state.value(),
#             param_locator=self.in_param_locator.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'FKIKComponent', components.FKIKComponent,
#         api.DataType.COMPONENT.get('color'), label='FKIK Component', default_value=None)
#
#     register_node(FKIKComponentNode.ID, FKIKComponentNode)
#
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.ik_control, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Control': api.DataType.CONTROL},
#         nice_name='Get IK Control', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.pole_vector_control, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Control': api.DataType.CONTROL},
#         nice_name='Get PV Control', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.param_control, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Control': api.DataType.CONTROL},
#         nice_name='Get Param Control', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.fk_controls, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Controls': api.dt.List},
#         nice_name='Get FK Controls', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.ik_handle, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'IK Handle': api.dt.List},
#         nice_name='Get IK Handle', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.hide_last_fk, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent},
#         nice_name='Hide Last FK', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.fk_control_at, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent, 'Index': api.dt.Numeric},
#         outputs={'FK Control': api.DataType.CONTROL},
#         nice_name='Get FK Control At', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.start_hook_index, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Hook Start': api.dt.Numeric},
#         nice_name='Get Start Hook', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.end_hook_index, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent}, outputs={'Hook End': api.dt.Numeric},
#         nice_name='Get End Hook', category='FKIK Component')
#     register_function(
#         FKIKComponentNode.COMPONENT_CLASS.add_fk_orient_switch, api.DataType.FKIKComponent,
#         inputs={'FKIK Component': api.DataType.FKIKComponent},
#         nice_name='Add FK Orient Switch', category='FKIK Component')
