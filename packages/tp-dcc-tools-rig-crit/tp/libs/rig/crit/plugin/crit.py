import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaRender as OpenMayaRender

from tp.maya.cmds import evaluationcache
from tp.libs.rig.crit.plugin.pinlocator import pinlocator, connector


# this is mandatory to notify Maya that we are writing a plugin that is going to use "new" API
def maya_useNewAPI():
	pass


def initializePlugin(mobj):

	plugin = OpenMaya.MFnPlugin(mobj, 'Tomi Poveda', '1.0')
	plugin.registerNode(
		'critPinLocator', pinlocator.PinLocator.ID, pinlocator.PinLocator.creator, pinlocator.PinLocator.initialize,
		OpenMaya.MPxNode.kLocatorNode, pinlocator.PinLocator.DRAW_DB_CLASSIFICATION)
	OpenMayaRender.MDrawRegistry.registerDrawOverrideCreator(
		pinlocator.PinLocator.DRAW_DB_CLASSIFICATION, pinlocator.PinLocator.DRAW_REGISTRANT_ID,
		pinlocator.PinLocatorDrawOverride.creator)
	plugin.registerNode(
		'critPinLocatorConnector', connector.PinLocatorConnector.ID, connector.PinLocatorConnector.creator,
		connector.PinLocatorConnector.initialize, OpenMaya.MPxNode.kLocatorNode,
		connector.PinLocatorConnector.DRAW_DB_CLASSIFICATION)
	OpenMayaRender.MDrawRegistry.registerDrawOverrideCreator(
		connector.PinLocatorConnector.DRAW_DB_CLASSIFICATION, connector.PinLocatorConnector.DRAW_REGISTRANT_ID,
		connector.PinLocatorConnectorDrawOverride.creator)

	# register our custom locator type in Maya evaluation cache
	evaluationcache.enable_caching_for_node_type('critPinLocator')
	evaluationcache.enable_caching_for_node_type('critPinLocatorConnector')

	# register custom CRIT Pin Locator display filter
	cmds.pluginDisplayFilter(
		'critPinLocator', classification=pinlocator.PinLocator.DRAW_DB_CLASSIFICATION,
		register=True, label='CRIT Pin Locator')
	cmds.pluginDisplayFilter(
		'critPinLocatorConnector', classification=connector.PinLocatorConnector.DRAW_DB_CLASSIFICATION,
		register=True, label='CRIT Pin Locator Connector')

	# register custom selection mask so our locator takes selection preference over joints
	if OpenMaya.MGlobal == OpenMaya.MGlobal.mayaState():
		OpenMaya.MSelectionMask.registerSelectionType(
			pinlocator.PinLocator.SELECTION_MASK_NAME, OpenMaya.MSelectionMask.kSelectJoints + 1)

	# # register custom node builder data types and nodes
	# register.load_register()


def uninitializePlugin(mobj):
	plugin = OpenMaya.MFnPlugin(mobj)
	plugin.deregisterNode(pinlocator.PinLocator.ID)
	plugin.deregisterNode(connector.PinLocatorConnector.ID)
	OpenMayaRender.MDrawRegistry.deregisterDrawOverrideCreator(
		pinlocator.PinLocator.DRAW_DB_CLASSIFICATION, pinlocator.PinLocator.DRAW_REGISTRANT_ID)
	OpenMayaRender.MDrawRegistry.deregisterDrawOverrideCreator(
		connector.PinLocatorConnector.DRAW_DB_CLASSIFICATION, connector.PinLocatorConnector.DRAW_REGISTRANT_ID)

	evaluationcache.disable_caching_for_node_type('critPinLocator')

	cmds.pluginDisplayFilter('critPinLocator', deregister=True)
	cmds.pluginDisplayFilter('critPinLocatorConnector', deregister=True)

	OpenMaya.MSelectionMask.deregisterSelectionType(pinlocator.PinLocator.SELECTION_MASK_NAME)
