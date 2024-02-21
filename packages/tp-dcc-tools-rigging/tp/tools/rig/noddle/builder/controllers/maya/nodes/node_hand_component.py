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
# class HandComponentNode(api.AnimComponentNode):
#
#     ID = 19
#     IS_EXEC = True
#     ICON = 'hand.png'
#     DEFAULT_TITLE = 'Hand'
#     CATEGORY = 'Components'
#     UNIQUE = False
#     COMPONENT_CLASS = components.HandComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('hand')
#         self.out_self.data_type = api.DataType.HandComponent
#
#     @override
#     def execute(self) -> Any:
#         self._component_instance = self.COMPONENT_CLASS(
#             character=self.in_character.value(),
#             component_name=self.in_name.value(),
#             side=self.in_side.value(),
#             tag=self.in_tag.value(),
#             hook=self.in_hook.value(),
#             parent=self.in_meta_parent.value())
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'HandComponent', components.HandComponent,
#         api.DataType.COMPONENT.get('color'), label='Hand Component', default_value=None)
#
#     register_node(HandComponentNode.ID, HandComponentNode)
#
#     register_function(
#         HandComponentNode.COMPONENT_CLASS.five_finger_setup, api.DataType.HandComponent,
#         inputs={
#             'Hand': api.DataType.HandComponent,
#             'Thumb Joint': api.DataType.STRING,
#             'Index Joint': api.DataType.STRING,
#             'Middle Joint': api.DataType.STRING,
#             'Ring Joint': api.DataType.STRING,
#             'Pinky Joint': api.DataType.STRING,
#             'Tip Control': api.DataType.BOOLEAN},
#         outputs={
#             'Thumb': api.DataType.FKComponent,
#             'Index': api.DataType.FKComponent,
#             'Middle': api.DataType.FKComponent,
#             'Ring': api.DataType.FKComponent,
#             'Pinky': api.DataType.FKComponent},
#         nice_name='Five Finger Setup', category='Hand Component')
