#ifndef UTILS_H
#define UTILS_H

#include <string>
#include <fstream>
#include <vector>
#include <stdlib.h>


#include <algorithm>
#include <iostream>
#include <iterator>
#include <sstream>


#include <maya/MString.h>
#include <maya/MStringArray.h>
#include <maya/MFloatArray.h>
#include <maya/MBoundingBox.h>
#include <maya/MFnMesh.h>
#include <maya/MItMeshEdge.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MFnNumericData.h>

using namespace std;


// Usage:
// -----
//
// BaseLocCommand -lp "test" -pp "d:/WORK/" -bl "BaseLoc1";
//
//



MStatus load_locatorData(MString &s_pathName, MString &s_presetName, MObject &o_baseLocNode)
{

	MStatus status;

	MPointArray	m_line_values_file;
	MPointArray	m_triangle_values_file;
	MBoundingBox m_boundingBox;


	MStringArray s_lines;
	MString s_f_presetName;
	MString s_f_linePosValues;
	MString s_f_triangleValues;

	MString s_path = s_pathName;
	s_pathName += s_presetName + ".blp";

	// BaseLocCommand -lp "box" -pp "p:/Maya/GitHub/cc-maya-base_locator/presets/" -bl "BaseLoc1";



	ifstream infile(s_pathName.asChar());

	string line;
	while (getline(infile, line))
	{
		istringstream iss(line);
		s_lines.append(line.c_str());
	}




	if (s_lines.length() == 3)
	{
		s_f_presetName = s_lines[0];
		s_f_linePosValues = s_lines[1];
		s_f_triangleValues = s_lines[2];


		MStringArray s_pointsA;
		status = s_f_linePosValues.split(',', s_pointsA);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		int count = 0;
		MPoint currP;

		// Line Array
		for (int i = 0; i < s_pointsA.length(); i += 3)
		{

			if (i > s_pointsA.length())
			{
				break;
			}


			currP.x = s_pointsA[i].asDouble();
			currP.y = s_pointsA[i+1].asDouble();
			currP.z = s_pointsA[i+2].asDouble();
			m_line_values_file.append(currP);

		}


		// Trinagle Array
		MStringArray s_trianglesA;
		s_f_triangleValues.split(',', s_trianglesA);

		// reset count
		count = 0;


		for (int i = 0; i < s_trianglesA.length(); i += 3)
		{

			if (i > s_trianglesA.length())
			{
				break;
			}


			currP.x = s_trianglesA[i].asDouble();
			currP.y = s_trianglesA[i+1].asDouble();
			currP.z = s_trianglesA[i+2].asDouble();
			m_triangle_values_file.append(currP);
		}

		MFnDependencyNode fnDepTrg( o_baseLocNode );

		// Set plugs
		MDagPath dag_LocATr;
		MDagPath dag_LocAShape;
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

		MPlug p_pointAPlug = fnDepLocShape.findPlug("inPointArray", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MPlug p_triangleAPlug = fnDepLocShape.findPlug("inTriangleArray", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);


		MPlug p_BBPlugA = fnDepLocShape.findPlug("boundingBoxA", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MPlug p_BBPlugB = fnDepLocShape.findPlug("boundingBoxB", &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);


		MFnPointArrayData pAD_points;
		MObject o_pA = pAD_points.create(m_line_values_file, &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		status = p_pointAPlug.setMObject(o_pA);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MFnPointArrayData pAD_triangles;
		MObject o_tA = pAD_triangles.create(m_triangle_values_file, &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		status = p_triangleAPlug.setMObject(o_tA);
		CHECK_MSTATUS_AND_RETURN_IT(status);


		for (int i = 0; i < m_triangle_values_file.length(); i++)
		{
			m_boundingBox.expand(m_triangle_values_file[i]);
		} 

		for (int i = 0; i < m_line_values_file.length(); i++)
		{
			m_boundingBox.expand(m_line_values_file[i]);
		} 

		MPoint p_BBA = m_boundingBox.min();
		MPoint p_BBB = m_boundingBox.max();

		//MGlobal::displayInfo(MString() + "BBA: " + p_BBA.x + ", " + p_BBA.y + ", " + p_BBA.z);
		//MGlobal::displayInfo(MString() + "BBA: " + p_BBA.x + ", " + p_BBA.y + ", " + p_BBA.z);


		MFnNumericData mfnBBA;
		MObject oData_BBA = mfnBBA.create(MFnNumericData::k3Float);
		MFnNumericData mfnBBB;
		MObject oData_BBB = mfnBBB.create(MFnNumericData::k3Float);

		mfnBBA.setData3Float(p_BBA.x, p_BBA.y, p_BBA.z);
		mfnBBB.setData3Float(p_BBB.x, p_BBB.y, p_BBB.z);


		status = p_BBPlugA.setMObject(oData_BBA);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		status = p_BBPlugB.setMObject(oData_BBB);
		CHECK_MSTATUS_AND_RETURN_IT(status);

	}


	else
	{
		MGlobal::displayInfo("[BaseLoc] Cant read file: " + s_pathName);
	}

	return::MStatus::kSuccess;

}



MStatus save_locatorData(MString &s_pathName, MString &s_presetName, MString &s_lineA, MString &s_triangleA, double &d_offset)
{

	// Locator data

	MStatus status;

	// Get active selection
	MSelectionList slist;

	MGlobal::getActiveSelectionList( slist, true );

	MDagPath objectPath_tr;
	MDagPath objectPath_shape;

	MObject component;

	status = slist.getDagPath(0,objectPath_tr, component);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	objectPath_shape = objectPath_tr;
	status = objectPath_shape.extendToShape();
	CHECK_MSTATUS_AND_RETURN_IT(status);

	

	// If polygon count is sxceeded return
	MFnMesh mFn(objectPath_shape);
	if (mFn.numPolygons() > 2000)
	{
		MGlobal::displayWarning(MString() + "[BaseLoc] Polygon count exceeded (" + mFn.numPolygons() + "). Select mesh with less than 2000 polygons");
		return::MStatus::kSuccess;
	}



	// Crete output file
	MString s_path = s_pathName;
	s_pathName += s_presetName + ".blp";

	ofstream fout( s_pathName.asChar() );

	if (s_lineA == "")
	{


		if (objectPath_shape.isValid())
		{

			if (component.apiType() ==  MFn::kMeshEdgeComponent )
			{

				MItMeshEdge mitEdge(objectPath_shape, component, &status);
				CHECK_MSTATUS_AND_RETURN_IT(status);



				for ( ; !mitEdge.isDone(); mitEdge.next() )
				{

					

					MPoint edgeVert_A = mitEdge.point(0, MSpace::kObject, &status);
					CHECK_MSTATUS_AND_RETURN_IT(status);

					MPoint edgeVert_B = mitEdge.point(1, MSpace::kObject, &status);
					CHECK_MSTATUS_AND_RETURN_IT(status);

					//int numConnE;
					//mitEdge.numConnectedEdges(numConnE);

					//if (numConnE != 0)
					//{
					//	MIntArray edges;
					//	mitEdge.getConnectedEdges(edges, &status);
					//	CHECK_MSTATUS_AND_RETURN_IT(status);

					//}

					s_lineA += MString() + edgeVert_A.x + "," + edgeVert_A.y + "," + edgeVert_A.z + ",";
					s_lineA += MString() + edgeVert_B.x + "," + edgeVert_B.y + "," + edgeVert_B.z + ",";

					s_lineA += MString() + 0.0 + "," + 0.0 + "," + 0.0 + ",";

				}

			}
		}

	}

	if (s_triangleA == "")
	{
		MSelectionList slist;
		MGlobal::getActiveSelectionList( slist );

		MDagPath objectPath_tr;
		MDagPath objectPath_shape;

		status = slist.getDagPath(0,objectPath_tr);
		CHECK_MSTATUS_AND_RETURN_IT(status);

		objectPath_shape = objectPath_tr;
		status = objectPath_shape.extendToShape();
		CHECK_MSTATUS_AND_RETURN_IT(status);

		MIntArray vertexList;

		if (objectPath_shape.isValid())
		{
			MItMeshPolygon mitPoly(objectPath_shape);

			MPointArray tirangle_A;

			for ( ; !mitPoly.isDone(); mitPoly.next() )
			{

				mitPoly.getTriangles(tirangle_A, vertexList,MSpace::kObject);
				CHECK_MSTATUS_AND_RETURN_IT(status);

				for (int i = 0; i < tirangle_A.length(); i++)
				{
					s_triangleA += MString() + tirangle_A[i].x + "," + tirangle_A[i].y + "," + tirangle_A[i].z + ",";
				}




			}
		}

	}

	// Create file
	if(fout.is_open()) 
	{

		MGlobal::displayInfo(MString() + "[BaseLoc] Writing preset to disk: " + s_pathName);

		fout << s_presetName.asChar();
		fout << endl;
		fout << s_lineA.asChar();
		fout << endl;
		fout << s_triangleA.asChar();


	}

	// File could not be opened
	else 
	{
		MGlobal::displayWarning(MString() + "[BaseLoc] File could not be opened: " + s_pathName);
	}




	return::MStatus::kSuccess;
}


// ----------------------



#endif