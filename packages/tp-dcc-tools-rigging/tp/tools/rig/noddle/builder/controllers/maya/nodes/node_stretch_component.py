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
# class IKSplineStretchComponentNode(api.ComponentNode):
#
#     ID = 21
#     IS_EXEC = True
#     ICON = None
#     DEFAULT_TITLE = 'Spline Stretch'
#     CATEGORY = 'Components'
#     COMPONENT_CLASS = components.IKSplineStretchComponent
#
#     @override
#     def setup_sockets(self):
#         super().setup_sockets()
#
#         self.in_name.set_value('stretch')
#         self.out_self.data_type = api.DataType.IkSplineStretchComponent
#
#         self.in_switch_control = self.add_input(api.DataType.CONTROL, label='Switch Control')
#         self.in_default_state = self.add_input(api.dt.Boolean, label='Default State', value=False)
#         self.in_switch_attr_name = self.add_input(api.dt.String, label='Stretch Attribute', value='stretch')
#         self.in_stretch_axis = self.add_input(api.dt.String, label='Stretch Axis', value='x')
#
#         self.mark_inputs_as_required([self.in_meta_parent, self.in_switch_attr_name, self.in_stretch_axis])
#
#     @override
#     def execute(self) -> Any:
#         self._component_instance = self.COMPONENT_CLASS(
#             component_name=self.in_name.value(),
#             side=self.in_side.value(),
#             tag=self.in_tag.value(),
#             switch_control=self.in_switch_control.value(),
#             default_state=self.in_default_state.value(),
#             switch_attr=self.in_switch_attr_name.value(),
#             stretch_axis=self.in_stretch_axis.value(),
#             parent=self.in_meta_parent.value()
#         )
#
#         self.out_self.set_value(self._component_instance)
#
#
# def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
#     register_data_type(
#         'IkSplineStretchComponent', components.IKSplineStretchComponent,
#         api.DataType.COMPONENT.get('color'), label='Spline Stretch', default_value=None)
#
#     register_node(IKSplineStretchComponentNode.ID, IKSplineStretchComponentNode)
