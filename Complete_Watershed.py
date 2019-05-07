#-------------------------------------------------------------------------------
# Name:        Complete Watershed Tool
# Purpose:      For use in the Outfall Delineation. Note that this tool
# requires the Spatial Analyst extension, and is for use with ArcGIS 10.2.
#
# Author:      Eliza Wallace, GIS Analyst, Metropolitan Area Planning Council
#
# Created:     26/10/2015
#-------------------------------------------------------------------------------

import arcpy
import sys
from arcpy import sa
from arcpy.sa import *
from arcpy import env

# Get inputs

workspace = arcpy.GetParameterAsText(0)
lidar = arcpy.GetParameterAsText(1)
pour = arcpy.GetParameterAsText(2)
pptfield = arcpy.GetParameterAsText(3)
snap = arcpy.GetParameterAsText(4)
outwtrshd = arcpy.GetParameterAsText(5)
outpoly = arcpy.GetParameterAsText(6)

# set environment settings
env.workspace = workspace

''' Checks to ensure proper data format- should not be necessary if 
toolbox is set up correctly. '''

# 1. Check that workspace is a geodatabase
desc = arcpy.Describe(workspace)
props = desc.connectionProperties
db = props.database
dbname = str(db)
if dbname[-3:] == 'gdb':
    pass
else:
    arcpy.AddMessage("Input workspace is not a geodatabase")
    arcpy.AddMessage("Halting execution- data error")
    sys.exit(0)
    arcpy.AddMessage("Failed to halt execution")
    
# 2. Check that the LIDAR file and pour points passed to the file are both in the
    # established workspace
rasters = arcpy.ListRasters()
featureclasses = arcpy.ListFeatureClasses()
lidarname  = os.path.basename(lidar)
if unicode(lidarname) in rasters:
    pass
else:
    arcpy.AddMessage("LIDAR file is not raster or not in workspace")
    arcpy.AddMessage(lidar)
    arcpy.AddMessage("Halting execution- data error")
    sys.exit(0)
    arcpy.AddMessage("Failed to halt execution")

pourname = os.path.basename(pour)
if unicode(pourname) in featureclasses:
    pass
else:
    arcpy.AddMessage("Pour point file is not feature class or not in workspace")
    arcpy.AddMessage("Halting execution- data error")
    sys.exit(0)
    arcpy.AddMessage("Failed to halt execution")
    
    
# 3. Files are not nested into group layer.
    
lidarpathname = lidar[:-len(lidarname)]
if lidarpathname[:-1] == workspace or lidarname == lidar:
    pass
else:
    arcpy.AddMessage("LIDAR image may be in a nested group layer. Please check and remove from group layer.")
    arcpy.AddMessage("Halting execution- data error")
    sys.exit(0)
    arcpy.AddMessage("Failed to halt execution")
    
pourpathname = pour[:-len(pourname)]
if pourpathname[:-1] == workspace or pourname == pour:
    pass
else:
    arcpy.AddMessage("Pour point file may be in a nested group layer. Please check and remove from group layer.")
    arcpy.AddMessage("Halting execution- data error")
    sys.exit(0)
    arcpy.AddMessage("Failed to halt execution")

# 4. Snap point field is an integer
fields = arcpy.ListFields(pour)
for field in fields:
    if field.name == pptfield:
        if field.type not in ['Integer', 'SmallInteger']:
            arcpy.AddMessage("Pour point field is not type 'Integer'")
            arcpy.AddMessage("Halting execution- data error")
            sys.exit(0)
            arcpy.AddMessage("Failed to halt execution")
        else:
            pass
    else:
        pass
    
arcpy.AddMessage("Passed all data checks")

# defines function that checks whether a raster exists and adds a
# suffix to the output file name if it does.
def AutoName(raster):
    raster = raster.replace(' ','') # removes spaces from layer name for ESRI GRID format
    checkraster = arcpy.Exists(raster) # checks to see if the raster already exists
    count = 2
    newname = raster

    while checkraster == True: # if the raster already exists, adds a suffix to the end and checks again
        newname = raster + str(count)
        count += 1
        checkraster = arcpy.Exists(newname)

    return newname

try: 
    # fill sinks

    arcpy.AddMessage("Filling the sinks in the DEM...")

    fill = lidar + "_fill"
    fill = AutoName(fill)
    outfill = fill
    fill = arcpy.sa.Fill(lidar, 1)

    message = "Saving filled DEM as " + outfill + "..."
    arcpy.AddMessage(message)

    fill.save(outfill)

    # create flow direction raster

    arcpy.AddMessage("Creating the flow direction raster...")

    flowdir = lidar + "_flwdir"
    flowdir = AutoName(flowdir)
    outflowdir = flowdir
    flowdir = arcpy.sa.FlowDirection(outfill,"NORMAL")

    message = "Saving flow direction raster as " + outflowdir + "..."
    arcpy.AddMessage(message)

    flowdir.save(outflowdir)

    # create flow accumulation raster
    arcpy.AddMessage("Creating the flow accumulation raster. This may take a while...")

    flowacc = lidar + "_flwacc"
    flowacc = AutoName(flowacc)
    outflowacc = flowacc
    flowacc = arcpy.sa.FlowAccumulation(outflowdir)

    message = "Saving flow accumulation raster as " + outflowacc + "..."
    arcpy.AddMessage(message)

    flowacc.save(outflowacc)

    # snap pour points
    arcpy.AddMessage("Snapping pour points...")

    snap = int(snap)
    pptsnap = pour + "_snp"
    pptsnap = AutoName(pptsnap)
    outppt = pptsnap
    pptsnap = arcpy.sa.SnapPourPoint(pour,outflowacc,snap,pptfield)

    message = "Saving pour point raster as " + outppt + "..."

    arcpy.AddMessage(message)

    pptsnap.save(outppt)

    # create watershed raster
    arcpy.AddMessage("Creating watershed raster...")

    wtrshd = arcpy.sa.Watershed(outflowdir,outppt,"Value")
    wtrshd.save(outwtrshd)
    
    arcpy.AddMessage("Creating watershed vector...")
    
    arcpy.RasterToPolygon_conversion(outwtrshd,outpoly,"SIMPLIFY","VALUE")
    
    # change gridcode field name to cbid_int
    arcpy.AddField_management(outpoly,"cbid_int","SHORT")
    arcpy.CalculateField_management(outpoly,"cbid_int","!gridcode!","PYTHON")
    arcpy.DeleteField_management(outpoly,"gridcode")
  
except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
    arcpy.AddError(e.args[0])
    







