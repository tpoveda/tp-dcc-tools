import traceback

import maya.mel as mel
import maya.cmds as cmds

from tp.core import log

logger = log.rigLogger


def clean_scene():
	"""
	Clean up Maya scene.
	"""

	# delete orphaned controller tags
	controller_tags = [
		x for x in cmds.ls(type='controller') if cmds.objExists(x) and not cmds.listConnections(f'{x}.controllerObject')]
	if controller_tags:
		cmds.delete(controller_tags)
		logger.info(f'Scene cleanup deleted controller tags : \n{controller_tags}')

	# delete unused shader nodes
	temp_cube = None
	try:
		# since Maya 2020 an error is thrown when running Delete Unused Nodes if the StandardSurface default shader is
		# unassigned, so we create a temporary object, assign the default StandardSurface material to it, then delete
		# unused and delete the sphere
		temp_cube = cmds.polyCube(name='TEMP_StandardSurface_Assignment')[0]
		temp_standard_shader = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='standardSurface1SG')
		cmds.connectAttr('standardSurface1.outColor', f'{temp_standard_shader}.surfaceShader')
		cmds.sets(temp_cube, edit=True, forceElement=temp_standard_shader)
		mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
	except Exception as err:
		logger.info('Failed to Delete uUnused Nodes')
		logger.info(traceback.format_exc())
	finally:
		if temp_cube and cmds.objExists(temp_cube):
			cmds.delete(temp_cube)

	# delete empty namespaces
	delete_empty_namespaces()

	# delete empty display layers
	delete_empty_display_layers()

	# delete render layers that are not a default layer
	render_layers = [x for x in cmds.ls(type='renderLayer') if x != 'defaultRenderLayer']
	if render_layers:
		cmds.delete(render_layers)
		logger.info(f'Scene cleanup deleted render layers : \n{render_layers}')

	# delete orphaned groupId nodes
	group_id_nodes = [x for x in cmds.ls(type='groupId') if not cmds.listConnections(x)]
	if group_id_nodes:
		cmds.delete(group_id_nodes)
		logger.info(f'Scene cleanup deleted groupID nodes : \n{group_id_nodes}')

	# delete orphaned TimeEditor tracks
	time_editor_tracks = [x for x in cmds.ls(type='timeEditorTracks') if not cmds.listConnections(x)]
	if time_editor_tracks:
		cmds.delete(time_editor_tracks)
		logger.info(f'Scene cleanup deleted TimeEditor tracks : \n{time_editor_tracks}')

	# delete orphaned GraphEditorInfo nodes
	graph_editor_info = [x for x in cmds.ls(type='nodeGraphEditorInfo') if not cmds.listConnections(x)]
	if graph_editor_info:
		cmds.delete(graph_editor_info)
		logger.info(f'Scene cleanup deleted GraphEditorInfo nodes : \n{graph_editor_info}')

	# delete orphaned and unlocked reference nodes
	reference_nodes = [x for x in cmds.ls(type='reference') if not cmds.listConnections(x) and not cmds.lockNode(
		x, query=True, lock=True)]
	if reference_nodes:
		cmds.delete(reference_nodes)
		logger.info(f'Scene cleanup deleted reference nodes : \n{reference_nodes}')


def delete_empty_namespaces():
	"""
	Removes all empty namespaces from bottom up to remove children namespaces first.
	"""

	namespaces = []
	ignore_namespaces = ['UI', 'shared']
	for ns in cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True, internal=False):
		if ns in ignore_namespaces:
			continue
		namespaces.append(ns)

	for ns in reversed(namespaces):
		if not cmds.namespaceInfo(ns, listNamespace=True):
			cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)


def delete_empty_display_layers():
	"""
	Deletes all empty display layers from scene.
	"""

	empty_layers = []
	default_display_layer = 'defaultLayer' if cmds.objExists('defaultLayer') else None
	for display_layer in cmds.ls(type='displayLayer'):
		if display_layer != default_display_layer and not cmds.editDisplayLayerMembers(
				display_layer, query=True, fullNames=True):
			empty_layers.append(display_layer)

	if empty_layers:
		cmds.delete(empty_layers)
