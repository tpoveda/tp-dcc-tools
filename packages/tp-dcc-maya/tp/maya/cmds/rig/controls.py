from __future__ import annotations

from typing import Sequence

import maya.cmds as cmds

from tp.core import log, command
from tp.maya.om import nodes
from tp.maya.cmds import filtertypes, node, shape, curve, attribute
from tp.maya.libs.curves.commands import curves

logger = log.tpLogger


CONTROL_ARROW_THIN = 'arrow_one'
TRACKER_TRANSLATE_ATTR_NAME = 'tpTranslateTrack'
TRACKER_TRANSLATE_DEFAULT_ATTR_NAME = 'tpTranslateTrackDefault'
TRACKER_ROTATE_ATTR_NAME = 'tpRotateTrack'
TRACKER_ROTATE_DEFAULT_ATTR_NAME = 'tpRotateTrackDefault'
TRACKER_SCALE_ATTR_NAME = 'tpScaleTrack'
TRACKER_SCALE_DEFAULT_ATTR_NAME = 'tpScaleTrackDefault'
TRACKER_COLOR_ATTR_NAME = 'tpColorTrack'
TRACKER_COLOR_DEFAULT_ATTR_NAME = 'tpColorDefault'
TRACKER_SHAPE_ATTR_NAME = 'tpShapeTrack'
TRACKER_SHAPE_DEFAULT_ATTR_NAME = 'tpShapeTrackDefault'
ALL_TRANSFORM_TRACKER_ATTRIBUTE_NAMES = [
    TRACKER_TRANSLATE_ATTR_NAME, TRACKER_TRANSLATE_DEFAULT_ATTR_NAME,
    TRACKER_ROTATE_ATTR_NAME, TRACKER_ROTATE_DEFAULT_ATTR_NAME,
    TRACKER_SCALE_ATTR_NAME, TRACKER_SCALE_DEFAULT_ATTR_NAME
]
ALL_COLOR_TRACKER_ATTRIBUTE_NAMES = [
    TRACKER_COLOR_ATTR_NAME, TRACKER_COLOR_DEFAULT_ATTR_NAME
]


def create_control_curve(
        folder_path: str = '', control_name: str = 'control', curve_scale: Sequence[float, float, float] | None = None,
        curve_type: str = 'circle', add_suffix: bool = True, shape_parent: str = '',
        rotate_offset: Sequence[float, float, float] | None = None, track_scale: bool = True, line_width: int = -1,
        rgb_color: Sequence[float, float, float] | None = None, add_to_undo: bool = True) -> list[str]:
    """
    Creates a control curve, using the specific curve from curves library.

    :param str folder_path: optional directory where curves library to use is located. If empty, default curves library
        directory will be used.
    :param str control_name: name of the control to create.
    :param tuple[float, float, float] curve_scale: scale of each control (in Maya units).
    :param str curve_type: name of the curve to use for the control.
    :param bool add_suffix: whether to add an underscore and suffix to the control.
    :param str shape_parent: If given, curve shape will be parented to this object.
    :param tuple[float, float, float] rotate_offset: optional CV rotation offset for the control curves.
    :param bool track_scale: whether to add scale tracking attributes for the control.
    :param int line_width: width of the curve lines (in pixels). If -1 (default value) global preferences value will be
        used.
    :param list[float, float, float] rgb_color: optional linear RGB color for the control curves.
    :param bool add_to_undo: whether to add create control curve operation to Maya undo queue.
    :return: long name of the newly created control curves.
    :rtype: list[str]
    """

    if add_suffix:
        control_name = '_'.join((control_name, filtertypes.CONTROLLER_SUFFIX))
    if shape_parent:
        control_name = ''.join((control_name, 'Shape'))

    placement_object = nodes.mobject_by_name(shape_parent) if shape_parent else None

    if folder_path:
        if add_to_undo:
            _, curve_objects = command.execute(
                'tp.maya.curves.createFromFilePath', curve_type=curve_type, folder_path=folder_path,
                parent=placement_object)
        else:
            cmd = curves.CreateCurveFromFilePath()
            _, curve_objects = cmd.run_arguments(
                curve_type=curve_type, folder_path=folder_path, parent=placement_object)
    else:
        if add_to_undo:
            _, curve_objects = command.execute(
                'tp.maya.curves.createFromLib', curve_type=curve_type, parent=placement_object)
        else:
            cmd = curves.CreateCurveFromLibrary()
            _, curve_objects = cmd.run_arguments(curve_type=curve_type, parent=placement_object)

    if shape_parent:
        for shape_object in curve_objects:
            nodes.rename(shape_object, control_name)
        curve_names = nodes.names_from_mobjs(curve_objects)
    else:
        nodes.rename(curve_objects[0], control_name)
        curve_names = [nodes.names_from_mobjs(curve_objects)[0]]

    if rotate_offset is not None:
        shape.rotate_nodes_cvs(curve_names, rotate_offset)
    if curve_scale is not None:
        shape.scale_nodes_cvs(curve_names, curve_scale)
    if line_width != -1:
        curve.set_curves_line_thickness(curve_names, line_width)
    if rgb_color is not None:
        node.set_nodes_rgb_color(curve_names, rgb_color, linear=True)
    if track_scale:
        shape_parent = shape_parent or curve_names[0]
        add_control_tracker_attributes(shape_parent, curve_scale, curve_type=curve_type, color=rgb_color)

    return curve_names


def add_control_tracker_attributes(
        transform_name, translate: Sequence[float, float, float] = (0.0, 0.0, 0.0),
        rotate: Sequence[float, float, float] = (0.0, 0.0, 0.0),
        scale: Sequence[float, float, float] = (1.0, 1.0, 1.0),
        color: Sequence[float, float, float] | None = None, curve_type: str = 'circle'):
    """
    Adds control tracker attributes to the given transform node to track scale/color values.

    :param str transform_name: name of the transform to track transforms of
    :param Sequence[float, float, float] translate: initial translation values.
    :param Sequence[float, float, float] rotate: initial rotation values.
    :param Sequence[float, float, float] scale: initial scale values.
    :param Sequence[float, float, float] or None color: initial color values.
    :param str curve_type: initial curve type.
    """

    # Add translation, rotation and scale track attributes.
    for attr_name in ALL_TRANSFORM_TRACKER_ATTRIBUTE_NAMES:
        if not cmds.attributeQuery(attr_name, node=transform_name, exists=True):
            cmds.addAttr(transform_name, longName=attr_name, attributeType='double3')
            for axis in 'xyz':
                axis_attr = f'{attr_name}_{axis}'
                if not cmds.attributeQuery(axis_attr, node=transform_name, exists=True):
                    cmds.addAttr(transform_name, longName=axis_attr, attributeType='double', parent=attr_name)

    # Add color track attributes.
    for attr_name in ALL_COLOR_TRACKER_ATTRIBUTE_NAMES:
        if not cmds.attributeQuery(attr_name, node=transform_name, exists=True):
            cmds.addAttr(transform_name, longName=attr_name, attributeType='double3')
            for axis in 'rgb':
                color_attr = f'{attr_name}_{axis}'
                if not cmds.attributeQuery(color_attr, node=transform_name, exists=True):
                    cmds.addAttr(transform_name, longName=color_attr, attributeType='double', parent=attr_name)

    # Add shape related track attributes.
    if not cmds.attributeQuery(TRACKER_SHAPE_ATTR_NAME, node=transform_name, exists=True):
        cmds.addAttr(transform_name, longName=TRACKER_SHAPE_ATTR_NAME, dataType='string')
    if not cmds.attributeQuery(TRACKER_SHAPE_DEFAULT_ATTR_NAME, node=transform_name, exists=True):
        cmds.addAttr(transform_name, longName=TRACKER_SHAPE_DEFAULT_ATTR_NAME, dataType='string')

    # Set attribute values.
    cmds.setAttr('.'.join((transform_name, TRACKER_TRANSLATE_ATTR_NAME)), translate[0], translate[1], translate[2])
    cmds.setAttr(
        '.'.join((transform_name, TRACKER_TRANSLATE_DEFAULT_ATTR_NAME)), translate[0], translate[1], translate[2])
    cmds.setAttr('.'.join((transform_name, TRACKER_ROTATE_ATTR_NAME)), rotate[0], rotate[1], rotate[2])
    cmds.setAttr('.'.join((transform_name, TRACKER_ROTATE_DEFAULT_ATTR_NAME)), rotate[0], rotate[1], rotate[2])
    cmds.setAttr('.'.join((transform_name, TRACKER_SCALE_ATTR_NAME)), scale[0], scale[1], scale[2])
    cmds.setAttr('.'.join((transform_name, TRACKER_SCALE_DEFAULT_ATTR_NAME)), scale[0], scale[1], scale[2])

    # We store color. If not given, we retrieve the color of the given transform shapes.
    if color:
        cmds.setAttr('.'.join((transform_name, TRACKER_COLOR_ATTR_NAME)), color[0], color[1], color[2])
        cmds.setAttr('.'.join((transform_name, TRACKER_COLOR_DEFAULT_ATTR_NAME)), color[0], color[1], color[2])
    else:
        shapes = cmds.listRelatives(transform_name, shapes=True, hsv=False, linear=True)
        if shapes:
            color = node.rgb_color(shapes[0], linear=True)
            cmds.setAttr('.'.join((transform_name, TRACKER_COLOR_ATTR_NAME)), color[0], color[1], color[2])
            cmds.setAttr('.'.join((transform_name, TRACKER_COLOR_DEFAULT_ATTR_NAME)), color[0], color[1], color[2])

    cmds.setAttr('.'.join((transform_name, TRACKER_SHAPE_ATTR_NAME)), curve_type, type='string')
    cmds.setAttr('.'.join((transform_name, TRACKER_SHAPE_DEFAULT_ATTR_NAME)), curve_type, type='string')


def freeze_scale_tracker(transform_name) -> bool:
    """
    Freezes the scale tracker attribute setting to a scale of 1.0 no matter the current scale of the given transform.

    :param STR transform_name: transform node we want to freeze scale tracker of.
    :return: True if scale track attributes were frozen successfully; False otherwise.
    :rtype: bool
    """

    if not cmds.attributeQuery(TRACKER_SCALE_ATTR_NAME, node=transform_name, exists=True):
        return False

    xyz_scale = cmds.getAttr('.'.join((transform_name, TRACKER_SCALE_ATTR_NAME)))[0]
    cmds.setAttr('.'.join((transform_name, TRACKER_SCALE_DEFAULT_ATTR_NAME)), xyz_scale[0], xyz_scale[1], xyz_scale[2])

    return True


def freeze_scale_tracker_nodes(transform_names: list[str]):
    """
    Freezes the scale tracker attribute setting to a scale of 1.0 no matter the current scale of the given transforms.

    :param list[str] transform_names: transform nodes we want to freeze scale tracker of.
    :return: list of frozen transform nodes.
    """

    frozen_transforms: list[str] = []
    for transform_to_freeze in transform_names:
        valid_freeze = freeze_scale_tracker(transform_to_freeze)
        if valid_freeze:
            frozen_transforms.append(transform_to_freeze)
    if not frozen_transforms:
        logger.warning('No controls found to be frozen.')
        return


def delete_tracker_attributes(transform_name: str):
    """
    Removes transform tracking attributes from the given transform node.

    :param str transform_name: name of the transform we want to remove tracker attributes of.
    """

    attrs_to_delete = ALL_TRANSFORM_TRACKER_ATTRIBUTE_NAMES + ALL_COLOR_TRACKER_ATTRIBUTE_NAMES + [
        TRACKER_SHAPE_ATTR_NAME, TRACKER_SHAPE_DEFAULT_ATTR_NAME]

    for tracker_attr in attrs_to_delete:
        attribute.safe_delete_attribute(transform_name, tracker_attr)


def delete_tracker_attribute_nodes(transform_names: list[str]):
    """
    Removes transform tracking attributes from the given transform nodes.

    :param list[str] transform_names: name of the transforms we want to remove tracker attributes of.
    """

    for transform_name in transform_names:
        delete_tracker_attributes(transform_name)


def delete_tracker_attributes_selected_nodes():
    """
    Removes transform tracking attributes of the current selected transform nodes.
    """

    delete_tracker_attribute_nodes(cmds.ls(selection=True) or [])
