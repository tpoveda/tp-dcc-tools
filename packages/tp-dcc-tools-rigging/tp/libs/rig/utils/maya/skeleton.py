import maya.api.OpenMaya as OpenMaya


def pole_vector_position(start: OpenMaya.MVector, mid: OpenMaya.MVector, end: OpenMaya.MVector, distance: float = -1.0):
	"""
	Returns the position of the pole vector from the given 3 vectors.

	:param OpenMaya.MVector start: start vector.
	:param OpenMaya.MVector mid: mid-vector.
	:param OpenMaya.MVector end: end vector.
	:param float distance: pole vector distance from the mid-position along the normal. If -1, then the distance from
		the start and mid will be used.
	:return: vector position of the pole vector.
	:rtype: OpenMaya.MVector
	:raises ValueError: if no valid angle given to calculate.
	"""

	line = end - start
	point = mid - start
	scale_value = (line * point) / (line * line)
	project_vector = line * scale_value + start

	if tuple(round(i, 3) for i in project_vector) == tuple(round(i, 3) for i in mid):
		raise ValueError('No valid angle to calculate')
	if distance < 0.0:
		distance = point.length()

	return (mid - project_vector).normal() * distance + mid
