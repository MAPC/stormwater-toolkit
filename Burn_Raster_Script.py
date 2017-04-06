#-------------------------------------------------------------------------------
# Name:        Create Burn Raster
# Purpose:      To create a "burn raster" from a vector file.
#
# Author:      Eliza Wallace, ewallace@mapc.org
#
# Created:     30/06/2015
#-------------------------------------------------------------------------------

import arcpy
import sys
from arcpy import sa
from arcpy import env

# set environments

lidar = arcpy.GetParameterAsText(0)

arcpy.AddMessage("     Setting Environment parameters...")

arcpy.env.extent = lidar
arcpy.env.snapRaster = lidar
arcpy.env.cellSize = lidar
arcpy.env.mask = lidar

# get inputs
vector = arcpy.GetParameterAsText(1)  # get vector
burnval = arcpy.GetParameterAsText(2)  # get burn value
outfile = arcpy.GetParameterAsText(3)  # get ouput file name

def AutoName(raster): # function that automatically names a feature class or raster
    checkraster = arcpy.Exists(raster) # checks to see if the raster already exists
    count = 2
    newname = raster

    while checkraster == True: # if the raster already exists, adds a suffix to the end and checks again
        newname = raster + str(count)
        count += 1
        checkraster = arcpy.Exists(newname)

    return newname

try: 
# Add burn value field to vector file
    newvector = AutoName("newvector")
    arcpy.CopyFeatures_management(vector,newvector)
    arcpy.AddMessage("     Creating burn value field...")

    burnfield = "burn_val"
    arcpy.AddField_management(newvector,burnfield,"DOUBLE") # once a field name that doesn't already exist is found, it is added to the attribute table

    # calculate field to add burn value to burn value field
    arcpy.CalculateField_management(newvector,burnfield, burnval) # adds the burn value to the new Burn_Val field

    # convert the vector feature to a raster
    arcpy.AddMessage("     Converting vector to raster...")

    rasteroutput = "rasterout_" + burnfield
    rasteroutput = AutoName(rasteroutput)

    arcpy.FeatureToRaster_conversion(newvector,burnfield,rasteroutput)

    # use map algebra to create burn raster with 0s isntead of Nulls
    arcpy.AddMessage("     Converting nulls to zeros...")

    outisnull = arcpy.sa.IsNull(rasteroutput)
    outcon = arcpy.sa.Con(outisnull,0,rasteroutput,"value = 1")

    arcpy.AddMessage("Saving results...")

    outcon.save(outfile)

except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
    arcpy.AddError(e.args[0])

