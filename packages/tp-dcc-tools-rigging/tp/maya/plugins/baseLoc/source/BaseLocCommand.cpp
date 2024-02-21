//	Example python command:
//
//	import maya.cmds as mc
//	locObj = mc.BaseLocCommand( n="ReName_Me", oy= 2, rx= -45.0, p=5, it=2, r=1.0, c=4)
//	cmds.move( 0, 3, 0, locObj, absolute=True )
//	cmds.makeIdentity( locObj, apply=True, t=1, r=1, s=1, n=2 )
//

#include "BaseLocCommand.h"
#include "Utils.h"

BaseLocCommand::BaseLocCommand()
{
}


void* BaseLocCommand::creator()
{
	return new BaseLocCommand;
}


bool BaseLocCommand::isUndoable() const
{
	return true;
}

MSyntax BaseLocCommand::newSyntax()
{
	MSyntax syntax;

	syntax.addFlag( "-n", "-name", MSyntax::kString );
	syntax.addFlag( "-p", "-preset", MSyntax::kUnsigned );
	syntax.addFlag( "-it", "-icontype", MSyntax::kUnsigned );

	syntax.addFlag( "-c", "-color", MSyntax::kUnsigned );

	syntax.addFlag( "-r", "-radius", MSyntax::kDouble );

	syntax.addFlag( "-ox", "-offsetx", MSyntax::kDouble );
	syntax.addFlag( "-oy", "-offsety", MSyntax::kDouble );
	syntax.addFlag( "-oz", "-offsetz", MSyntax::kDouble );

	syntax.addFlag( "-rx", "-rotatex", MSyntax::kDouble );
	syntax.addFlag( "-ry", "-rotatey", MSyntax::kDouble );
	syntax.addFlag( "-rz", "-rotatez", MSyntax::kDouble );

	syntax.addFlag( "-of", "-offset", MSyntax::kDouble  );

	syntax.addFlag( "-sp", "-savePreset", MSyntax::kString  );
	syntax.addFlag( "-lp", "-loadPreset", MSyntax::kString  );

	syntax.addFlag( "-bl", "-baseLocNode", MSyntax::kString  );

	syntax.addFlag( "-pp", "-presetPath", MSyntax::kString  );

	syntax.addFlag( "-la", "-lineArray", MSyntax::kString  );
	syntax.addFlag( "-ta", "-triangleArray", MSyntax::kString  );

	syntax.addFlag( "-bb", "-boundingBox", MSyntax::kBoolean  );
	syntax.addFlag( "-ob", "-objectSpaceBB", MSyntax::kBoolean  );
	syntax.addFlag( "-br", "-resetYBB", MSyntax::kBoolean  );
	syntax.addFlag( "-an", "-annotate", MSyntax::kString  );

	syntax.enableEdit( false );
	syntax.enableQuery( false );

	return syntax;
}


MStatus BaseLocCommand::doIt( const MArgList& argList )
{
	MStatus status;

	MArgDatabase argData( syntax(), argList, &status );

	// clear commmand result
	m_resA.clear();

	// clear command result selection list
	m_selList.clear();

	// Presets
	i_preset = 0;
	i_icontype = 0;
	i_color = 7;
	d_radius = 1.0;

	d_offX = 0.0;
	d_offY = 0.0;
	d_offZ = 0.0;

	d_rotX = 0.0;
	d_rotY = 0.0;
	d_rotZ = 0.0;

	d_scX = 1.0;
	d_scY = 1.0;
	d_scZ = 1.0;

	d_offset = 0.0;

	b_boundingbox = false;
	b_objectSpaceBB = false;
	b_resetYBB = false;
	b_annotate = "";


	s_locName = MString("baseLoc#");

	o_baseLocNodeA.clear();

	MString s_lineA;
	MString s_triangleA;



	if ( argData.isFlagSet( "name" ) ) { s_locName = argData.flagArgumentString("name",0); }
	if ( argData.isFlagSet( "preset" ) ) { i_preset = argData.flagArgumentInt("preset",0); }
	if ( argData.isFlagSet( "icontype" ) ) { i_icontype = argData.flagArgumentInt("icontype",0); }
	if ( argData.isFlagSet( "color" ) ) { i_color = argData.flagArgumentInt("color",0); }
	if ( argData.isFlagSet( "radius" ) ) { d_radius = argData.flagArgumentDouble("radius",0); }

	if ( argData.isFlagSet( "offsetx" ) ) { d_offX = argData.flagArgumentDouble("offsetx",0); }
	if ( argData.isFlagSet( "offsety" ) ) { d_offY = argData.flagArgumentDouble("offsety",0); }
	if ( argData.isFlagSet( "offsetz" ) ) { d_offZ = argData.flagArgumentDouble("offsetz",0); }

	if ( argData.isFlagSet( "rotatex" ) ) { d_rotX = argData.flagArgumentDouble("rotatex",0); }
	if ( argData.isFlagSet( "rotatey" ) ) { d_rotY = argData.flagArgumentDouble("rotatey",0); }
	if ( argData.isFlagSet( "rotatez" ) ) { d_rotZ = argData.flagArgumentDouble("rotatez",0); }

	if ( argData.isFlagSet( "offset" ) ) { d_offset = argData.flagArgumentDouble("offset",0); }

	if ( argData.isFlagSet( "boundingBox" ) ) { b_boundingbox = argData.flagArgumentBool("boundingBox",0); }
	if ( argData.isFlagSet( "objectSpaceBB" ) ) { b_objectSpaceBB = argData.flagArgumentBool("objectSpaceBB",0); }
	if ( argData.isFlagSet( "resetYBB" ) ) { b_resetYBB = argData.flagArgumentBool("resetYBB",0); }
	if ( argData.isFlagSet( "annotate" ) ) { b_annotate = argData.flagArgumentString("annotate",0); }


	if ( argData.isFlagSet( "lineArray" ) ) { s_lineA = argData.flagArgumentString("lineArray",0); }
	if ( argData.isFlagSet( "triangleArray" ) ) { s_triangleA = argData.flagArgumentString("triangleArray",0); }


	// -----------------------------------------------------------------------------------------
	// SAVE PRESET TO BaseLoc

	if ( argData.isFlagSet( "savePreset" ) )
	{

		MString s_presetName;
		MString s_baseLocNodeName;
		MString s_pPath;

		argData.getFlagArgument("savePreset", 0, s_presetName);



		if (!argData.isFlagSet( "baseLocNode" ))
		{
			MGlobal::displayError(MString() + "[BaseLoc] No BaseLoc name set for command (use the -bl flag to set)");
			return MStatus::kFailure;
		}

		argData.getFlagArgument("baseLocNode", 0, s_baseLocNodeName);

		if (!argData.isFlagSet( "presetPath" ))
		{
			MGlobal::displayError(MString() + "[BaseLoc] Preset path name set for command (use the -pp flag to set)");
			return MStatus::kFailure;
		}

		argData.getFlagArgument("presetPath", 0, s_pPath);

		save_locatorData(s_pPath, s_presetName, s_lineA, s_triangleA, d_offset);

		// Refresh plugs + AE Template
		MGlobal::executeCommand("dgdirty " + s_baseLocNodeName);
		MGlobal::executeCommand("refreshAE");


	}





	// -----------------------------------------------------------------------------------------
	// LOAD PRESET TO BaseLoc
	//
	// BaseLocCommand -lp "box" -pp "p:/Maya/GitHub/cc-maya-base_locator/presets/" -bl "BaseLoc1";
	//

	if ( argData.isFlagSet( "loadPreset" ) )
	{
		MString s_presetName;
		MString s_baseLocNodeName;
		MString s_pPath;

		argData.getFlagArgument("loadPreset", 0, s_presetName);

		if (!argData.isFlagSet( "baseLocNode" ))
		{
			MGlobal::displayError(MString() + "[BaseLoc] No BaseLoc name set for command (use the -bl flag to set)");
			return MStatus::kFailure;
		}

		argData.getFlagArgument("baseLocNode", 0, s_baseLocNodeName);

		if (!argData.isFlagSet( "presetPath" ))
		{
			MGlobal::displayError(MString() + "[BaseLoc] Preset path name set for command (use the -pp flag to set)");
			return MStatus::kFailure;
		}

		argData.getFlagArgument("presetPath", 0, s_pPath);

		// Find Shellmod from name
		MObject MObj;
		MSelectionList selList;
		selList.add(s_baseLocNodeName);
		selList.getDependNode(0,MObj);	

		load_locatorData(s_pPath, s_presetName, MObj);

		// Refresh plugs + AE Template
		MGlobal::executeCommand("dgdirty " + s_baseLocNodeName);
		MGlobal::executeCommand("refreshAE");


		return MStatus::kSuccess;
	}



	if (b_boundingbox)
	{

		MDagPath currDagPathTr;
		MSelectionList selectedObjects;

		MGlobal::getActiveSelectionList(selectedObjects);

		// Get Meshes
		for (unsigned int i = 0; i < selectedObjects.length(); i++)
		{
			selectedObjects.getDagPath(i, currDagPathTr);

			if (currDagPathTr.apiType() == MFn::kTransform)
			{



				MDagPath currDagPathShape = currDagPathTr;

				status = getShapeNodeFromTransformDAG(currDagPathShape);

				if (status)
				{



					MFnTransform fn_transform(currDagPathTr);

					MPoint rot_piv = fn_transform.rotatePivot(MSpace::kObject);
					MPoint scale_piv = fn_transform.scalePivot(MSpace::kObject);

					MMatrix currMat = fn_transform.transformationMatrix(&status);
					CHECK_MSTATUS_AND_RETURN_IT(status);


					MFnMesh mfn_mesh(currDagPathShape);

					MPointArray pA;
					mfn_mesh.getPoints(pA,MSpace::kWorld);

					if (pA.length() == 0)
					{
						MGlobal::displayWarning(MString() + "[BaseLoc] " + currDagPathShape.partialPathName() + " - Does not have any points...");
						return::MStatus::kSuccess;
					}

					//double pX = 0.0;
					//double pY = 0.0;
					//double pZ = 0.0;

					//for (int i = 0; i < pA.length(); i++)
					//{
					//	pX += pA[i].x;
					//	pY += pA[i].y;
					//	pZ += pA[i].z;
					//}

					//MVector centerP(pX/double(pA.length()), pY/double(pA.length()), pZ/double(pA.length()));

					//

					MBoundingBox bb_currMesh = mfn_mesh.boundingBox(&status);
					CHECK_MSTATUS_AND_RETURN_IT(status);

					i_preset = 1;

					d_scX = bb_currMesh.width();
					d_scY = bb_currMesh.height();
					d_scZ = bb_currMesh.depth();



					d_offX = bb_currMesh.center().x;
					d_offY = bb_currMesh.center().y;
					d_offZ = bb_currMesh.center().z;



					// MGlobal::displayInfo(MString() + bb_currMesh.center().x + "," + bb_currMesh.center().y + "," + bb_currMesh.center().z);

					BaseLocCommand::createLocator(argData);

					if(!b_objectSpaceBB)
					{
						MTransformationMatrix trMAt(currMat);

						MFnTransform fn_transform_loc(dag_LocATr);
						fn_transform_loc.set(trMAt);


						if (b_resetYBB)
						{
							//fn_transform_loc.setRotatePivot(MPoint(d_offX, (rot_piv.y - d_scY) -d_offY, d_offZ), MSpace::kObject, true);
							//fn_transform_loc.setScalePivot(MPoint(d_offX, (scale_piv.y - d_scY) -d_offY, d_offZ), MSpace::kObject, true);

							fn_transform_loc.setRotatePivot(MPoint(d_offX, bb_currMesh.min().y, d_offZ), MSpace::kObject, true);
							fn_transform_loc.setScalePivot(MPoint(d_offX, bb_currMesh.min().y, d_offZ), MSpace::kObject, true);

						}

						else
						{
							fn_transform_loc.setRotatePivot(MPoint(rot_piv.x, rot_piv.y, rot_piv.z), MSpace::kObject, true);
							fn_transform_loc.setScalePivot(MPoint(scale_piv.x, scale_piv.y, scale_piv.z), MSpace::kObject, true);
						}

					}

					//MPxCommand::setResult(m_resA);
					//MGlobal::setActiveSelectionList(m_selList);
				}
			}
		}


		//return redoIt();

	}


	// -----------------------------------------------------------------------------------------
	// Just create a default BaseLoc
	//
	// BaseLocCommand -sp "sphere" -pp "p:/Maya/GitHub/cc-maya-base_locator/presets/" -bl "BaseLoc1";
	//
	//

	else
	{
		BaseLocCommand::createLocator(argData);


	}

	MPxCommand::setResult(m_resA);
	MGlobal::setActiveSelectionList(m_selList);

	// BaseLocCommand -pa  "0.5,0.5,0.5,0.5,-0.5,0.5,0.5,-0.5,-0.5,0.5,0.5,-0.5,0.5,0.5,0.5,0.5,0.5,-0.5,-0.5,0.5,-0.5,-0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.5,-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,-0.5,0.0,0.0,0.0,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,-0.5,0.5,0.5,0.0,0.0,0.0,-0.5,-0.5,0.5,0.5,-0.5,0.5" -ta "-0.5,-0.5,0.5,0.5,-0.5,0.5,-0.5,0.5,0.5,-0.5,0.5,0.5,0.5,-0.5,0.5,0.5,0.5,0.5,-0.5,0.5,0.5,0.5,0.5,0.5,-0.5,0.5,-0.5,-0.5,0.5,-0.5,0.5,0.5,0.5,0.5,0.5,-0.5,-0.5,0.5,-0.5,0.5,0.5,-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,0.5,-0.5,0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,-0.5,-0.5,-0.5,-0.5,0.5,-0.5,-0.5,0.5,0.5,-0.5,-0.5,0.5,-0.5,0.5,0.5,-0.5,0.5,0.5,-0.5,-0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,-0.5,-0.5,0.5,0.5,-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,-0.5,0.5,-0.5,-0.5,0.5,-0.5,-0.5,-0.5,0.5,-0.5,0.5,0.5";

	return redoIt();
}


MStatus BaseLocCommand::createLocator(MArgDatabase& argData)
{
	MStatus status;


	// check results

	if ( i_preset > 10 ) { i_preset = 10;	}
	if ( i_icontype > 26)  { i_icontype = 26;}
	if ( d_radius <= 0.0 ) { d_radius = 1.0;}

	double r,g,b = 0.5;

	switch ( i_color ) 
	{

	case 1: r = 1.0; g = 0.0; b = 0.0; break;
	case 2: r = 0.0; g = 1.0; b = 0.0; break;
	case 3: r = 0.0; g = 0.0; b = 1.0; break;
	case 4: r = 0.0; g = 1.0; b = 1.0; break;
	case 5: r = 1.0; g = 0.0; b = 1.0; break;
	case 6: r = 1.0; g = 1.0; b = 0.0; break;
	case 7: r = 0.5; g = 0.5; b = 0.5; break;
	case 8: r = 1.0; g = 0.5; b = 0.5; break;
	case 9: r = 0.5; g = 1.0; b = 0.5; break;
	case 10: r = 1.0; g = 1.0; b = 1.0; break;

	default:
		r = 1.0; g = 1.0; b = 1.0;
	}

	// Create locator
	o_baseLocNode = m_DEPNode.create(MTypeId(0x00123942), &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MFnDependencyNode fnDepTrg( o_baseLocNode );

	o_baseLocNodeA.append(o_baseLocNode);


	if ( argData.isFlagSet( "name" ) )
	{
		// Rename it
		fnDepTrg.setName( s_locName, false, &status );
		CHECK_MSTATUS_AND_RETURN_IT(status);
	}

	// Set plugs
	MDagPath dag_LocA;
	MSelectionList sel_list;

	status = sel_list.add(fnDepTrg.name());
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = sel_list.getDagPath(0,dag_LocA);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	dag_LocATr = dag_LocA;
	status = dag_LocA.extendToShape();
	CHECK_MSTATUS_AND_RETURN_IT(status);

	dag_LocAShape = dag_LocA;

	MFnDependencyNode fnDepLocShape( dag_LocAShape.node() );

	MPlug p_preset = fnDepLocShape.findPlug("presets", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_icontype = fnDepLocShape.findPlug("iconType", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_radius = fnDepLocShape.findPlug("radius", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	MPlug p_trX = fnDepLocShape.findPlug("offsetX", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_trY = fnDepLocShape.findPlug("offsetY", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_trZ = fnDepLocShape.findPlug("offsetZ", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	MPlug p_rotX = fnDepLocShape.findPlug("rotateX", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_rotY = fnDepLocShape.findPlug("rotateY", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_rotZ = fnDepLocShape.findPlug("rotateZ", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	MPlug p_scX = fnDepLocShape.findPlug("scaleX", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_scY = fnDepLocShape.findPlug("scaleY", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_scZ = fnDepLocShape.findPlug("scaleZ", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);


	MPlug p_lineColR = fnDepLocShape.findPlug("lineColorR", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_lineColG = fnDepLocShape.findPlug("lineColorG", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_lineColB = fnDepLocShape.findPlug("lineColorB", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	MPlug p_polyColR = fnDepLocShape.findPlug("polygonColorR", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_polyColG = fnDepLocShape.findPlug("polygonColorG", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MPlug p_polyColB = fnDepLocShape.findPlug("polygonColorB", &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	if ( b_annotate.length() != 0 )
	{
		MPlug p_dispText = fnDepLocShape.findPlug("displayText", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);
		status = p_dispText.setBool( true );
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MPlug p_text = fnDepLocShape.findPlug("text", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);
		status = p_dispText.setString( b_annotate );
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MPlug p_testPosY = fnDepLocShape.findPlug("textPosition1", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);
		status = p_testPosY.setDouble( d_scY*0.5 + ((d_scY * 0.5) * 0.25) );
		CHECK_MSTATUS_AND_RETURN_IT(status);

	}


	status = p_preset.setInt( i_preset );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_icontype.setInt( i_icontype );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_radius.setDouble( d_radius );
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = p_trX.setDouble( d_offX );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_trY.setDouble( d_offY );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_trZ.setDouble( d_offZ );
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = p_rotX.setDouble( d_rotX );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_rotY.setDouble( d_rotY );
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_rotZ.setDouble( d_rotZ );
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = p_scX.setDouble(d_scX);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_scY.setDouble(d_scY);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_scZ.setDouble(d_scZ);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = p_lineColR.setDouble(r);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_lineColG.setDouble(g);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_lineColB.setDouble(b);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = p_polyColR.setDouble(r - 0.5);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_polyColG.setDouble(g - 0.5);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = p_polyColB.setDouble(b - 0.5);
	CHECK_MSTATUS_AND_RETURN_IT(status);


	m_resA.append(fnDepTrg.name());
	m_resA.append(fnDepLocShape.name());

	m_selList.add(fnDepTrg.name());



	return MS::kSuccess;
}



MStatus BaseLocCommand::getShapeNodeFromTransformDAG(MDagPath& path)
{
	MStatus status;

	if (path.apiType() == MFn::kMesh)
	{
		return MS::kSuccess;
	}

	unsigned int numShapes;
	status = path.numberOfShapesDirectlyBelow(numShapes);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	for (unsigned int i = 0; i < numShapes; ++i)
	{
		status = path.extendToShapeDirectlyBelow(i);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		if (!path.hasFn(MFn::kMesh))
		{
			path.pop();
			continue;
		}

		MFnDagNode fnNode(path, &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);
		if (!fnNode.isIntermediateObject())
		{
			return MS::kSuccess;
		}
		path.pop();
	}

	//MGlobal::displayWarning(MString() + "Selection is not a mesh");

	return MS::kFailure;

}

MStatus BaseLocCommand::redoIt()
{
	MStatus status;







	return MS::kSuccess;
}

MStatus BaseLocCommand::undoIt()
{
	MStatus status;

	// Restore the initial state
	status = m_DGMod.undoIt();
	CHECK_MSTATUS_AND_RETURN_IT( status );

	status = m_DAGMod.undoIt();
	CHECK_MSTATUS_AND_RETURN_IT(status);



	// Delete locator

	for (int i = 0; i < o_baseLocNodeA.length(); i++)
	{

		if ( !o_baseLocNodeA[i].isNull() )
		{
			MGlobal::displayInfo(MString() + "[BaseLocNode] Deleting nodes");

			status = m_DAGMod.deleteNode(o_baseLocNodeA[i]);
			CHECK_MSTATUS_AND_RETURN_IT(status);
			m_DAGMod.doIt();


		}
	}



	return MS::kSuccess;
}