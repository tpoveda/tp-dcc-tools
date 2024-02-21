from __future__ import annotations

import maya.cmds as cmds

from tp.core import log
from tp.maya.cmds import mathlib

from tp.libs.rig.crit.functions import attribute


logger = log.rigLogger


def create_line_guide(
		a: str | None = None, b: str | None = None, name: str | None = None, suffix: str | None = None) -> dict:
	"""
	Creates a line guide from given A node to given B node.

	:param a:
	:param b:
	:param name:
	:param suffix:
	:return: dictionary containing the clusters and the created line curve.
	:rtype: dict
	"""

	if not a and not b:
		a, b = cmds.ls(sl=True)[0:2]

	suffix = suffix or 'GDE'
	name = f'{name}_{suffix}' if name else f'{a}_to_{b}_{suffix}'

	# retrieve start and end positions
	pos_a = cmds.xform(a, query=True, worldSpace=True, translation=True)
	pos_b = cmds.xform(b, query=True, worldSpace=True, translation=True)

	# create guide curve and rename shape and setup drawing options for curve
	crv = cmds.curve(ep=[pos_a, pos_b], degree=1, name=name)
	shp = cmds.listRelatives(crv, shapes=True)[0]
	shape = cmds.rename(shp, f'{crv}Shape')
	cmds.setAttr(f'{shape}.overrideEnabled', True)
	cmds.setAttr(f'{shape}.overrideDisplayType', 1)

	# create and constraint clusters to drive guide
	_, handle_a = cmds.cluster(f'{crv}.cv[0]', name=f'{crv}_start_CLS')
	_, handle_b = cmds.cluster(f'{crv}.cv[1]', name=f'{crv}_end_CLS')
	cmds.pointConstraint(a, handle_a, maintainOffset=True)
	cmds.pointConstraint(b, handle_b, maintainOffset=True)
	cmds.hide(handle_a, handle_b)

	return {'clusters': [handle_a, handle_b], 'curve': crv}


def create_pole_vector_guide(
		guide_list: list[str], name: str | None = None, suffix: str | None = None,
		slide_pole_vector: int | None = None, offset_pole_vector: int = 0,
		delete_setup: bool | None = None) -> str | None:
	"""
	Creates a pole vector guide setup.

	:param guide_list:
	:param name:
	:param suffix:
	:param slide_pole_vector:
	:param offset_pole_vector:
	:param delete_setup:
	:return:
	"""

	guide_list = guide_list or cmds.ls(sl=True)
	if len(guide_list) != 3:
		logger.error('Must pass three transforms to use as guides!')
		return None
	suffix = suffix or 'guide'
	name = name or f'{guide_list[0]}_{suffix}'

	# build pole vector groups
	guide_group = cmds.group(name=f'{name}_GRP', empty=True)
	middle_group = cmds.group(name=f'{name}_middle_GRP', empty=True, parent=guide_group)
	dnt_group = cmds.group(name=f'{name}_DNT_GRP', empty=True, parent=guide_group)
	cls_group = cmds.group(name=f'{name}_CLS_GRP', empty=True, parent=dnt_group)
	cmds.hide(dnt_group)

	# define points of polygon from guides and create polygon plane
	point_list = [cmds.xform(guide, query=True, worldSpace=True, translation=True) for guide in guide_list]
	poly = cmds.polyCreateFacet(p=point_list, name=f'{name}_MSH', constructionHistory=False)[0]

	# create clusters of the plan and constrain them to guides
	for i, vtx in enumerate(cmds.ls(f'{poly}.vtx[*]', flatten=True)):
		_, handle = cmds.cluster(vtx, name='{}_{:02d}_CLS'.format(name, i))
		cmds.pointConstraint(guide_list[i], handle, maintainOffset=False)
		cmds.parent(handle, cls_group)

	# create up vector locator and constraint between the first and last guide and middle group to middle guide
	up_vector_loc = cmds.spaceLocator(name=f'{name}_upV_LOC')[0]
	up_vector_cns = cmds.pointConstraint(guide_list[0], guide_list[-1], up_vector_loc, maintainOffset=False)[0]
	weight_list = cmds.pointConstraint(up_vector_cns, query=True, weightAliasList=True)
	cmds.parentConstraint(guide_list[1], middle_group, maintainOffset=False)

	# create NURBS plane (and hide the NURBS shape) nad create normal constraint from poly to NURB
	nrb = cmds.nurbsPlane(
		name=f'{name}_NRB', pivot=(0, 0, 0), axis=(0, 1, 0), width=0.25, lengthRatio=1, degree=1, patchesU=1,
		patchesV=1, constructionHistory=False)[0]
	surf = cmds.listRelatives(nrb, shapes=True)[0]
	cmds.hide(surf)
	cmds.matchTransform(nrb, guide_list[1])
	cmds.parent(nrb, middle_group)
	cmds.normalConstraint(
		poly, nrb, weight=1, aimVector=(0, 0, 1), upVector=(1, 0, 0), worldUpType='object', worldUpObject=up_vector_loc)

	# create pole vector locator
	pole_vector_loc = cmds.spaceLocator(name=f'{name}_LOC')[0]
	cmds.matchTransform(pole_vector_loc, nrb)
	cmds.parent(pole_vector_loc, nrb)

	# find slide value and give attributes to pole vector locator
	if slide_pole_vector:
		slide_ratio = slide_pole_vector
	else:
		a_len = mathlib.distance_between_points(guide_list[0], guide_list[1])
		b_len = mathlib.distance_between_points(guide_list[1], guide_list[2])
		total_len = a_len + b_len
		slide_ratio = float(b_len) / total_len

	offset = attribute.Attribute(
		name='offset', node=pole_vector_loc, type='double', value=offset_pole_vector, keyable=True)
	slide = attribute.Attribute(
		name='slide', node=pole_vector_loc, type='double', min=0, max=1, value=slide_ratio, keyable=True)

	# calculate distance between mid-joint and up vector
	dist = cmds.createNode('distanceBetween', name=f'{name}_DST')
	adl = cmds.createNode('addDoubleLinear', name=f'{name}_ADL')
	mdl = cmds.createNode('multDoubleLinear', name=f'{name}_MDL')
	rev = cmds.createNode('reverse', name=f'{name}_REV')

	cmds.connectAttr(f'{up_vector_loc}.worldMatrix[0]', f'{dist}.inMatrix1')
	cmds.connectAttr(f'{guide_list[1]}.worldMatrix[0]', f'{dist}.inMatrix2')
	cmds.connectAttr(f'{dist}.distance', f'{adl}.input1')
	cmds.connectAttr(offset.attr, f'{adl}.input2')
	cmds.connectAttr(f'{adl}.output', f'{mdl}.input1')
	cmds.setAttr(f'{mdl}.input2', -1)
	cmds.connectAttr(slide.attr, f'{rev}.inputX')
	cmds.connectAttr(slide.attr, f'{up_vector_cns}.{weight_list[0]}')
	cmds.connectAttr(f'{rev}.outputX', f'{up_vector_cns}.{weight_list[1]}')
	cmds.connectAttr(f'{mdl}.output', f'{pole_vector_loc}.translateX')

	# create and organize guide-lines
	ik_guide = create_line_guide(guide_list[0], guide_list[-1], name=f'{name}_ik')
	pv_guide = create_line_guide(pole_vector_loc, up_vector_loc, name=f'{name}_pv')
	cmds.parent(ik_guide['curve'], pv_guide['curve'], pole_vector_loc)
	cmds.setAttr(f'{ik_guide["curve"]}.inheritsTransform', False)
	cmds.setAttr(f'{ik_guide["curve"]}.translate', 0, 0, 0, 0)
	cmds.setAttr(f'{ik_guide["curve"]}.rotate', 0, 0, 0, 0)
	cmds.setAttr(f'{pv_guide["curve"]}.inheritsTransform', False)
	cmds.setAttr(f'{pv_guide["curve"]}.translate', 0, 0, 0, 0)
	cmds.setAttr(f'{pv_guide["curve"]}.rotate', 0, 0, 0, 0)

	# cleanup
	cmds.parent(poly, up_vector_loc, ik_guide['clusters'], pv_guide['clusters'], dnt_group)
	offset.lock_and_hide(node=pole_vector_loc)

	if delete_setup:
		pv_guide = cmds.xform(pole_vector_loc, query=True, worldSpace=True, translation=True)
		cmds.delete(guide_group)
		return pv_guide

	return pole_vector_loc
