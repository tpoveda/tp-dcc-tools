#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related with Maya API
"""

from __future__ import print_function, division, absolute_import

from maya.api import OpenMaya, OpenMayaRender, OpenMayaUI, OpenMayaAnim

from tp.maya.api.types import *
from tp.maya.api.attributetypes import *
from tp.maya.api import consts
from tp.maya.api import factory
from tp.maya.api import env
from tp.maya.api.base import (
	node_by_name, nodes_by_names, nodes_by_type_names, node_by_object, iterate_selected, selected, select,
	clear_selection, lock_node_context, plug_by_name, lock_node_plug_context, lock_state_attr_context, DGNode, DagNode,
	ObjectSet, ContainerAsset, SkinCluster, BlendShape, DisplayLayer, Mesh, NurbsCurve, IkHandle, Joint, Plug,
	LOCAL_TRANSLATE_ATTRS, LOCAL_ROTATE_ATTRS, LOCAL_SCALE_ATTRS, LOCAL_TRANSFORM_ATTRS
)
from tp.maya.api.contexts import namespace_context
from tp.maya.api.spaceswitch import (
	CONSTRAINT_TYPES, CONSTRAINT_CLASSES, TP_CONSTRAINTS_ATTR_NAME, build_constraint, iterate_constraints
)
from tp.maya.api.animation import set_rotation_order_over_frames
from tp.maya.api.nodes import root_node, average_position, average_normal_vector
