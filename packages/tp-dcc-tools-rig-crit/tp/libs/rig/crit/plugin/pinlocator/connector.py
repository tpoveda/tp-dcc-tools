#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains custom locator used to draw pin locator connections
"""

from __future__ import print_function, division, absolute_import

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.api.OpenMayaRender as OpenMayaRender


def maya_useNewAPI():
    pass


class PinLocatorConnector(OpenMayaUI.MPxLocatorNode):

    ID = OpenMaya.MTypeId(0x321534)
    DRAW_DB_CLASSIFICATION = 'drawdb/geometry/critPinLocatorConnector'
    DRAW_REGISTRANT_ID = 'critPinLocatorConnector'

    size = OpenMaya.MObject()
    parent_world_matrix = OpenMaya.MObject()
    child_world_matrix = OpenMaya.MObject()
    line_color = OpenMaya.MObject()
    line_width = OpenMaya.MObject()
    num_joints = OpenMaya.MObject()
    joints_color = OpenMaya.MObject()
    joints_width = OpenMaya.MObject()
    xray = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        return cls()

    @classmethod
    def initialize(cls):
        num_fn = OpenMaya.MFnNumericAttribute()
        mat_fn = OpenMaya.MFnMatrixAttribute()

        cls.size = num_fn.create('size', 'size', OpenMaya.MFnNumericData.kFloat, 1.0)
        cls.parent_world_matrix = mat_fn.create('parentWorldMatrix', 'swmat', OpenMaya.MFnMatrixAttribute.kFloat)
        mat_fn.keyable = False
        cls.child_world_matrix = mat_fn.create('childWorldMatrix', 'cwmat', OpenMaya.MFnMatrixAttribute.kFloat)
        mat_fn.keyable = False
        cls.line_color = num_fn.createColor('color', 'color')
        num_fn.default = (1.0, 1.0, 0.0)
        cls.line_width = num_fn.create('width', 'width', OpenMaya.MFnNumericData.kFloat, 2.0)
        cls.num_joints = num_fn.create('numJoints', 'numJonts', OpenMaya.MFnNumericData.kShort, 0)
        cls.joints_color = num_fn.createColor('jointsColor', 'jntColor')
        num_fn.default = (0.0, 0.75, 1.0)
        cls.joints_width = num_fn.create('jointsWidth', 'jntWidth', OpenMaya.MFnNumericData.kFloat, 2.5)
        cls.xray = num_fn.create('xray', 'xr', OpenMaya.MFnNumericData.kBoolean, True)
        num_fn.channelBox = True
        num_fn.keyable = False

        cls.addAttribute(cls.size)
        cls.addAttribute(cls.child_world_matrix)
        cls.addAttribute(cls.parent_world_matrix)
        cls.addAttribute(cls.line_color)
        cls.addAttribute(cls.line_width)
        cls.addAttribute(cls.num_joints)
        cls.addAttribute(cls.joints_color)
        cls.addAttribute(cls.joints_width)
        cls.addAttribute(cls.xray)

    def postConstructor(self, *args):
        dependency_node = OpenMaya.MFnDependencyNode(self.thisMObject())
        dependency_node.setName('critPinLocatorConnectorShape#')

    def compute(self, plug, data):
        return None

    def isBounded(self):
        return False

    def preEvaluation(self, context, evaluation_node):
        if context.isNormal():
            if evaluation_node.dirtyPlugExists(self.parent_world_matrix):
                OpenMayaRender.MRenderer.setGeometryDrawDirty(self.thisMObject())

        return True


class PinLocatorConnectorData(OpenMaya.MUserData):
    def __init__(self):
        super(PinLocatorConnectorData, self).__init__(False)     # do not delete after draw

        self.size = 1.0
        self.color = OpenMaya.MColor((1.0, 1.0, 0.0))
        self.num_joints = 3
        self.joints_color = OpenMaya.MColor((0.0, 0.75, 1.0))
        self.parent_point = OpenMaya.MPoint()
        self.child_point = OpenMaya.MPoint()
        self.width = 2.0
        self.joints_width = 2.5
        self.xray = True


class PinLocatorConnectorDrawOverride(OpenMayaRender.MPxDrawOverride):
    def __init__(self, obj):
        super(PinLocatorConnectorDrawOverride, self).__init__(obj, None, False)

        # we want to perform custom bounding box drawing so return True so that the internal rendering code will not
        # draw it for us
        self._custom_box_draw = True
        self._current_bounding_box = OpenMaya.MBoundingBox()

    @staticmethod
    def creator(obj):
        return PinLocatorConnectorDrawOverride(obj)

    @staticmethod
    def draw(context, data):
        return

    def supportedDrawAPIs(self):
        return OpenMayaRender.MRenderer.kOpenGL | OpenMayaRender.MRenderer.kDirectX11 | \
               OpenMayaRender.MRenderer.kOpenGLCoreProfile

    def isBounded(self, obj_path, camera_path):
        return False

    def disableInternalBoundingBoxDraw(self):
        return self._custom_box_draw

    def traceCallSequence(self):
        # return True if internal tracking is desired.
        return False

    def handleTraceMessage(self, message):
        OpenMaya.MGlobal.displayInfo('drawVectorDrawOverride: {}'.format(message))

    def prepareForDraw(self, obj_path, camera_path, frame_context, old_data):
        data = old_data
        if not data or not isinstance(data, PinLocatorConnectorData):
            data = PinLocatorConnectorData()

        node = obj_path.node()
        dependency_node = OpenMaya.MFnDependencyNode(node)
        user_node = dependency_node.userNode() if dependency_node else None

        data.size = self._get_size(obj_path)
        data.color = self._get_color(obj_path)
        data.width = self._get_width(obj_path)
        parent_world_matrix, child_world_matrix = self._get_world_matrices(obj_path)
        data.parent_point = OpenMaya.MPoint(parent_world_matrix.translation(OpenMaya.MSpace.kWorld))
        data.child_point = OpenMaya.MPoint(child_world_matrix.translation(OpenMaya.MSpace.kWorld))
        data.num_joints = self._get_num_joints(obj_path)
        data.joints_color = self._get_joints_color(obj_path)
        data.joints_width = self._get_joints_width(obj_path)
        data.xray = user_node.xray

        return data

    def hasUIDrawables(self):
        return True

    def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
        if not data or not isinstance(data, PinLocatorConnectorData):
            return

        if data.xray:
            draw_manager.beginDrawInXray()

        draw_manager.beginDrawable(OpenMayaRender.MUIDrawManager.kNonSelectable)

        draw_manager.setColor(data.color)
        draw_manager.setDepthPriority(5)
        draw_manager.setLineWidth(data.width)
        draw_manager.line(data.parent_point, data.child_point)

        # draw end start spheres
        draw_manager.sphere(data.parent_point, 0.1 * data.size, True)
        draw_manager.sphere(data.child_point, 0.1 * data.size, True)

        # draw direction cone
        direction = OpenMaya.MVector(data.child_point - data.parent_point).normalize()
        distance = OpenMaya.MVector(data.child_point - data.parent_point).length()
        direction_vector = (direction * (distance / (2.0 if data.num_joints == 0 else 1.2)))
        mid_pos = OpenMaya.MVector(data.parent_point) + direction_vector
        draw_manager.cone(OpenMaya.MPoint(mid_pos), direction, 0.5 * data.size, 1.0 * data.size, True)

        # draw joints positions
        draw_manager.setColor(data.joints_color)
        draw_manager.setLineWidth(data.joints_width)
        distance_ratio = distance / (data.num_joints + 1)
        total_distance = 0.0
        for i in range(data.num_joints):
            total_distance += distance_ratio
            new_pos = OpenMaya.MPoint(OpenMaya.MVector(data.parent_point) + (direction * total_distance))
            draw_manager.sphere(new_pos, 0.1 * data.size, True)
            draw_manager.circle(new_pos, direction, 0.75 * data.size, False)

        draw_manager.endDrawable()

        if data.xray:
            draw_manager.endDrawInXray()

    def _get_size(self, obj_path):
        size = 1.0
        draw_vector_node = obj_path.node()
        size_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.size)
        if not size_plug.isNull:
            size = size_plug.asFloat()

        return size

    def _get_world_matrices(self, obj_path):
        draw_vector_node = obj_path.node()
        parent_world_matrix_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.parent_world_matrix)
        child_world_matrix_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.child_world_matrix)
        if not parent_world_matrix_plug.isNull:
            parent_handle = parent_world_matrix_plug.asMObject()
            parent_handle_data = OpenMaya.MFnMatrixData(parent_handle)
            parent_world_matrix = OpenMaya.MTransformationMatrix(parent_handle_data.matrix())
            if not child_world_matrix_plug.isNull:
                child_handle = child_world_matrix_plug.asMObject()
                child_handle_data = OpenMaya.MFnMatrixData(child_handle)
                child_world_matrix = OpenMaya.MTransformationMatrix(child_handle_data.matrix())
                return parent_world_matrix, child_world_matrix
            return parent_world_matrix

        return []

    def _get_color(self, obj_path):
        color = OpenMaya.MColor()
        draw_vector_node = obj_path.node()
        color_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.line_color)
        if not color_plug.isNull:
            color_handle = color_plug.asMDataHandle()
            color = OpenMaya.MColor(color_handle.asFloat3())

        return color

    def _get_num_joints(self, obj_path):
        num_joints = 3
        draw_vector_node = obj_path.node()
        num_joints_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.num_joints)
        if not num_joints_plug.isNull:
            num_joints = num_joints_plug.asShort()

        return num_joints

    def _get_joints_color(self, obj_path):
        joints_color = OpenMaya.MColor()
        draw_vector_node = obj_path.node()
        joints_color_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.joints_color)
        if not joints_color_plug.isNull:
            joints_color_handle = joints_color_plug.asMDataHandle()
            joints_color = OpenMaya.MColor(joints_color_handle.asFloat3())

        return joints_color

    def _get_width(self, obj_path):
        width = 1.0
        draw_vector_node = obj_path.node()
        width_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.line_width)
        if not width_plug.isNull:
            width = width_plug.asFloat()

        return width

    def _get_joints_width(self, obj_path):
        width = 1.0
        draw_vector_node = obj_path.node()
        joints_width_plug = OpenMaya.MPlug(draw_vector_node, PinLocatorConnector.joints_width)
        if not joints_width_plug.isNull:
            width = joints_width_plug.asFloat()

        return width
