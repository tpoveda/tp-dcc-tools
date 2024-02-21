from __future__ import annotations

import typing

from tp.common.python import decorators

if typing.TYPE_CHECKING:
    from tp.tools.rig.jointtoolbox.tool import (
        AlignJointEvent, ZeroRotationAxisEvent, RotateLraEvent, SetJointDrawModeEvent, SetLraVisibilityEvent,
        SetPlaneOrientPositionSnapEvent, ValidateReferencePlaneEvent, SetStartEndNodesEvent,
        UpdateJointsPropertiesEvent, MirrorSelectedJointsEvent, JointScaleCompensateToggleEvent,
        SetGlobalJointDisplaySizeEvent, SetJointRadiusEvent, FreezeMatrixEvent, ResetMatrixEvent
    )


class JointToolboxHook:

    @decorators.abstractmethod
    def check_meta_nodes(self):
        """Checks whether meta nodes for arrow and plane should exist. And create/delete them if necessary.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def delete_plane_orient(self):
        """
        Deletes plane orient from scene.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def delete_reference_plane(self):
        """
        Deletes if possible the reference plane/arrow from scene.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_plane_orient_position_snap(self, event: SetPlaneOrientPositionSnapEvent):
        """
        Sets where plane orient position should be snapped.

        :param SetPlaneOrientPositionSnapEvent event: set plane orient position snap event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def validate_reference_plane(self, event: ValidateReferencePlaneEvent):
        """
        Checks whether reference plane geometry still exists within the scene.

        :param ValidateReferencePlaneEvent event: validate reference plane event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def validate_meta_node(self, event: ValidateReferencePlaneEvent):
        """
        Checks whether reference plane meta node exists within the scene. If not, a new reference plane will be created.

        :param ValidateReferencePlaneEvent event: validate reference plane event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_start_end_nodes(self, event: SetStartEndNodesEvent):
        raise NotImplementedError

    @decorators.abstractmethod
    def align_joint(self, event: AlignJointEvent):
        """
        Aligns current selected joints in the scene.

        :param AlignJointEvent event: align joint event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def edit_lra(self):
        """
        Enters component mode, switch on edit local rotation axis and turns handle visibility on.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def exit_lra(self):
        """
        Exists component mode and turns off local rotation axis.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def align_to_parent(self):
        """
        Aligns selected joint to its parent.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def zero_rotation_axis(self, event: ZeroRotationAxisEvent):
        """
        Zeroes out the rotation axis of the selected joints.
        
        :param ZeroRotationAxisEvent event: zero rotation axis event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def rotate_lra(self, event: RotateLraEvent):
        """
        Rotates Local Rotate Axis of the selected joints.

        :param RotateLraEvent event: rotate local rotation axis event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_draw_joint_mode(self, event: SetJointDrawModeEvent):
        """
        Sets the draw joint mode of the selected joints.

        :param SetJointDrawModeEvent event: set joint draw mode event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_lra_visibility(self, event: SetLraVisibilityEvent):
        """
        Sets the local rotation axis visibility of the selected joints.

        :param SetLraVisibilityEvent event: set local rotation axis visibility event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def update_joints_properties(self, event: UpdateJointsPropertiesEvent):
        """
        Retrieves current joint properties from scene.

        :param UpdateJointsPropertiesEvent event: update joints properties event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def mirror_selected_joints(self, event: MirrorSelectedJointsEvent):
        """
        Mirror selected joints.

        :param MirrorSelectedJointsEvent event: mirror selected joints event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def joint_scale_compensate(self, event: JointScaleCompensateToggleEvent):
        """
        Toggles joint scale compensate on selected joints.

        :param JointScaleCompensateToggleEvent event: joint scale compensate toggle event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_global_joint_display_size(self, event: SetGlobalJointDisplaySizeEvent):
        """
        Sets the global display size of joints.

        :param SetGlobalJointDisplaySizeEvent event: set global joint display size event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def set_joint_radius(self, event: SetJointRadiusEvent):
        """
        Sets the joint radius for selected joints.

        :param SetJointRadiusEvent event: set joint radius event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def freeze_to_matrix(self, event: FreezeMatrixEvent):
        """
        Sets an object `translate` and `rotate` to be zero and scale to be one.

        :param FreezeMatrixEvent event: freeze matrix event.
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def reset_matrix(self, event: ResetMatrixEvent):
        """
        Resets an object offset matrix to be zero.

        :param ResetMatrixEvent event: reset matrix event.
        """

        raise NotImplementedError
