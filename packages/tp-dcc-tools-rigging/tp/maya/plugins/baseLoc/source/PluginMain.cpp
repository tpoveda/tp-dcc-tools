//
//  PluginMain.cpp
//  ClonerMultiThread
//
//  Created by Hunyadi Janos on 24/07/15.
//  Copyright (c) 2015 Janos Hunyadi. All rights reserved.
//

#include "BaseLoc.h"
#include "BaseLocCommand.h"
#include "icons.h"
#include "AETemplate.h"

#include <maya/MFnPlugin.h>
#include <maya/MCommonSystemUtils.h>

MStatus initializePlugin( MObject obj )
{
	MStatus status;

	MFnPlugin fnPlugin( obj, "Creative Case", "1.952", "Any" );


	MString rebuild_icons = MCommonSystemUtils::getEnv("BASELOC_REBUILD_ICONS", &status);

	if (!rebuild_icons.asShort())
	{
		icons_data_write();
	}

	MString rebuild_shelf = MCommonSystemUtils::getEnv("BASELOC_REBUILD_SHELF", &status);

	if (!rebuild_shelf.asShort())
	{
		MGlobal::executeCommand(mel_createShelf());
	}

	MStringArray aeTemplateA = mel_AETemplate();

	for (unsigned int i = 0; i < aeTemplateA.length(); i++)
	{
		MGlobal::executeCommand(aeTemplateA[i]);
	}


	// Locator
	status = fnPlugin.registerNode( "BaseLoc", BaseLoc::id, &BaseLoc::creator, &BaseLoc::initialize, MPxNode::kLocatorNode, &BaseLoc::drawDbClassification);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = fnPlugin.registerCommand( "BaseLocCommand", BaseLocCommand::creator, BaseLocCommand::newSyntax );
    CHECK_MSTATUS_AND_RETURN_IT( status );

	status = MHWRender::MDrawRegistry::registerDrawOverrideCreator( BaseLoc::drawDbClassification, BaseLoc::drawRegistrantId, BaseLocOverride::Creator);
	CHECK_MSTATUS_AND_RETURN_IT(status);


	BaseLoc::aPluginLoadPath = fnPlugin.loadPath(&status);
	CHECK_MSTATUS_AND_RETURN_IT(status);


	return MS::kSuccess;
}


MStatus uninitializePlugin( MObject obj )
{
	MStatus status;

	MFnPlugin fnPlugin( obj );

	// Locator
	status = MHWRender::MDrawRegistry::deregisterDrawOverrideCreator( BaseLoc::drawDbClassification, BaseLoc::drawRegistrantId);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = fnPlugin.deregisterNode( BaseLoc::id );
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = fnPlugin.deregisterCommand( "BaseLocCommand" );
    CHECK_MSTATUS_AND_RETURN_IT( status );


	return MS::kSuccess;
}

