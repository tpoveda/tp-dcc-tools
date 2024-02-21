//
//  BaseLoc.h
//  ClonerMultiThread
//
//  Created by Hunyadi Janos on 22/07/15.
//  Copyright (c) 2015 Janos Hunyadi. All rights reserved.
//

#ifndef BaseLoc_H
#define BaseLoc_H



#include <maya/MPxLocatorNode.h>
#include <maya/M3dView.h>
#include <maya/MMatrix.h>
#include <maya/MGlobal.h>
#include <maya/MFnMatrixAttribute.h>
#include <maya/MFnMatrixData.h>
#include <maya/MFnPointArrayData.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnGenericAttribute.h>
#include <maya/MFnArrayAttrsData.h>
#include <maya/MFnEnumAttribute.h>
#include <maya/MFnStringData.h>
#include <maya/MStringArray.h>
#include <maya/MEulerRotation.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MPointArray.h>
#include <maya/MFnTransform.h>
#include <maya/MFnUnitAttribute.h>
#include <maya/MTime.h>
#include <maya/MFileObject.h>
#include <maya/MFileIO.h>
#include <maya/MCallbackIdArray.h>
#include <maya/MEventMessage.h>
#include <maya/MDGModifier.h>
#include <maya/MVectorArray.h>
#include <maya/MFnVectorArrayData.h>

// Viewport 2.0 includes
#include <maya/MDrawRegistry.h>
#include <maya/MPxDrawOverride.h>
#include <maya/MUserData.h>
#include <maya/MDrawContext.h>
#include <maya/MHWGeometryUtilities.h>
#include <maya/MEvaluationNode.h>

#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <iomanip> // setprecision

//#include "Utils.h"

using namespace std;

#ifdef _WIN64
    #include<GL/glu.h>
#endif


//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
// Classic 1.0 viewport implementation
//---------------------------------------------------------------------------
//---------------------------------------------------------------------------

class BaseLoc : public MPxLocatorNode
{
public:
	BaseLoc();
	virtual ~BaseLoc();

	virtual void			postConstructor();

	virtual MStatus   		compute( const MPlug& plug, MDataBlock& data );

	//virtual MStatus         postEvaluation(const  MDGContext& context, const MEvaluationNode& evaluationNode, PostEvaluationType evalType);

	virtual void            draw( M3dView & view, const MDagPath & path, M3dView::DisplayStyle style, M3dView::DisplayStatus status );

	#if MAYA_API_VERSION > 201600
	virtual MPxNode::SchedulingType schedulingType() const override {return MPxNode::kParallel;}
	#endif

	virtual bool            isBounded() const;
	virtual MBoundingBox    boundingBox() const;

	virtual bool            isTransparent() const;

	static  void *          creator();
	static  MStatus         initialize();

public:

	MStatus				calculate_speed(MFloatVector goal);

	MStatus             checkPresetFolder();

	static MString		drawDbClassification;
	static MString		drawRegistrantId;

	//

	static MTypeId		id;
	static MObject      aLocID;
	static MObject		aDivision;
	static MObject		aRadius;

	static MObject		aOffsetX;
	static MObject		aOffsetY;
	static MObject		aOffsetZ;

	static MObject		aRotateX;
	static MObject		aRotateY;
	static MObject		aRotateZ;

	static MObject		aScaleX;
	static MObject		aScaleY;
	static MObject		aScaleZ;

	static MObject		aDispObj;
	static MObject		aDispNum;
	static MObject		aDispCard;
	static MObject		aDispLoc;
	static MObject		aDispLocPivot;
	static MObject		aDrawOnTop;
	static MObject		aBillboard;
	static MObject		aOrient;

	static MObject      aLineColor;
	static MObject      aLineAlpha;
	static MObject      aPolygonColor;
	static MObject      aPolygonAlpha;
	static MObject      aLineStyle;
	static MObject      aPaintStyle;
	static MObject      aDrawPresets;
	static MObject      aDrawIconsTypes;
	static MObject      aTwoDIconsTypes;
	static MObject      aDebugType;

	static MObject		aLineWidth;
	static MObject      aPointSize;
	static MObject		aFadeDistance;
	static MObject		aFadeByDistance;

	static MObject		aMirrorX;
	static MObject		aMirrorY;
	static MObject		aMirrorZ;
	static MObject		aWorldSpace;

	// Text attributes
	static MObject		aDispText;
	static MObject		aTextPosition;
	static MObject      aTextAlignment;
	static MObject      aTextIncline;
	static MObject      aTextWeight;
	static MObject      aTextStretch;
	static MObject      aTextLine;
	static MObject      aTextBoxSize;
	static MObject      aText;
	//static MObject      aDebugInputFloat;
	static MObject      aTextBoxColor;
	static MObject      aTextBoxTransparency;
	static MObject      aTextFontSize;
	static MObject      aFontFaceName;

	static MObject		aDebugInputDouble;
    
    static MObject		aInLocPosA;
    static MObject		aInLocPosB;
    
	static MString		aPluginLoadPath;
	static MObject		aPresetFolderPath;

	static MObject		aInPointArray;
	static MObject		aInTriangleArray;

	static MObject		aBoundingBoxA;
	static MObject		aBoundingBoxB;

	static MObject		aDebugInput3Double;
	static MObject		aDebugInputPoints;

	static MObject		aDebugPointsNumberDisplay;

	static MObject		aTime;

private:
	MMatrix				m_modelViewMat;
	bool				m_fileInitialized;

	MFileObject         o_presetPath;
	MString             s_readPluginPath;

	MTime				m_currentTime;
	int					m_startFrame;

	MTime				m_previousTime;
	MPoint				m_currentPosition;
	MPoint				m_previousPosition;
	bool				m_init;

	MFloatVector		m_offsetVector;

};

//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
// Viewport 2.0 override implementation
//---------------------------------------------------------------------------
//---------------------------------------------------------------------------


// data for override

class BaseLocData : public MUserData
{
public:
	BaseLocData() : MUserData(false) {} // don't delete after draw
	virtual ~BaseLocData() {}

	MDagPath				m_dagPath;

	MColor					m_locColor;
	MColor					m_lineColor;
	MColor					m_polygonColor;
	int						m_locID;
    
    
	MPoint					m_inLocA_pos;
    MPoint					m_inLocB_pos;


	MPointArray				m_locDrawPoints;
	MPointArray				m_locDrawPoints_mirror;
	vector<MPointArray>		m_locDrawPointsA;
	vector<MPointArray>		m_locDrawPointsA_mirror;
	MPointArray				m_locDrawTriangles;
	MPointArray				m_locDrawTriangles_mirror;
	MPoint					m_locDrawCenter;



	bool					m_orient;
	bool					m_dispObj;
	bool					m_dispCard;
	bool					m_dispNum;
	bool					m_dispLoc;
	bool					m_drawOnTop;
	bool					m_billboard;

	bool					m_mirror_x;
	bool					m_mirror_y;
	bool					m_mirror_z;
	bool					m_worldSpace;

	// Debug
	bool					m_debugPointsNumberDisplay;


	int						m_drawPresets;
	int						m_drawIconType;
	int						m_debugType;
	int						m_draw_twod_IconType;
	float					m_lineWidth;
	int						m_pointSize;
	int						m_lineStyle;
	int						m_paintStyle;
	int						m_division;
	double					m_radius;

	double                  m_localPosX;
	double                  m_localPosY;
	double                  m_localPosZ;


	double                  m_offsetX;
	double                  m_offsetY;
	double                  m_offsetZ;

	double					m_rotateX;
	double					m_rotateY;
	double					m_rotateZ;

	double					m_scaleX;
	double					m_scaleY;
	double					m_scaleZ;

	double					m_alpha;
	double					m_fadeDistance; // Distance to camera
	bool					m_fadeByDistance;

	float					m_lineAlpha;
	float					m_polygonAlpha;

	MMatrix					m_modelViewMatrix; // Camera inclusive matrix - for card display


	bool					m_dispText;
	bool					m_dispLocPivot;

	MString					m_textInputFloat;
	MString					m_text;
	MString					m_textDebug;
	unsigned int			m_textFontSize;
	unsigned int			m_fontFaceIndex;
	MPoint					m_textPosition;

	MHWRender::MUIDrawManager::TextAlignment m_textAlignment;
	int						m_textIncline;
	int						m_textWeight;
	int						m_textStretch;
	int						m_textLine;
	int						m_textBoxWidth;
	int						m_textBoxHeight;
	MColor					m_textBoxColor;

	MMatrix					m_rotMatrix;
	MMatrix					m_bilboardMatrix;

	static MStringArray		m_fFontList;

	//double					m_inTime;
	MDagPath				m_cameraPath;

	MTime					m_currentTime;

	bool					m_init;

	// text stuff

	MString					m_debug_double3_x;
	MString					m_debug_double3_y;
	MString					m_debug_double3_z;
	MString					m_debug_float;
	double					m_debug_angle;

	MMatrix					m_inLoc_mat;

	//
	MPointArray				m_inPoints;
	MIntArray				m_inPointIDs;
	MVectorArray			m_inPointRotations;

};


// override

class BaseLocOverride : public MHWRender::MPxDrawOverride
{
public:
	static MHWRender::MPxDrawOverride* Creator(const MObject& obj)
	{
		return new BaseLocOverride(obj);
	}

	virtual ~BaseLocOverride();
	virtual MHWRender::DrawAPI supportedDrawAPIs() const;

	virtual bool isBounded( const MDagPath& objPath, const MDagPath& cameraPath) const;
	virtual bool            drawLast() const;
	virtual MBoundingBox boundingBox( const MDagPath& objPath, const MDagPath& cameraPath) const;

	virtual MUserData* prepareForDraw( const MDagPath& objPath, const MDagPath& cameraPath, const MHWRender::MFrameContext& frameContext, MUserData* oldData);

	virtual bool hasUIDrawables() const { return true; }
	virtual void addUIDrawables( const MDagPath& objPath, MHWRender::MUIDrawManager& drawManager, const MHWRender::MFrameContext& frameContext, const MUserData* data);

	//static void draw(const MHWRender::MDrawContext& context, const MUserData* data) {};
	static void triggerRefresh(const MHWRender::MDrawContext& context, const MUserData* data);



protected:
	MBoundingBox mCurrentBoundingBox;

	MCallbackId fModelEditorChangedCbId;
	

private:

	MStatus getVectorArray(MFnArrayAttrsData &particleFn, const MString vectorName, MVectorArray &vectorArray, bool &exists);
	MStatus getIntArray(MFnArrayAttrsData &particleFn, const MString intName, MIntArray &intArray, bool &exists);

	void load_iconLocatorData(MString& s_f_linePosValues, MString& s_f_triangleValues, MPointArray* m_line_values, MPointArray* m_triangle_values);


	BaseLocOverride(const MObject& obj);

	static void OnModelEditorChanged(void *clientData);
	

	BaseLoc* fBaseLoc;
	MObject m_locator;

	MMatrix m_modelViewMat;
	MPoint m_bbCorner1;
	MPoint m_bbCorner2;

	bool				m_debug = false;
	

};


#endif