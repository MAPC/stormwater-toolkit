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

# defines function that checks whether a raster exists and adds a
# suffix to the output file name if it does.
def AutoName(raster):
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
    fill = arcpy.sa.Fill(lidar)

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
  
except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
    arcpy.AddError(e.args[0])
    







