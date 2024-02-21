#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains custom Pin Locator used by CRIT
"""

from __future__ import print_function, division, absolute_import

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.api.OpenMayaRender as OpenMayaRender

from tp.libs.rig.crit.plugin.pinlocator import utils, shapes


def maya_useNewAPI():
    pass


class PinLocator(OpenMayaUI.MPxLocatorNode):

    ID = OpenMaya.MTypeId(0x45534)
    DRAW_DB_CLASSIFICATION = 'drawdb/geometry/critPinLocator'
    DRAW_REGISTRANT_ID = 'critPinLocatorPlugin'
    SELECTION_MASK_NAME = 'critPinLocatorSelectionMask'

    draw_shape_attr = OpenMaya.MObject()
    shape_attr = OpenMaya.MObject()
    transform_attr = OpenMaya.MObject()
    local_rotate_attr = OpenMaya.MObject()
    color_attr = OpenMaya.MObject()
    alpha_attr = OpenMaya.MObject()
    border_color_attr = OpenMaya.MObject()
    border_alpha_attr = OpenMaya.MObject()
    border_line_width_attr = OpenMaya.MObject()
    xray_attr = OpenMaya.MObject()
    joint_node_attr = OpenMaya.MObject()
    draw_gizmo_attr = OpenMaya.MObject()
    gizmo_size_attr = OpenMaya.MObject()
    is_main_attr = OpenMaya.MObject()

    def __init__(self):
        super().__init__()

    @property
    def draw_shape(self):
        return OpenMaya.MPlug(self.thisMObject(), self.draw_shape_attr).asBool()

    @property
    def xray(self):
        return OpenMaya.MPlug(self.thisMObject(), self.xray_attr).asBool()

    @property
    def draw_gizmo(self):
        return OpenMaya.MPlug(self.thisMObject(), self.draw_gizmo_attr).asBool()

    @property
    def gizmo_size(self):
        return OpenMaya.MPlug(self.thisMObject(), self.gizmo_size_attr).asFloat()

    @classmethod
    def creator(cls):
        return cls()

    @classmethod
    def initialize(cls):

        enum_attr = OpenMaya.MFnEnumAttribute()
        mat_attr = OpenMaya.MFnMatrixAttribute()
        u_attr = OpenMaya.MFnUnitAttribute()
        num_attr = OpenMaya.MFnNumericAttribute()
        msg_attr = OpenMaya.MFnMessageAttribute()

        # shape enumerator attribute
        cls.shape_attr = enum_attr.create('shape', 'sh', 0)
        for index, shape in enumerate(shapes.SHAPES):
            enum_attr.addField(shape['name'], index)
        enum_attr.channelBox = True
        cls.addAttribute(cls.shape_attr)

        # transform attribute
        cls.transform_attr = mat_attr.create('transform', 't', OpenMaya.MFnMatrixAttribute.kFloat)
        mat_attr.keyable = False
        cls.addAttribute(cls.transform_attr)

        # local rotate attribute
        local_rotate_x = u_attr.create('localRotateX', 'lrx', OpenMaya.MFnUnitAttribute.kAngle, 0.0)
        local_rotate_y = u_attr.create('localRotateY', 'lry', OpenMaya.MFnUnitAttribute.kAngle, 0.0)
        local_rotate_z = u_attr.create('localRotateZ', 'lrz', OpenMaya.MFnUnitAttribute.kAngle, 0.0)
        cls.local_rotate_attr = num_attr.create('localRotate', 'lr', local_rotate_x, local_rotate_y, local_rotate_z)
        num_attr.channelBox = True
        num_attr.keyable = False
        cls.addAttribute(cls.local_rotate_attr)

        # draw shape attribute
        cls.draw_shape_attr = num_attr.create('drawShape', 'ds', OpenMaya.MFnNumericData.kBoolean, True)
        num_attr.channelBox = True
        num_attr.keyable = False
        cls.addAttribute(cls.draw_shape_attr)

        # color attribute
        cls.color_attr = num_attr.createColor('color', 'dc')
        num_attr.default = (0.38, 0.0, 0.02)
        cls.addAttribute(cls.color_attr)

        # alpha attribute
        cls.alpha_attr = num_attr.create('alpha', 'a', OpenMaya.MFnNumericData.kFloat, 0.333)
        num_attr.setSoftMin(0)
        num_attr.setSoftMax(1)
        num_attr.keyable = False
        cls.addAttribute(cls.alpha_attr)

        # border color attribute
        cls.border_color_attr = num_attr.createColor('borderColor', 'bc')
        num_attr.default = (-1, -1, -1)
        cls.addAttribute(cls.border_color_attr)

        # border alpha attribute
        cls.border_alpha_attr = num_attr.create('borderAlpha', 'ba', OpenMaya.MFnNumericData.kFloat, 1.0)
        num_attr.setSoftMin(0)
        num_attr.setSoftMax(1)
        num_attr.keyable = False
        cls.addAttribute(cls.border_alpha_attr)

        # border-line width attribute
        cls.border_line_width_attr = num_attr.create('borderWidth', 'bw', OpenMaya.MFnNumericData.kFloat, 2.0)
        num_attr.setSoftMin(0)
        num_attr.setSoftMax(10)
        num_attr.keyable = False
        cls.addAttribute(cls.border_line_width_attr)

        # xray attribute
        cls.xray_attr = num_attr.create('xray', 'xr', OpenMaya.MFnNumericData.kBoolean, True)
        num_attr.channelBox = True
        num_attr.keyable = False
        cls.addAttribute(cls.xray_attr)

        # draw gizmo attribute
        cls.draw_gizmo_attr = num_attr.create('drawGizmo', 'dg', OpenMaya.MFnNumericData.kBoolean)
        num_attr.keyable = True
        num_attr.default = False
        cls.addAttribute(cls.draw_gizmo_attr)

        # gizmo size attribute
        cls.gizmo_size_attr = num_attr.create('gizmoSize', 'gs', OpenMaya.MFnNumericData.kFloat, 1.0)
        num_attr.setSoftMin(0.01)
        num_attr.setSoftMax(100)
        cls.addAttribute(cls.gizmo_size_attr)

        # joint attribute
        cls.joint_node_attr = msg_attr.create('joint', 'jnt')
        cls.addAttribute(cls.joint_node_attr)

        # is main attribute
        cls.is_main_attr = num_attr.create('main', 'mn', OpenMaya.MFnNumericData.kBoolean)
        num_attr.keyable = False
        num_attr.default = False
        cls.addAttribute(cls.is_main_attr)

    def isBounded(self):
        return True

    def boundingBox(self):
        return self._get_shape_bounds(self.get_shape())

    def postConstructor(self):
        dependency_node = OpenMaya.MFnDependencyNode(self.thisMObject())
        dependency_node.setName('critPinLocatorShape#')

    def setDependentsDirty(self, plug, affected_plugs):
        plug = plug if not plug.isChild else plug.parent()

        # discard our transformed shape
        if any([plug == self.transform_attr, plug == self.localPosition, plug == self.local_rotate_attr,
                plug == self.localScale]):
            if hasattr(self, 'transformed_shape'):
                del self.transformed_shape

        # force bounding box recalculation
        if any([plug == self.transform_attr, plug == self.shape_attr, plug == self.localPosition,
                plug == self.local_rotate_attr, plug == self.localScale, plug == self.color_attr,
                plug == self.alpha_attr, plug == self.border_color_attr, plug == self.border_alpha_attr,
                plug == self.xray_attr, plug == self.draw_shape_attr]):
            OpenMayaRender.MRenderer.setGeometryDrawDirty(self.thisMObject(), True)

        if plug == self.shape_attr:
            if hasattr(self, 'transformed_shape'):
                del self.transformed_shape
            if hasattr(self, 'shape'):
                del self.shape

        return super(PinLocator, self).setDependentsDirty(plug, affected_plugs)

    def getShapeSelectionMask(self):
        mask = OpenMaya.MSelectionMask()
        # mask.addMask(OpenMaya.MSelectionMask.kSelectMeshes)
        # mask.addMask(OpenMaya.MSelectionMask.kSelectJoints)
        # mask.addMask(OpenMaya.MSelectionMask.kSelectJointPivots)
        mask.addMask(OpenMaya.MSelectionMask.getSelectionTypePriority(PinLocator.SELECTION_MASK_NAME))

        return mask

    def get_shape_index(self):
        return OpenMaya.MPlug(self.thisMObject(), self.shape_attr).asShort()

    def get_shape(self):
        if not hasattr(self, 'shape'):
            self.shape = self._get_shape_from_plug()
        if not hasattr(self, 'transformed_shape'):
            shape = self.shape
            transform = self._get_local_transform()
            self.transformed_shape = utils.transform_shape(shape, transform)

        return self.transformed_shape

    def _get_shape_from_plug(self):
        index = self.get_shape_index()
        shape = shapes.SHAPES[index]['geometry']

        return shape

    def _get_local_transform(self):
        mobj = self.thisMObject()

        transform_plug = OpenMaya.MPlug(mobj, self.transform_attr)
        transform = OpenMaya.MFnMatrixData(transform_plug.asMObject()).matrix()
        matrix = OpenMaya.MTransformationMatrix(transform)

        # apply local translation
        local_translate_plug = OpenMaya.MPlug(mobj, self.localPosition)
        local_translation = OpenMaya.MVector(*[local_translate_plug.child(idx).asFloat() for idx in range(3)])
        matrix.translateBy(local_translation, OpenMaya.MSpace.kObject)

        # apply local rotation
        local_rotate_plug = OpenMaya.MPlug(mobj, self.local_rotate_attr)
        local_rotate_plugs = [local_rotate_plug.child(idx) for idx in range(3)]
        local_rotate = OpenMaya.MVector(*[local_rotate_plugs[idx].asMAngle().asRadians() for idx in range(3)])
        matrix.rotateBy(OpenMaya.MEulerRotation(local_rotate), OpenMaya.MSpace.kObject)

        # apply local scale
        local_scale_plug = OpenMaya.MPlug(mobj, self.localScale)
        local_scale = OpenMaya.MFnNumericData(local_scale_plug.asMObject()).getData()
        matrix.scaleBy(local_scale, OpenMaya.MSpace.kObject)

        return matrix.asMatrix()

    def _get_shape_bounds(self, shape):
        bounding_box = OpenMaya.MBoundingBox()
        for item in shape.values():
            for point in item:
                bounding_box.expand(point)

        return bounding_box


class PinLocatorData(OpenMaya.MUserData):
    def __init__(self):
        super(PinLocatorData, self).__init__(False)     # do not delete after draw

        self.shape = None
        self.draw_shape = True
        self.color = OpenMaya.MColor((0.6, 0.2, 0.5))
        self.alpha = 1.0
        self.border_color = OpenMaya.MColor((-1, -1, -1))
        self.border_alpha = 1.0
        self.radius = 1.0
        self.xray = False
        self.draw_gizmo = False
        self.gizmo_size = 1.0
        self.local_matrix = OpenMaya.MMatrix()
        self.joint = None


class PinLocatorDrawOverride(OpenMayaRender.MPxDrawOverride):
    def __init__(self, obj):
        super(PinLocatorDrawOverride, self).__init__(obj, None, False)

        self._initalize_temporal_attribute()

    @staticmethod
    def creator(obj):
        return PinLocatorDrawOverride(obj)

    @staticmethod
    def draw(context, data):
        return

    def supportedDrawAPIs(self):
        return OpenMayaRender.MRenderer.kOpenGL | OpenMayaRender.MRenderer.kDirectX11 | \
               OpenMayaRender.MRenderer.kOpenGLCoreProfile

    def isBounded(self, obj_path, camera_path):
        return True

    def boundingBox(self, obj_path, camera_path):
        dependency_node = OpenMaya.MFnDependencyNode(obj_path.node())
        user_node = dependency_node.userNode()
        return user_node.boundingBox()

    def disableInternalBoundingBoxDraw(self):
        return True

    def prepareForDraw(self, obj_path, camera_path, frame_context, old_data):

        data = old_data
        if not isinstance(data, PinLocatorData):
            data = PinLocatorData()

        node = obj_path.node()
        dependency_node = OpenMaya.MFnDependencyNode(node)
        user_node = dependency_node.userNode() if dependency_node else None

        is_selected = utils.is_path_selected(obj_path)
        data.draw_shape = user_node.draw_shape
        data.xray = user_node.xray
        data.draw_gizmo = user_node.draw_gizmo
        data.gizmo_size = user_node.gizmo_size
        color_plug = OpenMaya.MPlug(node, PinLocator.color_attr)
        data.color = OpenMaya.MColor(OpenMaya.MFnNumericData(color_plug.asMObject()).getData())
        data.alpha = OpenMaya.MPlug(node, PinLocator.alpha_attr).asFloat()
        data.color.a = data.alpha
        data.local_matrix = self._get_local_matrix(node)

        if is_selected:
            data.border_color = OpenMayaRender.MGeometryUtilities.wireframeColor(obj_path)
        else:
            border_color_plug = OpenMaya.MPlug(node, PinLocator.border_color_attr)
            data.border_color = OpenMaya.MColor(OpenMaya.MFnNumericData(border_color_plug.asMObject()).getData())
            # if not color has been set and we are on the default of (-1, -1, -1), use main color so in the common
            # case where you want to use the same you do not have to set both
            if data.border_color.r == -1 and data.border_color.g == -1 and data.border_color.b == -1:
                data.border_color = OpenMaya.MColor(data.color)
            data.border_color.a = OpenMaya.MPlug(node, PinLocator.border_alpha_attr).asFloat()

        data.shape = user_node.get_shape()

        return data

    def hasUIDrawables(self):
        return True

    def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
        if not data or not isinstance(data, PinLocatorData):
            return

        if not data.draw_shape:
            return

        if data.xray:
            draw_manager.beginDrawInXray()

        draw_manager.beginDrawable()

        for item_type, mesh_data in data.shape.items():
            if item_type == OpenMayaRender.MUIDrawManager.kLines:
                # xray only
                continue
            draw_manager.setColor(data.color)
            draw_manager.setDepthPriority(5)
            draw_manager.mesh(item_type, mesh_data)
            # draw_manager.sphere(OpenMaya.MPoint(0.0, 0.0, 0.0), data.radius, True)

        lines = data.shape.get(OpenMayaRender.MUIDrawManager.kLines)
        if lines:
            draw_manager.setColor(data.border_color)
            draw_manager.mesh(OpenMayaRender.MUIDrawManager.kLines, lines)

        if data.draw_gizmo:
            local_matrix = data.local_matrix
            self._draw_arrow(draw_manager, local_matrix, self.xmat, self.xcolor, 'X', data.gizmo_size)
            self._draw_arrow(draw_manager, local_matrix, self.ymat, self.ycolor, 'Y', data.gizmo_size)
            self._draw_arrow(draw_manager, local_matrix, self.zmat, self.zcolor, 'Z', data.gizmo_size)
            draw_manager.setColor(OpenMaya.MColor((1.0, 1.0, 0.0)))
            draw_manager.sphere(OpenMaya.MPoint(0, 0, 0), 0.1 * data.gizmo_size, True)

        draw_manager.endDrawable()

        if data.xray:
            draw_manager.endDrawInXray()

    def _initalize_temporal_attribute(self):
        self.xcolor = OpenMaya.MColor(OpenMaya.MVector(1, 0, 0))
        self.xmat = OpenMaya.MMatrix((
            (1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0.8, 0, 0, 1)
        ))

        self.ycolor = OpenMaya.MColor(OpenMaya.MVector(0, 1, 0))
        self.ymat = OpenMaya.MMatrix((
            (1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0.8, 0, 1)
        ))

        self.zcolor = OpenMaya.MColor(OpenMaya.MVector(0, 0, 1))
        self.zmat = OpenMaya.MMatrix((
            (1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0.8, 1)
        ))

    def _get_local_matrix(self, node):

        transform_plug = OpenMaya.MPlug(node, PinLocator.transform_attr)
        transform = OpenMaya.MFnMatrixData(transform_plug.asMObject()).matrix()
        matrix = OpenMaya.MTransformationMatrix(transform)

        # apply local rotation
        local_rotate_plug = OpenMaya.MPlug(node, PinLocator.local_rotate_attr)
        local_rotate_plugs = [local_rotate_plug.child(idx) for idx in range(3)]
        local_rotate = OpenMaya.MVector(*[local_rotate_plugs[idx].asMAngle().asRadians() for idx in range(3)])
        matrix.rotateBy(OpenMaya.MEulerRotation(local_rotate), OpenMaya.MSpace.kObject)

        return matrix.asMatrix()

    def _draw_arrow(self, draw_manager, local_matrix, distance_matrix, color, text, size):
        draw_manager.setColor(color)

        # draw line
        end_matrix = distance_matrix * local_matrix
        posx = end_matrix.getElement(3, 0) * (size * 0.5)
        posy = end_matrix.getElement(3, 1) * (size * 0.5)
        posz = end_matrix.getElement(3, 2) * (size * 0.5)
        end_point = OpenMaya.MPoint(posx, posy, posz)

        base_point = OpenMaya.MPoint(0, 0, 0)

        draw_manager.setLineWidth(size)
        draw_manager.line(base_point, end_point)

        draw_manager.setFontSize(int(size))
        draw_manager.text(end_point, text)

        # draw cone(base, direction, radius, height, filled=False) -> self
        # direction = OpenMaya.MVector()
        # direction.x = posx - base_point.x
        # direction.y = posy - base_point.y
        # direction.z = posz - base_point.z
        # w = 0.1
        # h = 0.2
        # draw_manager.cone(end_point, direction, w, h, True)
        draw_manager.sphere(end_point, 0.01 * size, True)
