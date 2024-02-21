#!#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related to maya filter types
"""

from collections import OrderedDict

import maya.cmds

from tp.core import log
from tp.common.python import helpers

logger = log.tpLogger

GEO_SUFFIX = 'geo'
JOINT_SUFFIX = 'jnt'
CONTROLLER_SUFFIX = 'ctrl'
CONSTRAINT_SUFFIX = 'cnstr'
GROUP_SUFFIX = 'grp'
SRT_SUFFIX = 'srt'
LEFT_SUFFIX = 'L'
LEFT2_SUFFIX = 'lft'
RIGHT_SUFFIX = 'R'
RIGHT2_SUFFIX = 'rgt'
CENTER_SUFFIX = 'M'
CENTER2_SUFFIX = 'cntr'
CENTER3_SUFFIX = 'mid'
LOW_SUFFIX = 'low'
HIGH_SUFFIX = 'high'
LORES_SUFFIX = 'lores'
HIRES_SUFFIX = 'hires'
CURVE_SUFFIX = 'crv'
CLUSTER_SUFFIX = 'cstr'
FOLLICLE_SUFFIX = 'foli'
NURBS_SUFFIX = 'geo'
IMAGE_PLANE_SUFFIX = 'imgp'
LOCATOR_SUFFIX = 'loc'
LIGHT_SUFFIX = 'lgt'
SHADER_SUFFIX = 'shdr'
SHADING_GROUP_SUFFIX = 'shdg'
CAMERA_SUFFIX = 'cam'

SUFFIX_LIST = [
    'Select...',
    f'Mesh: "{GEO_SUFFIX}"',
    f'Joint: "{JOINT_SUFFIX}"',
    f'Control: "{CONTROLLER_SUFFIX}"',
    f'Constraint: "{CONSTRAINT_SUFFIX}"',
    f'Group: "{GROUP_SUFFIX}"',
    f'Rot Trans Scl: "{SRT_SUFFIX}"',
    f'Left: "{LEFT_SUFFIX}"',
    f'Left: "{LEFT2_SUFFIX}"',
    f'Right: "{RIGHT_SUFFIX}"',
    f'Right: "{RIGHT2_SUFFIX}"',
    f'Center: "{CENTER_SUFFIX}"',
    f'Center: "{CENTER2_SUFFIX}"',
    f'Center: "{CENTER3_SUFFIX}"',
    f'Low: "{LOW_SUFFIX}"',
    f'High: "{HIGH_SUFFIX}"',
    f'Lores: "{LORES_SUFFIX}"',
    f'Hires: "{HIRES_SUFFIX}"',
    f'Camera: "{CAMERA_SUFFIX}"',
    f'Curve: "{CURVE_SUFFIX}"',
    f'Cluster: "{CLUSTER_SUFFIX}"',
    f'Follicle: "{FOLLICLE_SUFFIX}"',
    f'Nurbs: "{NURBS_SUFFIX}"',
    f'Image Plane: "{IMAGE_PLANE_SUFFIX}"',
    f'Locator: "{LOCATOR_SUFFIX}"',
    f'Shader: "{SHADER_SUFFIX}"',
    f'Light: "{LIGHT_SUFFIX}"',
    f'Shading Group: "{SHADING_GROUP_SUFFIX}"',
]

AUTO_SUFFIX_DICT = {
    'mesh': GEO_SUFFIX,
    'joint': JOINT_SUFFIX,
    'nurbsCurve': CURVE_SUFFIX,
    'group': GROUP_SUFFIX,
    'follicle': FOLLICLE_SUFFIX,
    'nurbsSurface': GEO_SUFFIX,
    'imagePlane': IMAGE_PLANE_SUFFIX,
    'aiAreaLight': LIGHT_SUFFIX,
    'rsPhysicalLight': LIGHT_SUFFIX,
    'PxrRectLight': LIGHT_SUFFIX,
    'PxrSphereLight': LIGHT_SUFFIX,
    'PxrDiskLight': LIGHT_SUFFIX,
    'PxrDistantLight': LIGHT_SUFFIX,
    'PxrDomeLight': LIGHT_SUFFIX,
    'VRayLightRectShape': LIGHT_SUFFIX,
    'VRaySunShape': LIGHT_SUFFIX,
    'VRayLightDomeShape': LIGHT_SUFFIX,
    'locator': LOCATOR_SUFFIX,
    'light': LIGHT_SUFFIX,
    'lambert': SHADER_SUFFIX,
    'blinn': SHADER_SUFFIX,
    'phong': SHADER_SUFFIX,
    'rampShader': SHADER_SUFFIX,
    'phongE': SHADER_SUFFIX,
    'surfaceShader': SHADER_SUFFIX,
    'useBackground': SHADER_SUFFIX,
    'shadingGroup': SHADING_GROUP_SUFFIX,
    'aiStandardSurface': SHADER_SUFFIX,
    'RedshiftMaterial': SHADER_SUFFIX,
    'VRayMtl': SHADER_SUFFIX,
    'PxrSurface': SHADER_SUFFIX,
    'controller': CONTROLLER_SUFFIX,
    'camera': CAMERA_SUFFIX,
    'clusterHandle': CLUSTER_SUFFIX,
    'parentConstraint': CONSTRAINT_SUFFIX,
    'pointConstraint': CONSTRAINT_SUFFIX,
    'orientConstraint': CONSTRAINT_SUFFIX,
    'aimConstraint': CONSTRAINT_SUFFIX,
    'matrixConstraint': CONSTRAINT_SUFFIX
}

ALL_FILTER_TYPE = 'All Node Types'
GROUP_FILTER_TYPE = 'Group'
GEOMETRY_FILTER_TYPE = 'Geometry'
POLYGON_FILTER_TYPE = 'Polygon'
SPHERE_FILTER_TYPE = 'Sphere'
BOX_FILTER_TYPE = 'Box'
CYLINDER_FILTER_TYPE = 'Cylinder'
CAPSULE_FILTER_TYPE = 'Capsule'
NURBS_FILTER_TYPE = 'Nurbs'
JOINT_FILTER_TYPE = 'Joint'
CURVE_FILTER_TYPE = 'Curve'
CIRCLE_FILTER_TYPE = 'Circle'
LOCATOR_FILTER_TYPE = 'Locator'
LIGHT_FILTER_TYPE = 'Light'
CAMERA_FILTER_TYPE = 'Camera'
CLUSTER_FILTER_TYPE = 'Cluster'
FOLLICLE_FILTER_TYPE = 'Follicle'
DEFORMER_FILTER_TYPE = 'Deformer'
TRANSFORM_FILTER_TYPE = 'Transform'
CONTROLLER_FILTER_TYPE = 'Controller'
PARTICLE_FILTER_TYPE = 'Particle'
NETWORK_FILTER_TYPE = 'Network'

TYPE_FILTERS = OrderedDict([
    (ALL_FILTER_TYPE, 'All'),
    (GROUP_FILTER_TYPE, 'Group'),
    (GEOMETRY_FILTER_TYPE, ['mesh', 'nurbsSurface']),
    (POLYGON_FILTER_TYPE, ['polygon']),
    (SPHERE_FILTER_TYPE, ['sphere']),
    (BOX_FILTER_TYPE, ['box']),
    (CYLINDER_FILTER_TYPE, ['cylinder']),
    (CAPSULE_FILTER_TYPE, ['capsule']),
    (NURBS_FILTER_TYPE, ['nurbsSurface']),
    (JOINT_FILTER_TYPE, ['joint']),
    (CURVE_FILTER_TYPE, ['nurbsCurve']),
    (CIRCLE_FILTER_TYPE, ['circle']),
    (LOCATOR_FILTER_TYPE, ['locator']),
    (LIGHT_FILTER_TYPE, ['light']),
    (CAMERA_FILTER_TYPE, ['camera']),
    (CLUSTER_FILTER_TYPE, ['cluster']),
    (FOLLICLE_FILTER_TYPE, ['follicle']),
    (DEFORMER_FILTER_TYPE, [
        'clusterHandle', 'baseLattice', 'lattice', 'softMod', 'deformBend', 'sculpt',
        'deformTwist', 'deformWave', 'deformFlare']),
    (TRANSFORM_FILTER_TYPE, ['transform']),
    (CONTROLLER_FILTER_TYPE, ['control']),
    (PARTICLE_FILTER_TYPE, ['particle']),
    (NETWORK_FILTER_TYPE, ['network'])
])


PROTECTED_NODES = [
    "layerManager", "renderLayerManager", "poseInterpolatorManager", "defaultRenderLayer",
    "defaultLayer", "lightLinker1", "shapeEditorManager"
]


def filter_all_node_types(
        selection_only=True, search_hierarchy=False, dag=False, transforms_only=False, remove_maya_defaults=True):
    """
    Function that filters current scene objects by node types
    :param selection_only:
    :param search_hierarchy:
    :param dag:
    :param transforms_only:
    :param remove_maya_defaults:
    :return:
    """

    # Import here to avoid cyclic imports
    from tpDcc.dccs.maya.core import camera

    if not selection_only:
        all_objs = maya.cmds.ls(long=True, dagObjects=search_hierarchy, dag=dag)
        if not remove_maya_defaults:
            protected = maya.cmds.ls(defaultNodes=True) + PROTECTED_NODES
            scene_filtered = list(set(all_objs) - set(protected))
            if not transforms_only:
                return scene_filtered
            else:
                return filter_transforms_from_shapes_list(scene_filtered)

        default_cameras = camera.get_startup_camera_transforms() + camera.get_startup_camera_shapes()
        maya_defaults = default_cameras + maya.cmds.ls(defaultNodes=True) + PROTECTED_NODES
        scene_filtered = list(set(all_objs) - set(maya_defaults))
        if not transforms_only:
            return scene_filtered
        else:
            return filter_transforms_from_shapes_list(scene_filtered)

    all_selected_objs = maya.cmds.ls(sl=True, long=True, dagObjects=search_hierarchy, dag=dag)
    if not all_selected_objs:
        logger.warning('No objects selected, select at least one please!')
        return list()

    if not transforms_only:
        return all_selected_objs
    else:
        return filter_transforms_from_shapes_list(all_selected_objs)


def filter_transforms_from_shapes_list(objs_list, allow_joints=True, allow_dg=True):
    """
    If a shape node is found in given objects, it will be replace by its transform parent
    :param objs_list: list(str), list of Maya object names
    :param allow_joints: bool, Whether to include joints in the returned list or not. They will be treat as
        transform nodes
    :param allow_dg: bool, Whether to return DG nodes in the returned list of not.
    :return: list(str)
    """

    transform_list = list()

    for obj in objs_list:
        if maya.cmds.objectType(obj, isType='transform'):
            transform_list.append(obj)
        elif allow_joints and maya.cmds.objectType(obj, isType='joint'):
            transform_list.append(obj)
        else:
            if 'dagNode' in maya.cmds.nodeType(obj, inherited=True):
                transform_list.append(maya.cmds.listRelatives(obj, parent=True, fullPath=True)[0])
            elif allow_dg:
                # Not DAG nodes do not have transform nodes, we add them directly
                transform_list.append(obj)

    return list(set(transform_list))


def filter_by_group(selection_only, search_hierarchy, dag):
    """
    Returns nodes that are groups (empty transform nodes with no shape nodes)
    :param selection_only: bool, Whether to search all scene objects or only selected ones
    :param search_hierarchy: bool, Whether to search the hierarchy below the objects list or not
    :param dag: bool, Whether to only return DAG nodes or not
    :return: list(str( .list of group nodes
    """

    objs_list = list()
    group_list = list()

    if selection_only:
        objs_list = maya.cmds.ls(sl=True, long=True)
        if not objs_list:
            logger.warning('Nothing is selected, please select at least one object!')
            return list()

    obj_transforms = filter_list_by_types(
        filter_types='transform', objs_list=objs_list, search_hierarchy=search_hierarchy,
        selection_only=selection_only, dag=dag)
    if not obj_transforms:
        logger.warning('No groups found!')
        return list()

    # We check again to avoid not wanted transforms (such as joints, or shape nodes)
    for obj in obj_transforms:
        if not maya.cmds.listRelatives(obj, shapes=True) and maya.cmds.objectType(obj, isType='transform'):
            group_list.append(obj)

    return group_list


def filter_dag_transforms(filter_types, search_hierarchy=False, selection_only=True, dag=False, transforms_only=True):
    """
    Returns a list of Maya objects that match filter type and returns only transform parent of shape nodes
    :param filter_types: list(str), list of node types to filter by
    :param search_hierarchy: bool, Whether to search objects in hierarchies
    :param selection_only: bool, Whether to search all scene objects or only selected ones
    :param dag: bool, Whether to return only DAG nodes
    :param transforms_only: bool, Whether to return only transform nodes or not
    :return: list(str), list of filtered DAG transform nodes
    """

    if selection_only:
        sel_objs = maya.cmds.ls(sl=True, long=True)
        if not sel_objs:
            logger.warning('No objects selected. Please select at least one!')
            return list()
        shapes_list = maya.cmds.listRelatives(sel_objs, shapes=True, fullPath=True)
        if shapes_list:
            sel_objs += shapes_list
        filtered_shapes = filter_list_by_types(
            filter_types=filter_types, objs_list=sel_objs, search_hierarchy=search_hierarchy, dag=dag)
    else:
        filtered_shapes = filter_list_by_types(
            filter_types=filter_types, search_hierarchy=search_hierarchy, selection_only=selection_only, dag=dag)

    if not transforms_only:
        return filtered_shapes

    return filter_transforms_from_shapes_list(filtered_shapes)


def filter_by_type(
        filter_type, search_hierarchy=False, selection_only=True, dag=False, remove_maya_defaults=True,
        transforms_only=True, keep_order=False):
    """
    Returns a list of objects that match the given node type
    :param filter_type: str
    :param search_hierarchy: bool, Whether to search objects in hierarchies
    :param selection_only: bool, Whether to search all scene objects or only selected ones
    :param dag: bool, Whether to return only DAG nodes
    :param remove_maya_defaults: Whether to ignore Maya default nodes or not
    :param transforms_only: bool, Whether to return only transform nodes or not
    :param keep_order: bool, Whether or not take into account the order of selection and hierarchy
    :return:
    """

    if not selection_only:
        search_hierarchy = False

    obj_type_list = TYPE_FILTERS.get(filter_type, None)
    # logger.debug('Filtering by Type "{}"'.format(filter_type))

    if keep_order:
        if selection_only:
            sel_objs = maya.cmds.ls(sl=True, long=True, dagObjects=search_hierarchy)
            filtered_result = filter_by_type(
                filter_type=filter_type, search_hierarchy=search_hierarchy, selection_only=selection_only, dag=dag,
                remove_maya_defaults=remove_maya_defaults, transforms_only=transforms_only, keep_order=False)
            remove_result = [obj for obj in sel_objs if obj not in filtered_result]
            return [obj for obj in sel_objs if obj not in remove_result]
        else:
            return filter_by_type(
                filter_type=filter_type, search_hierarchy=search_hierarchy, selection_only=selection_only, dag=dag,
                remove_maya_defaults=remove_maya_defaults, transforms_only=transforms_only, keep_order=False)
    else:
        if not obj_type_list or obj_type_list == ALL_FILTER_TYPE:
            return filter_all_node_types(
                selection_only=selection_only, search_hierarchy=search_hierarchy, transforms_only=transforms_only,
                dag=dag, remove_maya_defaults=remove_maya_defaults)
        elif obj_type_list == GROUP_FILTER_TYPE:
            return filter_by_group(selection_only=selection_only, search_hierarchy=search_hierarchy, dag=dag)
        else:
            return filter_dag_transforms(
                filter_types=obj_type_list, search_hierarchy=search_hierarchy, selection_only=selection_only, dag=dag)


def filter_list_by_types(
        filter_types, objs_list=None, search_hierarchy=False, selection_only=True, dag=False):
    """
    Returns a list of objecst that match the given node type
    :param filter_types: list(str), list of node types to filter by
    :param objs_list: list(str), list of maya nodes to filter
    :param search_hierarchy: bool, Whether to search objects in hierarchies
    :param selection_only: bool, Whether to search all scene objects or only selected ones
    :param dag: bool, Whether to return only DAG nodes
    :return: list(str), list of filtered objects
    """

    if not filter_types:
        return

    if not objs_list:
        objs_list = list()

    filter_types = helpers.force_list(filter_types)

    filtered_objs = list()
    if not selection_only:
        for filter_type in filter_types:
            filtered_objs += maya.cmds.ls(type=filter_type, long=True, dagObjects=search_hierarchy, dag=dag)
    else:
        for filter_type in filter_types:
            filtered_objs += maya.cmds.ls(objs_list, type=filter_type, long=True, dagObjects=search_hierarchy, dag=dag)

    return list(set(filtered_objs))


def filter_transforms_with_shapes(transforms_list, children=False, shape_type='nurbsCurve', return_as_shapes=False):
    """
    Returns a list of transforms or shapes, returns only those nodes that have shapes nodes of the given type
    :param transforms_list: list(str), list of Maya transform nodes
    :param children: bool, Whether or not children should be taken into consideration
    :param shape_type: str, shape to filter by
    :param return_as_shapes: bool, whether shapes or transforms should be returned
    :return: list(str), list of transform nodes that contain shapes of the given type
    """

    transforms_with_shapes_of_type = list()
    transforms_shapes = list()
    full_objs_list = helpers.force_list(transforms_list)
    if children:
        joints = maya.cmds.listRelatives(transforms_list, children=True, allDescendents=True, f=True, type='joint')
        if joints:
            full_objs_list += joints
        transforms = maya.cmds.listRelatives(
            transforms_list, children=True, allDescendents=True, f=True, type='transform')
        if transforms:
            full_objs_list += joints
        full_objs_list = list(set(full_objs_list))

    for obj in full_objs_list:
        shapes = maya.cmds.listRelatives(obj, shapes=True, fullPath=True, type=shape_type)
        if shapes:
            transforms_with_shapes_of_type.append(obj)
            transforms_shapes.extend(shapes)

    if not return_as_shapes:
        return list(set(transforms_with_shapes_of_type))

    return list(set(transforms_shapes))


def filter_transforms_shapes(transforms_list, children=False, shape_type='nurbsCurve'):
    """
    Returns a list of shapes in the given list of transforms
    :param transforms_list: list(str), list of Maya transform nodes
    :param children: bool, Whether or not children should be taken into consideration
    :param shape_type: str, shape to filter by
    :return: list(str), list of shape nodes of the given type
    """

    return filter_transforms_with_shapes(
        transforms_list=transforms_list, children=children, shape_type=shape_type, return_as_shapes=True)


def filter_nodes_with_shapes(nodes_list, shape_type='nurbsCurve'):
    """
    Returns a list of shapes filtered by the given type from a list that can include transforms or shapes
    :param nodes_list: list(str), list of Maya nodes
    :param shape_type: str, the shape type we want to filter by
    :return: list(str), list of shape nodes
    """

    shapes_found = list()

    nodes_list = helpers.force_list(nodes_list)
    for node in nodes_list:
        if maya.cmds.objectType(node, isType='transform') or maya.cmds.objectType(node, isType='joint'):
            shapes_found += filter_transforms_with_shapes([node], shape_type=shape_type, return_as_shapes=True)
        elif maya.cmds.objectType(node, isType=shape_type):
            shapes_found.append(node)

    return shapes_found
