from __future__ import annotations

import json
import typing
from typing import List, Dict

from overrides import override

import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.maya import api
from tp.maya.meta import base

from tp.libs.rig.crit import consts

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.crit.meta.layers import CritLayer, CritComponentsLayer, CritSkeletonLayer, CritGeometryLayer

logger = log.tpLogger


class CritRig(base.DependentNode):

    ID = consts.RIG_TYPE
    DEPENDENT_NODE_CLASS = base.Core

    def __init__(
            self, node: OpenMaya.MObject | None = None, name: str | None = None, init_defaults: bool = True,
            lock: bool = True, mod: OpenMaya.MDagModifier | None = None):
        super().__init__(node=node, name=name, init_defaults=init_defaults, lock=lock, mod=mod)

    @override
    def meta_attributes(self) -> list[dict]:

        attrs = super().meta_attributes()

        attrs.extend([
            dict(name=consts.CRIT_NAME_ATTR, type=api.kMFnDataString),
            dict(name=consts.CRIT_ID_ATTR, type=api.kMFnDataString),
            dict(name=consts.CRIT_IS_CRIT_ATTR, value=True, type=api.kMFnNumericBoolean),
            dict(name=consts.CRIT_IS_ROOT_ATTR, value=True, type=api.kMFnNumericBoolean),
            dict(name=consts.CRIT_ROOT_TRANSFORM_ATTR, type=api.kMFnMessageAttribute),
            dict(name=consts.CRIT_RIG_CONFIG_ATTR, type=api.kMFnDataString),
            dict(name=consts.CRIT_CONTROL_DISPLAY_LAYER_ATTR, type=api.kMFnMessageAttribute),
            dict(name=consts.CRIT_ROOT_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute),
            dict(name=consts.CRIT_CONTROL_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute),
            dict(name=consts.CRIT_SKELETON_SELECTION_SET_ATTR, type=api.kMFnMessageAttribute),
            dict(name=consts.CRIT_BUILD_SCRIPT_CONFIG_ATTR, type=api.kMFnDataString),
        ])

        return attrs

    @override
    def delete(self, mod: OpenMaya.MDGModifier | None = None, apply: bool = True) -> bool:

        root = self.root_transform()
        if root:
            root.lock(False)
            root.delete()

        return super().delete(mod=mod, apply=apply)

    def rig_name(self) -> str:
        """
        Returns the name for the rig.

        :return: rig name.
        :rtype: str
        """

        return self.attribute(consts.CRIT_NAME_ATTR).asString()

    def root_transform(self) -> api.DagNode:
        """
        Returns the root transform node for this rig instance.

        :return: root transform instance.
        :rtype: api.DagNode
        """

        return self.sourceNodeByName(consts.CRIT_ROOT_TRANSFORM_ATTR)

    def create_transform(self, name: str, parent: api.DagNode | None = None) -> api.DagNode:
        """
        Creates the transform node within Maya scene linked to this meta node.

        :param str name: name of the transform node.
        :param OpenMaya.DagNode or None parent: optional parent node.
        :return: newly created transform node.
        :rtype:
        """

        layer_transform = api.factory.create_dag_node(name=name, node_type='transform', parent=parent)
        layer_transform.setLockStateOnAttributes(consts.TRANSFORM_ATTRS)
        layer_transform.showHideAttributes(consts.TRANSFORM_ATTRS)
        self.connect_to(consts.CRIT_ROOT_TRANSFORM_ATTR, layer_transform)

        return layer_transform

    def selection_sets(self) -> Dict[str, api.ObjectSet]:
        """
        Returns a list of all selection sets for this rig within current scene.

        :return: list of selection sets instances.
        :rtype: Dict[str, api.ObjectSet]
        """

        return {
            'ctrls': self.sourceNodeByName(consts.CRIT_CONTROL_SELECTION_SET_ATTR),
            'skeleton': self.sourceNodeByName(consts.CRIT_SKELETON_SELECTION_SET_ATTR),
            'root': self.sourceNodeByName(consts.CRIT_ROOT_SELECTION_SET_ATTR)
        }

    def create_selection_sets(self, name_manager: NameManager) -> Dict[str, api.DGNode]:
        """
        Creates the selection sets for this rig instance.

        :param tp.common.naming.manager.NameManager name_manager: name manager instanced used to solve valid selection
            set names.
        :return: list of created selection sets.
        :rtype: Dict[str, api.DGNode]
        ..note:: if the selection sets already exists within scene, they will not be created.
        """

        existing_selection_sets = self.selection_sets()
        rig_name = self.attribute(consts.CRIT_NAME_ATTR).value()

        if existing_selection_sets.get('root', None) is None:
            name = name_manager.resolve('rootSelectionSet', {'rigName': rig_name, 'type': 'objectSet'})
            root = api.factory.create_dg_node(name, 'objectSet')
            self.connect_to(consts.CRIT_ROOT_SELECTION_SET_ATTR, root)
            existing_selection_sets['root'] = root
        if existing_selection_sets.get('ctrls', None) is None:
            name = name_manager.resolve(
                'selectionSet', {'rigName': rig_name, 'selectionSet': 'ctrls', 'type': 'objectSet'})
            object_set = api.factory.create_dg_node(name, 'objectSet')
            root.addMember(object_set)
            self.connect_to(consts.CRIT_CONTROL_SELECTION_SET_ATTR, object_set)
            existing_selection_sets['ctrls'] = object_set
        if existing_selection_sets.get('skeleton', None) is None:
            name = name_manager.resolve(
                'selectionSet', {'rigName': rig_name, 'selectionSet': 'skeleton', 'type': 'objectSet'})
            object_set = api.factory.create_dg_node(name, 'objectSet')
            root.addMember(object_set)
            self.connect_to(consts.CRIT_SKELETON_SELECTION_SET_ATTR, object_set)
            existing_selection_sets['skeleton'] = object_set

        return existing_selection_sets

    def create_layer(
            self, layer_type: str, hierarchy_name: str, meta_name: str,
            parent: OpenMaya.MObject | api.DagNode | None = None) -> CritLayer:
        """
        Creates a new layer based on the given type. If the layer of given type already exists, creation will be
        skipped.

        :param str layer_type: layer type to create.
        :param str hierarchy_name: new name for the layer root transform.
        :param str meta_name: name for the layer meta node.
        :param OpenMaya.MObject or api.DagNode or None parent: optional new parent for the root.
        :return: newly created Layer instance.
        :rtype: CritLayer
        """

        existing_layer = self.layer(layer_type)
        if existing_layer:
            return existing_layer

        return self._create_layer(layer_type, hierarchy_name, meta_name, parent)

    def layer(self, layer_type: str) -> CritLayer | None:
        """
        Returns the layer of given type attached to this rig.

        :param str layer_type: layer type to get.
        :return: found layer instance.
        :rtype: CritLayer or None
        """

        meta = self.find_children_by_class_type(layer_type, depth_limit=1)
        if not meta:
            return None

        root = meta[0]
        if root is None:
            logger.warning(f'Missing layer connection: {layer_type}')
            return None

        return root

    def layers(self) -> List[CritLayer]:
        """
        Returns a list with all layer instances attached to this rig.

        :return: list of attached rig meta node instances.
        :rtype: list['tp.libs.rig.crit.meta.layer.CritLayer']
        """

        return [layer for layer in (self.geometry_layer(), self.skeleton_layer(), self.components_layer()) if layer]

    def components_layer(self) -> CritComponentsLayer | None:
        """
        Returns the components layer instance attached to this rig.

        :return: components layer meta node instance.
        :rtype: CritComponentsLayer or None
        """

        return self.layer(consts.COMPONENTS_LAYER_TYPE)

    def skeleton_layer(self) -> CritSkeletonLayer | None:
        """
        Returns the skeleton layer instance attached to this rig.

        :return: skeleton layer meta node instance.
        :rtype: CritSkeletonLayer or None
        """

        return self.layer(consts.SKELETON_LAYER_TYPE)

    def geometry_layer(self) -> CritGeometryLayer | None:
        """
        Returns the geometry layer instance attached to this rig.

        :return: geometry layer meta node instance.
        :rtype: CritGeometryLayer or None
        """

        return self.layer(consts.GEOMETRY_LAYER_TYPE)

    def build_script_configuration(self) -> Dict:
        """
        Returns the build scripts configuration data for this rig.

        :return: build script config dictionary containing the build script ID and properties.
        :rtype: Dict
        """

        config_string = self.attribute(consts.CRIT_BUILD_SCRIPT_CONFIG_ATTR).value()
        try:
            data = json.loads(config_string)
        except ValueError:
            return dict()

        return data

    def set_build_script_configuration(self, config_data: Dict):
        """
        Sets the build script configuration within meta node instance.

        :param Dict config_data: JSON compatible build script config data with the following format:
            { 'buildScriptId': {'propertyName': 'propertyValue'}
        """

        self.attribute(consts.CRIT_BUILD_SCRIPT_CONFIG_ATTR).set(json.dumps(config_data))

    def delete_control_display_layer(self) -> bool:
        """
        Deletes the primary control display layer for this rig instance.

        :return: True if control display layer was deleted successfully; False otherwise.
        :rtype: bool
        """

        display_layer_plug = self.attribute(consts.CRIT_CONTROL_DISPLAY_LAYER_ATTR)
        layer = display_layer_plug.sourceNode()

        return layer.delete() if layer else False

    def _create_layer(
            self, layer_type: str, hierarchy_name: str, meta_name: str,
            parent: OpenMaya.MObject | api.DagNode | None) -> CritLayer | None:
        """
        Internal function that creates a new layer based on the given type.

        :param str layer_type: layer type to create.
        :param str hierarchy_name: new name for the layer root transform.
        :param str meta_name: name for the layer meta node.
        :param OpenMaya.MObject or api.DagNode or None parent: optional new parent for the root.
        :return: newly created Layer instance.
        :rtype: CritLayer or None
        """

        new_layer_meta = base.create_meta_node_by_type(layer_type, name=meta_name, parent=self)
        if not new_layer_meta:
            logger.warning(f'Was not possible to create new layer meta node instance: {layer_type}')
            return None

        if layer_type not in [consts.REGIONS_LAYER_TYPE]:
            new_layer_meta.create_transform(hierarchy_name, parent=parent)

        self.add_meta_child(new_layer_meta)

        return new_layer_meta
