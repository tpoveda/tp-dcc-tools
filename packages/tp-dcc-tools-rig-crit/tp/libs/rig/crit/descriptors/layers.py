from __future__ import annotations

from typing import Tuple, List, Iterator, Dict, Any

from overrides import override

from tp.common.python import helpers
from tp.maya import api

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.descriptors import nodes, attributes, graphs


def traverse_descriptor_layer_dag(layer_descriptor: LayerDescriptor) -> Iterator:
    """
    Depth first search recursive generator function which walks the layer descriptor DAG nodes.

    :param LayerDescriptor layer_descriptor: layer descriptor to traverse.
    :return: iterated DAG nodes.
    :rtype: Iterator
    """

    def _node_iter(_node):
        for _child in iter(_node.get('children', list())):
            yield _child
            for i in _node_iter(_child):
                yield i

    for node in iter(layer_descriptor.get(consts.DAG_DESCRIPTOR_KEY, list())):
        yield node
        for child in _node_iter(node):
            yield child


class LayerDescriptor(helpers.ObjectDict):
    """
    Base layer descriptor used as containers to organise a single CRIT rig structure.

    ..warning:: this class should never be instantiated directly, but its subclasses.
    """

    @classmethod
    def from_data(cls, layer_data: Dict) -> LayerDescriptor:
        """
        Transforms given data to valid descriptor instances and returns an instance of this layer descriptor based on
        given data.

        :param Dict layer_data: layer dictionary data.
        :return: new layer descriptor instance.
        :rtype: LayerDescriptor
        """

        return cls()

    def has_node(self, node_id: str) -> bool:
        """
        Returns whether DAG node with given ID exists within this layer.

        :param str node_id: DAG node ID to check.
        :return: True if DAG node with given ID exists within this layer; False otherwise.
        :rtype: bool
        """

        return self.node(node_id) is not None

    def node(self, node_id: str) -> nodes.TransformDescriptor:
        """
        Returns DAG node from layer with given ID.

        :param str node_id: DAG node ID.
        :return: found DAG node with given ID.
        :rtype: nodes.TransformDescriptor
        """

        for found_node in traverse_descriptor_layer_dag(self):
            if found_node['id'] == node_id:
                return found_node

    def iterate_nodes(self, include_root: bool = True) -> Iterator[nodes.TransformDescriptor]:
        """
        Generator function that iterates over all DAG nodes within this layer.

        :param bool include_root: whether to include root node.
        :return: iterated DAG nodes.
        :rtype: Iterator[nodes.TransformDescriptor]
        """

        for found_node in traverse_descriptor_layer_dag(self):
            if not include_root and found_node['id'] == 'root':
                continue
            yield found_node

    def find_nodes(self, *node_ids: Tuple) -> List[nodes.TransformDescriptor | None]:
        """
        Loops through all nodes within this layer and returns a list with found nodes.

        :param Tuple[str] node_ids: list of node IDs to search.
        :return: List[nodes.TransformDescriptor or None]
        """

        results = [None] * len(node_ids)
        for found_node in traverse_descriptor_layer_dag(self):
            node_id = found_node['id']
            if node_id in node_ids:
                results[node_ids.index(node_id)] = found_node

        return results


class GuideLayerDescriptor(LayerDescriptor):
    """
    Guide layer descriptor class.
    """

    def __getattr__(self, item: str) -> nodes.GuideDescriptor:
        """
        Overrides __getattr__ function so guide objects are iterated and returns first one with the given name.

        :param str item: guide ID to get.
        :return: found guide or default behaviour.
        :rtype: nodes.GuideDescriptor
        """

        key = self.get(item)
        if key is not None:
            return key

        guide = self.guide(item)
        if guide is not None:
            return guide

        return super().__getattribute__(item)

    def update(self, kwargs: Dict):
        """
        Overrides update function to update data with proper descriptors.

        :param Dict kwargs: dictionary to update current one with.
        """

        settings = self[consts.SETTINGS_DESCRIPTOR_KEY]
        consolidated_settings = dict((i['name'], i) for i in settings)
        for i in kwargs.get(consts.SETTINGS_DESCRIPTOR_KEY, list()):
            existing_setting = consolidated_settings.get(i['name'])
            if existing_setting is not None and i.get('value') is not None:
                existing_setting['value'] = i['value']
            else:
                consolidated_settings[i['name']] = attributes.attribute_class_for_descriptor(i)
        self[consts.SETTINGS_DESCRIPTOR_KEY] = list(consolidated_settings.values())

        current_guides = {i['id'] for i in self.iterate_guides()}
        new_or_updated = []
        for guide_descriptor in traverse_descriptor_layer_dag(kwargs):
            new_or_updated.append(guide_descriptor['id'])
            current_node = self.guide(guide_descriptor['id'])
            guide_descriptor['pivotColor'] = current_node.get('pivotColor')
            guide_descriptor['pivotShape'] = current_node.get('pivotShape')
            if current_node is not None:
                children = guide_descriptor.get('children')
                if children:
                    guide_descriptor['children'] = [nodes.GuideDescriptor.deserialize(i, guide_descriptor['id']) for i in children]
                current_node.update(guide_descriptor)
            else:
                self.create_guide(**guide_descriptor)
        to_purge = [i for i in current_guides if i not in new_or_updated]
        if to_purge:
            self.delete_guides(*to_purge)

        self[consts.METADATA_DESCRIPTOR_KEY] = [attributes.attribute_class_for_descriptor(s) for s in kwargs.get(
            consts.METADATA_DESCRIPTOR_KEY, [])] or self.get(consts.METADATA_DESCRIPTOR_KEY, [])

        dg_graphs = kwargs.get(consts.DG_DESCRIPTOR_KEY)
        if dg_graphs is not None:
            self[consts.DG_DESCRIPTOR_KEY] = graphs.NamedGraphs.from_data(dg_graphs)

    @classmethod
    def from_data(cls, layer_data: Dict) -> GuideLayerDescriptor:
        """
        Transforms given data to valid descriptor instances and returns an instance of this layer descriptor based on
        given data.

        :param Dict layer_data: layer dictionary data.
        :return: new layer descriptor instance.
        :rtype: GuideLayerDescriptor
        """

        new_settings = cls.merge_default_settings(layer_data.get(consts.SETTINGS_DESCRIPTOR_KEY, list()))
        new_metadata = cls.merge_default_metadata(layer_data.get(consts.METADATA_DESCRIPTOR_KEY, list()))

        data = {
            consts.DAG_DESCRIPTOR_KEY: [nodes.GuideDescriptor.deserialize(
                guide_data) for guide_data in iter(layer_data.get(consts.DAG_DESCRIPTOR_KEY, list()))],
            consts.SETTINGS_DESCRIPTOR_KEY: new_settings,
            consts.METADATA_DESCRIPTOR_KEY: new_metadata,
            consts.DG_DESCRIPTOR_KEY: graphs.NamedGraphs.from_data(layer_data.get(consts.DG_DESCRIPTOR_KEY, list()))
        }

        return cls(data)

    @classmethod
    def default_metadata_settings(cls) -> List[attributes.AttributeDescriptor]:
        """
        Returns default metadata settings dictionary.

        :return: default metadata attribute settings.
        :rtype: List[attributes.AttributeDescriptor]
        """

        data = [
            dict(name='guideVisibility', type=api.kMFnNumericBoolean, default=True, value=True),
            dict(name='guideControlVisibility', type=api.kMFnNumericBoolean, default=True, value=True),
            dict(name='pinSettings', type=api.kMFnCompoundAttribute, children=[
                dict(name='pinned', type=api.kMFnNumericBoolean),
                dict(name='pinnedConstraints', type=api.kMFnDataString),
            ]),
        ]

        return [attributes.attribute_class_for_descriptor(attr_data) for attr_data in data]

    @classmethod
    def default_guide_settings(cls) -> List[attributes.AttributeDescriptor]:
        """
        Returns default guide setting dictionary.

        :return: default guide attribute settings.
        :rtype: List[attributes.AttributeDescriptor]
        """

        data = [
            {
                'name': 'manualOrient', 'value': False, 'isArray': False, 'locked': False, 'default': False,
                'channelBox': True, 'keyable': False, 'type': api.kMFnNumericBoolean
            }
        ]

        return [attributes.attribute_class_for_descriptor(attr_data) for attr_data in data]

    @classmethod
    def merge_default_settings(cls, new_state: Dict) -> List[attributes.AttributeDescriptor]:
        """
        Returns a dictionary with override guide settings based on default guide settings.

        :param Dict new_state: override guide settings dictionary.
        :return: merged override default guide settings dictionary.
        :rtype: List[attributes.AttributeDescriptor]
        """

        default_settings = dict((i['name'], i) for i in cls.default_guide_settings())
        for attr in new_state:
            existing_attr = default_settings.get(attr['name'])
            if existing_attr is not None:
                existing_attr['value'] = attr['value']
            else:
                default_settings[attr['name']] = attributes.attribute_class_for_descriptor(attr)

        return list(default_settings.values())

    @classmethod
    def merge_default_metadata(cls, new_state: Dict) -> List[attributes.AttributeDescriptor]:
        """
        Returns a dictionary with override metadata settings based on default metadata settings.

        :param Dict new_state: override metadata settings dictionary.
        :return: merged override default metadata settings dictionary.
        :rtype: List[attributes.AttributeDescriptor]
        """

        default_settings = dict((i['name'], i) for i in cls.default_guide_settings())
        for attr in new_state:
            default_settings[attr['name']] = attr

        return [attributes.attribute_class_for_descriptor(attr_data) for attr_data in default_settings.values()]

    def has_guides(self) -> bool:
        """
        Returns whether this guide layer descriptor instances has guides.

        :return: True if this layer descriptor has guides; False otherwise.
        :rtype: bool
        """

        return len(self.get(consts.DAG_DESCRIPTOR_KEY, list())) != 0

    def guide_count(self, include_root: bool = True) -> int:
        """
        Returns the total amount of guides within this guide layer descriptor instance.

        :param bool include_root: whether to take root guide into consideration.
        :return: total amount of guides.
        :rtype: int
        """

        return len(list(self.iterate_guides(include_root=include_root)))

    def iterate_guides(self, include_root: bool = True) -> Iterator[nodes.GuideDescriptor]:
        """
        Generator function that iterates over all guides defined within this descriptor instance.

        :param bool include_root: whether to take root guide into consideration.
        :return: Iterator[nodes.GuideDescriptor]
        """

        for guide_descriptor in iter(self.get(consts.DAG_DESCRIPTOR_KEY, list())):
            if not include_root and guide_descriptor.id == 'root':
                for child_descriptor in guide_descriptor.iterate_children():
                    yield child_descriptor
            else:
                yield guide_descriptor
                for child_descriptor in guide_descriptor.iterate_children():
                    yield child_descriptor

    def find_guides(self, *ids: Tuple) -> List[nodes.GuideDescriptor | None]:
        """
        Finds and returns all guides with the given IDs.

        :param Tuple[str] ids: guide IDs to find.
        :return: list of guides in given order.
        :rtype: List[nodes.GuideDescriptor or None]
        """

        return self.find_nodes(*ids)

    def has_guide(self, guide_id: str) -> bool:
        """
        Returns whether guide with given ID exists within this descriptor.

        :param str guide_id: ID of the guide to search for.
        :return: True if guide with given ID exists within this descriptor; False otherwise.
        :rtype: bool
        """

        return self.has_node(guide_id)

    def guide(self, guide_id: str ) -> nodes.GuideDescriptor | None:
        """
        Returns the guide descriptor instance attached to this guide layer descriptor instance with given ID.

        :param str guide_id: guide ID value.
        :return: found guide descriptor instance with given ID.
        :rtype: nodes.GuideDescriptor or None
        """

        return self.node(guide_id)

    def create_guide(self, **info: dict):
        """
        Creates a new guide based on given info.

        :param dict info: guide data.
        :return: newly guide descriptor instance.
        :rtype: nodes.GuideDescriptor
        """

        existing_guide = self.guide(info['id'])
        if existing_guide is not None:
            return existing_guide

        new_guide_descriptor = nodes.GuideDescriptor.deserialize(info, parent=info.get('parent'))
        self.add_guide(new_guide_descriptor)

        return new_guide_descriptor

    def set_guide_parent(self, child: nodes.GuideDescriptor, parent: nodes.GuideDescriptor):
        """

        :param nodes.GuideDescriptor child: guide descriptor we want to set parent of.
        :param nodes.GuideDescriptor parent: guide descriptor we want to set as parent.
        :return: True if the set guide parent operation was successful; False otherwise.
        :rtype: bool
        """

        if child.parent == parent:
            return False

        # Remove self from current parent and add self the new parent
        current_parent = self.guide(child.parent)
        if current_parent is not None:
            del current_parent.children[current_parent.children.index(child)]
        parent.children.append(child)
        child.parent = parent.id

        return True

    def add_guide(self, guide: nodes.GuideDescriptor) -> bool:
        """
        Appends a new guide descriptor to this descriptor.

        :param nodes.GuideDescriptor guide: guide descriptor to add.
        :return: True if the add guide descriptor operation was successful; False otherwise.
        :rtype: bool
        """

        guide['critType'] = 'guide'
        parent = guide.get('parent', None)
        if parent is None:
            self.setdefault(consts.DAG_DESCRIPTOR_KEY, list()).append(guide)
            return True

        parent_guide = None
        child = None
        for guide_descriptor in self.iterate_guides():
            if guide_descriptor['id'] == parent:
                parent_guide, child = guide_descriptor, guide
                break
        if parent_guide is not None:
            parent_guide['children'].append(child)

        return True

    def delete_guides(self, *guide_ids: tuple) -> bool:
        """
        Deletes all guides with given IDs from this descriptor.

        :param tuple[str] guide_ids: list of guides IDs to delete.
        :return: True if the delete guides operation was successful; False otherwise.
        :rtype: bool
        """

        root = self.guide('root')
        success = False
        for found_guide in self.iterate_guides():
            guide_id = found_guide.id
            if guide_id not in guide_ids:
                continue
            guide_parent_id = found_guide.parent
            guide_parent = self.guide(guide_parent_id) if guide_parent_id is not None else root
            if not guide_parent:
                continue
            deleted = guide_parent.delete_child(guide_id)
            if deleted:
                success = deleted

        return success

    def has_guide_setting(self, name: str) -> bool:
        """
        Returns whether the given guide setting exists.

        :param str name: name of the guide setting to find.
        :return: True if the guide setting exists; False otherwise.
        :rtype: bool
        """

        for guide_setting in self.iterate_guide_settings():
            if guide_setting.name == name:
                return True

        return False

    def iterate_guide_settings(self) -> Iterator[attributes.AttributeDescriptor]:
        """
        Generator function that iterates over all guide settings.

        :return: iterated guide settings.
        :rtype: Iterator[attributes.AttributeDescriptor]
        """

        return iter(self[consts.SETTINGS_DESCRIPTOR_KEY])

    def guide_setting(self, name: str) -> attributes.AttributeDescriptor | None:
        """
        Returns the guide setting with the given name.

        :param str name: guide's setting name to retrieve.
        :return: found attribute descriptor with given name.
        :rtype: attribute.AttributeDescriptor or None
        """

        for i in self.iterate_guide_settings():
            if i.name == name:
                return i

        return None

    def guide_settings(self, *names: Tuple) -> helpers.ObjectDict[str, attributes.AttributeDescriptor]:
        """
        Returns all matching guide settings attributes as a dict.

        :param Tuple[str] names: guides settings attribute names to retrieve.
        :return: dictionary with the guide settings.
        :rtype: helpers.ObjectDict[str, attributes.AttributeDescriptor]
        """

        settings = helpers.ObjectDict()
        for setting in self.iterate_guide_settings():
            name = setting.name
            if name in names:
                settings[name] = setting

        return settings

    def add_guide_setting(self, setting: attributes.AttributeDescriptor):
        """
        Appends a new guide setting to this descriptor.

        :param attributes.AttributeDescriptor setting: attribute descriptor describing the guide setting.
        :return: True if the guide setting operation was successful; False otherwise.
        :rtype: bool
        """

        if self.has_guide_setting(setting.name):
            return False

        self[consts.SETTINGS_DESCRIPTOR_KEY].append(setting)

        return True

    def delete_setting(self, name: str) -> bool:
        """
        Deletes a setting by its name.

        :param str name: name of the setting to delete.
        :return: True if the delete setting operation was successful; False otherwise.
        :rtype: bool
        """

        try:
            node_settings = self[consts.SETTINGS_DESCRIPTOR_KEY]
            for node_setting in node_settings:
                if node_setting.name == name:
                    node_settings.remove(node_setting)
                    return True
            return False
        except KeyError:
            return False

    def delete_settings(self, names: List[str]):
        """
        Deletes all guide settings based on the given names.

        :param List[str] names: list of settings to delete.
        """

        valid = list()
        for setting in self.iterate_guide_settings():
            if setting.name not in names:
                valid.append(setting)
        self[consts.SETTINGS_DESCRIPTOR_KEY] = valid


class InputLayerDescriptor(LayerDescriptor):

    @classmethod
    @override
    def from_data(cls, layer_data: dict) -> LayerDescriptor:

        data = {
            consts.SETTINGS_DESCRIPTOR_KEY: list(map(
                attributes.attribute_class_for_descriptor, layer_data.get(consts.SETTINGS_DESCRIPTOR_KEY, []))),
            consts.DAG_DESCRIPTOR_KEY: list(map(
                nodes.InputDescriptor.deserialize, iter(layer_data.get(consts.DAG_DESCRIPTOR_KEY, []))))
        }

        return cls(data)

    @override(check_signature=False)
    def update(self, kwargs):
        self[consts.SETTINGS_DESCRIPTOR_KEY] = list(map(
            attributes.attribute_class_for_descriptor,
            kwargs.get(consts.SETTINGS_DESCRIPTOR_KEY, []))) or self[consts.SETTINGS_DESCRIPTOR_KEY]

        for input_descriptor in traverse_descriptor_layer_dag(kwargs):
            self.create_input(**input_descriptor)

    def iterate_inputs(self) -> Iterator[nodes.InputDescriptor]:
        """
        Generator function that iterates over all input node descriptors.

        :return: iterated input node descriptors.
        :rtype: Iterator[nodes.InputDescriptor]
        """

        for input_descriptor in iter(self.get(consts.DAG_DESCRIPTOR_KEY, [])):
            yield input_descriptor
            for child in input_descriptor.iterate_children():
                yield child

    def input(self, name: str) -> nodes.InputDescriptor | None:
        """
        Returns input node descriptor with given name.

        :param str name: name of the input node.
        :return: input node descriptor.
        :rtype: nodes.InputDescriptor or None
        """

        found_input_descriptor = None
        for input_descriptor in self.iterate_inputs():
            if input_descriptor['id'] == name:
                found_input_descriptor = input_descriptor
                break

        return found_input_descriptor

    def create_input(self, **data: Dict) -> nodes.InputDescriptor:
        """
        Creates a new input descriptor from given data and adds it into this layer descriptor.

        :param Dict data: input descriptor data.
        :return: newly created input descriptor instance.
        :rtype: nodes.InputDescriptor
        """

        existing_input = self.input(data['id'])
        if existing_input is not None:
            return existing_input

        parent = data.get('parent', None)
        parent = parent if parent and parent != 'root' else None
        input_descriptor = nodes.InputDescriptor.deserialize(data, parent=parent)
        self.add_input(input_descriptor)

        return input_descriptor

    def add_input(self, input_descriptor: nodes.InputDescriptor):
        """
        Adds given input descriptor instance into this layer descriptor.

        :param nodes.InputDescriptor input_descriptor: input descriptor to add.
        """

        input_descriptor['critType'] = 'input'
        if input_descriptor.parent is None:
            self[consts.DAG_DESCRIPTOR_KEY].append(input_descriptor)
            return

        for _input_descriptor in self.iterate_inputs():
            if _input_descriptor.id == input_descriptor.parent:
                _input_descriptor.children.append(input_descriptor)
                break

    def clear_inputs(self):
        """
        Deletes all input node descriptors from this layer.
        """

        self[consts.DAG_DESCRIPTOR_KEY] = []


class OutputLayerDescriptor(LayerDescriptor):

    @classmethod
    @override
    def from_data(cls, layer_data: dict) -> LayerDescriptor:

        data = {
            consts.SETTINGS_DESCRIPTOR_KEY: list(map(
                attributes.attribute_class_for_descriptor, layer_data.get(consts.SETTINGS_DESCRIPTOR_KEY, []))),
            consts.DAG_DESCRIPTOR_KEY: list(map(
                nodes.OutputDescriptor.deserialize, iter(layer_data.get(consts.DAG_DESCRIPTOR_KEY, []))))
        }

        return cls(data)

    @override(check_signature=False)
    def update(self, kwargs):
        self[consts.SETTINGS_DESCRIPTOR_KEY] = list(map(
            attributes.attribute_class_for_descriptor,
            kwargs.get(consts.SETTINGS_DESCRIPTOR_KEY, []))) or self[consts.SETTINGS_DESCRIPTOR_KEY]

        for output_descriptor in traverse_descriptor_layer_dag(kwargs):
            current_node = self.output(output_descriptor['id'])
            if current_node is not None:
                children = output_descriptor.get('children')
                if children:
                    output_descriptor['children'] = [
                        nodes.OutputDescriptor.deserialize(i, output_descriptor['id']) for i in children]
                current_node.update(output_descriptor)
            else:
                self.create_output(**output_descriptor)

    def iterate_outputs(self) -> Iterator[nodes.OutputDescriptor]:
        """
        Generator function that iterates over all output node descriptors.

        :return: iterated output node descriptors.
        :rtype: Iterator[nodes.OutputDescriptor]
        """

        for output_descriptor in iter(self.get(consts.DAG_DESCRIPTOR_KEY, [])):
            yield output_descriptor
            for child in output_descriptor.iterate_children():
                yield child

    def output(self, name: str) -> nodes.OutputDescriptor | None:
        """
        Returns output node descriptor with given name.

        :param str name: name of the output node.
        :return: output node descriptor.
        :rtype: nodes.OutputDescriptor or None
        """

        found_output_descriptor = None
        for output_descriptor in self.iterate_outputs():
            if output_descriptor['id'] == name:
                found_output_descriptor = output_descriptor
                break

        return found_output_descriptor

    def create_output(self, **data: Dict) -> nodes.OutputDescriptor:
        """
        Creates a new output descriptor from given data and adds it into this layer descriptor.

        :param Dict data: output descriptor data.
        :return: newly created output descriptor instance.
        :rtype: nodes.OutputDescriptor
        """

        existing_output = self.output(data['id'])
        if existing_output is not None:
            existing_output.parent = data.get('parent', existing_output.parent)
            return existing_output

        parent = data.get('parent', None)
        parent = parent if parent and parent != 'root' else None
        output_descriptor = nodes.OutputDescriptor.deserialize(data, parent=parent)
        self.add_output(output_descriptor)

        return output_descriptor

    def add_output(self, output_descriptor: nodes.OutputDescriptor):
        """
        Adds given output descriptor instance into this layer descriptor.

        :param nodes.OutputDescriptor output_descriptor: output descriptor to add.
        """

        output_descriptor['critType'] = 'output'
        if output_descriptor.parent is None:
            self[consts.DAG_DESCRIPTOR_KEY].append(output_descriptor)
            return

        for _output_descriptor in self.iterate_outputs():
            if _output_descriptor.id == output_descriptor.parent:
                _output_descriptor.children.append(output_descriptor)
                break

    def clear_outputs(self):
        """
        Deletes all output node descriptors from this layer.
        """

        self[consts.DAG_DESCRIPTOR_KEY] = []


class SkeletonLayerDescriptor(LayerDescriptor):

    @classmethod
    @override
    def from_data(cls, layer_data: Dict) -> LayerDescriptor:

        data = {
            consts.SETTINGS_DESCRIPTOR_KEY: list(map(
                attributes.attribute_class_for_descriptor, layer_data.get(consts.SETTINGS_DESCRIPTOR_KEY, []))),
            consts.DAG_DESCRIPTOR_KEY: list(map(
                nodes.JointDescriptor.deserialize, iter(layer_data.get(consts.DAG_DESCRIPTOR_KEY, []))))
        }

        return cls(data)

    @override(check_signature=False)
    def update(self, kwargs: Dict):

        self[consts.SETTINGS_DESCRIPTOR_KEY] = list(
            map(attributes.attribute_class_for_descriptor, kwargs.get(consts.SETTINGS_DESCRIPTOR_KEY, []))) or self[
                                                   consts.SETTINGS_DESCRIPTOR_KEY]
        skeleton_layer_info = kwargs.get(consts.DAG_DESCRIPTOR_KEY)
        if skeleton_layer_info:
            self[consts.DAG_DESCRIPTOR_KEY] = list(map(nodes.JointDescriptor.deserialize, iter(skeleton_layer_info)))

    def joint(self, joint_id: str) -> nodes.JointDescriptor | None:
        """
        Returns the joint descriptor instance that matches given ID.

        :param str joint_id: ID of the joint descriptor to find.
        :return: found joint descriptor instance.
        :rtype: nodes.JointDescriptor or None
        """

        found_joint_descriptor = None
        for joint_descriptor in self.iterate_deform_joints():
            if joint_descriptor.id == joint_id:
                found_joint_descriptor = joint_descriptor
                break

        return found_joint_descriptor

    def iterate_deform_joints(self) -> Iterator[nodes.JointDescriptor]:
        """
        Generator function that iterates over all deform joints defined within this skeleton descriptor layer.

        :return: iterated skeleton deform descriptor joints.
        :rtype: terator[nodes.JointDescriptor]
        """

        for joint_descriptor in iter(self.get(consts.DAG_DESCRIPTOR_KEY, [])):
            yield joint_descriptor
            for child in joint_descriptor.iterate_children():
                yield child

    def find_joints(self, *ids: Tuple[str]) -> List[nodes.JointDescriptor | None]:
        """
        Returns the joint descriptor instances from given IDs.

        :param Tuple[str] ids: IDs to find joint descriptors of.
        :return: list containing the found joint descriptors.
        :rtype: List[nodes.JointDescriptor or None]
        """

        found_joint_descriptors = [None] * len(ids)
        for joint_descriptor in self.iterate_deform_joints():
            joint_id = joint_descriptor.id
            if joint_id in ids:
                found_joint_descriptors[ids.index(joint_id)] = joint_descriptor

        return found_joint_descriptors

    def create_joint(self, **data: Dict) -> nodes.JointDescriptor:
        """
        Creates a new joint descriptor based on given data.

        :param Dict data: joint descriptor data. e.g:
            {
                'id': 'root',
                'name': 'rootJnt'
                'translate': [0.0, 0.0, 0.0],
                'rotate': [0.0, 0.0, 0.0, 1.0],
                'rotateOrder': 0,
            }
        :return: newly created joint descriptor.
        :rtype: nodes.JointDescriptor
        """

        existing_joint = self.joint(data['id'])
        if existing_joint is not None:
            return existing_joint

        parent = data.get('parent', '')
        if parent == 'root':
            parent = None

        joint_descriptor = nodes.JointDescriptor.deserialize(data, parent=parent)
        self.add_joint(joint_descriptor)

        return joint_descriptor

    def add_joint(self, joint_descriptor: nodes.JointDescriptor):
        """
        Adds given joint descriptor into this layer descriptor.

        :param nodes.JointDescriptor joint_descriptor: joint descriptor instance to add.
        """

        joint_descriptor['critType'] = 'joint'
        if joint_descriptor.parent is None:
            self[consts.DAG_DESCRIPTOR_KEY].append(joint_descriptor)
            return

        for _joint_descriptor in self.iterate_deform_joints():
            if _joint_descriptor.id == joint_descriptor.parent:
                _joint_descriptor.children.append(joint_descriptor)
                break

    def delete_joints(self, *joints_ids: Tuple[str]):
        """
        Deletes joint descriptors that matches given IDs.

        :param Tuple[str] joints_ids: joint IDs to delete.
        """

        top_level_nodes_to_delete = []
        for joint_descriptor in self.iterate_deform_joints():
            if joint_descriptor.id not in joints_ids:
                continue
            elif joint_descriptor.parent is None:
                top_level_nodes_to_delete.append(joint_descriptor)
                continue
            parent = self.joint(joint_descriptor.parent)
            parent.delete_child(joint_descriptor.id)

        for joint_descriptor in top_level_nodes_to_delete:
            self[consts.DAG_DESCRIPTOR_KEY].remove(joint_descriptor)

    def clear_joints(self):
        """
        Clears all joint descriptors defined within this layer descriptor.
        """

        self[consts.DAG_DESCRIPTOR_KEY] = []


class RigLayerDescriptor(LayerDescriptor):

    @classmethod
    @override
    def from_data(cls, layer_data: Dict) -> LayerDescriptor:

        data = {
            consts.DAG_DESCRIPTOR_KEY: [nodes.ControlDescriptor.deserialize(i) for i in iter(layer_data.get(consts.DAG_DESCRIPTOR_KEY, []))],
            consts.SETTINGS_DESCRIPTOR_KEY: {name: list(map(attributes.attribute_class_for_descriptor, v)) for name, v in iter(layer_data.get(consts.SETTINGS_DESCRIPTOR_KEY, {}).items())},
            consts.DG_DESCRIPTOR_KEY: graphs.NamedGraphs.from_data(layer_data.get(consts.DG_DESCRIPTOR_KEY, []))
        }

        return cls(data)

    @override(check_signature=False)
    def update(self, kwargs: Dict):

        self._update_settings(kwargs)
        rig_layer_info = kwargs.get(consts.DAG_DESCRIPTOR_KEY)
        if rig_layer_info is not None:
            self[consts.DAG_DESCRIPTOR_KEY] = list(map(nodes.ControlDescriptor.deserialize, iter(rig_layer_info)))
        dg_graphs = kwargs.get(consts.DG_DESCRIPTOR_KEY)
        if dg_graphs is not None:
            self[consts.DG_DESCRIPTOR_KEY] = graphs.NamedGraphs.from_data(dg_graphs)

    def setting(self, node_name: str, name: str) -> attributes.AttributeDescriptor | None:
        """
        Returns the attribute descriptor instance attached to the node with and with the given name.

        :param str node_name: name of the node where the setting is located ('constants, 'controlPanel', ...).
        :param str name: name of the setting to get descriptor of.
        :return: attribute descriptor instance.
        :rtype: attributes.AttributeDescriptor or None
        """

        found_descriptor = None
        try:
            node_settings = self[consts.SETTINGS_DESCRIPTOR_KEY][node_name]
            for i in iter(node_settings):
                if i.name == name:
                    found_descriptor = i
                    break
        except KeyError:
            return None

        return found_descriptor

    def add_setting(self, node_name: str, **kwargs: Dict):
        """
        Adds a new setting to the node with the given attribute descriptor data.

        :param str node_name: name of the node to attach the setting to.
        :param Dict kwargs: attribute descriptor data with the attribute arguments to add.
        """

        exists = self.setting(node_name, kwargs.get('name', ''))
        if exists:
            exists.value = kwargs.get('value', exists.value)
            exists.default = kwargs.get('default', exists.default)
            exists.min = kwargs.get('min', exists.min)
            exists.max = kwargs.get('max', exists.max)
            exists.softMin = kwargs.get('softMin', exists.softMin)
            exists.softMax = kwargs.get('softMax', exists.softMax)
            return

        s = attributes.attribute_class_for_descriptor(kwargs)
        self[consts.SETTINGS_DESCRIPTOR_KEY].setdefault(node_name, []).append(s)

        return s

    def add_settings(self, node_name: str, attribute_descriptors: List[attributes.AttributeDescriptor]):
        """
        Adds given settings to the node with given name.

        :param str node_name: name of the node to attach the setting to.
        :param List[attributes.AttributeDescriptor] attribute_descriptors: attribute descriptors to add.
        """

        for setting in attribute_descriptors:
            self.add_setting(node_name, **setting)

    def insert_setting_by_name(
            self, node_name: str, name: str, setting_descriptor: attributes.AttributeDescriptor,
            before: bool = False) -> bool:
        """
        Inserts a setting either before or after the existing setting with given name.

        :param str node_name:
        :param str name:
        :param attributes.AttributeDescriptor setting_descriptor:
        :param bool before:
        :return: True if setting was inserted successfully; False otherwise.
        :rtype: bool
        """

        if node_name not in self[consts.SETTINGS_DESCRIPTOR_KEY]:
            return False

        s = attributes.attribute_class_for_descriptor(setting_descriptor)
        for i, attribute_descriptor in enumerate(self[consts.SETTINGS_DESCRIPTOR_KEY][node_name]):
            if attribute_descriptor.name == name:
                insert_index = i if before else i + 1
                self[consts.SETTINGS_DESCRIPTOR_KEY][node_name].insert(insert_index, s)
                return True

        return False

    def set_setting_value(self, node_name: str, name: str, value: Any):
        """
        Sets the value for setting.

        :param str node_name: name of the node where the setting is located ('constants, 'controlPanel', ...).
        :param str name: name of the setting to set value for.
        :param Any value: setting value.
        """

        sets = self.setting(node_name, name)
        if sets:
            sets.value = value

    def delete_setting(self, node_name: str, name: str) -> bool:
        """
        Deletes a setting with given name from the given node.

        :param str node_name: name of the node where the setting is located ('constants, 'controlPanel', ...).
        :param str name: name of the setting to delete.
        :return: True if the setting was deleted successfully; False otherwise.
        :rtype: bool
        """

        try:
            node_settings = self[consts.SETTINGS_DESCRIPTOR_KEY][node_name]
            for i in node_settings:
                if i.name == name:
                    node_settings.remove(i)
                    return True
            return False
        except KeyError:
            return False

    def _update_settings(self, kwargs: Dict):
        """
        Internal function that updates settings attriubtes.

        :param Dict kwargs: keyword arguments.
        """

        settings = self[consts.SETTINGS_DESCRIPTOR_KEY]
        kwargs_settings = kwargs.get(consts.SETTINGS_DESCRIPTOR_KEY, {})
        for node_type, attrs in settings.items():
            kwargs_node_settings = kwargs_settings.get(node_type, [])
            kwargs_node_settings = {i['name']: attributes.attribute_class_for_descriptor(i) for i in kwargs_node_settings}
            consolidated_settings = {i['name']: i for i in attrs}
            for name, new_attr in kwargs_node_settings.items():
                existing_atr = consolidated_settings.get(name, None)
                if existing_atr is None:
                    consolidated_settings[name] = new_attr
            settings[node_type] = list(consolidated_settings.values())
