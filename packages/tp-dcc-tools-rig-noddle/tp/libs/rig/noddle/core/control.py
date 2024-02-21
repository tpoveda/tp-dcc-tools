from __future__ import annotations

import json
import typing
from typing import Iterable

from overrides import override
import maya.cmds as cmds

from tp.core import log
from tp.maya.meta import base
from tp.maya import api
from tp.maya.api import curves as api_curves
from tp.maya.om import nodes
from tp.preferences.interfaces import noddle
from tp.maya.libs import curves as curves_lib

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.functions import naming, outliner, attributes, curves

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.component import Component

logger = log.rigLogger


class Control(api.DagNode):

    LINE_WIDTH = None

    def __repr__(self) -> str:
        return f'Control({self.fullPathName(partial_name=True, include_namespace=False)})'

    @property
    def tag_node(self) -> api.DGNode:

        found_tag_node = None
        for dest in self.message.destinations():
            node = dest.node()
            if node.apiType() == api.kControllerTag:
                found_tag_node = node
                break

        return found_tag_node

    @property
    def control_name(self) -> str:
        return self.tag_node.attribute('name').value()

    @property
    def indexed_name(self) -> str:
        return self.tag_node.attribute('indexedName').value()

    @property
    def index(self) -> str:
        return self.tag_node.attribute('index').value()

    @property
    def side(self) -> str:
        return self.tag_node.attribute('side').value()

    @property
    def tag(self) -> str:
        return self.tag_node.attribute('tag').value()

    @property
    def group(self) -> api.DagNode:
        return self.tag_node.attribute('group').sourceNode()

    @property
    def offsets(self) -> list[api.DagNode]:
        return [plug.sourceNode() for plug in self.tag_node.attribute('offset')]

    @property
    def offset(self) -> api.DagNode:
        all_offsets = self.offsets
        return all_offsets[-1] if all_offsets else None

    @property
    def joint(self) -> api.Joint | None:
        return self.tag_node.attribute('joint').sourceNode()

    @staticmethod
    def is_control(node: api.DagNode) -> bool:
        """
        Returns whether given node is a valid control node.

        :param api.DagNode node: node to check.
        :return: True if given node is a valid control; False otherwise.
        :rtype: bool
        """

        return all([
            cmds.controller(node.fullPathName(), query=True, isController=True),
            node.hasAttribute(base.MPARENT_ATTR_NAME)
        ])

    @classmethod
    def create(
            cls, name='control', side='c', shape: str = 'cube',
            color: int | str | Iterable[float, float, float] or None = None,
            not_locked_attributes: str | list[str, ...] | None = None, guide: api.DagNode | None = None,
            match_pos: bool = True, match_orient: bool = True, match_pivot: bool = True, delete_guide: bool = False,
            offset_group: bool = True, joint: bool = False, tag: str = '', orient_axis: str = 'x', scale: float = 1.0,
            component: Component | None = None, parent: api.DagNode | None = None) -> Control:
        """
        Creates a new control instance.

        :param str name: name for the control.
        :param str side: side for the control.
        :param str shape: control shape name from curves library.
        :param int or str or Iterable[float, float, float] or None color: optional control color.
        :param str or list[str, ...] not_locked_attributes: list of attribute names to not lock.
        :param api.DagNode or None guide: optional guide to match control with.
        :param bool match_pos: whether to match control position to guide position.
        :param bool match_orient: whether to match control rotation to guide rotation.
        :param bool match_pivot: whether to match control pivot to guide pivot.
        :param bool bool delete_guide: whether to delete guide after control was matched against it.
        :param bool bool offset_group: whether to create control offset group.
        :param bool bool joint: whether to create control joint.
        :param str tag: optional tag to set on the tag node.
        :param str orient_axis: control orientation.
        :param float scale: control scale.
        :param Component or None component: optional component to connect control to.
        :param api.DagNode or None parent: optional parent.
        :return: newly created control instance.
        :rtype: Control
        """

        if Control.LINE_WIDTH is None:
            Control.LINE_WIDTH = noddle.noddle_interface().rig_display_line_width()

        offset_node = None
        control_joint = None
        temp_parent = parent

        group_node = api.factory.create_dag_node(
            naming.generate_name(name, side, suffix='grp'), 'transform', parent=temp_parent)
        temp_parent = group_node

        if guide is not None:
            cmds.matchTransform(
                group_node.fullPathName(), guide.fullPathName(), pos=match_pos, rot=match_orient, piv=match_pivot)
            if delete_guide:
                guide.delete()

        if offset_group:
            offset_node = api.factory.create_dag_node(
                naming.generate_name(name, side, suffix='ofs'), 'transform', parent=temp_parent)
            temp_parent = offset_node

        transform_node = api.factory.create_dag_node(
            naming.generate_name(name, side, suffix='ctl'), 'transform', parent=temp_parent)
        temp_parent = transform_node

        if joint:
            control_joint = api.factory.create_dag_node(
                naming.generate_name(name, side, suffix='cjnt'), 'joint', parent=temp_parent)
            control_joint.setVisible(False)

        tag_node = api.factory.create_controller_tag(
            transform_node, name=naming.generate_name(name, side, suffix='tag'))
        tag_node.addAttribute('group', type=api.kMFnMessageAttribute)
        tag_node.addAttribute('offset', type=api.kMFnMessageAttribute, multi=True, isArray=True, indexMatters=False)
        tag_node.addAttribute('joint', type=api.kMFnMessageAttribute)

        tag_node.addAttribute('side', type=api.kMFnDataString)
        tag_node.addAttribute('name', type=api.kMFnDataString)
        tag_node.addAttribute('tag', type=api.kMFnDataString, value=tag)
        tag_node.addAttribute('index', type=api.kMFnDataString)
        tag_node.addAttribute('indexedName', type=api.kMFnDataString)

        tag_node.addAttribute('bindPose', type=api.kMFnDataString, keyable=False, value=json.dumps({}))
        tag_node.bindPose.lock(True)

        name_struct = naming.deconstruct_name(transform_node.fullPathName(partial_name=True, include_namespace=False))
        tag_node.attribute('name').set(name_struct.name)
        tag_node.attribute('side').set(name_struct.side)
        tag_node.attribute('index').set(name_struct.index)
        tag_node.attribute('indexedName').set(name_struct.indexed_name)
        for attr_name in ('side', 'name', 'tag', 'index', 'indexedName'):
            tag_node.attribute(attr_name).lock(True)

        for node in [group_node, offset_node, transform_node, control_joint]:
            if node is None:
                continue
            node.addAttribute(base.MPARENT_ATTR_NAME, type=api.kMFnMessageAttribute)

        group_node.attribute(base.MPARENT_ATTR_NAME).connect(tag_node.group)
        if offset_node is not None:
            offset_node.attribute(base.MPARENT_ATTR_NAME).connect(tag_node.offset.nextAvailableDestElementPlug())
        if control_joint is not None:
            control_joint.attribute(base.MPARENT_ATTR_NAME).connect(tag_node.joint)

        instance = Control(node=transform_node.object())
        instance.set_shape(shape)
        instance.set_color(color)
        instance.set_outliner_color(27)
        instance.set_line_width(Control.LINE_WIDTH)
        instance.lock_attributes(exclude_attributes=not_locked_attributes or ['t', 'r'])
        instance.scale_shapes(scale, factor=1.0)
        instance.orient_shape(direction=orient_axis)

        if component:
            component.store_controls((instance,))

        return instance

    @override(check_signature=False)
    def rename(
            self, side: str | None = None, name: str | None = None, index: str | None = None, suffix: str | None = None):
        raise NotImplementedError

    # @override(check_signature=False)
    # def setParent(
    # 		self, parent: api.DagNode | None, maintain_offset: bool = True, mod: api.OpenMaya.MDagModifier | None = None,
    # 		apply: bool = True) -> api.OpenMaya.MDagModifier:
    # 	raise NotImplementedError

    def shape(self) -> dict:
        """
        Returns control shape as dictionary.

        :return: control shape.
        :rtype: dict
        """

        return api_curves.serialize_transform_curve(self.object(), normalize=False)

    def set_shape(self, name: str) -> bool:
        """
        Sets the control shape from the curve with given name within curves library.

        :param str name: name of the shape to set.
        :returns: True if shape was set successfully; False otherwise.
        :rtype: bool
        """

        if name not in curves_lib.names():
            return False

        shapes = list(self.iterateShapes())

        color_data = {}
        line_width = None
        if shapes:
            color_data = nodes.node_color_data(shapes[0].object())
            line_width = shapes[0].lineWidth.asFloat()

        for shape in shapes:
            shape.delete()

        new_shapes = curves_lib.load_and_create_from_lib(name, parent=self.object())[1]
        if color_data:
            for shape in new_shapes:
                nodes.set_node_color(
                    shape, color_data.get('overrideColorRGB'), outliner_color=color_data.get('outlinerColor'),
                    use_outliner_color=color_data.get('useOutlinerColor', False))
                if line_width is not None:
                    api.node_by_name(shape).attribute('lineWidth').set(line_width)

        return True

    def color(self) -> int | tuple[float, float, float] | None:
        """
        Returns the control color.

        :return: control color.
        :rtype: int or tuple[float, float, float] or None
        """

        shapes = self.shapes()
        if not shapes:
            return None

        shape = shapes[0]
        return shape.overrideColorRGB.get() if shape.overrideRGBColors.get() else shape.overrideColor.get()

    def set_color(self, color: int | str | Iterable[float, float, float] | None = None):
        """
        Sets the control color.

        :param int or str | Iterable[float, float, float] or None color: color value.
        """

        if color is None:
            color = consts.SideColor[self.side].value
            is_rgb = True
        else:
            if isinstance(color, str):
                color = consts.ColorIndex.index_to_rgb(consts.ColorIndex[color].value)
            is_rgb = False if isinstance(color, (int, float)) else True

        for shape in self.iterateShapes():
            shape.overrideEnabled.set(True)
            shape.overrideRGBColors.set(True if is_rgb else False)
            shape.overrideColorRGB.set(color) if is_rgb else shape.overrideColor.set(color)

    def set_outliner_color(self, color: int | str | Iterable[float, float, float]):
        """
        Sets the color of the node within outliner panel.

        :param int or str or Iterable[float, float, float] color: outliner color to set.
        """

        outliner.set_color(self, color)

    def set_line_width(self, value: float):
        """
        Sets the line width of the control shapes.

        :param float value: line width value.
        """

        for shape in self.iterateShapes():
            shape.lineWidth.set(value)

    def lock_attributes(self, exclude_attributes: list[str, ...] | None = None, channel_box: bool = False):
        """
        Lock control transform attributes.

        :param list[str, ...] or None exclude_attributes: optional list of attributes to exclude.
        :param bool channel_box: whether to remove attributes from channel box.
        """

        to_lock = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
        exclude_attributes = [] if exclude_attributes is None else exclude_attributes
        for attr in exclude_attributes:
            if attr in list('trs'):
                for axis in 'xyz':
                    to_lock.remove(attr + axis)

        attributes.lock(self, to_lock, channel_box=channel_box)

    def move_shapes(self, vector: api.Vector):
        """
        Moves the control shapes.

        :param api.Vector vector: vector to move shapes with.
        """

        for shape in self.iterateShapes():
            cmds.move(*list(vector), f'{shape.fullPathName()}.cv[*]', r=True)

    def scale_shapes(self, scale: float, factor: float = 1.0):
        """
        Scales the control shapes.

        :param float scale: scale value.
        :param float factor: scale factor.
        """

        if scale == 1.0 and factor == 1.0:
            return

        for shape in self.iterateShapes():
            cmds.scale(
                factor * scale, factor * scale, factor * scale, f'{shape.fullPathName()}.cv[*]', objectSpace=True)

    def orient_shape(self, direction: str = 'x'):
        """
        Orients control shapes to match given direction axis.

        :param str direction: direction axis ('x', 'y' or 'z').
        """

        if direction.lower() not in 'xyz' and direction.lower() not in ['-x', '-y', '-z']:
            logger.exception(f'Invalid orient direction: {direction}')
            return
        if direction == 'y':
            return

        temp_transform = api.factory.create_dag_node('temp_transform', 'transform', parent=self)
        for shape in self.shapes():
            cmds.parent(shape.fullPathName(), temp_transform.fullPathName(), s=True, r=True)
        try:
            if direction == 'x':
                temp_transform.rotateX.set(api.OpenMaya.MAngle(-90, api.OpenMaya.MAngle.kDegrees))
                temp_transform.rotateY.set(api.OpenMaya.MAngle(-90, api.OpenMaya.MAngle.kDegrees))
            elif direction == '-x':
                temp_transform.rotateX.set(api.OpenMaya.MAngle(90, api.OpenMaya.MAngle.kDegrees))
                temp_transform.rotateY.set(api.OpenMaya.MAngle(-90, api.OpenMaya.MAngle.kDegrees))
            elif direction == '-y':
                temp_transform.rotateZ.set(api.OpenMaya.MAngle(180, api.OpenMaya.MAngle.kDegrees))
            elif direction == 'z':
                temp_transform.rotateX.set(api.OpenMaya.MAngle(90, api.OpenMaya.MAngle.kDegrees))
            elif direction == '-z':
                temp_transform.rotateX.set(api.OpenMaya.MAngle(-90, api.OpenMaya.MAngle.kDegrees))
            cmds.makeIdentity(temp_transform.fullPathName(), rotate=True, apply=True)
        finally:
            for shape in temp_transform.shapes():
                cmds.parent(shape.fullPathName(), self.fullPathName(), s=True, r=True)
            temp_transform.delete()

    def rotate_shape(self, rotation: Iterable[float, float, float]):
        """
        Rotate control shapes with given rotation.

        :param Iterable[float, float, float] rotation: iterable representing an XYZ degree rotation.
        """

        temp_transform = api.factory.create_dag_node('temp_transform', 'transform', parent=self)
        for shape in self.shapes():
            cmds.parent(shape.fullPathName(), temp_transform.fullPathName(), s=True, r=True)
        try:
            cmds.rotate(*rotation, temp_transform.fullPathName(), objectSpace=True)
            cmds.makeIdentity(temp_transform.fullPathName(), rotate=True, apply=True)
        finally:
            for shape in temp_transform.shapes():
                cmds.parent(shape.fullPathName(), self.fullPathName(), s=True, r=True)
            temp_transform.delete()

    def add_orient_switch(
            self, space_target: api.DagNode, local_parent: api.DagNode | None = None, default_state: float = 1.0):
        """

        :param space_target:
        :param local_parent:
        :param default_state:
        :return:
        """

        pass

    def pose(self) -> dict:
        """
        Returns control the current control pose.

        :return: control pose.
        :rtype: dict
        """

        # TODO: Use API calls intead of cmds
        pose_data = {}
        pose_attributes = cmds.listAttr(self.fullPathName(), k=True, u=True) or [] + cmds.listAttr(self.fullPathName(), cb=True, u=True) or []
        for attr_name in pose_attributes:
            if not cmds.listConnections(f'{self.fullPathName()}.{attr_name}', source=True, destination=False):
                pose_data[attr_name] = cmds.getAttr(f'{self.fullPathName()}.{attr_name}')

        return pose_data

    def bind_pose(self) -> dict:
        """
        Returns control the control bind pose.

        :return: control bind pose.
        :rtype: dict
        """

        pose_data = {}
        if not self.tag_node.hasAttribute('bindPose'):
            logger.warning(f'Missing bind pose: {self}')
            return pose_data

        return json.loads(self.tag_node.attribute('bindPose').value())

    def write_bind_pose(self):
        """
        Writes current control pose to bindPose attribute of the control transform node.
        """

        if not self.tag_node.hasAttribute('bindPose'):
            self.tag_node.addAttribute('bindPose', type=api.kMFnDataString, keyable=False, value=json.dumps(self.pose()))
            self.tag_node.bindPose.lock(True)
        else:
            self.tag_node.bindPose.lock(False)
            self.tag_node.bindPose.set(json.dumps(self.pose()))
            self.tag_node.bindPose.lock(True)

    def add_wire(self, source: api.DagNode):
        """
        Adds a straight line connecting the given source node and the the control's transform.

        :param apip.DagNode source: source node.
        """

        curve_points = [list(source.translation(api.kWorldSpace)), list(self.translation(api.kWorldSpace))]
        wire_curve = curves.curve_from_points(
            name=naming.generate_name([self.indexed_name, 'wire'], side=self.side, suffix='crv'), degree=1,
            points=curve_points)
        wire_curve.inheritsTransform.set(False)

        _, source_handle = cmds.cluster(
            str(wire_curve.shapes()[0].controlPoints[0]),
            n=naming.generate_name([self.indexed_name, 'wire', 'src'], side=self.side, suffix='clst'))
        _, dest_handle = cmds.cluster(
            str(wire_curve.shapes()[0].controlPoints[1]),
            n=naming.generate_name([self.indexed_name, 'wire', 'dest'], side=self.side, suffix='clst'))
        source_handle = api.node_by_name(source_handle)
        dest_handle = api.node_by_name(dest_handle)
        api.build_constraint(
            source_handle,
            drivers={
                'targets': ((source.fullPathName(partial_name=True, include_namespace=False), source),)},
            constraint_type='point',
            n=naming.generate_name([self.indexed_name, 'wire', 'src'], side=self.side, suffix='ptcon')
        )
        api.build_constraint(
            dest_handle,
            drivers={
                'targets': ((self.fullPathName(partial_name=True, include_namespace=False), self),)},
            constraint_type='point',
            n=naming.generate_name([self.indexed_name, 'wire', 'dest'], side=self.side, suffix='ptcon')
        )
        wire_group = api.factory.create_dag_node(
            name=naming.generate_name([self.indexed_name, 'wire'], side=self.side, suffix='grp'), node_type='transform')
        wire_group.setParent(self.group)
        for node in [source_handle, dest_handle, wire_curve]:
            node.setParent(wire_group)
        source_handle.setVisible(False)
        dest_handle.setVisible(False)
        wire_curve.shapes()[0].overrideEnabled.set(True)
        wire_curve.shapes()[0].overrideDisplayType.set(2)
