from __future__ import annotations

from typing import Callable, Any

from overrides import override

import maya.cmds as cmds

from tp.tools.rig.noddle.builder import api


class ConnectAttributesNode(api.NoddleNode):

    ID = 23
    IS_EXEC = True
    ICON = None
    AUTO_INIT_EXECS = True
    DEFAULT_TITLE = 'Connect Attributes'
    CATEGORY = 'Functions/cmds'

    @override
    def setup_sockets(self):
        super().setup_sockets()

        self.in_source_node_name = self.add_input(api.dt.String, label='Source Node')
        self.in_source_attr_name = self.add_input(api.dt.String, label='Source Attribute')
        self.in_dest_node_name = self.add_input(api.dt.String, label='Destination Node')
        self.in_dest_attr_name = self.add_input(api.dt.String, label='Destination Attribute')

        self.mark_inputs_as_required(
            (self.in_source_node_name, self.in_source_attr_name, self.in_dest_node_name, self.in_dest_attr_name))

    @override
    def execute(self) -> Any:
        cmds.connectAttr(
            f'{self.in_source_attr_name.value()}.{self.in_source_attr_name.value()}',
            f'{self.in_dest_node_name.value()}.{self.in_dest_attr_name.value()}'
        )


class AddToggleAttributeNode(api.NoddleNode):

    ID = 24
    IS_EXEC = True
    AUTO_INIT_EXECS = True
    ICON = None
    DEFAULT_TITLE = 'Add Toggle Attribute'
    CATEGORY = 'Functions/cmds'

    @override
    def setup_sockets(self):
        super().setup_sockets()

        self.in_node_name = self.add_input(api.dt.String, label='Node')
        self.in_attr_name = self.add_input(api.dt.String, label='Attribute')
        self.in_default_value = self.add_input(api.dt.Boolean, label='Value', value=False)

        self.mark_inputs_as_required((self.in_node_name, self.in_attr_name, self.in_default_value))

    @override
    def execute(self) -> Any:
        cmds.addAttr(
            self.in_node_name.value(), n=self.in_attr_name.value(), at='bool', k=True, dv=self.in_default_value.value())


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):
    register_node(ConnectAttributesNode.ID, ConnectAttributesNode)
    register_node(AddToggleAttributeNode.ID, AddToggleAttributeNode)

    register_function(
        cmds.parent, None,
        inputs={'Child': api.DataType.STRING, 'Parent': api.DataType.STRING},
        nice_name='Parent', category='Maya cmds API')
