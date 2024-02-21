from __future__ import annotations

import math

from overrides import override
import maya.cmds as cmds

from tp.core import log
from tp.maya import api
from tp.maya.meta import base
from tp.maya.om import mathlib
from tp.maya.cmds import shape
from tp.maya.cmds.rig import controls
from tp.libs.rig.utils.maya import align

logger = log.tpLogger


PLANE_ORIENT_NAME = 'OrientPlane_Reference_tp'
GRID_PLANE_COLOR = (0.073, 0.948, 1.0)


class PlaneOrientMeta(base.MetaBase):

    ID = 'tpPlaneOrient'

    POSITION_MODE: int = 0
    AXIS_ALIGNED_MODE: int = 1

    @staticmethod
    def delete_all_reference_planes():
        """
        Deletes all reference planes within scene.
        """

        all_reference_planes = cmds.ls(f'{PLANE_ORIENT_NAME}*')
        if all_reference_planes:
            cmds.delete(all_reference_planes)

    @staticmethod
    def create_arrow_control(control_name: str, control_scale: float = 1.0) -> str:
        """
        Creates an arrow control for the plane orient up, with pivot correcty place.

        :param str control_name: name of the control.
        :param control_scale: size of the control.
        :return: name of the created arrow control node.
        :rtype: str
        """

        up_arrow_ctrl = controls.create_control_curve(
            control_name=control_name, curve_scale=(control_scale, control_scale, control_scale),
            curve_type=controls.CONTROL_ARROW_THIN, add_suffix=False, rotate_offset=(90.0, 0.0, 0.0),
            track_scale=True, rgb_color=GRID_PLANE_COLOR, add_to_undo=True)[0]
        shape.translate_nodes_cvs([up_arrow_ctrl], [0.0, control_scale, 0.0])

        return up_arrow_ctrl

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()
        attrs.extend([
            {'name': 'tpPlaneOrientRefPlane', 'value': None, 'type': api.attributetypes.kMFnMessageAttribute},
            {'name': 'tpPlaneOrientStartNode', 'value': None, 'type': api.attributetypes.kMFnMessageAttribute},
            {'name': 'tpPlaneOrientEndNode', 'value': None, 'type': api.attributetypes.kMFnMessageAttribute},
            {'name': 'tpPlaneOrientMode', 'value': 0, 'type': api.attributetypes.kMFnkEnumAttribute,
             'enums': ['Position', 'AxisAligned']},
            {'name': 'tpPlaneOrientPrimaryAxis', 'value': 0, 'type': api.attributetypes.kMFnkEnumAttribute,
             'enums': ['X', 'Y', 'Z']},
            {'name': 'tpPlaneOrientSecondaryAxis', 'value': 2, 'type': api.attributetypes.kMFnkEnumAttribute,
             'enums': ['X', 'Y', 'Z']},
            {'name': 'tpPlaneOrientNegatePrimaryAxis', 'value': 0, 'type': api.attributetypes.kMFnNumericBoolean},
            {'name': 'tpPlaneOrientNegateSecondaryAxis', 'value': 0, 'type': api.attributetypes.kMFnNumericBoolean},
            {'name': 'tpPlaneOrientAxisAlignedAxis', 'value': 2, 'type':api. attributetypes.kMFnkEnumAttribute,
             'enums': ['X', 'Y', 'Z']},
            {'name': 'tpPlaneOrientNegateAxisAlignedAxis', 'value': 0, 'type': api.attributetypes.kMFnNumericBoolean},
            {'name': 'tpPlaneOrientPositionSnap', 'value': 0, 'type': api.attributetypes.kMFnNumericBoolean},
        ])

        return attrs

    def mode(self) -> int:
        """
        Returns the orient plane mode.

        :return: orient plane mode.
        :rtype: int
        """

        return self.attribute('tpPlaneOrientMode').value()

    def set_mode(self, value: int):
        """
        Sets orient plane mode.

        :param int value: orient plane mode.
        """

        self.attribute('tpPlaneOrientMode').set(value)

    def primary_axis(self) -> int:
        return self.attribute('tpPlaneOrientPrimaryAxis').value()

    def secondary_axis(self) -> int:
        return self.attribute('tpPlaneOrientSecondaryAxis').value()

    def negate_primary_axis(self) -> int:
        return self.attribute('tpPlaneOrientNegatePrimaryAxis').value()

    def negate_secondary_axis(self) -> int:
        return self.attribute('tpPlaneOrientNegateSecondaryAxis').value()

    def axis_aligned(self) -> int:
        return self.attribute('tpPlaneOrientAxisAlignedAxis').value()

    def negate_axis_aligned_axis(self) -> int:
        return self.attribute('tpPlaneOrientNegateAxisAlignedAxis').value()

    def reference_plane(self) -> api.DagNode | None:
        """
        Returns reference plane object.

        :return: reference plane instance.
        :rtype: api.DagNode or None
        """

        return self.attribute('tpPlaneOrientRefPlane').sourceNode()

    def reference_plane_exists(self) -> bool:
        """
        Returns whether reference plane exists.

        :return: True if reference plane exists; False otherwise.
        :rtype: bool
        """

        ref_plane = self.reference_plane()
        return True if ref_plane and ref_plane.exists() else False

    def create_reference_plane(self, create_plane: bool = True):
        """
        Creates the reference plane for the plane orient meta node.

        :param bool create_plane: If True, creates a plane; otherwise, only up arrow will be created.
        """

        if create_plane:
            ctrl: api.DagNode = api.factory.create_poly_plane(
                PLANE_ORIENT_NAME, createUVs=False, constructionHistory=False, width=100, height=100,
                subdivisionsWidth=10, subdivisionsHeight=10)[0]
            ctrl.setShapeColor(GRID_PLANE_COLOR)
        else:
            ctrl = api.node_by_name(cmds.group(name=PLANE_ORIENT_NAME, empty=True))

        arrow_ctrl = api.node_by_name(self.create_arrow_control('tempCtrlTpDeleteMe', 10.0))
        cmds.parent(arrow_ctrl.shapes()[0].fullPathName(), ctrl.fullPathName(), shape=True, relative=True)
        cmds.delete(arrow_ctrl.fullPathName())
        cmds.select(deselect=True)

        for ctrl_shape in ctrl.shapes():
            ctrl_shape.attribute('overrideEnabled').set(True)
            ctrl_shape.attribute('overrideTexturing').set(False)
            ctrl_shape.attribute('overrideShading').set(False)
            ctrl_shape.attribute('overridePlayback').set(False)

        ctrl.setRotation(align.world_axis_to_rotation(mathlib.Z_AXIS_INDEX))

        self.connect_to('tpPlaneOrientRefPlane', ctrl)

    def show_reference_plane(self):
        """
        Shows reference plane.
        """

        ref_plane = self.reference_plane()
        if ref_plane:
            ref_plane.setVisible(True)

    def hide_reference_plane(self):
        """
        Hides reference plane.
        """

        ref_plane = self.reference_plane()
        if ref_plane:
            ref_plane.setVisible(False)

    def update_reference_plane(self):
        """
        Updates reference plane.
        """

        if not self.reference_plane_exists():
            return

        reference_node = self.reference_plane()
        mode = self.mode()
        if mode == PlaneOrientMeta.POSITION_MODE:
            nodes = self.nodes()
            if not nodes:
                return
        elif mode == PlaneOrientMeta.AXIS_ALIGNED_MODE:
            world_rotation = align.world_axis_to_rotation(
                self.axis_aligned(), invert=bool(self.negate_axis_aligned_axis()))
            rotation = [math.degrees(i) for i in world_rotation]
            cmds.xform(reference_node.fullPathName(), rotation=rotation, worldSpace=True)

        start_node = self.start_node()
        end_node = self.end_node()

        if start_node:
            pass

        if start_node and end_node:
            pass

    def delete_reference_plane(self):
        """
        Deletes reference plane if it exists.
        """

        ref = self.reference_plane()
        if ref is not None:
            ref.delete()

    def start_node(self) -> api.DagNode | None:
        return self.attribute('tpPlaneOrientStartNode').sourceNode()

    def end_node(self) -> api.DagNode | None:
        return self.attribute('tpPlaneOrientEndNode').sourceNode()

    def nodes(self) -> list[api.DagNode]:

        start_node = self.start_node()
        end_node = self.end_node()
        if not start_node or not end_node:
            return []

        nodes = [end_node]
        if start_node == end_node:
            nodes = [start_node]
        else:
            for parent in end_node.iterateParents():
                if parent == start_node:
                    nodes.append(start_node)
                    break
                nodes.append(parent)
        nodes.reverse()

        return nodes

    def set_start_node(self, start_node: api.DagNode, update_reference_plane: bool = True):
        """
        Sets the start node for the reference plane.

        :param api.DagNode start_node: start node.
        :param bool update_reference_plane: whehter to match plane translation to the start node.
        """

        self.connect_to('tpPlaneOrientStartNode', start_node)
        if update_reference_plane:
            ref_plane = self.reference_plane()
            if ref_plane:
                cmds.xform(ref_plane.fullPathName(), translation=start_node.translation(), worldSpace=True)

    def set_end_node(self, end_node: api.DagNode):
        """
        Sets the end node for the reference plane.

        :param api.DagNode end_node: end node.
        """

        self.connect_to('tpPlaneOrientEndNode', end_node)

    def set_start_end_nodes(self, start_node: api.DagNode, end_node: api.DagNode):
        """
        Sets the start node for the reference plane.

        :param api.DagNode start_node: start node.
        :param api.DagNode end_node: end node.
        """

        self.set_start_node(start_node)
        self.set_end_node(end_node)
        self.update_reference_plane()

    def set_start_end_nodes_from_selection(self):
        """
        Sets the start and end nodes for the plane orient meta node based on current selection.
        """

        selection: list[api.DagNode] = list(api.selected())
        if not selection:
            logger.warning('Please select one or two nodes to set as the start and end nodes')
            return

        if len(selection) == 1:
            self.set_start_node(selection[0])
        else:
            self.set_start_end_nodes(selection[0], selection[1])

    def set_position_snap(self, flag: bool):
        self.attribute('tpPlaneOrientPositionSnap').set(flag)

    def project_and_align(self, skip_end: bool = False):
        print('Projecting and Aligning ...', skip_end)
