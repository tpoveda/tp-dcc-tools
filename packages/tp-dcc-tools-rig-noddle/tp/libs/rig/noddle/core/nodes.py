from __future__ import annotations

from typing import Iterator

from overrides import override

import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.common.python import helpers
from tp.maya import api
from tp.maya.api import curves
from tp.maya.om import factory, plugs, nodes as om_nodes
from tp.maya.libs import curves as curves_library
from tp.maya.meta import base

from tp.libs.rig.crit import consts

logger = log.rigLogger


class SettingsNode(api.DGNode):
    """
    Class that handles arbitrary settings.
    """

    @override(check_signature=False)
    def create(self, name: str, id: str, node_type: str = 'network') -> SettingsNode:
        """
        Creates the MFnSet and sets this instance MObject to the new node.

        :param str name: name for the asset container node.
        :param str id: name for the asset container node.
        :param str node_type: name for the asset container node.
        :return: settings node instance.
        :rtype: SettingsNode
        """

        settings_node = api.factory.create_dg_node(name, node_type=node_type)
        self.setObject(settings_node.object())
        self.addAttribute(consts.CRIT_ID_ATTR, type=api.attributetypes.kMFnDataString, value=id, locked=True)

        return self

    @override(check_signature=False)
    def serializeFromScene(self) -> list[dict]:
        """
        Serializes current node into a dictionary compatible with JSON.

        :return: JSON compatible dictionary.
        :rtype: list[dict]
        """

        skip = (consts.CRIT_ID_ATTR, 'id')
        return [plugs.serialize_plug(attr.plug()) for attr in self.iterateExtraAttributes(skip=skip)]

    def id(self) -> str:
        """
        Returns the ID of the settings node.

        :return: settings node ID.
        :rtype: str
        """

        id_attr = self.attribute(consts.CRIT_ID_ATTR)
        return id_attr.value() if id_attr is not None else ''


class ControlNode(api.DagNode):
    """
    Wrapper class for CRIT control nodes.
    """

    @override(check_signature=False)
    def create(self, **kwargs: dict):
        """
        Creates control with given arguments.

        :param dict kwargs: dictionary with arguments to create control with.
            {
                'color': (1.0, 1.0, 1.0),
                consts.CRIT_ID_ATTR: 'ctrl',
                'name': 'myCtrl',
                'translate': [0.0, 0.0, 0.0] or api.MVector
                'rotate': [0.0, 0.0, 0.0]		# radians
                'rotateOrder': 0
                'shape': 'circle'
            }
        :return: control node instance.
        :rtype: ControlNode
        :raises SystemError: if a node cannot be deserialized from given arguments.
        """

        shape = kwargs.get('shape')
        parent = kwargs.get('parent')
        kwargs['type'] = kwargs.get('type', 'critPinLocator')
        kwargs['name'] = kwargs.get('name', 'Control')
        kwargs['parent'] = None

        try:
            n = om_nodes.deserialize_node(kwargs)[0]
        except SystemError:
            logger.error('Failed to deserialize node: {} from structure'.format(
                kwargs['name']), exc_info=True, extra={'data': kwargs})
            raise

        self.setObject(n)

        with api.lock_state_attr_context(
                self, ['rotateOrder'] + api.LOCAL_TRANSFORM_ATTRS + ['translate', 'rotate', 'scale'], state=False):
            self.setRotationOrder(kwargs.get('rotateOrder', api.consts.kRotateOrder_XYZ))
            world_matrix = kwargs.get('worldMatrix')
            if world_matrix is None:
                self.setTranslation(api.Vector(kwargs.get('translate', (0.0, 0.0, 0.0))), space=api.kWorldSpace)
                self.setRotation(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0)), space=api.kWorldSpace)
                self.setScale(kwargs.get('scale', (1.0, 1.0, 1.0)))
            else:
                self.setWorldMatrix(api.Matrix(world_matrix))
            if parent is not None:
                self.setParent(parent, maintain_offset=True)

        if shape:
            if helpers.is_string(shape):
                self.add_shape_from_lib(shape, replace=True)
                color = kwargs.get('color')
                if color:
                    self.setShapeColor(color, shape_index=-1)
            else:
                self.add_shape_from_data(shape, space=api.kWorldSpace, replace=True)
        self.addAttribute(
            consts.CRIT_ID_ATTR, api.kMFnDataString, value=kwargs.get('id', kwargs['name']), default='', locked=True)

        child_highlighting = kwargs.get('selection_child_highlighting')
        if child_highlighting is not None:
            self.attribute('selectionChildHighlighting').set(child_highlighting)

        rotate_order = self.rotateOrder
        rotate_order.show()
        rotate_order.setKeyable(True)

        return self

    @override(check_signature=False)
    def setParent(
            self, parent: api.OpenMaya.MObject | api.DagNode, use_srt: bool = True,
            maintain_offset: bool = True) -> api.OpenMaya.MDagModifier | None:
        """
        Overrides setParent to set the control parent node.

        :param OpenMaya.MObject or api.DagNode parent: new parent node for the guide.
        :param bool use_srt: whether the SRT will be parented instead of the pivot node.
        :param bool maintain_offset: whether to maintain the current world transform after the parenting.
        :return: True if the set parent operation was successful; False otherwise.
        :rtype: bool
        """

        if use_srt:
            srt = self.srt()
            if srt is not None:
                srt.setParent(parent if parent is not None else None, maintain_offset=maintain_offset)
                return

        return super().setParent(parent, maintain_offset=maintain_offset)

    @override(check_signature=False)
    def serializeFromScene(
            self, skip_attributes: tuple = (), include_connections: bool = True, include_attributes: tuple = (),
            extra_attributes_only: bool = True, use_short_names: bool = True, include_namespace: bool = True) -> dict:
        """
        Serializes current node instance and returns a JSON compatible dictionary with the node data.

        :param set(str) or None skip_attributes: list of attribute names to skip serialization of.
        :param bool include_connections: whether to find and serialize all connections where the destination is this
            node instance.
        :param set(str) or None include_attributes: list of attribute names to serialize.
        :param bool extra_attributes_only: whether only extra attributes will be serialized.
        :param bool use_short_names: whether to use short name of nodes.
        :param bool include_namespace: whether to include namespace as part of the node name.
        :return: serialized node data.
        :rtype: dict
        """

        if self._handle is None:
            return {}

        base_data = super(ControlNode, self).serializeFromScene(
            skip_attributes=skip_attributes, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace)
        base_data.update({
            'id': self.attribute(consts.CRIT_ID_ATTR).value(),
            'name': base_data['name'].replace('_guide', ''),
            'shape': curves.serialize_transform_curve(self.object(), space=api.kObjectSpace, normalize=False),
            'critType': 'control'
        })

        return base_data

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

        controller_tag = self.controller_tag()
        if controller_tag:
            controller_tag.delete(mod=mod, apply=apply)

        return super().delete(mod=mod, apply=apply)

    def id(self) -> str:
        """
        Returns the ID for this control.

        :return: ID as a string.
        :rtype: str
        """

        id_attr = self.attribute(consts.CRIT_ID_ATTR)
        return id_attr.value() if id_attr is not None else ''

    def controller_tag(self) -> api.DGNode | None:
        """
        Returns the attached controller tag for this control
        .
        :return: control controller tag.
        :rtype: api.DGNode or None
        """

        found_controller_tag = None
        for dest in self.attribute('message').destinations():
            node = dest.node()
            if node.apiType() == api.kControllerTag:
                found_controller_tag = node
                break

        return found_controller_tag

    def add_controller_tag(
            self, name: str, parent: ControlNode | None = None, visibility_plug: api.Plug | None = None) -> api.DGNode:
        """
        Creates and attaches a new Maya kControllerTag node into this control.

        :param str name: name of the newly created controller tag.
        :param ControlNode parent: optional controller tag control parent.
        :param api.Plug visibility_plug: visibility plug to connect to.
        :return: newly created controller tag instance.
        :rtype: api.DGNode
        """

        parent = parent.controller_tag() if parent is not None else None
        return api.factory.create_controller_tag(self, name=name, parent=parent, visibility_plug=visibility_plug or None)

    def add_shape_from_lib(
            self, shape_name: str, replace: bool = False,
            maintain_colors: bool = False) -> tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]:
        """
        Adds a new CV shape with given name from the library of shapes.

        :param str shape_name: name of the CV shape to add from library.
        :param bool replace: whether to remove already existing CV shapes.
        :param bool maintain_colors: whether to maintain the color of the actual CV shapes.
        :return: tuple containing the control node instance and the created shape instances.
        :rtype: tuple[ControlNode or None, list[api.OpenMaya.MObject or api.DagNode]]
        """

        if shape_name not in curves_library.names():
            return None, list()

        color_data = dict()
        if maintain_colors:
            for shape in self.iterateShapes():
                color_data = om_nodes.node_color_data(shape.object())
                break

        if replace:
            self.deleteShapeNodes()

        shapes = list(map(api.node_by_object, curves_library.load_and_create_from_lib(
            shape_name, parent=self.object())[1]))
        if maintain_colors:
            for shape in shapes:
                om_nodes.set_node_color(
                    shape.object(), color_data.get('overrideColorRGB'), outliner_color=color_data.get('outlinerColor'),
                    use_outliner_color=color_data.get('useOutlinerColor', False))

        return self, shapes

    def add_shape_from_data(
            self, shape_data: dict, space: api.OpenMaya.MSpace = api.kObjectSpace, replace: bool = False,
            maintain_colors: bool = False) -> tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]:
        """
        Adds a new CV shape based on the given data.

        :param dict shape_data: shape data as a dictionary.
        :param api.OpenMaya.MSpace space: coordinates we want to create new curve in.
        :param bool replace: whether to replace already existing control shapes.
        :param bool maintain_colors: whether to maintain colors based on already existing shape colors.
        :return: tuple containing the control node instance and the created shape instances.
        :rtype: tuple[ControlNode | None, list[api.OpenMaya.MObject | api.DagNode]]
        """

        color_data = dict()
        if maintain_colors:
            for shape in self.iterateShapes():
                color_data = om_nodes.node_color_data(shape.object())

        if replace:
            self.deleteShapeNodes()

        shapes = list(map(api.node_by_object, curves.create_curve_shape(
            shape_data, parent=self.object(), space=space)[1]))
        if maintain_colors:
            for shape in shapes:
                om_nodes.set_node_color(
                    shape.object(), color_data.get('overrideColorRGB'),
                    outliner_color=color_data.get('outlinerColor'),
                    use_outliner_color=color_data.get('useOutlinerColor', False))

        return self, shapes

    def srt(self, index: int = 0) -> api.DagNode | None:
        """
        Returns the SRT (Scale-Rotate-Translate) node at given depth index from top to bottom.

        :param int index: SRT index to get.
        :return: SRT group at given index.
        :rtype: api.DagNode or None
        """

        for destination in self.attribute('message').destinations():
            node = destination.node()
            if not base.is_meta_node(node):
                continue
            control_element = destination.parent()
            srt_array = control_element[2]
            if index not in srt_array.getExistingArrayAttributeIndices():
                continue
            srt_element = srt_array.element(index)
            source_node = srt_element.sourceNode()
            if source_node is not None:
                return source_node

        return None

    def iterate_srts(self) -> Iterator[api.DagNode]:
        """
        Generator function that iterates over all SRT (Scale-Rotate-Translate) nodes of this control instance.

        :return: itearted srts nodes.
        :rtype: Iterator[api.DagNode]
        """

        for destination in self.attribute('message').destinations():
            node = destination.node()
            if not base.is_meta_node(node):
                continue
            control_element = destination.parent()
            for srt_element in control_element[2]:
                source = srt_element.sourceNode()
                if source is not None:
                    yield source


class InputNode(api.DagNode):

    ATTRIBUTES_TO_SKIP = (consts.CRIT_ID_ATTR, api.TP_CONSTRAINTS_ATTR_NAME, consts.CRIT_IS_INPUT_ATTR)

    @staticmethod
    def is_input(node: api.DGNode) -> bool:
        """
        Returns whether given node is a valid input node.

        :param api.DGNode node: node to check.
        :return: True if given node is a valid input node; False otherwise.
        :rtype: bool
        """

        return node.hasAttribute(consts.CRIT_IS_INPUT_ATTR)

    @override(check_signature=False)
    def create(self, **kwargs):

        name = kwargs.get('name', 'input')
        node = om_nodes.factory.create_dag_node(name, 'transform', self.parent())
        self.setObject(node)
        self.setRotationOrder(kwargs.get('rotateOrder', api.consts.kRotateOrder_XYZ))
        self.setTranslation(api.Vector(kwargs.get('translate', [0.0, 0.0, 0.0])), space=api.kWorldSpace)
        self.setRotation(api.Quaternion(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0))))
        self.addAttribute(consts.CRIT_ID_ATTR, api.kMFnDataString, value=kwargs.get('id', name))
        self.addAttribute(consts.CRIT_IS_INPUT_ATTR, api.kMFnNumericBoolean, value=True)

        return self

    @override
    def serializeFromScene(
            self, skip_attributes=(), include_connections=True, include_attributes=(), extra_attributes_only=False,
            use_short_names=False, include_namespace=True):

        base_data = super().serializeFromScene(
            skip_attributes=self.ATTRIBUTES_TO_SKIP, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace)

        _, parent_id = self.input_parent()
        children = [child.serializeFromScene(
            skip_attributes=self.ATTRIBUTES_TO_SKIP, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace) for child in self.iterate_child_inputs()]
        base_data['id'] = self.id()
        base_data['parent'] = parent_id
        base_data['children'] = children

        return base_data

    def id(self) -> str:
        """
        Returns the ID attribute value for this input node.

        :return: input node ID.
        :rtype: str
        """

        id_attr = self.attribute(consts.CRIT_ID_ATTR)
        return id_attr.value() if id_attr is not None else ''

    def is_root(self) -> bool:
        """
        Returns whether this input node is root, which means that it is not parented to other input nodes.

        :return: True if input node is a root one; False otherwise.
        :rtype: bool
        """

        return self.input_parent()[0] is None

    def input_parent(self) -> tuple[InputNode | None, str | None]:
        """
        Returns the input node parent of this node and its respective ID.

        :return: tuple with the input parent as the first element and the input parent ID as the second element.
        :rtype: tuple[InputNode or None, str or None]
        """

        for parent in self.iterateParents():
            if parent.hasAttribute(consts.CRIT_IS_INPUT_ATTR):
                return InputNode(parent.object()), parent.attribute(consts.CRIT_ID_ATTR).value()

        return None, None

    def iterate_child_inputs(self, recursive: bool = False) -> Iterator[InputNode]:
        """
        Generator function that iterates over all child input nodes.

        :param bool recursive: whether to retrieve child input nodes recursively.
        :return: iterated input nodes.
        :rtype: Iterator[InputNode]
        """

        def _child_inputs(_input_node: InputNode):
            if not recursive:
                for _child in _input_node.iterateChildren(recursive=False, node_types=(api.kTransform,)):
                    if self.is_input(_child):
                        yield InputNode(_child.object())
                    else:
                        for _child in _child_inputs(_child):
                            yield _child
            else:
                for _child in _input_node.iterateChildren(recursive=recursive, node_types=(api.kTransform,)):
                    if self.is_input(_child):
                        yield InputNode(_child.object())

        return _child_inputs(self)


class OutputNode(api.DagNode):

    ATTRIBUTES_TO_SKIP = (consts.CRIT_ID_ATTR, api.TP_CONSTRAINTS_ATTR_NAME, consts.CRIT_IS_OUTPUT_ATTR)

    @staticmethod
    def is_output(node: api.DGNode) -> bool:
        """
        Returns whether given node is a valid output node.

        :param api.DGNode node: node to check.
        :return: True if given node is a valid output node; False otherwise.
        :rtype: bool
        """

        return node.hasAttribute(consts.CRIT_IS_OUTPUT_ATTR)

    @override(check_signature=False)
    def create(self, **kwargs):

        name = kwargs.get('name', 'output')
        node = om_nodes.factory.create_dag_node(name, 'transform', self.parent())
        self.setObject(node)
        world_matrix = kwargs.get('worldMatrix', None)
        if world_matrix is not None:
            transform_matrix = api.TransformationMatrix(api.Matrix(world_matrix))
            transform_matrix.setScale((1, 1, 1), api.kWorldSpace)
            self.setWorldMatrix(transform_matrix.asMatrix())
        else:
            self.setTranslation(api.Vector(kwargs.get('translate', (0.0, 0.0, 0.0))), space=api.kWorldSpace)
            self.setRotation(api.Quaternion(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0))))

        self.setRotationOrder(kwargs.get('rotateOrder', api.consts.kRotateOrder_XYZ))
        self.addAttribute(consts.CRIT_ID_ATTR, api.kMFnDataString, value=kwargs.get('id', name))
        self.addAttribute(consts.CRIT_IS_OUTPUT_ATTR, api.kMFnNumericBoolean, value=True)

        return self

    @override
    def serializeFromScene(
            self, skip_attributes=(), include_connections=True, include_attributes=(), extra_attributes_only=False,
            use_short_names=False, include_namespace=True):

        base_data = super().serializeFromScene(
            skip_attributes=self.ATTRIBUTES_TO_SKIP, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace)

        _, parent_id = self.input_parent()
        children = [child.serializeFromScene(
            skip_attributes=self.ATTRIBUTES_TO_SKIP, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace) for child in self.iterate_child_outputs()]
        base_data['id'] = self.id()
        base_data['parent'] = parent_id
        base_data['children'] = children

        return base_data

    def id(self) -> str:
        """
        Returns the ID attribute value for this input node.

        :return: input node ID.
        :rtype: str
        """

        id_attr = self.attribute(consts.CRIT_ID_ATTR)
        return id_attr.value() if id_attr is not None else ''

    def is_root(self) -> bool:
        """
        Returns whether this output node is root, which means that it is not parented to other output nodes.

        :return: True if output node is a root one; False otherwise.
        :rtype: bool
        """

        return self.output_parent()[0] is None

    def output_parent(self) -> tuple[OutputNode | None, str | None]:
        """
        Returns the output node parent of this node and its respective ID.

        :return: tuple with the output parent as the first element and the output parent ID as the second element.
        :rtype: tuple[OutputNode or None, str or None]
        """

        for parent in self.iterateParents():
            if parent.hasAttribute(consts.CRIT_IS_OUTPUT_ATTR):
                return OutputNode(parent.object()), parent.attribute(consts.CRIT_ID_ATTR).value()

        return None, None

    def iterate_child_outputs(self, recursive: bool = False) -> Iterator[OutputNode]:
        """
        Generator function that iterates over all child output nodes.

        :param bool recursive: whether to retrieve child output nodes recursively.
        :return: iterated output nodes.
        :rtype: Iterator[OutputNode]
        """

        def _child_outputs(_output_node: OutputNode):
            if not recursive:
                for _child in _output_node.iterateChildren(recursive=False, node_types=(api.kTransform,)):
                    if self.is_output(_child):
                        yield OutputNode(_child.object())
                    else:
                        for _child in _child_outputs(_child):
                            yield _child
            else:
                for _child in _output_node.iterateChildren(recursive=recursive, node_types=(api.kTransform,)):
                    if self.is_output(_child):
                        yield OutputNode(_child.object())

        return _child_outputs(self)


class Joint(api.DagNode):

    @override(check_signature=False)
    def create(self, **kwargs: dict) -> Joint:

        joint = factory.create_dag_node(kwargs.get('name', 'joint'), 'joint')
        self.setObject(joint)
        world_matrix = kwargs.get('worldMatrix')
        if world_matrix is not None:
            translate_matrix = api.TransformationMatrix(api.Matrix(world_matrix))
            translate_matrix.setScale((1, 1, 1), api.kWorldSpace)
            self.setWorldMatrix(translate_matrix.asMatrix())
        else:
            translation = kwargs.get('translate', api.Vector())
            self.setTranslation(translation, api.kWorldSpace)
            self.setRotation(api.Quaternion(kwargs.get('rotate', (0.0, 0.0, 0.0, 1.0))))

        parent = kwargs.get('parent')
        rotate_order = kwargs.get('rotateOrder', 0)
        self.setRotationOrder(rotate_order)
        self.setParent(parent)

        self.addAttribute(
            consts.CRIT_ID_ATTR, api.kMFnDataString, default='', value=kwargs.get('id', ''), keyable=False,
            channelBox=False, locked=True)

        self.segmentScaleCompensate.set(False)

        return self

    @override(check_signature=False)
    def setParent(
            self, parent: api.DagNode | None, maintain_offset: bool = True, mod: OpenMaya.MDagModifier | None = None,
            apply: bool = True) -> OpenMaya.MDagModifier:
        rotation = self.rotation(space=api.kWorldSpace)
        result = super().setParent(parent, maintain_offset=True)
        if parent is None:
            return result
        parent_quaternion = parent.rotation(api.kWorldSpace, as_quaternion=True)
        new_rotation = rotation * parent_quaternion.inverse()
        self.jointOrient.set(new_rotation.asEulerRotation())
        self.setRotation((0, 0, 0), api.kTransformSpace)
        if parent.apiType() == api.kJoint:
            parent.attribute('scale').connect(self.inverseScale)

    @override
    def serializeFromScene(
            self, skip_attributes=(), include_connections=True, include_attributes=(), extra_attributes_only=False,
            use_short_names=False, include_namespace=True):

        data = super().serializeFromScene(
            skip_attributes=skip_attributes, include_connections=include_connections,
            include_attributes=include_attributes, extra_attributes_only=extra_attributes_only,
            use_short_names=use_short_names, include_namespace=include_namespace)

        data.update({
            'name': self.fullPathName(partial_name=True, include_namespace=False),
            'id': self.id(),
            'critType': 'joint'
        })

        return data

    def id(self) -> str:
        """
        Returns the ID attribute value for this joint.

        :return: joint ID.
        :rtype: str
        """

        id_attr = self.attribute(consts.CRIT_ID_ATTR)
        return id_attr.value() if id_attr is not None else ''

    def aim_to_child(self, aim_vector: api.Vector, up_vector: api.Vector, use_joint_orient: bool = True):
        """
        Aims this joint to its first child.

        :param api.Vector aim_vector: aim vector.
        :param api.Vector up_vector: up vector.
        :param bool use_joint_orient: whether to use joint orient to store rotations.
        """

        child = self.child(0)
        if child is None:
            self.setRotation(api.Quaternion())
            return

        om_nodes.aim_nodes(
            target_node=child.object(), driven=[self.object()], aim_vector=aim_vector, up_vector=up_vector)
        if use_joint_orient:
            self.jointOrient.set(self.rotation())
            self.setRotation(api.Quaternion())
