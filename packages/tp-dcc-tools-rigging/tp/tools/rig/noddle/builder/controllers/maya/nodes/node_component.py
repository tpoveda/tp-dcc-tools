from __future__ import annotations

from typing import Any, Callable

from overrides import override

from tp.libs.rig.noddle.core import component, animcomponent
from tp.tools.rig.noddle.builder import api


class ComponentNode(api.NoddleNode):

    DEFAULT_TITLE = 'Component'
    TITLE_EDITABLE = True
    COMPONENT_CLASS = component.Component

    def __init__(self, graph: api.NodeGraph):
        super().__init__(graph)

        self._component_instance: component.Component | None = None

    @property
    def in_meta_parent(self) -> api.InputSocket:
        return self._in_meta_parent

    @property
    def in_side(self) -> api.InputSocket:
        return self._in_side

    @property
    def in_name(self) -> api.InputSocket:
        return self._in_name

    @property
    def in_tag(self) -> api.InputSocket:
        return self._in_tag

    @property
    def out_self(self) -> api.OutputSocket:
        return self._out_self

    @property
    def out_meta_parent(self) -> api.OutputSocket:
        return self._out_meta_parent

    @property
    def out_meta_children(self) -> api.OutputSocket:
        return self._out_meta_children

    @property
    def out_side(self) -> api.OutputSocket:
        return self._out_side

    @property
    def out_name(self) -> api.OutputSocket:
        return self._out_name

    @property
    def out_tag(self) -> api.OutputSocket:
        return self._out_tag

    @override
    def setup_sockets(self):
        super().setup_sockets()

        self._in_meta_parent = self.add_input(api.DataType.COMPONENT, label='Parent', value=None)
        self._in_side = self.add_input(api.dt.String, label='Side', value='c')
        self._in_name = self.add_input(api.dt.String, label='Name', value='component')
        self._in_tag = self.add_input(api.dt.String, label='Tag', value='')

        self.mark_input_as_required(self._in_name)
        self.mark_input_as_required(self._in_side)

        self._out_self = self.add_output(api.DataType.COMPONENT, label='Self', value=None)
        self._out_meta_parent = self.add_output(api.DataType.COMPONENT, label='Parent', value=None)
        self._out_meta_children = self.add_output(api.dt.List, label='Children')
        self._out_side = self.add_output(api.dt.String, label='Side', value='c')
        self._out_name = self.add_output(api.dt.String, label='Name', value='component')
        self._out_tag = self.add_output(api.dt.String, label='Tag', value='')

        self._in_meta_parent.affects(self._out_meta_parent)
        self._in_side.affects(self._out_side)
        self._in_name.affects(self._out_name)
        self._in_tag.affects(self._in_tag)


class AnimComponentNode(ComponentNode):

    DEFAULT_TITLE = 'Anim Component'
    COMPONENT_CLASS = animcomponent.AnimComponent

    @override
    def setup_sockets(self):
        super().setup_sockets()

        self.out_self.data_type = api.DataType.ANIM_COMPONENT
        self.in_meta_parent.data_type = api.DataType.ANIM_COMPONENT
        self.out_meta_parent.data_type = api.DataType.ANIM_COMPONENT
        self.in_name.set_value('anim_component')

        self.in_character = self.add_input(api.DataType.CHARACTER, label='Character')
        self.in_hook = self.add_input(api.dt.Numeric, label='In Hook')
        self.mark_input_as_required(self.in_character)

        self.out_character = self.add_output(api.DataType.CHARACTER, label='Character')
        self.out_in_hook = self.add_output(api.dt.Numeric, label='In Hook')

        self.in_character.affects(self.out_character)
        self.in_hook.affects(self.out_in_hook)

        self.in_hook.set_value(None)


class GetComponentAsNode(api.NoddleNode):

    ID = 3
    IS_EXEC = True
    AUTO_INIT_EXECS = True
    DEFAULT_TITLE = 'Get Component As'

    @override
    def setup_sockets(self):
        super().setup_sockets()

        self.in_component = self.add_input(api.DataType.COMPONENT)
        self.in_sample_component = self.add_input(api.DataType.COMPONENT, label='Sample Type')
        self.out_component = self.add_output(api.DataType.COMPONENT, label='Cast Result')
        self.mark_input_as_required(self.in_sample_component)

        self.in_sample_component.signals.connectionChanged.connect(self._on_update_out_component_type)

    @override
    def execute(self) -> Any:
        component_class = self.in_sample_component.value().__class__
        cast_instance = component_class(self.in_component.value())
        self.out_component.set_value(cast_instance)

    def _on_update_out_component_type(self):
        if not self.in_sample_component.list_connections():
            self.out_component.data_type = api.DataType.COMPONENT
            return
        self.out_component.data_type = self.in_sample_component.list_connections()[0].data_type


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
    register_node(GetComponentAsNode.ID, GetComponentAsNode)

    register_function(
        ComponentNode.COMPONENT_CLASS.side, api.DataType.COMPONENT,
        inputs={'Component': api.DataType.COMPONENT}, outputs={'Side': api.DataType.STRING},
        nice_name='Get Side', category='Component')
    register_function(
        ComponentNode.COMPONENT_CLASS.component_name, api.DataType.COMPONENT,
        inputs={'Component': api.DataType.COMPONENT}, outputs={'Name': api.DataType.STRING},
        nice_name='Get Name', category='Component')
    register_function(
        ComponentNode.COMPONENT_CLASS.tag, api.DataType.COMPONENT,
        inputs={'Component': api.DataType.COMPONENT}, outputs={'Tag': api.DataType.STRING},
        nice_name='Get Tag', category='Component')
    register_function(
        ComponentNode.COMPONENT_CLASS.meta_parent, api.DataType.COMPONENT,
        inputs={'Component': api.DataType.COMPONENT}, outputs={'Parent': api.DataType.COMPONENT},
        nice_name='Get Parent', category='Component')
    register_function(
        ComponentNode.COMPONENT_CLASS.meta_children, api.DataType.COMPONENT,
        inputs={'Component': api.DataType.COMPONENT, 'Sample Type': api.DataType.COMPONENT,
                'By Tag': api.DataType.STRING}, outputs={'Children': api.DataType.LIST},
        nice_name='Get Children', category='Component')

    register_function(
        AnimComponentNode.COMPONENT_CLASS.meta_parent, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT},
        outputs={'Parent': api.DataType.ANIM_COMPONENT},
        nice_name='Get Parent', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.in_hook_index, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Hook Index': api.DataType.NUMERIC},
        nice_name='Get In Hook Index', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.character, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Character': api.DataType.CHARACTER},
        nice_name='Get Character', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.controls, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Controls': api.dt.List},
        nice_name='List Controls', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.control_joint_names, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Joint Chain': api.dt.List},
        nice_name='Get Control Joints', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.bind_joint_names, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Bind Joints': api.dt.List},
        nice_name='Get Bind Joints', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.root_group, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Root Group': api.dt.String},
        nice_name='Get Root Group', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.controls_group, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Controls Group': api.dt.String},
        nice_name='Get Controls Group', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.joints_group, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT}, outputs={'Joints Group': api.dt.String},
        nice_name='Get Joints Group', category='Anim Component')
    register_function(
        AnimComponentNode.COMPONENT_CLASS.hook_name, api.DataType.ANIM_COMPONENT,
        inputs={'AnimComponent': api.DataType.ANIM_COMPONENT, 'Hook Index': api.DataType.NUMERIC},
        outputs={'Hook Transform': api.dt.String},
        nice_name='Get Hook Transform', category='Anim Component')
