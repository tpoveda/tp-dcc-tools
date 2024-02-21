# from __future__ import annotations
#
# from typing import Any, Callable
#
# from overrides import override
#
# from tp.maya.api import base
# from tp.libs.rig.noddle.core import components
# from tp.tools.rig.noddle.builder import api
#
#
# class TwistComponentNode(api.AnimComponentNode):
#
#     ID = 18
#     IS_EXEC = True
#     ICON = None
#     DEFAULT_TITLE = 'Twist'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.TwistComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('twist')
#
#         self.out_self.data_type = api.DataType.TwistComponent
#
#         self.remove_socket('In Hook', is_input=True)
#         self.remove_socket('In Hook', is_input=False)
#
#         self.in_start_joint = self.add_input(api.dt.String, label='Start Joint', value=None)
#         self.in_end_joint = self.add_input(api.dt.String, label='End Joint', value=None)
#         self.in_start_object = self.add_input(api.DataType.STRING, label='Start Object', value=None)
#         self.in_end_object = self.add_input(api.DataType.STRING, label='End Object', value=None)
#         self.in_num_joints = self.add_input(api.DataType.NUMERIC, label='Num Joints', value=2)
#         self.in_is_mirrored = self.add_input(api.DataType.BOOLEAN, label='Is Mirrored', value=False)
#
#         self.mark_input_as_required(self.in_start_joint)
#
#     @override
#     def execute(self) -> Any:
#
#         start_joint = self.in_start_joint.value()
#         end_joint = self.in_end_joint.value()
#         start_object = self.in_start_object.value()
#         end_object = self.in_end_object.value()
#
#         self._component_instance = self.COMPONENT_CLASS(
#             character=self.in_character.value(),
#             component_name=self.in_name.value(),
#             side=self.in_side.value(),
#             tag=self.in_tag.value(),
#             start_joint=base.node_by_name(start_joint) if start_joint else None,
#             end_joint=base.node_by_name(end_joint) if end_joint else None,
#             num_joints=self.in_num_joints.value(),
#             start_object=base.node_by_name(start_object) if start_object else None,
#             end_object=base.node_by_name(end_object) if end_object else None,
#             mirrored_chain=self.in_is_mirrored.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'TwistComponent', components.TwistComponent,
#         api.DataType.COMPONENT.get('color'), label='Twist Component', default_value=None)
#
#     register_node(TwistComponentNode.ID, TwistComponentNode)
#
#     register_function(
#         TwistComponentNode.COMPONENT_CLASS.start_hook_index, api.DataType.TwistComponent,
#         inputs={'Twist Component': api.DataType.TwistComponent}, outputs={'Hook Start': api.dt.Numeric},
#         nice_name='Hook Start', category='Twist Component')
#     register_function(
#         TwistComponentNode.COMPONENT_CLASS.end_hook_index, api.DataType.TwistComponent,
#         inputs={'Twist Component': api.DataType.TwistComponent}, outputs={'Hook End': api.dt.Numeric},
#         nice_name='Hook End', category='Twist Component')
