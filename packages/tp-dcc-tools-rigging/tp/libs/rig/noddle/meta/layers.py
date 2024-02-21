from __future__ import annotations

import typing
from typing import Iterator, Iterable

from overrides import override

from tp.maya import api
from tp.maya.om import plugs
from tp.maya.meta import base
from tp.common.python import helpers

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import errors, nodes

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.component import NoddleComponent


class NoddleLayer(base.DependentNode):
    """
    Base class for Noddle layer nodes. Crit layers are used simply for organization purposes and can be used as the
    entry point ot access rig DAG related nodes.
    """

    ID = consts.BASE_LAYER_TYPE

    def __init__(
            self, node: api.OpenMaya.MObject | None = None, name: str | None = None,
            parent: api.OpenMaya.MObject | None = None, init_defaults: bool = True, lock: bool = True,
            mod: api.OpenMaya.MDGModifier | None = None):
        super().__init__(node=node, name=name, parent=parent, init_defaults=init_defaults, lock=lock, mod=mod)

    @override
    def meta_attributes(self) -> list[dict]:
        """
        Overrides base meta_attributes function.
        Returns the list of default meta attributes that should be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: list[dict]
        """

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(name=consts.NODDLE_EXTRA_NODES_ATTR, isArray=True, type=api.kMFnMessageAttribute),
                dict(name=consts.NODDLE_ROOT_TRANSFORM_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.NODDLE_CONNECTORS_ATTR, isArray=True, type=api.kMFnMessageAttribute),
                dict(
                    name=consts.NODDLE_SETTING_NODES_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_SETTING_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_SETTING_NAME_ATTR, type=api.kMFnDataString),
                    ]
                ),
                dict(
                    name=consts.NODDLE_TAGGED_NODE_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_TAGGED_NODE_SOURCE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_SETTING_NAME_ATTR, type=api.kMFnDataString),
                    ]
                )
            )
        )

        return attrs

    @override
    def delete(self, mod: api.OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
        """
        Deletes the node from the scene.

        :param OpenMaya.MDGModifier mod: modifier to add the delete operation into.
        :param bool apply: whether to apply the modifier immediately.
        :return: True if the node deletion was successful; False otherwise.
        :raises RuntimeError: if deletion operation fails.
        :rtype: bool
        """

        self.lock(True)
        try:
            [s.delete(mod=mod, apply=apply) for s in list(
                self.iterate_extra_nodes()) + list(self.iterate_settings_nodes()) + list(self.iterate_connectors())]
            transform = self.root_transform()
            if transform:
                transform.lock(False)
                transform.delete(mod=mod, apply=apply)
        finally:
            self.lock(False)

        return super().delete(mod=mod, apply=apply)

    @override(check_signature=False)
    def serializeFromScene(self) -> dict:
        """
        Serializes current layer into a dictionary compatible with JSON.

        :return: JSON compatible dictionary.
        :rtype: dict
        """

        return {}

    def root_transform(self) -> api.DagNode:
        """
        Returns the root transform node for this layer instance.

        :return: root transform instance.
        :rtype: api.DagNode
        """

        return self.sourceNodeByName(consts.NODDLE_ROOT_TRANSFORM_ATTR)

    def create_transform(self, name: str, parent: api.OpenMaya.MObject | api.DagNode | None = None) -> api.DagNode:
        """
        Creates the transform node within Maya scene linked to this meta node.

        :param str name: name of the transform node.
        :param api.OpenMaya.MObject or api.DagNode or None parent: optional parent node.
        :return: newly created transform node.
        :rtype: api.DagNode
        """

        layer_transform = api.factory.create_dag_node(name=name, node_type='transform', parent=parent)
        layer_transform.setLockStateOnAttributes(consts.TRANSFORM_ATTRS)
        layer_transform.showHideAttributes(consts.TRANSFORM_ATTRS)
        self.connect_to(consts.NODDLE_ROOT_TRANSFORM_ATTR, layer_transform)
        layer_transform.lock(True)

        return layer_transform

    def update_metadata(self, metadata: dict):
        """
        Updates metadata attribute with given metadata dictionary contents.

        :param dict metadata: metadata dictionary contents.
        """

        for meta_attr in metadata:
            attribute = self.attribute(meta_attr['name'])
            if attribute is None:
                self.addAttribute(**meta_attr)
            else:
                attribute.setFromDict(**meta_attr)

    def iterate_extra_nodes(self) -> Iterator[api.DGNode]:
        """
        Generator function that iterates over all the extra nodes attached to this meta node instance.

        :return: iterated attached extra nodes.
        :rtype: Iterator[api.DGNode]
        """

        for element in self.attribute(consts.NODDLE_EXTRA_NODES_ATTR):
            source = element.source()
            if source:
                yield source.node()

    def add_extra_nodes(self, extra_nodes: Iterable[api.DGNode]):
        """
        Connects given nodes into this meta node instance as extra nodes.

        :param Iterable[api.DGNode] extra_nodes: nodes to add as extra node.
        """

        extras_array = self.attribute(consts.NODDLE_EXTRA_NODES_ATTR)
        for extra_node in extra_nodes:
            if not extra_node.object():
                continue
            element = extras_array.nextAvailableDestElementPlug()
            extra_node.message.connect(element)

    def add_extra_node(self, node: api.DGNode):
        """
        Connects given node into this meta node instance as an extra node.

        :param api.DGNode node: node to add as extra node.
        """

        self.add_extra_nodes([node])

    def iterate_settings_nodes(self) -> Iterator[nodes.SettingsNode]:
        """
        Generator function that iterates over all the attached settings nodes attached to this meta node instance.

        :return: iterated attached setting node instances.
        :rtype: Iterator[nodes.SettingsNode]
        """

        settings_nodes_compound_attr = self.attribute(consts.NODDLE_SETTING_NODES_ATTR)
        for element in settings_nodes_compound_attr:
            source_node = element.child(0).sourceNode()
            if source_node is not None:
                yield nodes.SettingsNode(node=source_node.object())

    def setting_node(self, name: str) -> nodes.SettingsNode | None:
        """
        Finds and returns the settings node with given name it exists.

        :param str name: name of the settings node.
        :return: found settings node instance.
        :rtype: meta_nodes.SettingsNode or None
        """

        for setting_node in self.iterate_settings_nodes():
            if setting_node.id() == name:
                return setting_node

        return None

    def create_settings_node(self, name: str, attr_name: str) -> nodes.SettingsNode:
        """
        Creates a Noddle setting nodes and adds it to the meta node with given name nad value.

        :param str name: name for the new settings node.
        :param str attr_name: meta attribute name.
        :return: newly created settings node instance.
        :rtype: nodes.SettingsNode
        """

        setting_node = self.setting_node(attr_name)
        if setting_node is not None:
            return setting_node

        setting_node = nodes.SettingsNode()
        setting_node.create(name, id=attr_name)
        settings_nodes_attr = self.attribute(consts.NODDLE_SETTING_NODES_ATTR)
        new_element = settings_nodes_attr.nextAvailableElementPlug()
        self.connect_to_by_plug(new_element.child(0), setting_node)
        new_element.child(1).set(attr_name)
        setting_node.lock(True)

        return setting_node


class NoddleComponentsLayer(NoddleLayer):

    ID = consts.COMPONENTS_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        """
        Overrides base meta_attributes function.
        Returns the list of default meta attributes that should be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: list[dict]
        """

        attrs = super().meta_attributes()

        attrs.extend([
            {
                'name': consts.NODDLE_COMPONENT_GROUPS_ATTR,
                'isArray': True,
                'locked': False,
                'type': api.kMFnDataString,
                'children': [
                    {
                        'name': consts.NODDLE_COMPONENT_GROUP_NAME_ATTR,
                        'type': api.kMFnDataString
                    },
                    {
                        'name': consts.NODDLE_GROUP_COMPONENTS_ATTR,
                        'type': api.kMFnMessageAttribute,
                        'isArray': False,
                        'locked': False
                    }
                ]
            },
        ])

        return attrs

    def iterate_components(
            self, depth_limit: int = 256) -> Iterator[NoddleComponent]:
        """
        Generator function that iterates over all components linked to this layer.

        :param int depth_limit: recursive depth limit.
        :return: iterated components linked to this layer.
        :rtype: Iterator[NoddleComponent]
        """

        for meta_child in self.iterate_meta_children(depth_limit):
            if meta_child.hasAttribute(consts.NODDLE_COMPONENT_TYPE_ATTR):
                yield meta_child

    def components(self, depth_limit: int = 256) -> list[NoddleComponent]:
        """
        Returns all components in order as a list.

        :param int depth_limit: recursive depth limit.
        :return: list of components linked to this layer.
        :rtype: list[NoddleComponent]
        """

        return list(self.iterate_components(depth_limit=depth_limit))


class NoddleInputLayer(NoddleLayer):

    ID = consts.INPUT_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.NODDLE_INPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_INPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_INPUT_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.NODDLE_IS_INPUT_ROOT_ATTR, type=api.kMFnNumericBoolean),
                        dict(
                            name=consts.NODDLE_SOURCE_INPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                            children=[
                                dict(name=consts.NODDLE_SOURCE_INPUT_ATTR, type=api.kMFnMessageAttribute),
                                dict(
                                    name=consts.NODDLE_SOURCE_INPUT_CONSTRAINT_NODES_ATTR,
                                    type=api.kMFnMessageAttribute, isArray=True),
                            ]),
                    ]
                ),
            )
        )

        return attrs

    @override
    def serializeFromScene(self) -> dict:

        return {
            consts.INPUT_LAYER_DESCRIPTOR_KEY: {
                consts.SETTINGS_DESCRIPTOR_KEY: map(
                    plugs.serialize_plug, self.root_transform().iterateExtraAttributes()),
                consts.DAG_DESCRIPTOR_KEY: [
                    i.serializeFromScene(
                        include_namespace=False, use_short_names=True) for i in self.iterate_root_inputs()]
            }
        }

    def has_input(self, name: str) -> bool:
        """
        Returns whether input node with given name is attached to this layer instance.

        :param str name: name of the input node to check.
        :return: True if input node with given name is attached to this layer instance; False otherwise.
        :rtype: bool
        """

        try:
            return self.input_node(name) is not None
        except errors.NoddleInvalidInputNodeMetaData:
            return False

    def input_plug_by_id(self, input_id: str) -> api.Plug | None:
        """
        Returns the input plug instance for the input node with given ID.

        :param str input_id: ID of the input node plug to retrieve.
        :return: found plug instance with given ID.
        :rtype: api.Plug or None
        """

        input_plug = self.attribute(consts.NODDLE_INPUTS_ATTR)
        found_plug = None
        for element in input_plug:
            if element.child(1).asString() == input_id:
                found_plug = element
                break

        return found_plug

    def input_node(self, name: str) -> nodes.InputNode | None:
        """
        Returns input node with given name attached to this layer instance.

        :param str name: name of the input node to get.
        :return: input node instance.
        :rtype: nodes.InputNode or None
        """

        element = self.input_plug_by_id(name)
        if element is None:
            return None

        source = element.child(0).source()
        if not source:
            raise errors.NoddleInvalidInputNodeMetaData('-'.join([name, element.child(1).asString()]))

        return nodes.InputNode(source.node().object())

    def root_input_plug(self) -> api.Plug | None:
        """
        Returns the plug where root input is connected to.

        :return: root input plug.
        :rtype: api.Plug or None
        """

        found_root_plug = None
        for element in self.attribute(consts.NODDLE_INPUTS_ATTR):
            is_root = element.child(2).value()
            if not is_root:
                continue
            found_root_plug = element
            break

        return found_root_plug

    def root_input(self) -> nodes.InputNode | None:
        """
        Returns the root input node.

        :return: root input node.
        :rtype: nodes.InputNode or None
        """

        root_input_plug = self.root_input_plug()
        if root_input_plug is None:
            return None

        return nodes.InputNode(root_input_plug.child(0).sourceNode().object())

    def iterate_root_inputs(self) -> Iterator[nodes.InputNode]:
        """
        Generator function that iterates over all root input nodes within this layer.

        :return: iterated root input nodes.
        :rtype: Iterator[nodes.InputNode]
        """

        for input_node in self.iterate_inputs():
            if input_node.is_root():
                yield input_node

    def iterate_inputs(self) -> Iterator[nodes.InputNode]:
        """
        Generator function that iterates over all input nodes within this layer.

        :return: iterated input nodes.
        :rtype: Iterator[nodes.InputNode]
        """

        input_plug = self.attribute(consts.NODDLE_INPUTS_ATTR)
        for element in input_plug:
            source = element.child(0).source()
            if source is not None:
                yield nodes.InputNode(source.node().object())

    def inputs(self) -> list[nodes.InputNode]:
        """
        Function that returns all input nodes within this layer.

        :return: all input nodes.
        :rtype: list[nodes.InputNode]
        """

        return list(self.iterate_inputs())

    def find_inputs(self, *ids: Iterable[str]) -> list[nodes.InputNode | None]:
        """
        Searches and returns input nodes with given IDs.

        :param Tuple[str] ids: list of input node IDs to search for.
        :return: list of found input nodes.
        :rtype: list[nodes.InputNode]
        """

        valid_inputs: list[nodes.InputNode | None] = [None] * len(ids)
        for element in self.attribute(consts.NODDLE_INPUTS_ATTR):
            input_id = element.child(1).asString()
            if input_id not in ids:
                continue
            source = element.child(0).source()
            if source:
                valid_inputs[ids.index(input_id)] = nodes.InputNode(source.node().object())

        return valid_inputs

    def create_input(self, name: str, **kwargs: dict) -> nodes.InputNode:
        """
        Creates a new input node with given name and given attributes.

        :param str name: input node name.
        :param dict kwargs: input node attributes.
        :return: newly created input node.
        :rtype: nodes.InputNode
        """

        assert not self.has_input(name)
        new_input_node = nodes.InputNode()
        new_input_node.create(name=name, **kwargs)
        new_input_node.setParent(self.root_transform(), True)
        self.add_input_node(new_input_node, as_root=kwargs.get('root', False))

        return new_input_node

    def add_input_node(self, input_node: nodes.InputNode, as_root: bool = False):
        """
        Attaches given input node into this layer meta node instance.

        :param nodes.InputNode input_node: input node instance.
        :param bool as_root: whether input node is a root one.
        """

        input_plug = self.attribute(consts.NODDLE_INPUTS_ATTR)
        next_element = input_plug.nextAvailableDestElementPlug()
        input_node.message.connect(next_element.child(0))
        next_element.child(1).setString(input_node.id())
        next_element.child(2).setBool(as_root)

    def delete_input(self, input_id: str) -> bool:
        """
        Deletes input with given ID.

        :param str input_id: ID of the input node to delete.
        :return: True if input node was deleted successfully; False otherwise.
        :rtype: bool
        """

        input_plug = self.input_plug_by_id(input_id)
        if not input_plug:
            return False

        node = input_plug.child(0).sourceNode()
        if node is not None:
            node.delete()

        input_plug.delete()

        return True

    def clear_inputs(self) -> api.DGModifier:
        """
        Clears all input nodes from this layer. Only input nodes whose are parented under the layer root node will be
        deleted.

        :return: DG modifier instance used to clear outputs.
        :rtype: api.DGModifier
        """

        input_array = self.attribute(consts.NODDLE_INPUTS_ATTR)
        root_transform = self.root_transform()
        mod = api.DGModifier()
        for element in input_array:
            source = element.child(0).sourceNode()
            if source is not None and source.parent() == root_transform:
                source.delete(mod=mod, apply=False)
        mod.doIt()
        input_array.deleteElements(mod=mod, apply=True)

        return mod


class NoddleOutputLayer(NoddleLayer):

    ID = consts.OUTPUT_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.NODDLE_OUTPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_OUTPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_OUTPUT_ID_ATTR, type=api.kMFnDataString),
                    ]
                ),
            )
        )

        return attrs

    def has_output(self, name: str) -> bool:
        """
        Returns whether output node with given name is attached to this layer instance.

        :param str name: name of the output node to check.
        :return: True if output node with given name is attached to this layer instance; False otherwise.
        :rtype: bool
        """

        try:
            return self.output_node(name) is not None
        except errors.NoddleInvalidOutputNodeMetaData:
            return False

    def output_plug_by_id(self, output_id: str) -> api.Plug | None:
        """
        Returns the output plug instance for the output node with given ID.

        :param str output_id: ID of the output node plug to retrieve.
        :return: found plug instance with given ID.
        :rtype: api.Plug or None
        """

        output_plug = self.attribute(consts.NODDLE_OUTPUTS_ATTR)
        found_plug = None
        for element in output_plug:
            if element.child(1).asString() == output_id:
                found_plug = element
                break

        return found_plug

    def output_node(self, name: str) -> nodes.OutputNode | None:
        """
        Returns output node with given name attached to this layer instance.

        :param str name: name of the output node to get.
        :return: output node instance.
        :rtype: nodes.OutputNode or None
        """

        element = self.output_plug_by_id(name)
        if element is None:
            return None

        source = element.child(0).source()
        if not source:
            raise errors.NoddleInvalidOutputNodeMetaData('-'.join([name, element.child(1).asString()]))

        return nodes.OutputNode(source.node().object())

    def iterate_outputs(self) -> Iterator[nodes.OutputNode]:
        """
        Generator function that iterates over all output nodes within this layer.

        :return: iterated output nodes.
        :rtype: Iterator[nodes.OutputNode]
        """

        output_plug = self.attribute(consts.NODDLE_OUTPUTS_ATTR)
        for element in output_plug:
            source = element.child(0).source()
            if source is not None:
                yield nodes.OutputNode(source.node().object())

    def create_output(self, name: str, **kwargs: dict) -> nodes.OutputNode:
        """
        Creates a new output node with given name and given attributes.

        :param str name: output node name.
        :param dict kwargs: output node attributes.
        :return: newly created output node.
        :rtype: nodes.OutputNode
        """

        assert not self.has_output(name)
        new_output_node = nodes.OutputNode()
        new_output_node.create(name=name, **kwargs)
        new_output_node.setParent(self.root_transform(), True)
        self.add_output_node(new_output_node)

        return new_output_node

    def add_output_node(self, output_node: nodes.OutputNode):
        """
        Attaches given output node into this layer meta node instance.

        :param nodes.OutputNode output_node: output node instance.
        """

        output_plug = self.attribute(consts.NODDLE_OUTPUTS_ATTR)
        next_element = output_plug.nextAvailableDestElementPlug()
        output_node.message.connect(next_element.child(0))
        next_element.child(1).setString(output_node.id())

    def find_output_nodes(self, *ids: tuple[str]) -> list[nodes.OutputNode | None]:
        """
        Returns the output node instances from given IDs.

        :param tuple[str] ids: IDs to find output nodes of.
        :return: list containing the found output nodes.
        :rtype: list[nodes.OutputNode or None]
        """

        found_outputs: list[nodes.OutputNode | None] = [None] * len(ids)
        output_plug = self.attribute(consts.NODDLE_OUTPUTS_ATTR)
        for element in output_plug:
            output_id = element.child(1).asString()
            if output_id not in ids:
                continue
            source = element.child(0).source()
            if not source:
                continue
            found_outputs[ids.index(output_id)] = nodes.OutputNode(source.node().object())

        return found_outputs

    def delete_output(self, output_id: str) -> bool:
        """
        Deletes output given ID.

        :param str output_id: ID of the output node to delete.
        :return: True if output node was deleted successfully; False otherwise.
        :rtype: bool
        """

        output_plug = self.output_plug_by_id(output_id)
        if not output_plug:
            return False

        node = output_plug.child(0).sourceNode()
        if node is not None:
            node.delete()

        output_plug.delete()

        return True

    def clear_outputs(self) -> api.DGModifier:
        """
        Clears all output nodes from this layer. Only output nodes whose are parented under the layer root node will be
        deleted.

        :return: DG modifier instance used to clear outputs.
        :rtype: api.DGModifier
        """

        output_array = self.attribute(consts.NODDLE_OUTPUTS_ATTR)
        root_transform = self.root_transform()
        mod = api.DGModifier()
        for element in output_array:
            source = element.child(0).sourceNode()
            if source is not None and source.parent() == root_transform:
                source.delete(mod=mod, apply=False)
        mod.doIt()
        output_array.deleteElements(mod=mod, apply=True)

        return mod


class NoddleSkeletonLayer(NoddleLayer):

    ID = consts.SKELETON_LAYER_TYPE
    
    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.NODDLE_JOINTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_JOINT_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_JOINT_ID_ATTR, type=api.kMFnDataString)
                    ]
                ),
                dict(
                    name=consts.NODDLE_REGIONS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_REGION_NAME_ATTR, type=api.kMFnDataString),
                        dict(name=consts.NODDLE_REGION_SIDE_ATTR, type=api.kMFnDataString),
                        dict(name=consts.NODDLE_REGION_START_JOINT_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_REGION_END_JOINT_ATTR, type=api.kMFnMessageAttribute)
                    ]
                ),
                dict(name=consts.NODDLE_JOINT_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute)
            )
        )

        return attrs

    def selection_set(self) -> api.ObjectSet | None:
        """
        Returns the selection set attached to this layer.

        :return: selection set instance.
        :rtype: api.ObjectSet or None
        """

        return self.sourceNodeByName(consts.NODDLE_JOINT_SELECTION_SET_ATTR)

    def create_selection_set(self, name: str, parent: api.ObjectSet | None = None) -> api.ObjectSet:
        """
        Creates layer selection set and parent it in the optional parent selection set.

        :param str name: name of the selection set.
        :param api.ObjectSet or None parent: optional selection set parent instance.
        :return: newly created selection set instance.
        :rtype: api.ObjectSet
        """

        existing_set = self.selection_set()
        if existing_set is not None:
            return existing_set

        object_set = api.factory.create_dg_node(name, 'objectSet')
        if parent is not None:
            parent.addMember(object_set)
        self.connect_to(consts.NODDLE_JOINT_SELECTION_SET_ATTR, object_set)

        return object_set

    def iterate_joint_plugs(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over all joint plugs.

        :return: iterated joint plugs.
        :rtype: Iterator[api.Plug]
        """

        for i in self.attribute(consts.NODDLE_JOINTS_ATTR):
            yield i

    def iterate_joints(self) -> Iterator[nodes.Joint]:
        """
        Generator function that iterates over all deform skeleton joints.

        :return: iterated deform skeleton joints.
        :rtype: Iterator[nodes.Joint]
        """

        for i in self.iterate_joint_plugs():
            source = i.child(0).source()
            if source:
                yield nodes.Joint(source.node().object())

    def joints(self) -> list[nodes.Joint]:
        """
        Returns all the joints that are under this layer in order of the DAG.

        :return: list of DAG ordered joints.
        :rtype: list[nodes.Joint]
        """

        found_joints = []
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            source = joint_plug.source()
            if not source:
                continue
            found_joints.append(nodes.Joint(source.node().object()))

        return found_joints

    def iterate_root_joints(self) -> Iterator[nodes.Joint]:
        """
        Generator function that iterates over all deform root skeleton joints.

        :return: iterated root deform skeleton joints.
        :rtype: Iterator[nodes.Joint]
        """

        current_joints = self.joints()
        for joint in current_joints:
            parent = joint.parent()
            if parent is None or parent not in current_joints:
                yield joint

    def joint(self, name: str) -> nodes.Joint | None:
        """
        Return joint with given ID.

        :param str name: ID of the joint to retrieve.
        :return: joint found with given ID.
        :rtype: nodes.Joint or None
        """

        found_joint = None
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == name:
                source = joint_plug.source()
                if not source:
                    return None
                found_joint = nodes.Joint(source.node().object())
                break

        return found_joint

    def find_joints(self, *ids: tuple[str]) -> list[nodes.Joint | None]:
        """
        Returns the joint node instances from given IDs.

        :param tuple[str] ids: IDs to find joint nodes of.
        :return: list containing the found joint nodes.
        :rtype: list[nodes.Joint or None]
        """

        found_joints: list[nodes.Joint | None] = [None] * len(ids)
        for joint in self.iterate_joints():
            current_id = joint.attribute(consts.NODDLE_ID_ATTR).value()
            if current_id in ids:
                found_joints[ids.index(current_id)] = joint

        return found_joints

    def create_joint(self, **kwargs) -> nodes.Joint:
        """
        Creates a new joint based on given data.

        :param kwargs: joint data. e.g:
            {
                'id': 'root',
                'name': 'rootJnt'
                'translate': [0.0, 0.0, 0.0],
                'rotate': [0.0, 0.0, 0.0, 1.0],
                'rotateOrder': 0,
                'parent': None
            }
        :return: newly created joint.
        :rtype: meta_nodes.Joint
        """

        new_joint = nodes.Joint()
        new_joint.create(
            id=kwargs.get('id', ''),
            name=kwargs.get('name', 'NO_NAME'),
            translate=kwargs.get('translate', (0.0, 0.0, 0.0)),
            rotate=kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)),
            rotateOrder=kwargs.get('rotateOrder', 0),
            parent=kwargs.get('parent', None))
        self.add_joint(new_joint, kwargs.get('id', ''))

        return new_joint

    def add_joint(self, joint: nodes.Joint, joint_id: str | None = None):
        """
        Attaches given joint to this layer with given ID.

        :param nodes.Joint joint: joint instance to attach to this layer instance.
        :param str or None joint_id: joint ID.
        """

        joints_attr = self.attribute(consts.NODDLE_JOINTS_ATTR)
        joints_attr.isLocked = False
        element = joints_attr.nextAvailableDestElementPlug()
        joint.message.connect(element.child(0))
        if not joint.hasAttribute(consts.NODDLE_ID_ATTR):
            joint.addAttribute(name=consts.NODDLE_ID_ATTR, type=api.kMFnDataString, default='', value=joint_id)
        else:
            joint_id = joint.attribute(consts.NODDLE_ID_ATTR).value()
        joint_id = joint_id or joint.fullPathName(partial_name=True, include_namespace=False)
        element.child(1).set(joint_id)

    def delete_joint(self, joint_id: str) -> bool:
        """
        Deletes joint with given ID from this layer instance.

        :param str joint_id: ID of the joint to delete.
        :return: True if the joint was deleted successfully; False otherwise.
        :rtype: bool
        """

        found_plug = None
        found_node = None
        for element in self.iterate_joint_plugs():
            node_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == joint_id:
                found_plug = element
                found_node = node_plug.sourceNode()
                break
        if found_plug is None and found_node is None:
            return False

        if found_plug is not None:
            found_plug.delete()
        if found_node is not None:
            found_node.delete()

        return True

    def add_region(self, name: str, side: str, start_joint_id: str, end_joint_id: str):
        """
        Adds a new region to the skeleton layer.

        :param str name: name of the region to add.
        :param str side: side of the region to add.
        :param str start_joint_id: region start joint ID.
        :param str end_joint_id: region end joint ID.
        """

        regions_attr = self.attribute(consts.NODDLE_REGIONS_ATTR)
        regions_attr.isLocked = False
        element = regions_attr.nextAvailableDestElementPlug()
        element.child(0).set(name)
        element.child(1).set(side)
        element.child(2).set(start_joint_id)
        element.child(3).set(end_joint_id)


class NoddleRigLayer(NoddleLayer):

    ID = consts.RIG_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.NODDLE_JOINTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_JOINT_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_JOINT_ID_ATTR, type=api.kMFnDataString),
                    ]
                ),
                dict(
                    name=consts.NODDLE_CONTROLS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.NODDLE_CONTROL_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.NODDLE_CONTROL_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.NODDLE_CONTROL_SRTS_ATR, type=api.kMFnMessageAttribute, isArray=True)
                    ]
                ),
                dict(name=consts.NODDLE_CONTROL_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute)
            )
        )

        return attrs

    @override
    def serializeFromScene(self) -> dict:

        data = {}
        for i in self.iterate_settings_nodes():
            data[i.id()] = i.serializeFromScene()

        return {
            consts.RIG_LAYER_DESCRIPTOR_KEY: {
                consts.SETTINGS_DESCRIPTOR_KEY: data,
                consts.DAG_DESCRIPTOR_KEY: [],
                consts.DG_DESCRIPTOR_KEY: []
            }
        }

    def control_panel(self) -> nodes.SettingsNode:
        """
        Returns the control panel settings node.

        :return: control panel settings node.
        :rtype: nodes.SettingsNode
        """

        return self.setting_node(consts.CONTROL_PANEL_TYPE)

    def selection_set(self) -> api.ObjectSet | None:
        """
        Returns rig layer controls selection set.

        :return: controls selection set.
        :rtype: api.ObjectSet or None
        """

        return self.sourceNodeByName(consts.NODDLE_CONTROL_SELECTION_SET_ATTR)

    def create_selection_set(self, name: str, parent: api.ObjectSet | None = None):
        """
        Creates rig layer controls selection set if it does not exist.

        :param str name: selection set name.
        :param api.ObjectSet or None parent: optional parent selection set.
        :return: newly created selection set.
        :rtype: api.ObjectSet
        """

        existing_set = self.sourceNodeByName(consts.NODDLE_CONTROL_SELECTION_SET_ATTR)
        if existing_set is not None:
            return existing_set

        object_set = api.factory.create_dg_node(name, 'objectSet')
        if parent is not None:
            parent.addMember(object_set)
        self.connect_to(consts.NODDLE_CONTROL_SELECTION_SET_ATTR, object_set)

        return object_set

    def iterate_joint_plugs(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over all joint plugs.

        :return: iterated joint plugs.
        :rtype: Iterator[api.Plug]
        """

        for i in self.attribute(consts.NODDLE_JOINTS_ATTR):
            yield i

    def iterate_joints(self) -> Iterator[nodes.Joint]:
        """
        Generator function that iterates over all deform skeleton joints.

        :return: iterated deform skeleton joints.
        :rtype: Iterator[nodes.Joint]
        """

        for i in self.iterate_joint_plugs():
            source = i.child(0).source()
            if source:
                yield nodes.Joint(source.node().object())

    def joints(self) -> list[nodes.Joint]:
        """
        Returns all the joints that are under this layer in order of the DAG.

        :return: list of DAG ordered joints.
        :rtype: list[nodes.Joint]
        """

        found_joints: list[nodes.Joint] = []
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            source = joint_plug.source()
            if not source:
                continue
            found_joints.append(nodes.Joint(source.node().object()))

        return found_joints

    def iterate_root_joints(self) -> Iterator[nodes.Joint]:
        """
        Generator function that iterates over all deform root skeleton joints.

        :return: iterated root deform skeleton joints.
        :rtype: Iterator[nodes.Joint]
        """

        current_joints = self.joints()
        for joint in current_joints:
            parent = joint.parent()
            if parent is None or parent not in current_joints:
                yield joint

    def joint(self, name: str) -> nodes.Joint | None:
        """
        Return joint with given ID.

        :param str name: ID of the joint to retrieve.
        :return: joint found with given ID.
        :rtype: nodes.Joint or None
        """

        found_joint = None
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == name:
                source = joint_plug.source()
                if not source:
                    return None
                found_joint = nodes.Joint(source.node().object())
                break

        return found_joint

    def find_joints(self, *ids: tuple[str]) -> list[nodes.Joint | None]:
        """
        Returns the joint node instances from given IDs.

        :param tuple[str] ids: IDs to find joint nodes of.
        :return: list containing the found joint nodes.
        :rtype: list[nodes.Joint or None]
        """

        found_joints: list[nodes.Joint | None] = [None] * len(ids)
        for joint in self.iterate_joints():
            current_id = joint.attribute(consts.NODDLE_ID_ATTR).value()
            if current_id in ids:
                found_joints[ids.index(current_id)] = joint

        return found_joints

    def create_joint(self, **kwargs) -> nodes.Joint:
        """
        Creates a new joint based on given data.

        :param Dict kwargs: joint data. e.g:
            {
                'id': 'root',
                'name': 'rootJnt'
                'translate': [0.0, 0.0, 0.0],
                'rotate': [0.0, 0.0, 0.0, 1.0],
                'rotateOrder': 0,
                'parent': None
            }
        :return: newly created joint.
        :rtype: nodes.Joint
        """

        new_joint = nodes.Joint()
        new_joint.create(
            id=kwargs.get('id', ''),
            name=kwargs.get('name', 'NO_NAME'),
            translate=kwargs.get('translate', (0.0, 0.0, 0.0)),
            rotate=kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)),
            rotateOrder=kwargs.get('rotateOrder', 0),
            parent=kwargs.get('parent', None))
        self.add_joint(new_joint, kwargs.get('id', ''))

        return new_joint

    def add_joint(self, joint: nodes.Joint, joint_id: str):
        """
        Attaches given joint to this layer with given ID.

        :param nodes.Joint joint: joint instance to attach to this layer instance.
        :param str joint_id: joint ID.
        """

        joints_attr = self.attribute(consts.NODDLE_JOINTS_ATTR)
        joints_attr.isLocked = False
        element = joints_attr.nextAvailableDestElementPlug()
        joint.message.connect(element.child(0))
        if not joint.hasAttribute(consts.NODDLE_ID_ATTR):
            joint.addAttribute(name=consts.NODDLE_ID_ATTR, type=api.kMFnDataString, default='', value=joint_id)
        element.child(1).set(joint_id)

    def delete_joint(self, joint_id: str) -> bool:
        """
        Deletes joint with given ID from this layer instance.

        :param str joint_id: ID of the joint to delete.
        :return: True if the joint was deleted successfully; False otherwise.
        :rtype: bool
        """

        found_plug = None
        found_node = None
        for element in self.iterate_joint_plugs():
            node_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == joint_id:
                found_plug = element
                found_node = node_plug.sourceNode()
                break
        if found_plug is None and found_node is None:
            return False

        if found_plug is not None:
            found_plug.delete()
        if found_node is not None:
            found_node.delete()

        return True

    def iterate_control_plugs(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over all control plugs connected to this rig layer instance.

        :return: iterated control plugs.
        :rtype: Iterator[api.Plug]
        """

        control_parent_plug = self.attribute(consts.NODDLE_CONTROLS_ATTR)
        if control_parent_plug is not None:
            for i in control_parent_plug:
                yield i

    def iterate_controls(self, recursive: bool = False) -> Iterator[nodes.ControlNode]:
        """
        Generator function that iterates over all control nodes connected to this rig layer instance.

        :param bool recursive: whether to return all controls recursively or only parent controls.
        :return: iterated control nodes.
        :rtype: Iterator[nodes.ControlNode]
        """

        for element in self.iterate_control_plugs():
            source = element.child(0).source()
            if not source:
                continue
            yield nodes.ControlNode(source.node().object())
        if recursive:
            for child in self.find_children_by_class_types(consts.RIG_LAYER_TYPE, depth_limit=1):
                child_layer = NoddleRigLayer(node=child.object())
                for child_control in child_layer.iterate_controls():
                    yield child_control

    def control_plug_by_id(self, control_id: str) -> api.Plug | None:
        """
        Returns the plug where control with given ID is connected.

        :param str control_id: ID of the control whose plug we want to retrieve.
        :return: control plug.
        :rtype: api.Plug or None
        """

        found_plug = None
        for element in self.iterate_control_plugs():
            id_plug = element.child(1)
            if id_plug.asString() == control_id:
                found_plug = element
                break

        return found_plug

    def control(self, name: str) -> nodes.ControlNode:
        """
        Returns control instance with given name attached to this rig layer instance.

        :param str name: name of the control to find.
        :return: found control instance with given name.
        :rtype: meta_nodes.ControlNode
        :raises errors.CritMissingControlError: if no control with name is found.
        """

        for element in self.iterate_control_plugs():
            control_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() != name:
                continue
            source = control_plug.source()
            if source is not None:
                return nodes.ControlNode(source.node().object())

        raise errors.NoddleMissingControlError(f'No control found with name "{name}"')

    def add_control(self, control: nodes.ControlNode):
        """
        Attaches given control node instance to this rig layer instance.

        :param meta_nodes.ControlNode control: control node to attach to this rig layer instance.
        """

        controls_attr = self.attribute(consts.NODDLE_CONTROLS_ATTR)
        controls_attr.isLocked = False
        element = controls_attr.nextAvailableDestElementPlug()
        control.message.connect(element.child(0))
        element.child(1).set(control.id())
        srt = control.srt()
        if srt is not None:
            srt.message.connect(element.child(2))

    def create_control(self, **kwargs) -> nodes.ControlNode:
        """
        Creats a new control attached to this rig layer instance.

        :param Dict kwargs: control keyword arguments.
        :return: newly created control.
        :rtype: meta_nodes.ControlNode
        """

        new_control = nodes.ControlNode()
        control_parent = kwargs.get('parent', '')
        if not control_parent:
            kwargs['parent'] = self.root_transform()
        elif helpers.is_string(control_parent):
            kwargs['parent'] = self.root_transform() if control_parent == 'root' else self.control(control_parent)
        world_matrix = kwargs.get('worldMatrix')
        if world_matrix is not None:
            world_matrix = api.TransformationMatrix(api.Matrix(world_matrix))
            world_matrix.setScale((1, 1, 1), api.kWorldSpace)
            kwargs['worldMatrix'] = world_matrix.asMatrix()

        new_control.create(**kwargs)
        self.add_control(new_control)

        new_control.set_outliner_color(27)
        # new_control.set_line_width(new_control.LINE_WIDTH)
        new_control.lock_attributes(kwargs.get('not_locked_attributes', ['t', 'r']))
        new_control.orient_shape(direction=kwargs.get('orient_axis', 'y'))

        for srt_descriptor in kwargs.get('srts', []):
            self.create_srt_buffer(kwargs['id'], srt_descriptor['name'])

        return new_control

    def find_controls(self, *ids: tuple[str]) -> list[nodes.ControlNode | None]:
        """
        Returns controls with given IDs that are linked to this rig layer instance.

        :param tuple[str] ids: IDs of the controls to find.
        :return: found controls that matches given IDs.
        :rtype: list[meta_nodes.ControlNode | None]
        """

        found_controls: list[nodes.ControlNode | None] = [None] * len(ids)
        for ctrl in self.iterate_controls(recursive=False):
            ctrl_id = ctrl.id()
            if ctrl_id not in ids:
                continue
            found_controls[ids.index(ctrl_id)] = ctrl

        return found_controls

    def create_srt_buffer(self, control_id: str, name: str) -> api.DagNode | None:
        """
        Creates a new SRT buffer for the control with given ID and with the given name.

        :param str control_id: ID of the control we want to create SRT buffer for.
        :param str name: name of the SRT buffer node.
        :return: newly created SRT buffer.
        :rtype: api.DagNode or None
        """

        control_element = self.control_plug_by_id(control_id)
        if control_element is None:
            return None

        control_source = control_element.child(0).source()
        control_node = nodes.ControlNode(control_source.node().object())
        srt_plug = control_element[2]
        next_element = srt_plug.nextAvailableDestElementPlug()
        ctrl_parent = control_node.parent()
        new_srt = api.factory.create_dag_node(name, 'transform')
        new_srt.setWorldMatrix(control_node.worldMatrix())
        new_srt.setParent(ctrl_parent)
        control_node.setParent(new_srt, use_srt=False)
        new_srt.message.connect(next_element)

        return new_srt


class NoddleXGroupLayer(NoddleLayer):

    ID = consts.XGROUP_LAYER_TYPE


class NoddleGeometryLayer(NoddleLayer):

    ID = consts.GEOMETRY_LAYER_TYPE
