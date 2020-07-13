# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 13:14:40 2019

@author: cspence
"""


import arcpy
import numpy as np

mxd = arcpy.mapping.MapDocument("CURRENT")

''' 
Set up workspace 
'''

workspace = arcpy.GetParameterAsText(0)
arcpy.env.workspace = workspace

# Assemble layers
parcels = arcpy.GetParameterAsText(1)
townpolys = arcpy.GetParameterAsText(2)
score1 = arcpy.GetParameterAsText(3)
score2 = arcpy.GetParameterAsText(4)
score3 = arcpy.GetParameterAsText(5)
score4 = arcpy.GetParameterAsText(6)

outfolder = workspace


''' Define Useful Functions'''
    
def join_attrblyrs(inlyr, targetlyr, joinfield, keepfields):
    ''' This function spatially joins two feature classes. "lyr2" is the target shapefile.
    "lyr1" is the joining shapefile. From the input layer, only "keepfields"
    are retained in the target layer. "Keepfields" are renamed in the target layer
    according to the parcel table's prioritization theme.'''
    
    def findindex(table, fieldname):
        ''' Function from https://gis.stackexchange.com/questions/101540/finding-the-index-of-a-field-with-its-name-using-arcpy
        to find the index of a table's fields from the field name '''
        return [i.name for i in arcpy.ListFields(table)].index(fieldname)
    
    arcpy.AddMessage('Adding ' + keepfields + ' attributes to '+ targetlyr + '...')
    print('Adding ' + keepfields + ' attributes to '+ targetlyr + '...')
    arcpy.JoinField_management(targetlyr, joinfield, inlyr, joinfield, keepfields)
    
    pathstr = workspace + '\\Parcels_'
    lenpath = len(pathstr)
    theme = inlyr[lenpath:]
    newname = keepfields + '_' + theme
    
    arcpy.AddField_management(targetlyr, newname, 'DOUBLE')
    arcpy.CalculateField_management(targetlyr, newname, "!" + keepfields + "!", "PYTHON")
    arcpy.DeleteField_management(targetlyr, keepfields)
    
    
    return() 
    
def AutoName(table): 
    # function that automatically names a feature class or raster
    # Adapted from MAPC's stormwater toolkit script at https://github.com/MAPC/stormwater-toolkit/blob/master/Burn_Raster_Script.py
    
    checktable = arcpy.Exists(table) # checks to see if the raster already exists
    count = 2
    newname = table

    while checktable == True: # if the raster already exists, adds a suffix to the end and checks again
        newname = table + str(count)
        count += 1
        checktable = arcpy.Exists(newname)

    return newname

def unique_values(table, field):
    # Function from http://geospatialtraining.com/get-a-list-of-unique-attribute-values-using-arcpy/
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})

    
def join_table_shapefile(table, tablefield, shapefile, shapefield, outputname):
    # Function to join a table to a shapefile, resulting in a hard-copy shapefile with attributes from the table
    
    # Join luloadtable to bmpparcels to get code from 3-12
    shape_layer = AutoName(shapefile + '_table')
    arcpy.MakeFeatureLayer_management(shapefile, shape_layer, workspace = workspace)
    
    # Add a join from the pollutant-relevant land use type to parcel database
    temp_join = arcpy.AddJoin_management(shape_layer, shapefield, table, tablefield, 'KEEP_ALL')
    arcpy.CopyFeatures_management(temp_join, outputname)

    return(outputname)
    
def muni_addatts(inparcels, townpolys, muniname, muniname_caps):
    
    
    # Create clip boundary
    munioutline = AutoName(muniname + '_outline')
    arcpy.Select_analysis(townpolys, munioutline, "town = '" + muniname_caps + "'")
    # Create a new file of parcels clipped to muni outline
    parcelmuniname = AutoName('clipparcels' + muniname)
    arcpy.AddMessage('Clipping parcels to ' + muniname + ' outline')
    print('Clipping parcels to ' + muniname + ' outline')
    arcpy.Clip_analysis(inparcels, munioutline, parcelmuniname)     # ORIGINALLY USE "parcels" the global name, not "inparcels", the passed fuction argument.
    # "parcels" was parcelswithloadvals3. Is this correct? Failed on Walpole.
    
    ''' Combine municipal parcels, each of which has one of the desired attributes, into a single feature class with all attributes.'''
    # Join together based on MAPC assigned ID
    arcpy.AddMessage('Joining in each attribute to parcels based on MAPC parcel ID...')
    commonid = 'mapc_id'
    join_attrblyrs(score1, parcelmuniname, commonid, 'pri_pct')
    if score2: join_attrblyrs(score2, parcelmuniname, commonid, 'pri_pct')
    if score3: join_attrblyrs(score3, parcelmuniname, commonid, 'pri_pct')
    if score4: join_attrblyrs(score4, parcelmuniname, commonid, 'pri_pct')
    
    arcpy.Delete_management(munioutline)
    
    return(parcelmuniname)

''' Select subset of parcel database to work with '''

# Get town names from "townpolys" feature class
townnames = unique_values(townpolys, 'town')
townnames = [x.title() for x in townnames]
townnames_caps = [x.upper() for x in townnames]

''' 
Generate Scores 
'''

# Go through list of towns, add soil and BMP attributes to each town
muniparcelnames = list()
for k in np.arange(0, len(townnames)):
    muniname = townnames[k]
    muninamecaps = townnames_caps[k]
    print('Starting ' + muniname)
    muniparcelnames.append(muni_addatts(parcels, townpolys, muniname, muninamecaps))
    
arcpy.AddMessage("Completed all municipalities")
    
''' Combine municipal-specific results into one feature class. '''
# Create an empty feature class with the desired schema
outfile = AutoName('Parcels_complete')
arcpy.CopyFeatures_management(muniparcelnames[0], outfile)
arcpy.DeleteRows_management(outfile)    # Empty the output file

# Append all municipal files onto empty feature class with appropriate schema
arcpy.AddMessage("Re-merging municipalities")
arcpy.Append_management(muniparcelnames, outfile, schema_type = "TEST")
for k in range(len(muniparcelnames)):
    arcpy.Delete_management(muniparcelnames[k])

# Repair geometry
outtable = AutoName('geomtable')
arcpy.AddMessage('Checking ' + outfile + ' geometry...')
arcpy.CheckGeometry_management(outfile, outtable)

    
#Repair geometry problems
arcpy.AddMessage('Repairing ' + outfile + ' geometry...')
arcpy.RepairGeometry_management(outfile)
arcpy.Delete_management(outtable)

