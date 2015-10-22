#-------------------------------------------------------------------------------
# Name:        Lidar Mosaic Tool
# Purpose:      To mosaic several lidar images
#
# Author:      ewallace
#
# Created:     09/11/2014
#-------------------------------------------------------------------------------

import arcpy
from arcpy import env
from arcpy.sa import *

in_workspace = arcpy.GetParameterAsText(0)

env.workspace = in_workspace

lidarlist = arcpy.ListRasters()

arcpy.AddMessage("Setting null values...")

for file in lidarlist:
    outSetNull = arcpy.sa.SetNull(file, file, "VALUE < -400")
    outsplit = file.split(".")
    outfilename = outsplit[0] + "_stnull" + ".tif"
    outfilepath = in_workspace + "/" + outfilename
    outSetNull.save(outfilepath)

arcpy.AddMessage("Building pyramids and calculating statistics...")

arcpy.BuildPyramidsandStatistics_management(in_workspace, "NONE",
"BUILD_PYRAMIDS", "CALCULATE_STATISTICS" )

lidarstnull = arcpy.ListRasters("*_stnull.tif")

outrastername = arcpy.GetParameterAsText(1)

outraster = outrastername + ".tif"

arcpy.AddMessage("Mosaicking images...")

testraster = in_workspace + "/" + lidarstnull[0]

pixelcode = arcpy.GetRasterProperties_management(testraster,"VALUETYPE")

pixeldict = {'0':'1_BIT', '1':'2_BIT', '2':'4_BIT', '3':'8_BIT_UNSIGNED', '4':'8_BIT_SIGNED', '5':'16_BIT_UNSIGNED', '6':'16_BIT_SIGNED','7':'32_BIT_UNSIGNED','8':'32_BIT_SIGNED','9':'32_BIT_FLOAT','10':'64_BIT'}

pixelcode = str(pixelcode)

pixeltype = pixeldict.get(pixelcode)

arcpy.MosaicToNewRaster_management(lidarstnull, in_workspace, outraster, "",pixeltype,"","1","FIRST", "FIRST")

arcpy.AddMessage("Mosaicked to new raster.")

