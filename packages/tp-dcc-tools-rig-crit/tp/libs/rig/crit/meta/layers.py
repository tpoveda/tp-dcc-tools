from __future__ import annotations

import typing
from typing import Iterator, Iterable

from overrides import override

import maya.cmds as cmds

from tp.common.python import helpers
from tp.maya import api
from tp.maya.meta import base
from tp.maya.om import plugs, mathlib as om_mathlib, nodes as om_nodes

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import errors
from tp.libs.rig.crit.meta import nodes as meta_nodes

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.meta.component import CritComponent


class CritLayer(base.DependentNode):
    """
    Base class for Crit layer nodes. Crit layers are used simply for organization purposes and can be used as the
    entry point ot access rig DAG related nodes.
    """

    def __init__(
            self, node: api.OpenMaya.MObject | None = None, name: str | None = None,
            parent: api.OpenMaya.MObject | None = None, init_defaults: bool = True, lock: bool = True,
            mod: api.OpenMaya.MDGModifier | None = None):
        super().__init__(node=node, name=name, parent=parent, init_defaults=init_defaults, lock=lock, mod=mod)

    @override
    def meta_attributes(self) -> list[dict]:
        """
        Overrides base meta_attributes function.
        Returns the list of default meta attributes that should 	be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: List[Dict]
        """

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(name=consts.CRIT_EXTRA_NODES_ATTR, isArray=True, type=api.kMFnMessageAttribute),
                dict(name=consts.CRIT_ROOT_TRANSFORM_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.CRIT_CONNECTORS_ATTR, isArray=True, type=api.kMFnMessageAttribute),
                dict(
                    name=consts.CRIT_SETTING_NODES_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_SETTING_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_SETTING_NAME_ATTR, type=api.kMFnDataString),
                    ]
                ),
                dict(
                    name=consts.CRIT_TAGGED_NODE_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_TAGGED_NODE_SOURCE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_SETTING_NAME_ATTR, type=api.kMFnDataString),
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

    def show(self, mod: api.OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
        """
        Sets the visibility for this node to 1.0.

        :param api.OpenMaya.MDGModifier or None mod: optional modifier to use to show this node.
        :param bool apply: whether to apply the operation immediately.
        :return: True if node was showed successfully; False otherwise.
        :rtype: bool
        """

        root = self.root_transform()
        if root:
            root.show(mod=mod, apply=apply)
            return True

        return False

    def hide(self, mod: api.OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:
        """
        Sets the visibility for this node to 0.0.

        :param OpenMaya.MDGModifier or None mod: optional modifier to use to hide this node.
        :param bool apply: whether to apply the operation immediately.
        :return: True if node was hidden successfully; False otherwise.
        :rtype: bool
        """

        root = self.root_transform()
        if root:
            root.hide(mod=mod, apply=apply)
            return True

        return False

    def root_transform(self) -> api.DagNode:
        """
        Returns the root transform node for this layer instance.

        :return: root transform instance.
        :rtype: api.DagNode
        """

        return self.sourceNodeByName(consts.CRIT_ROOT_TRANSFORM_ATTR)

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
        self.connect_to(consts.CRIT_ROOT_TRANSFORM_ATTR, layer_transform)
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

        for element in self.attribute(consts.CRIT_EXTRA_NODES_ATTR):
            source = element.source()
            if source:
                yield source.node()

    def add_extra_nodes(self, nodes: list[api.DGNode]):
        """
        Connects given nodes into this meta node instance as extra nodes.

        :param list[api.DGNode] nodes: nodes to add as extra node.
        """

        extras_array = self.attribute(consts.CRIT_EXTRA_NODES_ATTR)
        for node in nodes:
            if not node.object():
                continue
            element = extras_array.nextAvailableDestElementPlug()
            node.message.connect(element)

    def add_extra_node(self, node: api.DGNode):
        """
        Connects given node into this meta node instance as an extra node.

        :param api.DGNode node: node to add as extra node.
        """

        self.add_extra_nodes([node])

    def iterate_settings_nodes(self) -> Iterator[meta_nodes.SettingsNode]:
        """
        Generator function that iterates over all the attached settings nodes attached to this meta node instance.

        :return: iterated attached setting node instances.
        :rtype: Iterator[meta_nodes.SettingsNode]
        """

        settings_nodes_compound_attr = self.attribute(consts.CRIT_SETTING_NODES_ATTR)
        for element in settings_nodes_compound_attr:
            source_node = element.child(0).sourceNode()
            if source_node is not None:
                yield meta_nodes.SettingsNode(node=source_node.object())

    def setting_node(self, name: str) -> meta_nodes.SettingsNode | None:
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

    def create_settings_node(self, name: str, attr_name: str) -> meta_nodes.SettingsNode:
        """
        Creates a CRIT setting nodes and adds it to the meta node with given name nad value.

        :param str name: name for the new settings node.
        :param str attr_name: meta attribute name.
        :return: newly created settings node instance.
        :rtype: meta_nodes.SettingsNode
        """

        setting_node = self.setting_node(attr_name)
        if setting_node is not None:
            return setting_node

        setting_node = meta_nodes.SettingsNode()
        setting_node.create(name, id=attr_name)
        settings_nodes_attr = self.attribute(consts.CRIT_SETTING_NODES_ATTR)
        new_element = settings_nodes_attr.nextAvailableElementPlug()
        self.connect_to_by_plug(new_element.child(0), setting_node)
        new_element.child(1).set(attr_name)
        setting_node.lock(True)

        return setting_node


class CritComponentsLayer(CritLayer):

    ID = consts.COMPONENTS_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        """
        Overrides base meta_attributes function.
        Returns the list of default meta attributes that should be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: List[Dict]
        """

        attrs = super().meta_attributes()

        attrs.extend([
            {
                'name': 'componentGroups',
                'isArray': True,
                'locked': False,
                'type': api.kMFnDataString,
                'children': [
                    {
                        'name': 'groupName',
                        'type': api.kMFnDataString
                    },
                    {
                        'name': 'groupComponents',
                        'type': api.kMFnMessageAttribute,
                        'isArray': False,
                        'locked': False
                    }
                ]
            },
        ])

        return attrs

    def components(self, depth_limit: int = 256) -> list[CritComponent]:
        """
        Returns all components in order as a list.

        :param int depth_limit: recursive depth limit.
        :return: list of components linked to this layer.
        :rtype: list[CritComponent]
        """

        return list(self.iterate_components(depth_limit=depth_limit))

    def iterate_components(
            self, depth_limit: int = 256) -> Iterator[CritComponent]:
        """
        Generator function that iterates over all components linked to this layer.

        :param int depth_limit: recursive depth limit.
        :return: iterated components linked to this layer.
        :rtype: Iterator[CritComponent]
        """

        for meta_child in self.iterate_meta_children(depth_limit):
            if meta_child.hasAttribute(consts.CRIT_COMPONENT_TYPE_ATTR):
                yield meta_child


class CritGuideLayer(CritLayer):

    ID = consts.GUIDE_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        """
        Overrides base meta_attributes function.
        Returns the list of default meta attributes that should be added into the meta node during creation.

        :return: list of attributes data within a dictionary.
        :rtype: List(Dict)
        """

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.CRIT_GUIDES_ATTR, type=api.kMFnCompoundAttribute, isArray=True, locked=False,
                    children=[
                        dict(name=consts.CRIT_GUIDE_NODE_ATTR, type=api.kMFnMessageAttribute, isArray=False),
                        dict(name=consts.CRIT_GUIDE_ID_ATTR, type=api.kMFnDataString, isArray=False),
                        dict(name=consts.CRIT_GUIDE_SRTS_ATTR, type=api.kMFnMessageAttribute, isArray=True),
                        dict(name=consts.CRIT_GUIDE_SHAPE_NODE_ATTR, type=api.kMFnMessageAttribute, isArray=False),
                        dict(
                            name=consts.CRIT_GUIDE_SOURCE_GUIDES_ATTR, type=api.kMFnCompoundAttribute,
                            isArray=True,
                            children=[
                                dict(name=consts.CRIT_GUIDE_SOURCE_GUIDE_ATTR, type=api.kMFnMessageAttribute, isArray=False),
                                dict(name=consts.CRIT_GUIDE_SOURCE_GUIDE_CONSTRAINT_NODES_ATTR, type=api.kMFnMessageAttribute, isArray=True)
                            ]
                        ),
                        dict(name=consts.CRIT_GUIDE_MIRROR_ROTATION_ATTR, type=api.kMFnNumericBoolean),
                        dict(name=consts.CRIT_GUIDE_AUTO_ALIGN_ATTR, type=api.kMFnNumericBoolean),
                        dict(name=consts.CRIT_GUIDE_AIM_VECTOR_ATTR, type=api.kMFnNumeric3Float),
                        dict(name=consts.CRIT_GUIDE_UP_VECTOR_ATTR, type=api.kMFnNumeric3Float),
                    ]),
                dict(name=consts.CRIT_GUIDE_VISIBILITY_ATTR, type=api.kMFnNumericBoolean, default=True, value=True),
                dict(name=consts.CRIT_GUIDE_CONTROL_VISIBILITY_ATTR, type=api.kMFnNumericBoolean, default=False, value=False),
                dict(name=consts.CRIT_GUIDE_PIN_SETTINGS_ATTR, type=api.kMFnCompoundAttribute, children=[
                    dict(name=consts.CRIT_GUIDE_PIN_PINNED_ATTR, type=api.kMFnNumericBoolean),
                    dict(name=consts.CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR, type=api.kMFnDataString),
                ]),
                dict(name=consts.CRIT_GUIDE_LIVE_LINK_NODES_ATTR, type=api.kMFnMessageAttribute, isArray=True),
                dict(name=consts.CRIT_GUIDE_IS_LIVE_LINK_ACTIVE_ATTR, type=api.kMFnNumericBoolean, default=False, value=False),
                dict(name=consts.CRIT_GUIDE_CONNECTORS_GROUP_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.CRIT_GUIDE_DG_GRAPH_ATTR, type=api.kMFnCompoundAttribute, isArray=True, locked=False, children=[
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_ID_ATTR, type=api.kMFnDataString),
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_NAME_ATTR, type=api.kMFnDataString),
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_METADATA_ATTR, type=api.kMFnDataString),
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_INPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_OUTPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                    dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODES_ATTR, type=api.kMFnCompoundAttribute, isArray=True, children=[
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODE_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODE_ATTR, type=api.kMFnMessageAttribute),
                    ]),
                ]),
            )
        )

        return attrs

    @override(check_signature=False)
    def serializeFromScene(self):
        """
        Serializes current layer into a dictionary compatible with JSON.

        :return: JSON compatible dictionary.
        :rtype: dict
        """

        root = self.guide_root()
        dag = []
        if root:
            dag.append(
                root.serializeFromScene(extra_attributes_only=True, include_namespace=False, use_short_names=True))

        setting_nodes = []
        for setting_node in iter(self.iterate_settings_nodes()):
            setting_nodes.extend(setting_node.serializeFromScene())

        metadata = []
        for attr_name in (
                consts.CRIT_GUIDE_VISIBILITY_ATTR,
                consts.CRIT_GUIDE_CONTROL_VISIBILITY_ATTR,
                consts.CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR,
                consts.CRIT_GUIDE_PIN_PINNED_ATTR):
            metadata.append(self.attribute(attr_name).serializeFromScene())

        data = {
            consts.GUIDE_LAYER_DESCRIPTOR_KEY: {
                consts.DAG_DESCRIPTOR_KEY: dag,
                consts.SETTINGS_DESCRIPTOR_KEY: setting_nodes,
                consts.METADATA_DESCRIPTOR_KEY: metadata,
                consts.DG_DESCRIPTOR_KEY: []
            }
        }

        return data

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

        for guide in self.iterate_guides():
            guide.lock(False)

        return super().delete(mod=mod, apply=apply)

    def guide_root(self) -> meta_nodes.Guide | None:
        """
        Returns the guide which contains the expected root attribute as True.

        :return: root guide.
        :rtype: meta_nodes.Guide or None
        """

        if not self.exists() or not self.hasAttribute(consts.CRIT_GUIDES_ATTR):
            return None

        for element in self.iterate_guides_compound_attribute():
            is_root_flag = element.child(2)
            if not is_root_flag:
                continue
            source = element.child(0).sourceNode()
            if source is not None:
                return meta_nodes.Guide(source.object())

        return None

    def iterate_guides_compound_attribute(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over the attribute that links this layer meta node instance with the different
        guide nodes within current scene.

        :return: guide's compound attribute iterator.
        :rtype: Iterator[api.Plug]
        """

        guide_plug = self.attribute(consts.CRIT_GUIDES_ATTR)
        for i in range(guide_plug.evaluateNumElements()):
            yield guide_plug.elementByPhysicalIndex(i)

    def iterate_guides(self, include_root: bool = True) -> Iterator[meta_nodes.Guide]:
        """
        Generator function that iterates through the guides connected to this layer. The iteration is done based on the
        order the guides were added to the layer meta node instance.

        :param bool include_root: whether to include root guide.
        :return: generator of iterated guide instances.
        :rtype: Iterator[meta_nodes.Guide]
        """

        if not self.exists() or not self.hasAttribute(consts.CRIT_GUIDES_ATTR):
            return
        for element in self.iterate_guides_compound_attribute():
            guide_plug = element.child(0)
            source = guide_plug.sourceNode()
            if source is None:
                continue
            if not include_root and element.child(1).asString() == 'root':
                continue
            if meta_nodes.Guide.is_guide(source):
                yield meta_nodes.Guide(source.object())

    def guide(self, name: str) -> meta_nodes.Guide | None:
        """
        Returns the guide node instance with given attached to this layer.

        :param str name: short name of the guide to retrieve.
        :return: found guide with given name.
        :rtype: meta_nodes.Guide or None
        """

        if not self.exists():
            return None

        for found_guide in self.iterate_guides():
            if found_guide.id() == name:
                return found_guide

        return None

    def guide_count(self) -> int:
        """
        Returns the total amount of guides attached to this layer.

        :return: total amount of guides.
        :rtype: int
        """

        guide_plug = self.attribute(consts.CRIT_GUIDES_ATTR)
        return guide_plug.evaluateNumElements()

    def find_guides(self, *guide_ids: Iterable[str]) -> list[meta_nodes.Guide]:
        """
        Searches and returns guides with given IDs.

        :param Tuple[str] guide_ids: list of guide IDs to search for.
        :return: list of found guides.
        :rtype: list[meta_nodes.Guide]
        """

        if not self.exists():
            return []

        results: list[meta_nodes.Guide | None] = [None] * len(guide_ids)
        for found_guide in self.iterate_guides():
            guide_id = found_guide.id()
            if guide_id in guide_ids:
                results[guide_ids.index(guide_id)] = found_guide

        return results

    def are_guides_visible(self) -> bool:
        """
        Returns whether guides within this layer instance are visible.

        :return: True if guides are visible; False otherwise.
        :rtype: bool
        """

        return self.guideVisibiilty.value()

    def set_guides_visible(
            self, flag: bool, include_root: bool = True, mod: api.DGModifier | None = None,
            apply: bool = True) -> api.DGModifier:
        """
        Sets whether guides are visible.

        :param bool flag: True to make guides visible; False otherwise.
        :param bool include_root: whether to include root guide.
        :param api.DGModifier mod: optional modifier to use to set guides visibility.
        :param bool apply: whether to apply changes immediately.
        :return: modifier used to set guides visibility.
        :rtype: api.DGModifier
        """

        modifier = mod or api.DGModifier()
        connectors = self.iterate_connectors()
        for guide in self.iterate_guides(include_root=include_root):
            if guide.visibility.isLocked:
                continue
            guide.setVisible(flag, mod=modifier, apply=False)
        for connector in connectors:
            if connector.visibility.isLocked:
                continue
            connector.setVisible(flag, mod=modifier, apply=True)
        self.attribute(consts.CRIT_GUIDE_VISIBILITY_ATTR).set(flag, mod=modifier, apply=apply)
        if mod or apply:
            modifier.doIt()

        return modifier

    def are_guides_controls_visible(self) -> bool:
        """
        Returns whether guide controls within this layer instance are visible.

        :return: True if guides controls are visible; False otherwise.
        :rtype: bool
        """

        return self.attribute(consts.CRIT_GUIDE_CONTROL_VISIBILITY_ATTR).value()

    def set_guides_controls_visible(self, flag: bool, mod: api.DGModifier = None, apply: bool = True):
        """
        Sets whether guides controls are visible.

        :param bool flag: True to make guides visible; False otherwise.
        :param api.DGModifier mod: optional modifier to use to set guides visibility.
        :param bool apply: whether to apply changes immediately.
        """

        for guide in self.iterate_guides():
            shape = guide.shape_node()
            if shape is None:
                continue
            shape.setVisible(flag, mod=mod, apply=apply)
        self.attribute(consts.CRIT_GUIDE_CONTROL_VISIBILITY_ATTR).set(flag)

    def create_guide(self, **kwargs) -> meta_nodes.Guide:
        """
        Creates a new guide node into current scene and attaches it the guide layer.

        :keyword str id: guide unique identifier relative to the guide layer instance.
        :keyword str name: guide's name.
        :keyword list(float) translate: translate X, Y, Z in world space.
        :keyword list(float) rotate: rotation X, Y, Z in world space.
        :keyword list(float) scale: scale X, Y, Z in world space.
        :keyword int rotateOrder: rotate order using tp.maya.api.attributetypes.kConstant value.
        :keyword str or dict shape: if str then the shape name will be used, otherwise serialized shape will be used.
        :keyword dict locShape: BaseLoc attributes to set.
        :keyword list(float) color: shape color to use.
        :keyword dict shapeTransform: shape pivot transform.
        :keyword dict shapeTransform: shape pivot transform.
        :keyword str or tp.maya.api.DagNode parent: optional guide parent.
        :keyword bool root: whether this guide is the root guide of the component.
        :keyword list(float) or api.Matrix worldMatrix: world matrix for the guide, which takes priority over the
            local transform.
        :keyword list(float) or api.Matrix matrix: local matrix for the guide.
        :keyword list(dict): list of SRTS transforms data to create.
        :keyword bool selectionChildHighlighting: whether to enable selection child highlighting feature.
        :keyword bool requiresPivotShape: sets whether pivot display is required.
        :keyword int pivotShape: index to set for the guide (0: ball; 1: pyramid; 2: pivot).
        :keyword list(float) pivotColor: guide pivot color.
        :keyword list(dict) attributes: list contaiing the extra attributes to create for the guide.
        :return:
        """

        parent = kwargs.get('parent')
        parent = self.root_transform() if parent is None else self.guide(parent)
        kwargs['parent'] = parent

        new_guide = meta_nodes.Guide()
        new_guide.create(**kwargs)
        self.add_child_guide(new_guide)
        guide_plug = self.guide_plug_by_id(kwargs.get('id', ''))
        if guide_plug is None:
            return new_guide

        srt_plug = guide_plug.child(2)
        new_guide.set_shape_parent(self.root_transform())
        parent_node = new_guide.parent() or self.root_transform()
        srts = kwargs.get('srts', list())
        for srt in srts:
            if parent_node is not None:
                parent_node = parent_node.object()
            new_srt = api.DagNode(om_nodes.deserialize_node(srt, parent=parent_node)[0])
            parent_node = new_srt
            srt_element = srt_plug.nextAvailableDestElementPlug()
            new_srt.message.connect(srt_element)

        new_guide.setParent(parent_node, use_srt=False)

        return new_guide

    def add_child_guide(self, guide: meta_nodes.Guide):
        """
        Attaches given guide node to this layer.

        :param meta_nodes.Guide guide: guide to attach to this layer.
        :raises ValueError: if given node is not a valid DagNode instance.
        """

        if not isinstance(guide, api.DagNode):
            raise ValueError('Child node must be a DagNode instance')

        self._add_guide_to_meta(guide)

    def guide_plug_by_id(self, guide_id: str) -> api.Plug | None:
        """
        Returns the guide node instance with given attached to this layer with given ID.

        :param str guide_id: guide's name.
        :return: found guide plug with given name attached to this layer.
        :rtype: api.Plug or None
        """

        for element in self.iterate_guides_compound_attribute():
            id_plug = element.child(1)
            if id_plug.asString() == guide_id:
                return element

        return None

    def guide_node_plug_by_id(self, guide_id: str) -> api.Plug | None:
        """
        Returns the guide node instance with given attached to this layer with given ID.

        :param str guide_id: guide's name.
        :return: found node guide plug attached to this layer.
        :rtype: api.Plug or None
        """

        guide_element_plug = self.guide_plug_by_id(guide_id)
        if not guide_element_plug:
            return None

        return guide_element_plug.child(0)

    def source_guide_by_id(self, guide_id: str, source_index: int) -> meta_nodes.Guide | None:
        """
        Returns source guide from given ID.

        :param str guide_id: guide's name.
        :param source_index: source index.
        :return: meta_nodes.Guide or None
        """

        guide_element_plug = self.guide_plug_by_id(guide_id)
        if not guide_element_plug:
            return None

        return guide_element_plug.child(4)[source_index]

    def duplicate_guide(self, guide: meta_nodes.Guide, name: str, guide_id: str, parent: meta_nodes.Guide | None):
        """
        Duplicates given guide.

        :param meta_nodes.Guide guide: guide to duplicate.
        :param str name: name of the duplicated guide.
        :param guide_id: ID of the duplicated guide.
        :param meta_nodes.Guide or None parent: optional guide parent.
        :return: duplicated guide.
        :rtype: meta_nodes.Guide
        """

        guide_data = guide.serializeFromScene()
        guide_data['parent'] = parent or guide
        guide_data['name'] = name
        guide_data['id'] = guide_id
        duplicated_guide = self.create_guide(**guide_data)

        return duplicated_guide

    @api.lock_node_context
    def delete_guides(self, *guide_ids: tuple):
        """
        Deletes all guides from the layer.

        :param tuple[str] guide_ids: list of guide IDs to delete.
        """

        if not self.exists() or not self.hasAttribute(consts.CRIT_GUIDES_ATTR):
            return

        for element in self.iterate_guides_compound_attribute():
            guide_plug = element.child(0)
            source = guide_plug.sourceNode()
            if source is None or not meta_nodes.Guide.is_guide(source):
                continue
            guide = meta_nodes.Guide(source.object())
            if guide_ids and guide.id() not in guide_ids:
                continue
            connectors = set()
            for destination in guide.message.destinations():
                if destination.partialName().startswith('critConn'):
                    connectors.add(destination.node())
                    break
            for connector in connectors:
                connector.delete()
            guide.delete()
            element.delete()

    def guide_settings(self) -> meta_nodes.SettingsNode:
        """
        Returns guide settings node

        :return: guide settings node instance.
        :rtype: meta_nodes.SettingsNode
        """

        return self.setting_node(consts.GUIDE_LAYER_TYPE)

    def create_connector(
            self, name: str, start_guide: meta_nodes.Guide, end_guide: meta_nodes.Guide,
            attribute_holder: api.Plug | None = None, size: float = 1.0, color: tuple[float, float, float] = (0, 1, 1),
            parent: api.DagNode | None = None) -> meta_nodes.Connector:
        """
        Creates a new connector that visually connectors the given start and end guides.

        :param str name: name of the connector node.
        :param meta_nodes.Guide start_guide: start guide instance.
        :param meta_nodes.Guide end_guide: end guide instance, connector will point to this guide.
        :param api.Plug or None attribute_holder: optional plug that will have the connector connected to by a message.
        :param float size: size of the connector.
        :param tuple[float, float, float] color: color of the connector.
        :param api.DagNode or None parent: optional connector node parent.
        :return: newly created connector instance.
        :rtype: meta_nodes.Connector
        """

        existing_connector = self.connector(start_guide, end_guide)
        if existing_connector:
            return existing_connector

        new_connector = meta_nodes.Connector()
        new_connector.create(
            name, start_guide, end_guide, attribute_holder=attribute_holder, color=color, size=size, parent=parent)
        connectors_array = self.attribute(consts.CRIT_CONNECTORS_ATTR)
        new_connector.message.connect(connectors_array.nextAvailableDestElementPlug())
        if start_guide.isHidden() or end_guide.isHidden():
            new_connector.hide()
            new_connector.setLockStateOnAttributes(['visibility'], state=True)

        return new_connector

    def connector(self, start_guide: meta_nodes.Guide, end_guide: meta_nodes.Guide) -> meta_nodes.Connector | None:
        """
        Returns connector instance that connect given start and end guides.

        :param meta_nodes.Guide start_guide: start guide instance.
        :param end_guide: end guide instance.
        :return: found connector that connect both guides.
        :rtype: meta_nodes.Connector or None
        """

        found_connector = None
        for _connector in self.iterate_connectors():
            start = _connector.start_guide()
            end = _connector.end_guide()
            if start == start_guide and end == end_guide:
                found_connector = _connector
                break

        return found_connector

    def iterate_connectors(self) -> Iterator[meta_nodes.Connector]:
        """
        Generator function that iterates over all connector nodes linked to this layer.

        :return: iterated connectors.
        :rtype: Iterator[meta_nodes.Connector]
        """

        attr = self.attribute(consts.CRIT_CONNECTORS_ATTR)
        for connector in attr or []:
            source_connector = connector.sourceNode()
            if source_connector:
                yield meta_nodes.Connector(source_connector.object())

    def is_pinned(self) -> bool:
        """
        Returns whether guides attached to this layer are pinned.

        :return: True if guides are pinned; False otherwise.
        :rtype: bool
        """

        return self.attribute(consts.CRIT_GUIDE_PIN_PINNED_ATTR).value() if self.exists() else False

    def align_guides(self):
        """
        Aligns all guides attached to this layer instance.
        """

        guides = list(self.iterate_guides(include_root=False))
        if not guides:
            return

        matrices = list()
        align_guides = list()
        new_transforms = dict()
        for guide in guides:
            aim_state = guide.attribute(consts.CRIT_AUTO_ALIGN_ATTR).asBool()
            if not aim_state:
                continue
            up_vector = guide.attribute(consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR).value()
            aim_vector = guide.attribute(consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR).value()
            child = None																# type: meta_nodes.Guide or None
            for child in guide.iterate_child_guides(recursive=False):
                break
            if child is None:
                print('1')
                parent_guide, _ = guide.guide_parent()
                parent_matrix = new_transforms.get(parent_guide.id(), guide.worldMatrix())
                transform_matrix = api.TransformationMatrix(parent_matrix)
                transform_matrix.setTranslation(guide.translation(api.kWorldSpace), api.kWorldSpace)
                transform_matrix.setScale(guide.scale(api.kWorldSpace), api.kWorldSpace)
                matrix = transform_matrix.asMatrix()
            else:
                print('2')
                transform_matrix = guide.transformationMatrix()
                rotation = om_mathlib.look_at(
                    guide.translation(), child.translation(), api.Vector(aim_vector), api.Vector(up_vector))
                transform_matrix.setRotation(rotation)
                matrix = transform_matrix.asMatrix()
            new_transforms[guide.id()] = matrix
            matrices.append(matrix)
            align_guides.append(guide)

        if align_guides and matrices:
            meta_nodes.Guide.set_guides_world_matrix(align_guides, matrices)

    def is_live_link(self) -> bool:
        """
        Returns whether current layer is set to be linked to the live guiding system.

        :return: True if live link is enabled; False otherwise.
        :rtype: bool
        """

        return self.attribute(consts.CRIT_GUIDE_IS_LIVE_LINK_ACTIVE_ATTR).asBool()

    def set_live_link(self, offset_node: meta_nodes.SettingsNode, state: bool = True):
        """
        Live link the guides on the current guide layer to the given offset node.

        :param meta_nodes.SettingsNode offset_node: input guide offset node which contains the local matrices.
        :param flag state: if True, then the joints will be connected to the bindPreMatrix and the offset node matrices
            will be connected to the local transform of the joint.
        ..info:: this system works by directly connecting the worldInverseMatrix plug to the skin clusters bindPreMatrix.
            By doing this, we allow all the joint transforms without effect the skin.
        """

        current_state = self.is_live_link()
        if state == current_state:
            return

        metadata_attr = self.attribute(consts.CRIT_GUIDE_LIVE_LINK_NODES_ATTR)

        for source, dest in offset_node.iterateConnections(source=False, destination=True):
            if plugs.plug_type(dest.plug()) == api.attributetypes.kMFnDataMatrix:
                dest.disconnect(source)

        source_nodes_to_delete = list()
        for element in metadata_attr:
            source = element.sourceNode()
            if source is not None:
                source_nodes_to_delete.append(source.fullPathName())
        if source_nodes_to_delete:
            cmds.delete(source_nodes_to_delete)

        self.attribute(consts.CRIT_GUIDE_IS_LIVE_LINK_ACTIVE_ATTR).set(state)
        if not state:
            return

        transform_array = offset_node.attribute(consts.CRIT_GUIDE_OFFSET_TRANSFORMS_ATTR)
        transform_elements = {i.child(0).asString(): i for i in transform_array}
        for guide in self.iterate_guides():
            guide_transform_plug = transform_elements[guide.id()]
            local_matrix_plug = guide_transform_plug.child(1)
            world_matrix_plug = guide_transform_plug.child(2)
            parent_matrix_plug = guide_transform_plug.child(3)
            parent_guide, parent_id = guide.guide_parent()
            metadata_plug = metadata_attr.nextAvailableDestElementPlug()
            metadata_index = metadata_plug.logicalIndex()
            guide.attribute('worldMatrix')[0].connect(world_matrix_plug)
            if parent_id is None:
                local_matrix = guide.attribute('matrix')
            else:
                pick_mat_dest = parent_guide
                if parent_id == 'root':
                    pick_mat_dest = parent_guide.srt()
                guide.attribute('parentMatrix')[0].connect(parent_matrix_plug)
                live_mult = api.factory.create_dg_node('_'.join([parent_guide.name(), 'liveGuideMult']), 'multMatrix')
                world_matrix = guide.attribute('worldMatrix')[0]
                world_inverse_matrix = pick_mat_dest.attribute('worldInverseMatrix')[0]
                pick_matrix = api.factory.create_dg_node('_'.join([parent_guide.name(), 'pickScale']), 'pickMatrix')
                pick_matrix.useTranslate = False
                pick_matrix.useRotate = False
                pick_matrix.useScale = False
                world_matrix.connect(live_mult.matrixIn[0])
                world_inverse_matrix.connect(live_mult.matrixIn[1])
                pick_matrix.outputMatrix.connect(live_mult.matrixIn[2])
                local_matrix = live_mult.matrixSum
                live_mult.message.connect(metadata_plug)
                pick_matrix.message.connect(metadata_attr[metadata_index + 1])
                pick_mat_dest.attribute('worldMatrix')[0].connect(pick_matrix.inputMatrix)

            local_matrix.connect(local_matrix_plug)

    def _add_guide_to_meta(self, guide: meta_nodes.Guide) -> api.Plug:
        """
        Internal function that adds given guide into the meta node attributes.

        :param meta_nodes.Guide guide: guide to attach to this layer.
        :return: guide's compound plug.
        :rtype: api.Plug
        """

        guides_compound_attribute = self.attribute(consts.CRIT_GUIDES_ATTR)
        is_locked_attribute = guides_compound_attribute.isLocked
        guides_compound_attribute.isLocked = False
        element = guides_compound_attribute.nextAvailableDestElementPlug()
        guide.message.connect(element.child(0))
        element.child(1).set(guide.id())
        shape_node = guide.shape_node()
        if shape_node is not None:
            shape_node.message.connect(element.child(3))
        element.child(5).setAsProxy(guide.attribute(consts.CRIT_MIRROR_ATTR))
        element.child(6).setAsProxy(guide.attribute(consts.CRIT_AUTO_ALIGN_ATTR))
        element.child(7).setAsProxy(guide.attribute(consts.CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR))
        element.child(8).setAsProxy(guide.attribute(consts.CRIT_AUTO_ALIGN_UP_VECTOR_ATTR))
        guides_compound_attribute.isLocked = is_locked_attribute

        return guides_compound_attribute

    def _serialize_graphs(self) -> list[dict]:
        """
        Internal function that serializes network nodes connected to this layer.

        :return: serialized nodes JSON compatible dictionaries.
        :rtype: list(dict)
        """

        graphs = []
        for graph_element in self.attribute(consts.CRIT_GUIDE_DG_GRAPH_ATTR):
            graph_id = graph_element.child(self.DG_GRAPH_ID_INDEX).value()
            node_data = []
            for node_element in graph_element.child(self.DG_GRAPH_NODES_INDEX):
                node_id = node_element.child(self.DG_GRAPH_NODE_ID_INDEX).value()
                node = node_element.child(self.DG_GRAPH_NODE_INDEX).sourceNode()
                if node is None:
                    continue
                data = node.serializeFromScene(include_connections=True)
                node_data.append({'id': node_id, 'data': data})
            graphs.append({'id': graph_id, 'nodes': node_data})

        return graphs


class CritInputLayer(CritLayer):

    ID = consts.INPUT_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.CRIT_INPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_INPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_INPUT_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_IS_INPUT_ROOT_ATTR, type=api.kMFnNumericBoolean),
                        dict(
                            name=consts.CRIT_SOURCE_INPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                            children=[
                                dict(name=consts.CRIT_SOURCE_INPUT_ATTR, type=api.kMFnMessageAttribute),
                                dict(
                                    name=consts.CRIT_SOURCE_INPUT_CONSTRAINT_NODES_ATTR,
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
                consts.SETTINGS_DESCRIPTOR_KEY: map(plugs.serialize_plug, self.root_transform().iterateExtraAttributes()),
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
        except errors.CritInvalidInputNodeMetaData:
            return False

    def input_plug_by_id(self, input_id: str) -> api.Plug | None:
        """
        Returns the input plug instance for the input node with given ID.

        :param str input_id: ID of the input node plug to retrieve.
        :return: found plug instance with given ID.
        :rtype: api.Plug or None
        """

        input_plug = self.attribute(consts.CRIT_INPUTS_ATTR)
        found_plug = None
        for element in input_plug:
            if element.child(1).asString() == input_id:
                found_plug = element
                break

        return found_plug

    def input_node(self, name: str) -> meta_nodes.InputNode | None:
        """
        Returns input node with given name attached to this layer instance.

        :param str name: name of the input node to get.
        :return: input node instance.
        :rtype: meta_nodes.InputNode or None
        """

        element = self.input_plug_by_id(name)
        if element is None:
            return None

        source = element.child(0).source()
        if not source:
            raise errors.CritInvalidInputNodeMetaData('-'.join([name, element.child(1).asString()]))

        return meta_nodes.InputNode(source.node().object())

    def root_input_plug(self) -> api.Plug | None:
        """
        Returns the plug where root input is connected to.

        :return: root input plug.
        :rtype: api.Plug or None
        """

        found_root_plug = None
        for element in self.attribute(consts.CRIT_INPUTS_ATTR):
            is_root = element.child(2).value()
            if not is_root:
                continue
            found_root_plug = element
            break

        return found_root_plug

    def root_input(self) -> meta_nodes.InputNode | None:
        """
        Returns the root input node.

        :return: root input node.
        :rtype: meta_nodes.InputNode or None
        """

        root_input_plug = self.root_input_plug()
        if root_input_plug is None:
            return None

        return meta_nodes.InputNode(root_input_plug.child(0).sourceNode().object())

    def iterate_root_inputs(self) -> Iterator[meta_nodes.InputNode]:
        """
        Generator function that iterates over all root input nodes within this layer.

        :return: iterated root input nodes.
        :rtype: Iterator[meta_nodes.InputNode]
        """

        for input_node in self.iterate_inputs():
            if input_node.is_root():
                yield input_node

    def iterate_inputs(self) -> Iterator[meta_nodes.InputNode]:
        """
        Generator function that iterates over all input nodes within this layer.

        :return: iterated input nodes.
        :rtype: Iterator[meta_nodes.InputNode]
        """

        input_plug = self.attribute(consts.CRIT_INPUTS_ATTR)
        for element in input_plug:
            source = element.child(0).source()
            if source is not None:
                yield meta_nodes.InputNode(source.node().object())

    def find_inputs(self, *ids: Iterable[str]) -> list[meta_nodes.InputNode | None]:
        """
        Searches and returns input nodes with given IDs.

        :param Tuple[str] ids: list of input node IDs to search for.
        :return: list of found input nodes.
        :rtype: list[meta_nodes.InputNode]
        """

        valid_inputs: list[meta_nodes.InputNode | None] = [None] * len(ids)
        for element in self.attribute(consts.CRIT_INPUTS_ATTR):
            input_id = element.child(1).asString()
            if input_id not in ids:
                continue
            source = element.child(0).source()
            if source:
                valid_inputs[ids.index(input_id)] = meta_nodes.InputNode(source.node().object())

        return valid_inputs

    def create_input(self, name: str, **kwargs: dict) -> meta_nodes.InputNode:
        """
        Creates a new input node with given name and given attributes.

        :param str name: input node name.
        :param dict kwargs: input node attributes.
        :return: newly created input node.
        :rtype: meta_nodes.InputNode
        """

        assert not self.has_input(name)
        new_input_node = meta_nodes.InputNode()
        new_input_node.create(name=name, **kwargs)
        new_input_node.setParent(self.root_transform(), True)
        self.add_input_node(new_input_node, as_root=kwargs.get('root', False))

        return new_input_node

    def add_input_node(self, input_node: meta_nodes.InputNode, as_root: bool = False):
        """
        Attaches given input node into this layer meta node instance.

        :param meta_nodes.InputNode input_node: input node instance.
        :param bool as_root: whether input node is a root one.
        """

        input_plug = self.attribute(consts.CRIT_INPUTS_ATTR)
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

        input_array = self.attribute(consts.CRIT_INPUTS_ATTR)
        root_transform = self.root_transform()
        mod = api.DGModifier()
        for element in input_array:
            source = element.child(0).sourceNode()
            if source is not None and source.parent() == root_transform:
                source.delete(mod=mod, apply=False)
        mod.doIt()
        input_array.deleteElements(mod=mod, apply=True)

        return mod


class CritOutputLayer(CritLayer):

    ID = consts.OUTPUT_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:

        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.CRIT_OUTPUTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_OUTPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_OUTPUT_ID_ATTR, type=api.kMFnDataString),
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
        except errors.CritInvalidOutputNodeMetaData:
            return False

    def output_plug_by_id(self, output_id: str) -> api.Plug | None:
        """
        Returns the output plug instance for the output node with given ID.

        :param str output_id: ID of the output node plug to retrieve.
        :return: found plug instance with given ID.
        :rtype: api.Plug or None
        """

        output_plug = self.attribute(consts.CRIT_OUTPUTS_ATTR)
        found_plug = None
        for element in output_plug:
            if element.child(1).asString() == output_id:
                found_plug = element
                break

        return found_plug

    def output_node(self, name: str) -> meta_nodes.OutputNode | None:
        """
        Returns output node with given name attached to this layer instance.

        :param str name: name of the output node to get.
        :return: output node instance.
        :rtype: meta_nodes.OutputNode or None
        """

        element = self.output_plug_by_id(name)
        if element is None:
            return None

        source = element.child(0).source()
        if not source:
            raise errors.CritInvalidOutputNodeMetaData('-'.join([name, element.child(1).asString()]))

        return meta_nodes.OutputNode(source.node().object())

    def iterate_outputs(self) -> Iterator[meta_nodes.OutputNode]:
        """
        Generator function that iterates over all output nodes within this layer.

        :return: iterated output nodes.
        :rtype: Iterator[meta_nodes.OutputNode]
        """

        output_plug = self.attribute(consts.CRIT_OUTPUTS_ATTR)
        for element in output_plug:
            source = element.child(0).source()
            if source is not None:
                yield meta_nodes.OutputNode(source.node().object())

    def create_output(self, name: str, **kwargs: dict) -> meta_nodes.OutputNode:
        """
        Creates a new output node with given name and given attributes.

        :param str name: output node name.
        :param dict kwargs: output node attributes.
        :return: newly created output node.
        :rtype: meta_nodes.OutputNode
        """

        assert not self.has_output(name)
        new_output_node = meta_nodes.OutputNode()
        new_output_node.create(name=name, **kwargs)
        new_output_node.setParent(self.root_transform(), True)
        self.add_output_node(new_output_node)

        return new_output_node

    def add_output_node(self, output_node: meta_nodes.OutputNode):
        """
        Attaches given output node into this layer meta node instance.

        :param meta_nodes.OutputNode output_node: output node instance.
        """

        output_plug = self.attribute(consts.CRIT_OUTPUTS_ATTR)
        next_element = output_plug.nextAvailableDestElementPlug()
        output_node.message.connect(next_element.child(0))
        next_element.child(1).setString(output_node.id())

    def find_output_nodes(self, *ids: tuple[str]) -> list[meta_nodes.OutputNode | None]:
        """
        Returns the output node instances from given IDs.

        :param tuple[str] ids: IDs to find output nodes of.
        :return: list containing the found output nodes.
        :rtype: list[meta_nodes.OutputNode or None]
        """

        found_outputs: list[meta_nodes.OutputNode | None] = [None] * len(ids)
        output_plug = self.attribute(consts.CRIT_OUTPUTS_ATTR)
        for element in output_plug:
            output_id = element.child(1).asString()
            if output_id not in ids:
                continue
            source = element.child(0).source()
            if not source:
                continue
            found_outputs[ids.index(output_id)] = meta_nodes.OutputNode(source.node().object())

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

        output_array = self.attribute(consts.CRIT_OUTPUTS_ATTR)
        root_transform = self.root_transform()
        mod = api.DGModifier()
        for element in output_array:
            source = element.child(0).sourceNode()
            if source is not None and source.parent() == root_transform:
                source.delete(mod=mod, apply=False)
        mod.doIt()
        output_array.deleteElements(mod=mod, apply=True)

        return mod


class CritSkeletonLayer(CritLayer):

    ID = consts.SKELETON_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.CRIT_JOINTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_JOINT_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_JOINT_ID_ATTR, type=api.kMFnDataString)
                    ]
                ),
                dict(
                    name=consts.CRIT_REGIONS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_REGION_NAME_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_REGION_SIDE_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_REGION_START_JOINT_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_REGION_END_JOINT_ID_ATTR, type=api.kMFnDataString)
                    ]
                ),
                dict(name=consts.CRIT_JOINT_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.CRIT_GUIDE_LIVE_LINK_NODES_ATTR, type=api.kMFnMessageAttribute, isArray=True),
                dict(name=consts.CRIT_GUIDE_IS_LIVE_LINK_ACTIVE_ATTR, type=api.kMFnNumericBoolean),
            )
        )

        return attrs

    @override
    def serializeFromScene(self) -> dict:

        return {}

    @override(check_signature=False)
    def delete(self, mod: api.OpenMaya.MDGModifier | None = None, apply: bool = True, delete_joints: bool = True) -> bool:
        if not delete_joints:
            return super().delete(mod=mod, apply=apply)

        joints = self.joints()
        success = super().delete(mod=mod, apply=apply)
        for joint in joints:
            joint.delete(mod, apply=apply)

        return success

    def selection_set(self) -> api.ObjectSet | None:
        """
        Returns the selection set attached to this layer.

        :return: selection set instance.
        :rtype: api.ObjectSet or None
        """

        return self.sourceNodeByName(consts.CRIT_JOINT_SELECTION_SET_ATTR)

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
        self.connect_to(consts.CRIT_JOINT_SELECTION_SET_ATTR, object_set)

        return object_set

    def iterate_joint_plugs(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over all joint plugs.

        :return: iterated joint plugs.
        :rtype: Iterator[api.Plug]
        """

        for i in self.attribute(consts.CRIT_JOINTS_ATTR):
            yield i

    def iterate_joints(self) -> Iterator[meta_nodes.Joint]:
        """
        Generator function that iterates over all deform skeleton joints.

        :return: iterated deform skeleton joints.
        :rtype: Iterator[meta_nodes.Joint]
        """

        for i in self.iterate_joint_plugs():
            source = i.child(0).source()
            if source:
                yield meta_nodes.Joint(source.node().object())

    def joints(self) -> list[meta_nodes.Joint]:
        """
        Returns all the joints that are under this layer in order of the DAG.

        :return: list of DAG ordered joints.
        :rtype: list[meta_nodes.Joint]
        """

        found_joints = []
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            source = joint_plug.source()
            if not source:
                continue
            found_joints.append(meta_nodes.Joint(source.node().object()))

        return found_joints

    def iterate_root_joints(self) -> Iterator[meta_nodes.Joint]:
        """
        Generator function that iterates over all deform root skeleton joints.

        :return: iterated root deform skeleton joints.
        :rtype: Iterator[meta_nodes.Joint]
        """

        current_joints = self.joints()
        for joint in current_joints:
            parent = joint.parent()
            if parent is None or parent not in current_joints:
                yield joint

    def joint(self, name: str) -> meta_nodes.Joint | None:
        """
        Return joint with given ID.

        :param str name: ID of the joint to retrieve.
        :return: joint found with given ID.
        :rtype: meta_nodes.Joint or None
        """

        found_joint = None
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == name:
                source = joint_plug.source()
                if not source:
                    return None
                found_joint = meta_nodes.Joint(source.node().object())
                break

        return found_joint

    def find_joints(self, *ids: tuple[str]) -> list[meta_nodes.Joint | None]:
        """
        Returns the joint node instances from given IDs.

        :param tuple[str] ids: IDs to find joint nodes of.
        :return: list containing the found joint nodes.
        :rtype: list[meta_nodes.Joint or None]
        """

        found_joints: list[meta_nodes.Joint | None] = [None] * len(ids)
        for joint in self.iterate_joints():
            current_id = joint.attribute(consts.CRIT_ID_ATTR).value()
            if current_id in ids:
                found_joints[ids.index(current_id)] = joint

        return found_joints

    def create_joint(self, **kwargs) -> meta_nodes.Joint:
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
        :rtype: meta_nodes.Joint
        """

        new_joint = meta_nodes.Joint()
        new_joint.create(
            id=kwargs.get('id', ''),
            name=kwargs.get('name', 'NO_NAME'),
            translate=kwargs.get('translate', (0.0, 0.0, 0.0)),
            rotate=kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)),
            rotateOrder=kwargs.get('rotateOrder', 0),
            parent=kwargs.get('parent', None))
        self.add_joint(new_joint, kwargs.get('id', ''))

        return new_joint

    def add_joint(self, joint: meta_nodes.Joint, joint_id: str | None = None):
        """
        Attaches given joint to this layer with given ID.

        :param meta_nodes.Joint joint: joint instance to attach to this layer instance.
        :param str or None joint_id: joint ID.
        """

        joints_attr = self.attribute(consts.CRIT_JOINTS_ATTR)
        joints_attr.isLocked = False
        element = joints_attr.nextAvailableDestElementPlug()
        joint.message.connect(element.child(0))
        if not joint.hasAttribute(consts.CRIT_ID_ATTR):
            joint.addAttribute(name=consts.CRIT_ID_ATTR, type=api.kMFnDataString, default='', value=joint_id)
        else:
            joint_id = joint.attribute(consts.CRIT_ID_ATTR).value()
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

        regions_attr = self.attribute(consts.CRIT_REGIONS_ATTR)
        regions_attr.isLocked = False
        element = regions_attr.nextAvailableDestElementPlug()
        element.child(0).set(name)
        element.child(1).set(side)
        element.child(2).set(start_joint_id)
        element.child(3).set(end_joint_id)


class CritRigLayer(CritLayer):

    ID = consts.RIG_LAYER_TYPE

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(
                    name=consts.CRIT_JOINTS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_JOINT_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_JOINT_ID_ATTR, type=api.kMFnDataString),
                    ]
                ),
                dict(
                    name=consts.CRIT_CONTROLS_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_CONTROL_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_CONTROL_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_CONTROL_SRTS_ATR, type=api.kMFnMessageAttribute, isArray=True)
                    ]
                ),
                dict(
                    name=consts.CRIT_SPACE_SWITCHING_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    children=[
                        dict(name=consts.CRIT_SPACE_SWITCH_CONTROL_NAME_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_SPACE_SWITCH_DRIVEN_NODE_ATTR, type=api.kMFnMessageAttribute),
                    ]
                ),
                dict(name=consts.CRIT_CONTROL_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute),
                dict(
                    name=consts.CRIT_GUIDE_DG_GRAPH_ATTR, type=api.kMFnCompoundAttribute, isArray=True,
                    locked=False, children=[
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_ID_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_NAME_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_METADATA_ATTR, type=api.kMFnDataString),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_INPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_OUTPUT_NODE_ATTR, type=api.kMFnMessageAttribute),
                        dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODES_ATTR, type=api.kMFnCompoundAttribute, isArray=True, children=[
                            dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODE_ID_ATTR, type=api.kMFnDataString),
                            dict(name=consts.CRIT_GUIDE_DG_GRAPH_NODE_ATTR, type=api.kMFnMessageAttribute),
                        ]),
                    ]),
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

    def control_panel(self) -> meta_nodes.SettingsNode:
        """
        Returns the control panel settings node.

        :return: control panel settings node.
        :rtype: meta_nodes.SettingsNode
        """

        return self.setting_node(consts.CONTROL_PANEL_TYPE)

    def selection_set(self) -> api.ObjectSet | None:
        """
        Returns rig layer controls selection set.

        :return: controls selection set.
        :rtype: api.ObjectSet or None
        """

        return self.sourceNodeByName(consts.CRIT_CONTROL_SELECTION_SET_ATTR)

    def create_selection_set(self, name: str, parent: api.ObjectSet | None = None):
        """
        Creates rig layer controls selection set if it does not exist.

        :param str name: selection set name.
        :param api.ObjectSet or None parent: optional parent selection set.
        :return: newly created selection set.
        :rtype: api.ObjectSet
        """

        existing_set = self.sourceNodeByName(consts.CRIT_CONTROL_SELECTION_SET_ATTR)
        if existing_set is not None:
            return existing_set

        object_set = api.factory.create_dg_node(name, 'objectSet')
        if parent is not None:
            parent.addMember(object_set)
        self.connect_to(consts.CRIT_CONTROL_SELECTION_SET_ATTR, object_set)

        return object_set

    def iterate_joint_plugs(self) -> Iterator[api.Plug]:
        """
        Generator function that iterates over all joint plugs.

        :return: iterated joint plugs.
        :rtype: Iterator[api.Plug]
        """

        for i in self.attribute(consts.CRIT_JOINTS_ATTR):
            yield i

    def iterate_joints(self) -> Iterator[meta_nodes.Joint]:
        """
        Generator function that iterates over all deform skeleton joints.

        :return: iterated deform skeleton joints.
        :rtype: Iterator[meta_nodes.Joint]
        """

        for i in self.iterate_joint_plugs():
            source = i.child(0).source()
            if source:
                yield meta_nodes.Joint(source.node().object())

    def joints(self) -> list[meta_nodes.Joint]:
        """
        Returns all the joints that are under this layer in order of the DAG.

        :return: list of DAG ordered joints.
        :rtype: list[meta_nodes.Joint]
        """

        found_joints: list[meta_nodes.Joint] = []
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            source = joint_plug.source()
            if not source:
                continue
            found_joints.append(meta_nodes.Joint(source.node().object()))

        return found_joints

    def iterate_root_joints(self) -> Iterator[meta_nodes.Joint]:
        """
        Generator function that iterates over all deform root skeleton joints.

        :return: iterated root deform skeleton joints.
        :rtype: Iterator[meta_nodes.Joint]
        """

        current_joints = self.joints()
        for joint in current_joints:
            parent = joint.parent()
            if parent is None or parent not in current_joints:
                yield joint

    def joint(self, name: str) -> meta_nodes.Joint | None:
        """
        Return joint with given ID.

        :param str name: ID of the joint to retrieve.
        :return: joint found with given ID.
        :rtype: meta_nodes.Joint or None
        """

        found_joint = None
        for element in self.iterate_joint_plugs():
            joint_plug = element.child(0)
            id_plug = element.child(1)
            if id_plug.asString() == name:
                source = joint_plug.source()
                if not source:
                    return None
                found_joint = meta_nodes.Joint(source.node().object())
                break

        return found_joint

    def find_joints(self, *ids: tuple[str]) -> list[meta_nodes.Joint | None]:
        """
        Returns the joint node instances from given IDs.

        :param tuple[str] ids: IDs to find joint nodes of.
        :return: list containing the found joint nodes.
        :rtype: list[meta_nodes.Joint or None]
        """

        found_joints: list[meta_nodes.Joint | None] = [None] * len(ids)
        for joint in self.iterate_joints():
            current_id = joint.attribute(consts.CRIT_ID_ATTR).value()
            if current_id in ids:
                found_joints[ids.index(current_id)] = joint

        return found_joints

    def create_joint(self, **kwargs) -> meta_nodes.Joint:
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
        :rtype: meta_nodes.Joint
        """

        new_joint = meta_nodes.Joint()
        new_joint.create(
            id=kwargs.get('id', ''),
            name=kwargs.get('name', 'NO_NAME'),
            translate=kwargs.get('translate', (0.0, 0.0, 0.0)),
            rotate=kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)),
            rotateOrder=kwargs.get('rotateOrder', 0),
            parent=kwargs.get('parent', None))
        self.add_joint(new_joint, kwargs.get('id', ''))

        return new_joint

    def add_joint(self, joint: meta_nodes.Joint, joint_id: str):
        """
        Attaches given joint to this layer with given ID.

        :param meta_nodes.Joint joint: joint instance to attach to this layer instance.
        :param str joint_id: joint ID.
        """

        joints_attr = self.attribute(consts.CRIT_JOINTS_ATTR)
        joints_attr.isLocked = False
        element = joints_attr.nextAvailableDestElementPlug()
        joint.message.connect(element.child(0))
        if not joint.hasAttribute(consts.CRIT_ID_ATTR):
            joint.addAttribute(name=consts.CRIT_ID_ATTR, type=api.kMFnDataString, default='', value=joint_id)
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

        control_parent_plug = self.attribute(consts.CRIT_CONTROLS_ATTR)
        if control_parent_plug is not None:
            for i in control_parent_plug:
                yield i

    def iterate_controls(self, recursive: bool = False) -> Iterator[meta_nodes.ControlNode]:
        """
        Generator function that iterates over all control nodes connected to this rig layer instance.

        :param bool recursive: whether to return all controls recursively or only parent controls.
        :return: iterated control nodes.
        :rtype: Iterator[meta_nodes.ControlNode]
        """

        for element in self.iterate_control_plugs():
            source = element.child(0).source()
            if not source:
                continue
            yield meta_nodes.ControlNode(source.node().object())
        if recursive:
            for child in self.find_children_by_class_types(consts.RIG_LAYER_TYPE, depth_limit=1):
                child_layer = CritRigLayer(node=child.object())
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

    def control(self, name: str) -> meta_nodes.ControlNode:
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
                return meta_nodes.ControlNode(source.node().object())

        raise errors.CritMissingControlError(f'No control found with name "{name}"')

    def add_control(self, control: meta_nodes.ControlNode):
        """
        Attaches given control node instance to this rig layer instance.

        :param meta_nodes.ControlNode control: control node to attach to this rig layer instance.
        """

        controls_attr = self.attribute(consts.CRIT_CONTROLS_ATTR)
        controls_attr.isLocked = False
        element = controls_attr.nextAvailableDestElementPlug()
        control.message.connect(element.child(0))
        element.child(1).set(control.id())
        srt = control.srt()
        if srt is not None:
            srt.message.connect(element.child(2))

    def create_control(self, **kwargs) -> meta_nodes.ControlNode:
        """
        Creats a new control attached to this rig layer instance.

        :param Dict kwargs: control keyword arguments.
        :return: newly created control.
        :rtype: meta_nodes.ControlNode
        """

        new_control = meta_nodes.ControlNode()
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

        for srt_descriptor in kwargs.get('srts', []):
            self.create_srt_buffer(kwargs['id'], srt_descriptor['name'])

        return new_control

    def find_controls(self, *ids: tuple[str]) -> list[meta_nodes.ControlNode | None]:
        """
        Returns controls with given IDs that are linked to this rig layer instance.

        :param tuple[str] ids: IDs of the controls to find.
        :return: found controls that matche given IDs.
        :rtype: list[meta_nodes.ControlNode | None]
        """

        found_controls: list[meta_nodes.ControlNode | None] = [None] * len(ids)
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
        control_node = meta_nodes.ControlNode(control_source.node().object())
        srt_plug = control_element[2]
        next_element = srt_plug.nextAvailableDestElementPlug()
        ctrl_parent = control_node.parent()
        new_srt = api.factory.create_dag_node(name, 'transform')
        new_srt.setWorldMatrix(control_node.worldMatrix())
        new_srt.setParent(ctrl_parent)
        control_node.setParent(new_srt, use_srt=False)
        new_srt.message.connect(next_element)

        return new_srt


class CritXGroupLayer(CritLayer):

    ID = consts.XGROUP_LAYER_TYPE


class CritGeometryLayer(CritLayer):

    ID = consts.GEOMETRY_LAYER_TYPE
