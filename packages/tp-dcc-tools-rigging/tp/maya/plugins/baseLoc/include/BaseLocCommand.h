#ifndef BaseLocCommand_H
#define BaseLocCommand_H

#ifdef __linux__ 
#include <maya/MArgDatabase.h>
#else
#include <maya/MArgDataBase.h>
#endif
#include <maya/MDagPath.h>
#include <maya/MDGModifier.h>
#include <maya/MFnDagNode.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MFnMesh.h>
#include <maya/MGlobal.h>
#include <maya/MIntArray.h>
#include <maya/MItDependencyGraph.h>
#include <maya/MMeshIntersector.h>
#include <maya/MObject.h>
#include <maya/MPlug.h>
#include <maya/MPlugArray.h>
#include <maya/MPointArray.h>
#include <maya/MPxCommand.h>
#include <maya/MSelectionList.h>
#include <maya/MSyntax.h>
#include <maya/MDagModifier.h>
#include <maya/MFnSet.h>
#include <maya/MTransformationMatrix.h>
#include <maya/MFnTransform.h>
#include <maya/MDagPathArray.h>
#include <maya/MArgList.h>
#include <maya/MFnPointArrayData.h>


class BaseLocCommand : public MPxCommand
{
public:
	BaseLocCommand();
	virtual MStatus			doIt( const MArgList& argList );
	virtual MStatus			redoIt();
	virtual MStatus			undoIt();
	virtual bool			isUndoable() const;
	static void*			creator();
	static MSyntax			newSyntax();

	//void					setResult();

private:

	MStatus					getShapeNodeFromTransformDAG(MDagPath& path);
	MStatus					createLocator(MArgDatabase& argData);

	MDagModifier			m_DAGMod;
	MDGModifier				m_DGMod;
	MFnDependencyNode		m_DEPNode;

	MDagPath				dag_LocATr;
	MDagPath				dag_LocAShape;

	MObject					o_baseLocNode;
	MObjectArray			o_baseLocNodeA;


	// Presets

	int						i_preset;
	int						i_icontype;
	int						i_color;
	double					d_radius;

	double					d_offX;
	double					d_offY;
	double					d_offZ;

	double					d_rotX;
	double					d_rotY;
	double					d_rotZ;

	double					d_scX;
	double					d_scY;
	double					d_scZ;

	double					d_offset;

	bool					b_boundingbox;
	bool					b_objectSpaceBB;
	bool					b_resetYBB;
	
	MString					b_annotate;
	MString					s_locName;

	MStringArray			m_resA;
	MSelectionList			m_selList;

};


#endif