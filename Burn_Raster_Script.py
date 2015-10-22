#-------------------------------------------------------------------------------
# Name:        Create Burn Raster
# Purpose:      To create a "burn raster" from a vector file.
#
# Author:      ewallace
#
# Created:     30/06/2015
#-------------------------------------------------------------------------------

import arcpy
from arcpy import sa
from arcpy import env

# set environments

lidar = arcpy.GetParameterAsText(0)

arcpy.AddMessage("     Setting Environment parameters...")

arcpy.env.extent = lidar
arcpy.env.snapRaster = lidar
arcpy.env.cellSize = lidar

# get inputs

vector = arcpy.GetParameterAsText(1)  # get vector

burnval = arcpy.GetParameterAsText(2)  # get burn value

outfile = arcpy.GetParameterAsText(3)  # get ouput file name

# Add burn value field to vector file

arcpy.AddMessage("     Creating burn value field...")


def FieldExist(featureclass, fieldname):    # function that checks whether the field already exists
    fieldList = arcpy.ListFields(featureclass,fieldname)
    fieldCount = len(fieldList)
    return fieldCount == 1

burnfield = "Burn_Val" # uses FieldExist function to check whether the 'Burn_Val' field exists
check = FieldExist(vector, burnfield)
count = 1

while check == True:  # if the Burn_Val field already exists, this will add a suffix and check again
    burnfield = "Burn_Val" + str(count)
    check = FieldExist(vector,burnfield)
    count = count + 1

else:
    arcpy.AddField_management(vector,burnfield,"DOUBLE") # once a field name that doesn't already exist is found, it is added to the attribute table

# calculate field to add burn value to burn value field

arcpy.CalculateField_management(vector,burnfield, burnval) # adds the burn value to the new Burn_Val field

# convert the vector feature to a raster

arcpy.AddMessage("     Converting vector to raster...")

rasteroutput = "rasterout_" + burnfield

checkraster = arcpy.Exists(rasteroutput) # checks to see if the raster already exists
count = 1

while checkraster == True: # if the raster already exists, adds a suffix to the end and checks again
    rasteroutput = rasteroutput + "_" + str(count)
    count = count + 1
    checkraster = arcpy.Exists(rasteroutput)

arcpy.FeatureToRaster_conversion(vector,burnfield,rasteroutput)

# use map algebra to create burn raster with 0s isntead of Nulls

arcpy.AddMessage("     Converting nulls to zeros...")

outisnull = arcpy.sa.IsNull(rasteroutput)
outcon = arcpy.sa.Con(outisnull,0,rasteroutput,"value = 1")

arcpy.AddMessage("Saving results...")

outcon.save(outfile)



