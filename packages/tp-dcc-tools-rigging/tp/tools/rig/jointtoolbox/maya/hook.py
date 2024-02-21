from __future__ import annotations

import typing

import maya.cmds as cmds
from overrides import override

from tp.core import log
from tp.maya.cmds import decorators
from tp.maya.cmds.nodes import joints, matrix
from tp.tools.rig.jointtoolbox import consts, hook
from tp.libs.rig.jointtolbox.maya import api

if typing.TYPE_CHECKING:
    from tp.maya.meta.planeorient import PlaneOrientMeta
    from tp.tools.rig.jointtoolbox.tool import (
        SetStartEndNodesEvent, AlignJointEvent, ZeroRotationAxisEvent, RotateLraEvent, SetJointDrawModeEvent,
        SetLraVisibilityEvent, SetPlaneOrientPositionSnapEvent, ValidateReferencePlaneEvent,
        UpdateJointsPropertiesEvent, MirrorSelectedJointsEvent, JointScaleCompensateToggleEvent,
        SetGlobalJointDisplaySizeEvent, SetJointRadiusEvent, FreezeMatrixEvent, ResetMatrixEvent
    )

logger = log.rigLogger


class MayaJointToolbox(hook.JointToolboxHook):

    def __init__(self):
        super().__init__()

        self._plane_orient: PlaneOrientMeta | None = None

    @override
    def check_meta_nodes(self):
        """Checks whether meta nodes for arrow and plane should exist. And create/delete them if necessary.
        """

        print('checking ...')

    @override
    def delete_reference_plane(self):
        """
        Deletes if possible the reference plane/arrow from scene.
        """

        if not self._plane_orient:
            return

        self._plane_orient.delete_reference_plane()

    @override
    def delete_plane_orient(self):
        """
        Deletes plane orient from scene.
        """

        if not self._plane_orient:
            return

        self._plane_orient.delete_reference_plane()
        self._plane_orient.delete()

    @override
    def set_plane_orient_position_snap(self, event: SetPlaneOrientPositionSnapEvent):
        """
        Sets where plane orient position should be snapped.

        :param SetPlaneOrientPositionSnapEvent event: set plane orient position snap event.
        """

        if not self._plane_orient:
            return

        self._plane_orient.set_position_snap(event.enable)

    @override
    def validate_reference_plane(self, event):
        """
        Checks whether reference plane geometry still exists within the scene.

        :param ValidateReferencePlaneEvent event: validate reference plane event.
        """

        if not self._plane_orient:
            return

        if self._plane_orient.reference_plane_exists():
            return

        self._plane_orient.delete_all_reference_planes()
        self._plane_orient.create_reference_plane(create_plane=event.create_plane)
        self._plane_orient.update_reference_plane()
        self._plane_orient.show_reference_plane()

    @override
    def validate_meta_node(self, event):
        """
        Checks whether reference plane meta node exists within the scene. If not, a new reference plane will be created.

        :param ValidateReferencePlaneEvent event: validate reference plane event.
        """

        if self._plane_orient:
            if self._plane_orient.exists():
                return
            self._plane_orient.delete()

        self._plane_orient = api.create_plane_orient(create_plane=event.create_plane)
        if self._plane_orient:
            self._plane_orient.show_reference_plane()
            event.primary_axis = self._plane_orient.primary_axis()
            event.primary_negate_axis = self._plane_orient.negate_primary_axis()
            event.secondary_axis = self._plane_orient.secondary_axis()

    @override
    def set_start_end_nodes(self, event: SetStartEndNodesEvent):
        if self._plane_orient:
            self._plane_orient.set_start_end_nodes_from_selection()
            event.success = True

    @decorators.undo
    @override
    def align_joint(self, event: AlignJointEvent):
        """
        Aligns current selected joints in the scene.

        :param AlignJointEvent event: align joint event.
        """

        if not event.align_to_plane:
            api.align_selected_joints(
                primary_axis_vector=event.primary_axis_vector, secondary_axis_vector=event.secondary_axis_vector,
                world_up_axis_vector=event.world_up_axis_vector, orient_children=event.orient_children)
        else:
            raise NotImplementedError

    @decorators.undo
    @override
    def edit_lra(self):
        """
        Enters component mode, switch on edit local rotation axis and turns handle visibility on.
        """

        joints.edit_component_lra(True)

    @decorators.undo
    @override
    def exit_lra(self):
        """
        Exists component mode and turns off local rotation axis.
        """

        joints.edit_component_lra(False)

    @decorators.undo
    @override
    def align_to_parent(self):
        """
        Aligns selected joint to its parent.
        """

        joints.align_selected_joints_to_parent()

    @decorators.undo
    @override
    def zero_rotation_axis(self, event: ZeroRotationAxisEvent):
        """
        Zeroes out the rotation axis of the selected joints.

        :param ZeroRotationAxisEvent event: zero rotation axis event.
        """

        joints.zero_selected_joints_rotation_axis(zero_children=event.orient_children)

    @decorators.undo
    @override
    def rotate_lra(self, event: RotateLraEvent):
        """
        Rotates Local Rotate Axis of the selected joints.

        :param RotateLraEvent event: rotate local rotation axis event.
        """

        joints.rotate_selected_joints_local_rotation_axis(event.lra_rotation, include_children=event.orient_children)

    @decorators.undo
    @override
    def set_draw_joint_mode(self, event: SetJointDrawModeEvent):
        """
        Sets the draw joint mode of the selected joints.

        :param SetJointDrawModeEvent event: set joint draw mode event.
        """

        if event.mode == consts.JointDrawMode.Bone:
            joints.set_selected_joints_draw_style_to_bone(children=event.affect_children)
        elif event.mode == consts.JointDrawMode.Hide:
            joints.set_selected_joints_draw_style_to_none(children=event.affect_children)
        elif event.mode == consts.JointDrawMode.Joint:
            joints.set_selected_joints_draw_style_to_joint(children=event.affect_children)
        elif event.mode == consts.JointDrawMode.MultiBoxChild:
            joints.set_selected_joints_draw_style_to_multi_box(children=event.affect_children)
        else:
            logger.warning(f'Draw mode "{event.mode.value}" is not supported!')

    @decorators.undo
    @override
    def set_lra_visibility(self, event: SetLraVisibilityEvent):
        """
        Sets the local rotation axis visibility of the selected joints.

        :param SetLraVisibilityEvent event: set local rotation axis visibility event.
        """

        joints.set_selected_joints_local_rotation_axis_display(
            display=event.visibility, children=event.affect_children)

    @override
    def update_joints_properties(self, event: UpdateJointsPropertiesEvent):
        """
        Retrieves current joint properties from scene.

        :param UpdateJointsPropertiesEvent event: update joints properties event.
        """

        joint_global_scale, joint_local_radius, scale_compensate = api.selected_joint_properties()
        event.joint_global_scale = joint_global_scale
        event.joint_local_radius = joint_local_radius
        event.joint_scale_compensate = scale_compensate

    @decorators.undo
    @override
    def mirror_selected_joints(self, event: MirrorSelectedJointsEvent):
        """
        Mirror selected joints.

        :param MirrorSelectedJointsEvent event: mirror selected joints event.
        """

        joints.mirror_selected_joints(
            event.mirror_axis, search_replace=event.search_replace, mirror_behavior=bool(event.mirror_mode))

    @decorators.undo
    @override
    def joint_scale_compensate(self, event: JointScaleCompensateToggleEvent):
        """
        Toggles joint scale compensate on selected joints.

        :param JointScaleCompensateToggleEvent event: joint scale compensate toggle event.
        """

        joints.selected_joints_scale_compensate(compensate=event.compensate, children=event.affect_children)

    @decorators.undo
    @override
    def set_global_joint_display_size(self, event: SetGlobalJointDisplaySizeEvent):
        """
        Sets the global display size of joints.

        :param SetGlobalJointDisplaySizeEvent event: set global joint display size event.
        """

        cmds.jointDisplayScale(event.size)

    @decorators.undo
    @override
    def set_joint_radius(self, event: SetJointRadiusEvent):
        """
        Sets the joint radius for selected joints.

        :param SetJointRadiusEvent event: set joint radius event.
        """

        joints.set_selected_joints_radius(event.radius, children=event.affect_children)

    @decorators.undo
    @override
    def freeze_to_matrix(self, event: FreezeMatrixEvent):
        """
        Sets an object `translate` and `rotate` to be zero and scale to be one.

        :param FreezeMatrixEvent event: freeze matrix event.
        """

        matrix.selected_transforms_to_matrix_offset(children=event.affect_children, node_type='joint')

    @decorators.undo
    @override
    def reset_matrix(self, event: ResetMatrixEvent):
        """
        Resets an object offset matrix to be zero.

        :param ResetMatrixEvent event: reset matrix event.
        """

        matrix.reset_selected_transforms_matrix_offset(children=event.affect_children, node_type='joint')
