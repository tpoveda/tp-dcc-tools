from __future__ import annotations

import typing
from functools import partial
from dataclasses import dataclass, field

from overrides import override

from tp.core import log, tool, dcc
from tp.common.qt import api as qt
from tp.dcc import scene

from . import consts, hook

if typing.TYPE_CHECKING:
    from tp.common.plugin import PluginFactory
    from tp.core.managers.tools import ToolsManager

logger = log.rigLogger


@dataclass
class AlignJointEvent:
    align_to_plane: bool
    primary_axis_vector: tuple[float, float, float]
    secondary_axis_vector: tuple[float, float, float]
    world_up_axis_vector: tuple[float, float, float]
    orient_children: bool


@dataclass
class ZeroRotationAxisEvent:
    orient_children: bool


@dataclass
class RotateLraEvent:
    lra_rotation: list[float, float, float]
    orient_children: bool


@dataclass
class SetJointDrawModeEvent:
    mode: consts.JointDrawMode
    affect_children: bool


@dataclass
class SetLraVisibilityEvent:
    visibility: bool
    affect_children: bool


@dataclass
class SetPlaneOrientPositionSnapEvent:
    enable: bool


@dataclass
class ValidateReferencePlaneEvent:
    create_plane: bool
    primary_axis: int | None = None
    primary_negate_axis: int | None = None
    secondary_axis: int | None = None


@dataclass
class SetStartEndNodesEvent:
    success: bool = False


@dataclass
class UpdateJointsPropertiesEvent:
    joint_global_scale: float | None = None
    joint_local_radius: float | None = None
    joint_scale_compensate: bool | None = None


@dataclass
class MirrorSelectedJointsEvent:
    mirror_mode: int
    mirror_axis: str
    search_replace: tuple[list[str]] = field(default_factory=lambda: [['_L', '_R'], ['_lft', '_rgt']])


@dataclass
class JointScaleCompensateToggleEvent:
    compensate: bool
    affect_children: bool


@dataclass
class SetGlobalJointDisplaySizeEvent:
    size: float


@dataclass
class SetJointRadiusEvent:
    radius: float
    affect_children: bool


@dataclass
class FreezeMatrixEvent:
    affect_children: bool


@dataclass
class ResetMatrixEvent:
    affect_children: bool


class JointToolBox(tool.Tool):

    id = consts.TOOL_ID
    creator = 'Tomi Poveda'
    ui_data = tool.UiData(label='Joint Toolbox')
    tags = ['joint', 'toolbox']

    setStartEndNodes = qt.Signal(SetStartEndNodesEvent)
    alignJoint = qt.Signal(AlignJointEvent)
    editLra = qt.Signal()
    exitLra = qt.Signal()
    alignToParent = qt.Signal()
    zeroRotationAxis = qt.Signal(ZeroRotationAxisEvent)
    rotateLra = qt.Signal(RotateLraEvent)
    setJointDrawMode = qt.Signal(SetJointDrawModeEvent)
    setLraVisibility = qt.Signal(SetLraVisibilityEvent)
    setPlaneOrientPositionSnap = qt.Signal(SetPlaneOrientPositionSnapEvent)
    updateJointsProperties = qt.Signal(UpdateJointsPropertiesEvent)
    mirrorSelectedJoints = qt.Signal(MirrorSelectedJointsEvent)
    jointScaleCompensate = qt.Signal(JointScaleCompensateToggleEvent)
    setGlobalJointDisplaySize = qt.Signal(SetGlobalJointDisplaySizeEvent)
    setJointRadius = qt.Signal(SetJointRadiusEvent)
    freezeMatrix = qt.Signal(FreezeMatrixEvent)
    resetMatrix = qt.Signal(ResetMatrixEvent)

    def __init__(self, factory: PluginFactory, tools_manager: ToolsManager):
        super().__init__(factory, tools_manager)

        self._hook: hook.JointToolboxHook | None = None
        self._coplanar_meta = None
        self._main_widget: JointToolboxView | None = None

    @override
    def initialize_properties(self) -> list[tool.UiProperty]:
        return [
            tool.UiProperty(name='affect_children', value=1),
            tool.UiProperty(name='mirror_mode', value=1),
            tool.UiProperty(name='mirror_axis', value=0),
            tool.UiProperty(name='rotate_lra_axis', value=0),
            tool.UiProperty(name='rotate_lra', value=45.0),
            tool.UiProperty(name='world_up', value=1),
            tool.UiProperty(name='primary_axis', value=0),
            tool.UiProperty(name='secondary_axis', value=1),
            tool.UiProperty(name='joint_scale_compensate_ratio', value=True),
            tool.UiProperty(name='joint_global_display_size', value=1),
            tool.UiProperty(name='joint_radius', value=1.0),
        ]

    @override
    def pre_content_setup(self):

        self._coplanar_meta = None

        if dcc.is_maya():
            from tp.tools.rig.jointtoolbox.maya import hook as maya_hook
            self._hook = maya_hook.MayaJointToolbox()
        else:
            self._hook = hook.JointToolboxHook()

        self.closed.connect(self._hook.delete_plane_orient)
        self.setStartEndNodes.connect(self._hook.set_start_end_nodes)
        self.alignJoint.connect(self._hook.align_joint)
        self.editLra.connect(self._hook.edit_lra)
        self.exitLra.connect(self._hook.exit_lra)
        self.alignToParent.connect(self._hook.align_to_parent)
        self.zeroRotationAxis.connect(self._hook.zero_rotation_axis)
        self.rotateLra.connect(self._hook.rotate_lra)
        self.setJointDrawMode.connect(self._hook.set_draw_joint_mode)
        self.setLraVisibility.connect(self._hook.set_lra_visibility)
        self.setPlaneOrientPositionSnap.connect(self._hook.set_plane_orient_position_snap)
        self.updateJointsProperties.connect(self._hook.update_joints_properties)
        self.mirrorSelectedJoints.connect(self._hook.mirror_selected_joints)
        self.jointScaleCompensate.connect(self._hook.joint_scale_compensate)
        self.setGlobalJointDisplaySize.connect(self._hook.set_global_joint_display_size)
        self.setJointRadius.connect(self._hook.set_joint_radius)
        self.freezeMatrix.connect(self._hook.freeze_to_matrix)
        self.resetMatrix.connect(self._hook.reset_matrix)

    @override
    def contents(self) -> list[qt.QWidget]:
        self._main_widget = JointToolboxView(self)
        return [self._main_widget]

    @override
    def post_content_setup(self):
        self.update_joints_properties()
        self._main_widget.setup_signals()

        self.update_widgets_from_properties()

    def reset_ui(self):
        """
        Resets UI state.
        """

        self.reset_properties(update_widgets=True)

    def check_meta_nodes(self):
        """Checks whether meta nodes for arrow and plane should exist. And create/delete them if necessary.
        """

        world_up = self.properties.world_up.value
        if world_up > 2:
            event = ValidateReferencePlaneEvent(create_plane=False if self.properties.world_up.value == 3 else True)
            self._hook.validate_reference_plane(event)
            self._hook.validate_meta_node(event)
            if event.primary_axis is not None:
                self.properties.primary_axis.value = event.primary_axis
            if event.primary_negate_axis:
                self.properties.primary_axis.value += 3
            if event.secondary_axis is not None:
                self.properties.secondary_axis.value = event.secondary_axis
            self.update_widgets_from_properties()
        else:
            self.delete_reference_plane()

    def delete_reference_plane(self):
        """
        Deletes if possible the reference plane/arrow from scene.
        """

        self._hook.delete_reference_plane()

    def set_plane_orient_position_snap(self, flag):
        """
        Sets where plane orient position should be snapped.

        :param bool flag: True to enable plane orient position snap; False to disable it.
        """

        event = SetPlaneOrientPositionSnapEvent(flag)
        self.setPlaneOrientPositionSnap.emit(event)

    def set_start_end_nodes(self):
        """
        Sets the start and end nodes.
        """

        event = SetStartEndNodesEvent()
        self.setStartEndNodes.emit(event)
        if not event.success:
            event = ValidateReferencePlaneEvent(create_plane=False if self.properties.world_up.value == 3 else True)
            self._hook.validate_meta_node(event)

    def align_joint(self, align_up: bool = True):
        """
        Aligns the selected joints in the scene.

        :param bool align_up: if True, joint will point the axis up; False will point down relative to the world axis.
        """

        primary_axis_vector = consts.AXIS_VECTORS[self.properties.primary_axis.value]

        if align_up:
            secondary_axis_vector = consts.AXIS_VECTORS[self.properties.secondary_axis.value]
        else:
            # Make secondary axis negative
            secondary_axis_vector = consts.AXIS_VECTORS[self.properties.secondary_axis.value + 3]

        world_up_axis = self.properties.world_up.value
        align_to_plane = True if world_up_axis == 4 else False
        world_up_axis_vector = consts.AXIS_VECTORS[world_up_axis]
        if self._coplanar_meta:
            if world_up_axis == 3:      # Get vector normal from coplanar arrow plane normal
                world_up_axis_vector = self._coplanar_meta.arrow_plane_normal()
                if not world_up_axis_vector:
                    logger.warning('No arrow plane found, please create one.')
                    return
                world_up_axis_vector = tuple(world_up_axis_vector)

        event = AlignJointEvent(
            align_to_plane=align_to_plane, primary_axis_vector=primary_axis_vector,
            secondary_axis_vector=secondary_axis_vector, world_up_axis_vector=world_up_axis_vector,
            orient_children=bool(self.properties.affect_children))
        self.alignJoint.emit(event)

    def edit_lra(self):
        """
        Enters component mode, switch on edit local rotation axis and turns handle visibility on.
        """

        self.editLra.emit()

    def exit_lra(self):
        """
        Exists component mode and turns off local rotation axis.
        """

        self.exitLra.emit()

    def align_to_parent(self):
        """
        Aligns selected joint to its parent.
        """

        self.alignToParent.emit()

    def zero_rotation_axis(self):
        """
        Zeroes out the rotation of axis of the selected joints.
        """

        event = ZeroRotationAxisEvent(orient_children=bool(self.properties.affect_children.value))
        self.zeroRotationAxis.emit(event)

    def rotate_lra(self, negative: bool = False):
        """
        Rotate Local Rotation Axis of selected joints.

        :param bool negative: whether to rotate lra in negative value.
        """

        modifiers = qt.QApplication.keyboardModifiers()
        multiplier = 2.0 if modifiers == qt.Qt.ShiftModifier else 0.5 if modifiers == qt.Qt.ControlModifier else 1.0

        lra_rotate_value = self.properties.rotate_lra.value * multiplier
        lra_rotate_value = -lra_rotate_value if negative else lra_rotate_value
        if self.properties.rotate_lra_axis == 0:
            lra_rotation = [lra_rotate_value, 0.0, 0.0]
        elif self.properties.rotate_lra_axis == 1:
            lra_rotation = [0.0, lra_rotate_value, 0.0]
        else:
            lra_rotation = [0.0, 0.0, lra_rotate_value]
        event = RotateLraEvent(lra_rotation=lra_rotation, orient_children=bool(self.properties.affect_children.value))

        self.rotateLra.emit(event)

    def draw_joint(self, mode: consts.JointDrawMode):
        """
        Sets the joint draw visibility of the selected joints.

        :param consts.JointDrawMode name of the draw mode: Mode to draw joint with.
        """

        event = SetJointDrawModeEvent(mode=mode, affect_children=bool(self.properties.affect_children.value))
        self.setJointDrawMode.emit(event)

    def set_lra_visibility(self, visibility: bool = True):
        """
        Shows/Hides the joints local rotation axis.

        :param bool visibility: True to show local rotation axis manipulators; False to hidde them.
        """

        event = SetLraVisibilityEvent(visibility=visibility, affect_children=self.properties.affect_children.value)
        self.setLraVisibility.emit(event)

    def mirror_joint(self):
        """
        Mirror joint/s across a given plane.
        """

        event = MirrorSelectedJointsEvent(
            mirror_mode=self.properties.mirror_mode.value,
            mirror_axis={0: 'X', 1: 'Y', 2: 'Z'}[self.properties.mirror_axis.value])
        self.mirrorSelectedJoints.emit(event)

    def joint_scale_compensate(self):
        """
        Turns the segment scale compensate on/off for the selected joints.
        """

        event = JointScaleCompensateToggleEvent(
            compensate=self.properties.joint_scale_compensate_ratio.value,
            affect_children=self.properties.affect_children.value)
        self.jointScaleCompensate.emit(event)

    def display_joint_size(self):
        """
        Sets the global joint display size.
        """

        event = SetGlobalJointDisplaySizeEvent(size=self.properties.joint_global_display_size.value)
        self.setGlobalJointDisplaySize.emit(event)

    def set_joint_radius(self):
        """
        Sets the joint radius for selected joints
        """

        event = SetJointRadiusEvent(
            radius=self.properties.joint_radius.value, affect_children=self.properties.affect_children.value)
        self.setJointRadius.emit(event)

    def freeze_to_matrix(self):
        """
        Sets an object translate and rotate to be zero and scale to be one.
        """

        event = FreezeMatrixEvent(affect_children=self.properties.affect_children.value)
        self.freezeMatrix.emit(event)

    def reset_matrix(self):
        """
        Reset an object offset matrix to be zero.
        """

        event = ResetMatrixEvent(affect_children=self.properties.affect_children.value)
        self.resetMatrix.emit(event)

    def update_joints_properties(self):
        """
        Updates tool model based on the first selected joint properties.
        """

        event = UpdateJointsPropertiesEvent()
        self.updateJointsProperties.emit(event)
        if event.joint_global_scale is not None:
            self.properties.joint_global_display_size.value = event.joint_global_scale
        if event.joint_local_radius is not None:
            self.properties.joint_radius.value = event.joint_local_radius
        if event.joint_scale_compensate is not None:
            self.properties.joint_scale_compensate_ratio.value = event.joint_scale_compensate
        self.update_widgets_from_properties()


class JointToolboxView(qt.QWidget):
    def __init__(self, tool_instance: JointToolBox, parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

        self._tool = tool_instance

        self._accordion: qt.AccordionWidget | None = None
        self._orient_widget: qt.QWidget | None = None
        self._select_radio_widget: qt.RadioButtonGroup | None = None
        self._reset_ui_button: qt.BaseButton | None = None
        self._primary_axis_combo: qt.ComboBoxRegularWidget | None = None
        self._secondary_axis_combo: qt.ComboBoxRegularWidget | None = None
        self._world_up_axis_combo: qt.ComboBoxRegularWidget | None = None
        self._start_end_arrow_chain_button: qt.LeftAlignedButton | None = None
        self._start_end_chain_button: qt.LeftAlignedButton | None = None
        self._select_plane_arrow_ctrl_button: qt.LeftAlignedButton | None = None
        self._orient_y_pos_button: qt.LeftAlignedButton | None = None
        self._orient_y_neg_button: qt.LeftAlignedButton | None = None
        self._edit_lra_button: qt.LeftAlignedButton | None = None
        self._exit_lra_button: qt.LeftAlignedButton | None = None
        self._align_parent_button: qt.LeftAlignedButton | None = None
        self._zero_rotation_axis_button: qt.LeftAlignedButton | None = None
        self._rotate_axis_lra_combo: qt.ComboBoxRegularWidget | None = None
        self._rotate_lra_line: qt.FloatLineEditWidget | None = None
        self._rotate_lra_negative_button: qt.BaseButton | None = None
        self._rotate_lra_positive_button: qt.BaseButton | None = None
        self._draw_style_widget: qt.QWidget | None = None
        self._draw_bone_button: qt.LeftAlignedButton | None = None
        self._draw_none_button: qt.LeftAlignedButton | None = None
        self._draw_joint_button: qt.LeftAlignedButton | None = None
        self._draw_multi_button: qt.LeftAlignedButton | None = None
        self._show_lra_button: qt.LeftAlignedButton | None = None
        self._hide_lra_button: qt.LeftAlignedButton | None = None
        self._mirror_widget: qt.QWidget | None = None
        self._mirror_behavior_radio: qt.RadioButtonGroup | None = None
        self._mirror_combo: qt.ComboBoxRegularWidget | None = None
        self._mirror_button: qt.LeftAlignedButton | None = None
        self._size_widget: qt.QWidget | None = None
        self._scale_compensate_radio: qt.RadioButtonGroup | None = None
        self._global_display_size_edit: qt.FloatLineEditWidget | None = None
        self._joint_radius_edit: qt.FloatLineEditWidget | None = None
        self._matrix_offsets_widget: qt.QWidget | None = None
        self._freeze_offset_matrix_button: qt.LeftAlignedButton | None = None
        self._reset_offset_matrix_button: qt.LeftAlignedButton | None = None
        self._create_position_widget: qt.QWidget | None = None

        self.setup_widgets()
        self.setup_layouts()
        self.link_properties()

        self._on_world_up_axis_combo_current_index_changed()

    @property
    def tool(self) -> JointToolBox:
        """
        Getter method that returns tool instance.

        :return: tool instance.
        :rtype: JointToolBox
        """

        return self._tool

    @override
    def enterEvent(self, event: qt.QEvent) -> None:
        super().enterEvent(event)

        self.tool.check_meta_nodes()

    def setup_widgets(self):
        """
        Function that setup widgets.
        """

        self._select_radio_widget = qt.RadioButtonGroup(
            radio_names=['Selected', 'Hierarchy'], tooltips=consts.RADIO_TOOLTIPS,
            margins=(qt.consts.SUPER_LARGE_SPACING_2, 0, qt.consts.SUPER_LARGE_SPACING_2, 0),
            spacing=qt.consts.SUPER_EXTRA_LARGE_SPACING, alignment=qt.Qt.AlignLeft,  parent=self)
        self._reset_ui_button = qt.styled_button(
            '', icon='refresh', min_width=qt.consts.BUTTON_WIDTH_ICON_MEDIUM, tooltip=consts.RESET_UI_BUTTON_TOOLTIP,
            parent=self)

        self._accordion = qt.AccordionWidget(parent=self)
        self._accordion.rollout_style = qt.AccordionStyle.ROUNDED

        self._orient_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Orient', self._orient_widget)
        self._primary_axis_combo = qt.ComboBoxRegularWidget(
            label='Aim Axis', items=consts.XYZ_WITH_NEG_LIST, set_index=0, tooltip=consts.PRIMARY_AXIS_COMBO_TOOLTIP,
            parent=self)
        self._secondary_axis_combo = qt.ComboBoxRegularWidget(
            label='Roll Up', items=consts.XYZ_LIST, set_index=1, tooltip=consts.SECONDARY_AXIS_COMBO_TOOLTIP,
            parent=self)
        self._world_up_axis_combo = qt.ComboBoxRegularWidget(
            label='World Up', items=consts.XYZ_LIST + ['Up Ctrl', 'Plane'], set_index=1,
            tooltip=consts.WORLD_UP_AXIS_COMBO_TOOLTIP, parent=self)

        self._start_end_arrow_chain_button = qt.left_aligned_button(
            'Position Ctrl (Right Click)', icon='exit', tooltip=consts.START_END_ARROW_CHAIN_BUTTON_TOOLTIP,
            parent=self)
        self._start_end_chain_button = qt.left_aligned_button(
            'Position Ctrl (Right-Click)', icon='plane', tooltip=consts.START_END_ARROW_CHAIN_BUTTON_TOOLTIP,
            parent=self)
        self._select_plane_arrow_ctrl_button = qt.left_aligned_button(
            'Select Control', icon='cursor', tooltip=consts.SELECT_PLANE_ARROW_CONTROL_BUTTON_TOOLTIP, parent=self)
        self._orient_y_pos_button = qt.left_aligned_button(
            'Orient Roll +Y (Aim X)', icon='arrow_up', tooltip=consts.ORIENT_Y_POSITIVE_BUTTON_TOOLTIP, parent=self)
        self._orient_y_neg_button = qt.left_aligned_button(
            'Orient Roll -Y (Aim X)', icon='arrow_down', tooltip=consts.ORIENT_Y_NEGATIVE_BUTTON_TOOLTIP, parent=self)
        self._edit_lra_button = qt.left_aligned_button(
            'Edit LRA', icon='edit', tooltip=consts.EDIT_LRA_BUTTON_TOOLTIP, parent=self)
        self._exit_lra_button = qt.left_aligned_button(
            'Exit LRA', icon='exit', tooltip=consts.EXIT_LRA_BUTTON_TOOLTIP, parent=self)
        self._align_parent_button = qt.left_aligned_button(
            'Align To Parent', icon='manipulator', tooltip=consts.ALIGN_PARENT_BUTTON_TOOLTIP, parent=self)
        self._zero_rotation_axis_button = qt.left_aligned_button(
            'Zero Rotation Axis', icon='check', tooltip=consts.ZERO_ROTATION_AXIS_BUTTON_TOOLTIP, parent=self)
        self._rotate_axis_lra_combo = qt.ComboBoxRegularWidget(
            'Rotation Axis', items=consts.XYZ_LIST, tooltip=consts.ROTATE_COMBO_TOOLTIP, parent=self)
        self._rotate_lra_line = qt.FloatLineEditWidget(
            label='', text=self.tool.properties.rotate_lra.value, tooltip=consts.ROTATE_LRA_TOOLTIP, parent=self)
        self._rotate_lra_negative_button = qt.styled_button(
            '', icon='arrow_rotation_left', min_width=qt.consts.BUTTON_WIDTH_ICON_MEDIUM,
            tooltip=consts.ROTATE_LRA_BUTTON_TOOLTIP, parent=self)
        self._rotate_lra_positive_button = qt.styled_button(
            '', icon='arrow_rotation_right', min_width=qt.consts.BUTTON_WIDTH_ICON_MEDIUM,
            tooltip=consts.ROTATE_LRA_BUTTON_TOOLTIP, parent=self)

        self._draw_style_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Draw Style', self._draw_style_widget)
        self._draw_bone_button = qt.left_aligned_button(
            'Bone', icon='skeleton', tooltip=consts.DRAW_BONE_BUTTON_TOOLTIP, parent=self)
        self._draw_none_button = qt.left_aligned_button(
            'None', icon='skeleton_hide', tooltip=consts.DRAW_BONE_BUTTON_TOOLTIP, parent=self)
        self._draw_joint_button = qt.left_aligned_button(
            'Joint', icon='joint', tooltip=consts.DRAW_BONE_BUTTON_TOOLTIP, parent=self)
        self._draw_multi_button = qt.left_aligned_button(
            'Multi-Box', icon='cube_wire', tooltip=consts.DRAW_BONE_BUTTON_TOOLTIP, parent=self)
        self._show_lra_button = qt.left_aligned_button(
            'Show Local Rotation Axis', icon='axis', tooltip=consts.SHOW_LRA_BUTTON_TOOLTIP, parent=self)
        self._hide_lra_button = qt.left_aligned_button(
            'Hide Local Rotation Axis', icon='axis', tooltip=consts.HIDE_LRA_BUTTON_TOOLTIP, parent=self)

        self._mirror_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Mirror', self._mirror_widget)
        self._mirror_behavior_radio = qt.RadioButtonGroup(
            radio_names=['Mirror Orientation', 'Mirror Behavior'], tooltips=consts.MIRROR_BEHAVIOR_RADIO_TOOLTIPS,
            default=1, margins=(qt.consts.SPACING, 0, qt.consts.SPACING, qt.consts.SPACING), parent=self)
        self._mirror_combo = qt.ComboBoxRegularWidget(
            'Mirror Axis', items=consts.XYZ_LIST, tooltip=consts.MIRROR_COMBO_TOOLTIP, parent=self)
        self._mirror_button = qt.left_aligned_button(
            'Mirror', icon='mirror', tooltip=consts.MIRROR_BUTTON_TOOLTIP, parent=self)

        self._size_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Size', self._size_widget)
        self._scale_compensate_radio = qt.RadioButtonGroup(
            radio_names=['Scale Compensate Off', 'Scale Compensate On'],
            tooltips=consts.SCALE_COMPENSATE_RADIO_TOOLTIPS, default=1,
            margins=(qt.consts.SPACING, qt.consts.SPACING, qt.consts.SPACING, qt.consts.SPACING), parent=self)
        self._global_display_size_edit = qt.FloatLineEditWidget(
            'Scene Joint Size', tooltip=consts.SCENE_JOINT_SIZE_TOOLTIP, parent=self)
        self._joint_radius_edit = qt.FloatLineEditWidget(
            'Local Joint Radius', tooltip=consts.JOINT_RADIUS_EDIT_TOOLTIP, parent=self)

        self._matrix_offsets_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Matrix & Offset', self._matrix_offsets_widget)
        self._freeze_offset_matrix_button = qt.left_aligned_button(
            'Freeze To Offset Matrix', icon='matrix', tooltip=consts.FREEZE_TO_OFFSET_MATRIX_BUTTON_TOOLTIP,
            parent=self)
        self._reset_offset_matrix_button = qt.left_aligned_button(
            'Unfreeze Offset Matrix', icon='matrix', tooltip=consts.RESET_OFFSET_MATRIX_BUTTON_TOOLTIP, parent=self)

        self._create_position_widget = qt.QWidget(parent=self)
        self._accordion.add_item('Create & Position', self._create_position_widget)

    def setup_layouts(self):
        """
        Function that creates all UI layouts and add all widgets to them.
        """

        contents_layout = qt.vertical_layout(
            margins=(
                qt.consts.WINDOW_SIDE_PADDING, qt.consts.WINDOW_BOTTOM_PADDING,
                qt.consts.WINDOW_SIDE_PADDING, qt.consts.WINDOW_BOTTOM_PADDING),
            spacing=qt.consts.SPACING, parent=self)
        self.setLayout(contents_layout)

        select_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        select_layout.addWidget(self._select_radio_widget)
        select_layout.addStretch()
        select_layout.addWidget(self._reset_ui_button)

        orient_main_layout = qt.vertical_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        self._orient_widget.setLayout(orient_main_layout)
        axis_layout = qt.horizontal_layout(
            margins=(qt.consts.SMALL_SPACING, qt.consts.SMALL_SPACING, qt.consts.SMALL_SPACING, 0),
            spacing=qt.consts.SUPER_EXTRA_LARGE_SPACING)
        axis_layout.addWidget(self._primary_axis_combo, 5)
        axis_layout.addWidget(self._secondary_axis_combo, 5)
        axis_layout.addWidget(self._world_up_axis_combo, 5)
        control_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        control_layout.addWidget(self._start_end_arrow_chain_button)
        control_layout.addWidget(self._start_end_chain_button)
        control_layout.addWidget(self._select_plane_arrow_ctrl_button)
        orient_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        orient_layout.addWidget(self._orient_y_pos_button)
        orient_layout.addWidget(self._orient_y_neg_button)
        edit_lra_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        edit_lra_layout.addWidget(self._edit_lra_button)
        edit_lra_layout.addWidget(self._exit_lra_button)
        zero_parent_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        zero_parent_layout.addWidget(self._align_parent_button)
        zero_parent_layout.addWidget(self._zero_rotation_axis_button)
        rotate_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        rotate_layout.addWidget(self._rotate_axis_lra_combo)
        rotate_layout.addWidget(self._rotate_lra_line)
        rotate_buttons_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        rotate_buttons_layout.addWidget(self._rotate_lra_negative_button)
        rotate_buttons_layout.addWidget(self._rotate_lra_positive_button)
        rotate_layout.addLayout(rotate_buttons_layout)

        orient_main_layout.addLayout(axis_layout)
        orient_main_layout.addLayout(control_layout)
        orient_main_layout.addLayout(orient_layout)
        orient_main_layout.addLayout(edit_lra_layout)
        orient_main_layout.addLayout(zero_parent_layout)
        orient_main_layout.addLayout(rotate_layout)

        draw_style_layout = qt.vertical_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        self._draw_style_widget.setLayout(draw_style_layout)
        draw_buttons_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        draw_buttons_layout.addWidget(self._draw_bone_button)
        draw_buttons_layout.addWidget(self._draw_none_button)
        draw_buttons_layout.addWidget(self._draw_joint_button)
        draw_buttons_layout.addWidget(self._draw_multi_button)
        display_lra_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        display_lra_layout.addWidget(self._show_lra_button)
        display_lra_layout.addWidget(self._hide_lra_button)
        draw_style_layout.addLayout(draw_buttons_layout)
        draw_style_layout.addLayout(display_lra_layout)

        mirror_layout = qt.vertical_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        mirror_bottom_layout = qt.horizontal_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        mirror_bottom_layout.addWidget(self._mirror_combo, 1)
        mirror_bottom_layout.addWidget(self._mirror_button, 1)
        mirror_layout.addWidget(self._mirror_behavior_radio)
        mirror_layout.addLayout(mirror_bottom_layout)
        self._mirror_widget.setLayout(mirror_layout)

        size_layout = qt.vertical_layout(margins=(0, 0, 0, 0), spacing=qt.consts.SPACING)
        size_bottom_layout = qt.horizontal_layout(
            margins=(0, 0, 0, qt.consts.DEFAULT_SPACING), spacing=qt.consts.SUPER_LARGE_SPACING)
        size_bottom_layout.addWidget(self._global_display_size_edit, 1)
        size_bottom_layout.addWidget(self._joint_radius_edit, 1)
        size_layout.addWidget(self._scale_compensate_radio)
        size_layout.addLayout(size_bottom_layout)
        self._size_widget.setLayout(size_layout)

        matrix_layout = qt.horizontal_layout(margins=(0, 0, 0, qt.consts.DEFAULT_SPACING), spacing=qt.consts.SPACING)
        matrix_layout.addWidget(self._freeze_offset_matrix_button)
        matrix_layout.addWidget(self._reset_offset_matrix_button)
        self._matrix_offsets_widget.setLayout(matrix_layout)

        contents_layout.addLayout(select_layout)
        contents_layout.addWidget(self._accordion)

    def link_properties(self):
        """
        Function that link between UI widgets and tool UI properties.
        """

        self.tool.link_property(self._select_radio_widget, 'affect_children')
        self.tool.link_property(self._primary_axis_combo, 'primary_axis')
        self.tool.link_property(self._secondary_axis_combo, 'secondary_axis')
        self.tool.link_property(self._world_up_axis_combo, 'world_up')
        self.tool.link_property(self._rotate_axis_lra_combo, 'rotate_lra_axis')
        self.tool.link_property(self._rotate_lra_line, 'rotate_lra')
        self.tool.link_property(self._mirror_behavior_radio, 'mirror_mode')
        self.tool.link_property(self._mirror_combo, 'mirror_axis')
        self.tool.link_property(self._scale_compensate_radio, 'joint_scale_compensate_ratio')
        self.tool.link_property(self._global_display_size_edit, 'joint_global_display_size')
        self.tool.link_property(self._joint_radius_edit, 'joint_radius')

    def setup_signals(self):
        """
        Function that creates all the signal connections for all the widgets contained within this UI.
        """

        self._reset_ui_button.clicked.connect(self._on_reset_ui_button_clicked)
        self._primary_axis_combo.currentIndexChanged.connect(self._on_primary_axis_combo_current_index_changed)
        self._secondary_axis_combo.currentIndexChanged.connect(self._on_secondary_axis_combo_current_index_changed)
        self._world_up_axis_combo.currentIndexChanged.connect(self._on_world_up_axis_combo_current_index_changed)
        self._start_end_arrow_chain_button.clicked.connect(self.tool.set_start_end_nodes)
        self._orient_y_pos_button.clicked.connect(partial(self.tool.align_joint, align_up=True))
        self._orient_y_neg_button.clicked.connect(partial(self.tool.align_joint, align_up=False))
        self._edit_lra_button.clicked.connect(self.tool.edit_lra)
        self._exit_lra_button.clicked.connect(self.tool.exit_lra)
        self._align_parent_button.clicked.connect(self.tool.align_to_parent)
        self._zero_rotation_axis_button.clicked.connect(self.tool.zero_rotation_axis)
        self._rotate_lra_negative_button.clicked.connect(partial(self.tool.rotate_lra, negative=True))
        self._rotate_lra_positive_button.clicked.connect(partial(self.tool.rotate_lra, negative=False))
        self._draw_bone_button.clicked.connect(partial(self.tool.draw_joint, mode=consts.JointDrawMode.Bone))
        self._draw_none_button.clicked.connect(partial(self.tool.draw_joint, mode=consts.JointDrawMode.Hide))
        self._draw_joint_button.clicked.connect(partial(self.tool.draw_joint, mode=consts.JointDrawMode.Joint))
        self._draw_multi_button.clicked.connect(partial(self.tool.draw_joint, mode=consts.JointDrawMode.MultiBoxChild))
        self._show_lra_button.clicked.connect(partial(self.tool.set_lra_visibility, visibility=True))
        self._hide_lra_button.clicked.connect(partial(self.tool.set_lra_visibility, visibility=False))
        self._mirror_button.clicked.connect(self.tool.mirror_joint)
        self._scale_compensate_radio.toggled.connect(self.tool.joint_scale_compensate)
        self._global_display_size_edit.textModified.connect(self.tool.display_joint_size)
        self._joint_radius_edit.textModified.connect(self.tool.set_joint_radius)
        self._freeze_offset_matrix_button.clicked.connect(self.tool.freeze_to_matrix)
        self._reset_offset_matrix_button.clicked.connect(self.tool.reset_matrix)

        self.tool.callbacks.add_selection_changed_callback(self._on_selection_changed_callback)

    def _update_orient_buttons(self):
        """
        Internal function that updates orient Y position and Y negative buttons text based on current tool properties.
        """

        self._orient_y_pos_button.setText(
            f'Orient Roll +{consts.XYZ_LIST[self.tool.properties.secondary_axis.value]} '
            f'(Aim {consts.XYZ_WITH_NEG_LIST[self.tool.properties.primary_axis.value]})')
        self._orient_y_pos_button.setText(
            f'Orient Roll -{consts.XYZ_LIST[self.tool.properties.secondary_axis.value]} '
            f'(Aim {consts.XYZ_WITH_NEG_LIST[self.tool.properties.primary_axis.value]})')

    def _on_reset_ui_button_clicked(self):
        """
        Internal callback function that is called each time Reset UI button is clicked by the user.
        """

        self.tool.reset_ui()

        # Force the deletion of plane/arrow orient meta nodes and hides arrow/plane buttons.
        self._on_world_up_axis_combo_current_index_changed()

    def _on_primary_axis_combo_current_index_changed(self):
        """
        Internal callback function that is called each time primary axis combobox index is changed by the user.
        """

        aim_index = self.tool.properties.primary_axis.value
        roll_up_index = self.tool.properties.secondary_axis.value
        if aim_index == roll_up_index:
            if roll_up_index == 1:
                self.tool.properties.secondary_axis.value = 2      # If Y, make Z
            else:
                self.tool.properties.secondary_axis.value = 1      # If Z or X, make Y

        self.tool.properties.rotate_lra_axis.value = aim_index

        self.tool.update_widgets_from_properties()
        self._update_orient_buttons()

    def _on_secondary_axis_combo_current_index_changed(self):
        """
        Internal callback function that is called each time secondary axis combo box index is changed by the user.
        """

        aim_index = self.tool.properties.primary_axis.value
        roll_up_index = self.tool.properties.secondary_axis.value
        if aim_index == roll_up_index:
            if roll_up_index == 0:
                self.tool.properties.primary_axis.value = 2              # If X, make Z
                self.tool.properties.rotate_lra_axis.value = 2           # Set rotate to the roll up to match.
            else:
                self.tool.properties.primary_axis.value = 0              # If Z or Y, make X
                self.tool.properties.rotate_lra_axis.value = 0           # Set rotate to the roll up to match.

        self.tool.update_widgets_from_properties()
        self._update_orient_buttons()

    def _on_world_up_axis_combo_current_index_changed(self):
        """Internal callback function that is called each time world up axis combo box index is changed by the user.

        Shows the visibility of the arrow and plane buttons and handles the showing or deletion of the plane/arrow meta
        nodes.
        """

        world_up = self.tool.properties.world_up.value
        if world_up <= 2:
            arrow_visibility = False
            plane_visibility = False
            either = False
        elif world_up == 3:
            arrow_visibility = True
            plane_visibility = False
            either = True
        else:
            arrow_visibility = False
            plane_visibility = True
            either = True

        self._select_plane_arrow_ctrl_button.setVisible(either)
        self._start_end_arrow_chain_button.setVisible(arrow_visibility)
        self._start_end_chain_button.setVisible(plane_visibility)

        self.tool.delete_reference_plane()
        self.tool.check_meta_nodes()

        if plane_visibility:
            self.tool.set_plane_orient_position_snap(True)
        elif arrow_visibility:
            self.tool.set_plane_orient_position_snap(False)

    def _on_selection_changed_callback(self, *args, **kwargs):
        """
        Internal callback function that is called each time scene selection changes.
        """

        selection = scene.FnScene().active_selection()
        if not selection:
            return

        self.tool.update_joints_properties()
