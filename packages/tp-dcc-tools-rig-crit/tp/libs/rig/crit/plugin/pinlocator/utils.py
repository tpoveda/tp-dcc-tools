#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utilities functions used by Pin Locator used by CRIT
"""

from __future__ import print_function, division, absolute_import

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaRender as OpenMayaRender
import maya.OpenMayaRender as OpenMayaRender1

from tp.libs.rig.crit.plugin.pinlocator import shapes

# NOTE: We need to be very cautious about mixin OpenMaya 2.0 API and OpenMaya 1.0.
# In some special scenarios, like this one can be used, but that is not the general rule.
glRenderer = OpenMayaRender1.MHardwareRenderer.theRenderer()
glFT = glRenderer.glFunctionTable()


def iterate_mesh(iterator):
    """
    Iterates over given mesh polygon iterator.
    :param MItMeshPolygon iterator: mesh polygon iterator.
    :return: yield generator
    :rtype: generator
    """

    while not iterator.isDone():
        yield iterator

        # workaround Maya 2020 removing the iterator.next() parameter.
        if int(cmds.about(version=True)) >= 2020:
            iterator.next()
        else:
            iterator.next(1)


def get_shape_bounds(shape):
    bounding_box = OpenMaya.MBoundingBox()
    for item in shape.values():
        for point in item:
            bounding_box.expand(point)

    return bounding_box


def transform_shape(shape, transform):
    result = dict()
    for key, data in shape.items():
        result[key] = OpenMaya.MPointArray([v * transform for v in data])

    return result


def hit_test_shape(view, shape):
    """
    Function that hit test given shape within given view
    :param view:
    :param shape:
    :return:
    """

    for item_type, data in shape.items():
        view.beginSelect()

        glFT.glBegin(OpenMayaRender1.MGL_TRIANGLES)
        for v in data:
            glFT.glVertex3f(v.x, v.y, v.z)
        glFT.glEnd()

        # Check the hit test.
        if view.endSelect() > 0:
            return True

    return False


def get_custom_shape(mobj, custom_mesh_attr):
    dependency_node = OpenMaya.MFnDependencyNode(mobj)
    user_node = dependency_node.userNode()
    data_block = user_node.forceCache()
    mesh_handle = data_block.inputValue(custom_mesh_attr)

    try:
        it = OpenMaya.MItMeshPolygon(mesh_handle.asMesh())
    except RuntimeError:
        # we will get "kInvalidParameter: argument is a NULL pointer" if there is no mesh connection.
        # TODO: find a better way to check this
        return shapes.SHAPES[0]['geometry']

    tris = list()
    lines = list()
    for face in iterate_mesh(it):
        face = it.getPoints(OpenMaya.MSpace.kObject)
        # the data from the iterator does not stay valid, so make a copy of the point.
        face = [OpenMaya.MPoint(v) for v in face]
        if len(face) == 3:
            tris.extend(face)
            lines.extend((face[0], face[1], face[1], face[2], face[2], face[0]))
        elif len(face) == 4:
            tris.extend((face[0], face[1], face[2], face[2], face[3], face[0]))
            lines.extend((face[0], face[1], face[1], face[2], face[2], face[3], face[3], face[0]))
        else:
            # TODO: Support meshes with more than four faces.
            # TODO: We could triangle with MFnMesh.polyTriangulate maybe?
            pass

    return {OpenMayaRender.MUIDrawManager.kTriangles: tris, OpenMayaRender.MUIDrawManager.kLines: lines}


def is_path_selected(obj_path):
    selection_list = OpenMaya.MGlobal.getActiveSelectionList()
    if selection_list.hasItem(obj_path):
        return True

    obj_path = OpenMaya.MDagPath(obj_path)
    obj_path.pop()
    if selection_list.hasItem(obj_path):
        return True

    return False
