#-------------------------------------------------------------------------------
# Name:        Lidar Mosaic Tool
# Purpose:      To mosaic several lidar images
#
# Author:      Eliza Wallace, GIS Analyst, MAPC, ewallace@mapc.org
#
# Created:     09/11/2014
#-------------------------------------------------------------------------------

import arcpy
import sys
from arcpy import env
from arcpy.sa import *

in_workspace = arcpy.GetParameterAsText(0)
outrastername = arcpy.GetParameterAsText(1)

env.workspace = in_workspace



try:
    lidarlist = arcpy.ListRasters()

    arcpy.AddMessage("Setting null values...")

    for file in lidarlist:
       outSetNull = arcpy.sa.SetNull(file, file, "VALUE < -1355")
       outSetNull = arcpy.sa.SetNull(file,file, "VALUE > 29100")
       outsplit = file.split(".")
       outfilename = outsplit[0] + "_stnull" + ".tif"
       outfilepath = in_workspace + "/" + outfilename
       outSetNull.save(outfilepath)

    arcpy.AddMessage("Building pyramids and calculating statistics...")

    arcpy.BuildPyramidsandStatistics_management(in_workspace, "NONE","BUILD_PYRAMIDS", "CALCULATE_STATISTICS" )

    lidarstnull = arcpy.ListRasters("*_stnull.tif") # creates a list of rasters in the folder with _stnull suffix
    outraster = outrastername + ".tif"

    arcpy.AddMessage("Mosaicking images...")

    testraster = in_workspace + "/" + lidarstnull[0] #chooses a raster to check for cell size and pixel type
    
    #reads pixel size from the test raster and stores as text for mosaic to new raster tool
    xcellsize = str(arcpy.GetRasterProperties_management(testraster,"CELLSIZEX"))
    ycellsize = str(arcpy.GetRasterProperties_management(testraster,"CELLSIZEY"))
    cellsize = str(max(int(xcellsize), int(ycellsize)))
    
    #reads pixel type from the test raster and stores as text for mosaic to new raster tool
    pixeldict = {'0':'1_BIT', '1':'2_BIT', '2':'4_BIT', '3':'8_BIT_UNSIGNED', '4':'8_BIT_SIGNED', 
    '5':'16_BIT_UNSIGNED', '6':'16_BIT_SIGNED','7':'32_BIT_UNSIGNED','8':'32_BIT_SIGNED',
    '9':'32_BIT_FLOAT','10':'64_BIT'}
    pixelcode = str(arcpy.GetRasterProperties_management(testraster,"VALUETYPE"))
    pixeltype = pixeldict.get(pixelcode)
    
    arcpy.MosaicToNewRaster_management(lidarstnull, in_workspace, outraster, "",pixeltype,"",cellsize,"FIRST", "FIRST")
    
    for raster in lidarstnull:
        arcpy.Delete_management(raster)
        
    arcpy.AddMessage("Mosaicked to new raster.")

except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
    arcpy.AddError(e.args[0])