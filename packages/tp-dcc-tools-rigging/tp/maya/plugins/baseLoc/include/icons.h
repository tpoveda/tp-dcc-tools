#ifndef ICONS_H
#define ICONS_H

#include "icons_repo.h"

void writeIcon_binary(MString path, MString filename, const unsigned char output[], int char_size)
{

	ofstream myfile;

	myfile.open(MString(path + filename).asChar(), ios::out | ios::binary);
	myfile.write((char *)output, char_size);
	myfile.close();
	MGlobal::displayInfo(MString() + "[BaseLoc] Created icon: " + path + filename);


}



void icons_data_write()
{


	MString path;
	MGlobal::executeCommand("internalVar -userBitmapsDir", path);
	MGlobal::displayInfo(MString() + "[BaseLoc] Icons path: " + path);

	std::string c_path = path.asChar();


	const size_t out_BaseLoc_png_size = sizeof(out_BaseLoc_png_start);

	writeIcon_binary(path, "out_BaseLoc.png", out_BaseLoc_png_start, sizeof(out_BaseLoc_png_start));
	writeIcon_binary(path, "BaseLoc_bb.png", BaseLoc_bb_png_start, sizeof(BaseLoc_bb_png_start));
	writeIcon_binary(path, "BaseLoc.png", BaseLoc_png_start, sizeof(BaseLoc_png_start));
	writeIcon_binary(path, "baseLoc_Refresh.png", baseLoc_Refresh_png_start, sizeof(baseLoc_Refresh_png_start));
	writeIcon_binary(path, "baseLoc_Plus.png", baseLoc_Plus_png_start, sizeof(baseLoc_Plus_png_start));
	writeIcon_binary(path, "baseLoc_Minus.png", baseLoc_Minus_png_start, sizeof(baseLoc_Minus_png_start));
	writeIcon_binary(path, "baseLoc_CCLogo.png", baseLoc_CCLogo_png_start , sizeof(baseLoc_CCLogo_png_start));
	writeIcon_binary(path, "baseLoc_Apply.png", baseLoc_Apply_png_start, sizeof(baseLoc_Apply_png_start));


}

#endif