# -*- coding: utf-8 -*-
"""
Created on Fri Jan 18 11:37:30 2019

@author: cspence
"""

import arcpy
from arcpy import env
import numpy as np
import os

mxd = arcpy.mapping.MapDocument("CURRENT")

''' 
Set up workspace 
'''

workspace = arcpy.GetParameterAsText(0)
arcpy.env.workspace = workspace

# Assemble layers
parcels = arcpy.GetParameterAsText(1)
townpolys = arcpy.GetParameterAsText(2)
watershedpolys = arcpy.GetParameterAsText(3)
auls = arcpy.GetParameterAsText(4)
soilsA = arcpy.GetParameterAsText(5)
soilsB = arcpy.GetParameterAsText(6)
soilsC = arcpy.GetParameterAsText(7)
soilsCD = arcpy.GetParameterAsText(8)
soilsD = arcpy.GetParameterAsText(9)
soilsUNC = arcpy.GetParameterAsText(10)
wetlands = arcpy.GetParameterAsText(11)
wpas_other = arcpy.GetParameterAsText(12)
z2wpas = arcpy.GetParameterAsText(13)
aqrecharge = arcpy.GetParameterAsText(14)
muniownedpts = arcpy.GetParameterAsText(15)
pastinspectpts = arcpy.GetParameterAsText(16)
catchbasins = arcpy.GetParameterAsText(17)
drainpipes = arcpy.GetParameterAsText(18)

''' Define Useful Functions'''

def join_spatiallyrs(lyr1, lyr2, outlyr, joinfield = '', newname = '', newalias = '', method = 'INTERSECT'):
    ''' This function spatially joins two shapefiles. "lyr2" is the target shapefile.
    "lyr1" is the joining shapefile. "outlyr" is the name of the resulting file.
    The default method is 'INTERSECT', assuming the joining shapefile is polygon
    data. Alternatively, users could run the function using "WITHIN" for point
    joining data.
    
    The join operation is 'JOIN_ONE_TO_MANY' so that multiple join features 
    intersecting/within the target parcel are all reported in the resulting
    shapefile. However, this means individual parcels will have multiple entries
    in the resulting attribute table.''' 
    def findindex(table, fieldname):
        ''' Function from https://gis.stackexchange.com/questions/101540/finding-the-index-of-a-field-with-its-name-using-arcpy
        to find the index of a table's fields from the field name '''
        return [i.name for i in arcpy.ListFields(table)].index(fieldname)
    
    # Repair geometry of both input feature classes
    # Check for geometry problems
    outtable = AutoName('geomtable')
    arcpy.AddMessage('Checking ' + lyr1 + ' geometry...')
    print('Checking ' + lyr1 + ' geometry...')
    arcpy.CheckGeometry_management(lyr1, outtable)
    
    #Repair geometry problems
    arcpy.AddMessage('Repairing ' + lyr1 + ' geometry...')
    print('Repairing ' + lyr1 + ' geometry...')
    arcpy.RepairGeometry_management(lyr1)
    
    arcpy.Delete_management(outtable)
    
    # Initiate a fieldmap object
    arcpy.AddMessage('Checking field maps')
    print('Checking field maps')
    fieldmappings = arcpy.FieldMappings()
    
    # Add two layer tables to the fieldmapping object
    fieldmappings.addTable(lyr2)
    fieldmappings.addTable(lyr1)
    
    
    if len(joinfield) < 1:
        # No meaningful join field: Just join them with no field method
        arcpy.AddMessage('Conducting spatial join')
        print('Conducting spatial join')
        arcpy.SpatialJoin_analysis(lyr2, lyr1, outlyr, 
                               'JOIN_ONE_TO_ONE',
                               'KEEP_ALL',
                               method)
    else:
        
        targetfields = arcpy.ListFields(lyr2)
        joinfields = arcpy.ListFields(lyr1)
        keepfield = findindex(lyr1, joinfield)
        
        keepfieldprops = joinfields[keepfield]
        fieldlength = keepfieldprops.length
        fieldtype = keepfieldprops.type
        # reset fieldtype to add field-compatible equivalent
        if fieldtype == 'Integer':
            fieldtype = 'LONG'
        elif fieldtype == 'String':
            fieldtype = 'TEXT'
        elif fieldtype == 'SmallInteger':
            fieldtype = 'SHORT'
        else:
            pass
        
        targetfields.append(joinfields[keepfield])
        keepers = list()
        for k in range(len(targetfields)):
            keepers.append(targetfields[k].name)
        
        for field in fieldmappings.fields:
            if field.name not in keepers:
                fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))
            else:
                field.mergeRule = 'maximum'
        arcpy.AddMessage('Conducting spatial join')
        print('Conducting spatial join')
        arcpy.SpatialJoin_analysis(lyr2, lyr1, outlyr, 
                                   'JOIN_ONE_TO_ONE',
                                   'KEEP_ALL',
                                   fieldmappings,
                                   method)
        
        # Re-name field
        arcpy.AddField_management(outlyr, newname, field_type = fieldtype)
        arcpy.CalculateField_management(outlyr, newname, "!" + joinfield + "!", "PYTHON_9.3")
        arcpy.DeleteField_management(outlyr, joinfield)
    
    return()  
    
def join_attrblyrs(inlyr, targetlyr, joinfield, keepfields):
    ''' This function spatially joins two feature classes. "lyr2" is the target shapefile.
    "lyr1" is the joining shapefile. '''
    
    def findindex(table, fieldname):
        ''' Function from https://gis.stackexchange.com/questions/101540/finding-the-index-of-a-field-with-its-name-using-arcpy
        to find the index of a table's fields from the field name '''
        return [i.name for i in arcpy.ListFields(table)].index(fieldname)
    
    arcpy.AddMessage('Adding ' + keepfields + ' attributes to '+ targetlyr + '...')
    print('Adding ' + keepfields + ' attributes to '+ targetlyr + '...')
    arcpy.JoinField_management(targetlyr, joinfield, inlyr, joinfield, keepfields)
    
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
    
    def addatt(clippedparcels, attlyr, muniname, joinfield, newname, newalias, method='INTERSECT'):
        # Get name of feature being added to parcels
        attname = os.path.basename(os.path.normpath(attlyr))

        # Spatially join input layer to clipped parcels
        arcpy.AddMessage('Adding ' + attname + ' attributes to ' + muniname + ' parcels...')
        print('Adding ' + attname + ' attributes to ' + muniname + ' parcels...')
        outname = AutoName(muniname + attname + '_parcels' )
        join_spatiallyrs(attlyr, clippedparcels, outname, joinfield, newname, newalias, method)
        
        return(outname)
        
    def overlapatt(clippedparcels, outline, attlyr, muniname, newname, newalias):
        
        # Add a field to each to hold area in square feet
        exp = "float(!SHAPE.AREA@SQUAREFEET!)"
        
        attname = os.path.basename(os.path.normpath(attlyr))
        clippedparcelname = os.path.basename(os.path.normpath(clippedparcels))
        areafield_attlyr = 'AREA_' + attname
        arcpy.AddField_management(clippedparcels, 'AREA_parcel', 'DOUBLE')
        arcpy.AddField_management(attlyr, areafield_attlyr, 'DOUBLE')
        
        # Calculate area in square feet
        # AREA_parcel: Area of each parcel.
        arcpy.CalculateField_management(clippedparcels, 'AREA_parcel', exp, "PYTHON_9.3")
        # areafield_attlyr: Area of each polygon with which to calculate overlap.
        arcpy.CalculateField_management(attlyr, areafield_attlyr, exp, "PYTHON_9.3")
        
        # Take union- will retain info of each unioned piece. 
        unionname = 'sites_union_' + attname
        arcpy.Union_analysis([clippedparcels, attlyr], unionname)
        
        # Find those that overlap BOTH
        exp1 = 'FID_' + clippedparcelname + ' <> -1 AND FID_' + attname + ' <> -1'
        filteredname = 'sites_' + attname + '_filtered'
        arcpy.Select_analysis(unionname, filteredname, exp1)
        
        # Calculate the area of each in square feet
        arcpy.AddField_management(filteredname, 'areacalc', 'DOUBLE')
        arcpy.CalculateField_management(filteredname, 'areacalc', exp, "PYTHON_9.3")
        
        # Calculate percent overlap
        arcpy.AddField_management(filteredname, 'overlap_p', 'DOUBLE')
        exp_overlap = '!areacalc!/!AREA_parcel!'
        arcpy.CalculateField_management(filteredname, 'overlap_p', exp_overlap, "PYTHON_9.3")
        
        # Spatially join back to original parcels, maintaining "overlap_p"
        newlayer = addatt(clippedparcels, filteredname, muniname, 'overlap_p', newname, newalias, method='CONTAINS')
        
        # Garbage collection!
        arcpy.Delete_management(unionname)
        arcpy.Delete_management(filteredname)
        
        return(newlayer)
        
    def areaatt(clippedparcels, outline, attlyr, muniname, newname, newalias):
        
        # Take union- will retain info of each unioned piece. 
        attname = os.path.basename(os.path.normpath(attlyr))
        clippedparcelname = os.path.basename(os.path.normpath(clippedparcels))
        unionname = 'sites_union_' + attname
        arcpy.Union_analysis([clippedparcels, attlyr], unionname)
        
        # Find those that overlap BOTH
        exp1 = 'FID_' + clippedparcelname + ' <> -1 AND FID_' + attname + ' <> -1'
        filteredname = 'sites_' + attname + '_filtered'
        arcpy.Select_analysis(unionname, filteredname, exp1)
        
        # Calculate the area of each in acres
        exp = "float(!SHAPE.AREA@ACRES!)"
        arcpy.AddField_management(filteredname, 'areacalc', 'DOUBLE')
        arcpy.CalculateField_management(filteredname, 'areacalc', exp, "PYTHON_9.3")
        
        # Spatially join back to original parcels, maintaining "overlap_p"
        newlayer = addatt(clippedparcels, filteredname, muniname, 'areacalc', newname, newalias, method = 'CONTAINS')
        
        # Garbage collection!
        arcpy.Delete_management(unionname)
        arcpy.Delete_management(filteredname)
        
        return(newlayer)
    
    # Create clip boundary
    munioutline = AutoName(muniname + '_outline')
    arcpy.Select_analysis(townpolys, munioutline, "town = '" + muniname_caps + "'")
    # Create a new file of parcels clipped to muni outline
    parcelmuniname = AutoName('clipparcels' + muniname)
    arcpy.AddMessage('Clipping parcels to ' + muniname + ' outline')
    print('Selecting parcels in ' + muniname)
    arcpy.Select_analysis(inparcels, parcelmuniname, "muni = '" + muniname + "'")     # ORIGINALLY USE "parcels" the global name, not "inparcels", the passed fuction argument.
    
    ''' Clip each input layer to the municipal outline, join to municipal parcels, and export as new file. '''
    # Add wetlands
    parcelswetlands = overlapatt(parcelmuniname, munioutline, wetlands, muniname, newname = 'wetland_p', newalias = 'Fraction wetland')
    
    # Add soils
    parcelssoilsA = areaatt(parcelmuniname, munioutline, soilsA, muniname, newname = 'hsgA_ac', newalias = 'Area A Soils')
    
    parcelssoilsB = areaatt(parcelmuniname, munioutline, soilsB, muniname, newname = 'hsgB_ac', newalias = 'Area B Soils')
    
    parcelssoilsC = areaatt(parcelmuniname, munioutline, soilsB, muniname, newname = 'hsgC_ac', newalias = 'Area C Soils')
    
    parcelssoilsCD = areaatt(parcelmuniname, munioutline, soilsCD, muniname, newname = 'hsgCD_ac', newalias = 'Area C/D Soils')
    
    parcelssoilsD = areaatt(parcelmuniname, munioutline, soilsD, muniname, newname = 'hsgD_ac', newalias = 'Area D Soils')
    
    parcelssoilsUNC = areaatt(parcelmuniname, munioutline, soilsUNC, muniname, newname = 'hsgUNC_ac', newalias = 'Area UNC Soils')
    
    # Add AUL sites
    parcelsauls = addatt(parcelmuniname, auls, muniname, joinfield = 'site_info', newname = 'aulsite', newalias = 'AUL Information')
    
    # Add Zone 2 WPAs
    parcelswpa2 = overlapatt(parcelmuniname, munioutline, z2wpas, muniname, newname = 'zii_p', newalias = 'Fraction Zone II Wellhead Protection Area')
    
    parcelswpa1i = overlapatt(parcelmuniname, munioutline, wpas_other, muniname, newname = 'z1i_p', newalias = 'Fraction Zone 1 Wellhead Protection Area')
    
    # Add watershed name
    parcelswshed = addatt(parcelmuniname, watershedpolys, muniname, joinfield = 'name', newname = 'watershed', newalias = 'Major Watershed', method='HAVE_THEIR_CENTER_IN')
    
    ''' Open optional inputs '''
    # Add municipal ownership status
    if muniownedpts: parcelsmunicipal = addatt(parcelmuniname, muniownedpts, muniname, joinfield = 'OWNER1', newname = 'owner', newalias = 'Municipal Owner', method = 'HAVE_THEIR_CENTER_IN')
    
    # Add catch basin presence/absence
    if catchbasins: parcelscbs = addatt(parcelmuniname, catchbasins, muniname, joinfield = 'Facility_I', newname = 'cbid', newalias = 'Catch Basin ID')

    # Add catch basin presence/absence
    if drainpipes: parcelsdps = addatt(parcelmuniname, drainpipes, muniname, joinfield = 'Feature_ID', newname = 'dpid', newalias = 'Drain Pipe ID')   
    
    # Add field inspection status
    if pastinspectpts: parcelspastinspect = addatt(parcelmuniname, pastinspectpts, muniname, joinfield = 'Date', newname = 'visityear', newalias = 'Year Inspected')
    
    # Add potential recharge depth
    if aqrecharge: parcelsrecharge = addatt(parcelmuniname, aqrecharge, muniname, joinfield = 'Ann_Rch_Depth', newname = 'rech_depth', newalias = 'Annual Recharge Depth (Units)')
    
    ''' Combine municipal parcels, each of which has one of the desired attributes, into a single feature class with all attributes.'''
    # Join together based on MAPC assigned ID
    arcpy.AddMessage('Joining in each attribute to parcels based on MAPC parcel ID...')
    commonid = 'mapc_id'
    join_attrblyrs(parcelswetlands, parcelmuniname, commonid, 'wetland_p')
    join_attrblyrs(parcelssoilsA, parcelmuniname, commonid, 'hsgA_ac')
    join_attrblyrs(parcelssoilsB, parcelmuniname, commonid, 'hsgB_ac')
    join_attrblyrs(parcelssoilsC, parcelmuniname, commonid, 'hsgC_ac')
    join_attrblyrs(parcelssoilsCD, parcelmuniname, commonid, 'hsgCD_ac')
    join_attrblyrs(parcelssoilsD, parcelmuniname, commonid, 'hsgD_ac')
    join_attrblyrs(parcelssoilsUNC, parcelmuniname, commonid, 'hsgUNC_ac')
    join_attrblyrs(parcelsauls, parcelmuniname, commonid, 'aulsite')
    join_attrblyrs(parcelswpa2, parcelmuniname, commonid, 'zii_p')
    join_attrblyrs(parcelswpa1i, parcelmuniname, commonid, 'z1i_p')
    join_attrblyrs(parcelswshed, parcelmuniname, commonid, 'watershed')
    
    ''' Optional inputs'''
    if muniownedpts: join_attrblyrs(parcelsmunicipal, parcelmuniname, commonid, 'owner')
    if pastinspectpts: join_attrblyrs(parcelspastinspect, parcelmuniname, commonid, 'visityear')
    if aqrecharge: join_attrblyrs(parcelsrecharge, parcelmuniname, commonid, 'rech_depth')
    if catchbasins: join_attrblyrs(parcelscbs, parcelmuniname, commonid, 'cbid')
    if drainpipes: join_attrblyrs(parcelsdps, parcelmuniname, commonid, 'dpid')

    
    print('Deleting unnecessary ' + muniname + ' files...')
    arcpy.Delete_management(parcelswetlands)
    arcpy.Delete_management(parcelssoilsA)
    arcpy.Delete_management(parcelssoilsB)
    arcpy.Delete_management(parcelssoilsC)
    arcpy.Delete_management(parcelssoilsCD)
    arcpy.Delete_management(parcelssoilsD)
    arcpy.Delete_management(parcelssoilsUNC)
    arcpy.Delete_management(parcelsauls)
    arcpy.Delete_management(munioutline)
    arcpy.Delete_management(parcelswpa2)
    arcpy.Delete_management(parcelswpa1i)
    arcpy.Delete_management(parcelswshed)
    
    ''' Optional inputs '''
    if muniownedpts: arcpy.Delete_management(parcelsmunicipal)
    if pastinspectpts: arcpy.Delete_management(parcelspastinspect)
    if catchbasins: arcpy.Delete_management(parcelscbs)
    if drainpipes: arcpy.Delete_management(parcelsdps)
    if aqrecharge: arcpy.Delete_management(parcelsrecharge)
    
    return(parcelmuniname)



''' Select subset of parcel database to work with '''

### In this case, towns in the Neponset River watershed
#townnames = ('Boston', 'Milton','Randolph','Dover','Dedham','Westwood','Medfield','Walpole','Norwood','Canton','Foxborough','Sharon', 'Stoughton', 'Quincy')
#townnames_caps = ('BOSTON', 'MILTON','RANDOLPH','DOVER', 'DEDHAM', 'WESTWOOD', 'MEDFIELD', 'WALPOLE', 'NORWOOD', 'CANTON', 'FOXBOROUGH', 'SHARON', 'STOUGHTON', 'QUINCY')

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
    arcpy.AddMessage("Starting " + muniname)
    muniparcelnames.append(muni_addatts(parcels, townpolys, muniname, muninamecaps))
    
arcpy.AddMessage("Completed all municipalities")
    
# Create an empty feature class with the desired schema
outfile = AutoName('Parcels_Reunited')
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

