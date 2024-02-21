from __future__ import annotations

import typing
from typing import Iterable, Any

from overrides import override

import maya.cmds as cmds

from tp.core import log
from tp.maya import api
from tp.maya.meta import base

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.meta import layers
from tp.libs.rig.noddle.descriptors import component

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.layers import (
        NoddleLayer, NoddleInputLayer, NoddleOutputLayer, NoddleSkeletonLayer, NoddleGeometryLayer, NoddleXGroupLayer,
        NoddleRigLayer
    )

logger = log.rigLogger


class NoddleComponent(base.MetaBase):

    ID = consts.COMPONENT_TYPE
    REQUIRED_PLUGINS: list[str] = []

    @classmethod
    def load_required_plugins(cls):
        """
        Loads all the required plugins for this component to work as expected.
        """

        for plugin_name in cls.REQUIRED_PLUGINS:
            if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
                try:
                    logger.info(f'Loading plugin {plugin_name} required by {cls.as_str(name_only=True)}')
                    cmds.loadPlugin(plugin_name, quiet=True)
                except Exception:
                    logger.exception(f'Failed to load plugin {plugin_name} required by {cls.as_str(name_only=True)}')
                    raise

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        descriptor_attrs = [{'name': i, 'type': api.kMFnDataString} for i in consts.NODDLE_DESCRIPTOR_CACHE_ATTR_NAMES]

        attrs.extend(
            (
                dict(name=consts.NODDLE_IS_ROOT_ATTR, value=False, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_IS_COMPONENT_ATTR, value=True, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_CONTAINER_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.NODDLE_ID_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_NAME_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_SIDE_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_REGION_NAME_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_VERSION_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_COMPONENT_TYPE_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_IS_ENABLED_ATTR, value=True, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_HAS_SKELETON_ATTR, value=False, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_HAS_RIG_ATTR, value=False, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_HAS_POLISHED_ATTR, value=False, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_HAS_POLISHED_ATTR, value=False, type=api.kMFnNumericBoolean),
                dict(name=consts.NODDLE_COMPONENT_GROUP_ATTR, type=api.kMFnMessageAttribute),
                dict(name=consts.NODDLE_ROOT_TRANSFORM_ATTR, type=api.kMFnMessageAttribute),
                dict(
                    name=consts.NODDLE_COMPONENT_DESCRIPTOR_ATTR, type=api.kMFnCompoundAttribute,
                    children=descriptor_attrs
                )
            )
        )

        return attrs

    @override(check_signature=False)
    def serializeFromScene(self, layer_ids: Iterable[str] | None = None):

        data = {
            'name': self.attribute(consts.NODDLE_NAME_ATTR).asString(),
            'side': self.attribute(consts.NODDLE_SIDE_ATTR).asString(),
            'type': self.attribute(consts.NODDLE_COMPONENT_TYPE_ATTR).asString(),
            'enabled': self.attribute(consts.NODDLE_IS_ENABLED_ATTR).asBool(),
        }

        if self.attribute(consts.NODDLE_HAS_RIG_ATTR).asBool():
        # if not self.attribute(consts.CRIT_HAS_GUIDE_ATTR).asBool():
            raw = self.raw_descriptor_data()
            return component.parse_raw_descriptor(raw)

        if layer_ids:
            for layer_id, layer_node in self.layer_id_mapping().items():
                if layer_id in layer_ids:
                    data.update(layer_node.serializeFromScene())
        else:
            for i in iter(self.layers()):
                data.update(i.serializeFromScene())

        return data

    @override(check_signature=False)
    def delete(self, mod: api.OpenMaya.MDGModifier | None = None) -> bool:
        root = self.root_transform()
        if root:
            root.lock(False)
            root.delete()

        return super().delete(mod=mod)

    def root_transform(self) -> api.DagNode | None:
        """
        Returns the root transform node for this component instance.

        :return: root transform instance.
        :rtype: api.DagNode or None
        """

        return self.sourceNodeByName(consts.NODDLE_ROOT_TRANSFORM_ATTR)

    def create_transform(self, name: str, parent: api.OpenMaya.MObject | api.DagNode | None) -> api.DagNode:
        """
        Creates the transform node within Maya scene linked to this meta node.

        :param str name: name of the transform node.
        :param api.OpenMaya.DagNode or api.DagNode or None parent: optional parent node.
        :return: newly created transform node.
        :rtype: api.DagNode
        """

        component_transform = api.factory.create_dag_node(name=name, node_type='transform', parent=parent)
        component_transform.setLockStateOnAttributes(consts.TRANSFORM_ATTRS)
        component_transform.showHideAttributes(consts.TRANSFORM_ATTRS)
        self.connect_to(consts.NODDLE_ROOT_TRANSFORM_ATTR, component_transform)
        component_transform.lock(True)

        return component_transform

    def raw_descriptor_data(self) -> dict:
        """
        Returns the descriptor data from the meta node instance within current scene.

        :return: descriptor data.
        :rtype: dict
        """

        # space_switching = self.attribute(consts.CRIT_DESCRIPTOR_CACHE_SPACE_SWITCHING_ATTR)
        info = self.attribute(consts.NODDLE_DESCRIPTOR_CACHE_INFO_ATTR)
        prefix = 'noddleDescriptorCache'
        sub_keys = (
            consts.DAG_DESCRIPTOR_KEY, consts.SETTINGS_DESCRIPTOR_KEY, consts.METADATA_DESCRIPTOR_KEY,
            consts.DG_DESCRIPTOR_KEY)
        data = {'info': info.asString() or '{}'}

        for layer_name in consts.LAYER_DESCRIPTOR_KEYS:
            attr_name = prefix + layer_name[0].upper() + layer_name[1:]
            layer_data = {}
            for k in sub_keys:
                sub_attr_name = attr_name + k[0].upper() + k[1:]
                try:
                    layer_data[k] = self.attribute(sub_attr_name).asString()
                except AttributeError:
                    pass
            data[layer_name] = layer_data

        return data

    def save_descriptor_data(self, descriptor_data: dict):
        """
        Saves given descriptor data into meta node instance.

        :param dict descriptor_data: descriptor data.
        """

        for attr_name, str_data in descriptor_data.items():
            attr = self.attribute(attr_name)
            attr.setString(str_data)

    def layer(self, layer_type: str) -> NoddleLayer | None:
        """
        Returns the layer of give ntype attached to this rig.

        :param str layer_type: layer type to get.
        :return: found layer instance.
        :rtype: NoddleLayer or None
        """

        meta = self.find_children_by_class_type(layer_type, depth_limit=1)
        if not meta:
            return None

        root = meta[0]
        if root is None:
            logger.warning(f'Missing layer connection: {layer_type}')
            return None

        return root

    def layers(self) -> list[NoddleLayer]:
        """
        Returns a list with all layers linked to this component meta node.

        :return: list of layer meta node instances.
        :rtype: List[meta_layer.CritLayer]
        """

        layer_types = (
            layers.NoddleOutputLayer.ID, layers.NoddleSkeletonLayer.ID, layers.NoddleInputLayer.ID,
            layers.NoddleRigLayer.ID, layers.NoddleXGroupLayer.ID)

        return self.find_children_by_class_types(layer_types)

    def layer_id_mapping(self) -> dict[str, Any]:
        """
        Returns a list with all layers linked to this component meta node.

        :return: mapping of layer ids with layer meta node instances.
        :rtype: dict[str, Any]
        """

        layer_types = (
            layers.NoddleOutputLayer.ID, layers.NoddleSkeletonLayer.ID, layers.NoddleInputLayer.ID,
            layers.NoddleRigLayer.ID, layers.NoddleXGroupLayer.ID)

        return self.layers_by_id(layer_types)

    def layers_by_id(self, layer_ids: tuple) -> dict[str, NoddleLayer]:
        """
        Returns a dictionary mapping each given layer ID with the layer meta node instance found.

        :param tuple[str] layer_ids: list layer IDs to retrieve.
        :return: mapping of layer ids with layer meta node instances.
        :rtype: dict[str, NoddleLayer]
        """

        layers_map = {layer_id: None for layer_id in layer_ids}
        for found_layer in self.find_children_by_class_types(layer_ids, depth_limit=1):
            layers_map[found_layer.ID] = found_layer

        return layers_map

    def create_layer(
            self, layer_type: str, hierarchy_name: str, meta_name: str,
            parent: api.OpenMaya.MObject | api.DagNode | None = None) -> NoddleLayer:
        """
        Creates a new layer based on the given type. If the layer of given type already exists, creation will be
        skipped.

        :param str layer_type: layer type to create.
        :param str hierarchy_name: new name for the layer root transform.
        :param str meta_name: name for the layer meta node.
        :param OpenMaya.MObject or api.DagNode or None parent: optional new parent for the root.
        :return: newly created Layer instance.
        :rtype: NoddleLayer
        """

        existing_layer = self.layer(layer_type)
        if existing_layer:
            return existing_layer

        return self._create_layer(layer_type, hierarchy_name, meta_name, parent)

    def input_layer(self) -> NoddleInputLayer | None:
        """
        Returns input layer class instance from the meta node instance attached to this root.

        :return: input layer instance.
        :rtype: NoddleInputLayer or None
        """

        return self.layer(consts.INPUT_LAYER_TYPE)

    def output_layer(self) -> NoddleOutputLayer | None:
        """
        Returns output layer class instance from the meta node instance attached to this root.

        :return: output layer instance.
        :rtype: NoddleOutputLayer or None
        """

        return self.layer(consts.OUTPUT_LAYER_TYPE)

    def skeleton_layer(self) -> NoddleSkeletonLayer | None:
        """
        Returns skeleton layer class instance from the meta node instance attached to this root.

        :return: skeleton layer instance.
        :rtype: NoddleSkeletonLayer or None
        """

        return self.layer(consts.SKELETON_LAYER_TYPE)

    def rig_layer(self) -> NoddleRigLayer | None:
        """
        Returns rig layer class instance from the meta node instance attached to this root.

        :return: rig layer instance.
        :rtype: NoddleRigLayer or None
        """

        return self.layer(consts.RIG_LAYER_TYPE)

    def xgroup_layer(self) -> NoddleXGroupLayer | None:
        """
        Returns xgroup layer class instance from the meta node instance attached to this root.

        :return: xgroup layer instance.
        :rtype: NoddleXGroupLayer or None
        """

        return self.layer(consts.XGROUP_LAYER_TYPE)

    def geometry_layer(self) -> NoddleGeometryLayer | None:
        """
        Returns geometry layer class instance from the meta node instance attached to this root.

        :return: geometry layer instance.
        :rtype: NoddleGeometryLayer or None
        """

        return self.layer(consts.GEOMETRY_LAYER_TYPE)

    def _create_layer(
            self, layer_type: str, hierarchy_name: str, meta_name: str,
            parent: api.OpenMaya.MObject | api.DagNode | None = None) -> NoddleLayer | None:
        """
        Internal function that creates a new layer based on the given type.

        :param str layer_type: layer type to create.
        :param str hierarchy_name: new name for the layer root transform.
        :param str meta_name: name for the layer meta node.
        :param OpenMaya.MObject or None parent: optional new parent for the root.
        :return: newly created Layer instance.
        :rtype: NoddleLayer or None
        """

        new_layer_meta = base.create_meta_node_by_type(layer_type, name=meta_name)
        if not new_layer_meta:
            logger.warning('Was not possible to create new layer meta node instance: {}'.format(layer_type))
            return None

        new_layer_meta.create_transform(hierarchy_name, parent=parent)
        self.add_meta_child(new_layer_meta)

        return new_layer_meta
