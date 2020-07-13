# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 12:47:37 2019

@author: cspence
"""

# set environments, etc
import arcpy
import numpy as np
import os
#from arcpy import env
#import math
#import pandas as pd
#import numpy as np


'''
Define useful functions
'''

def AutoName(table): # function that automatically names a feature class or raster
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
    
    # Join luloadtable to bmpparcels to get code from 3-12
    shape_layer = AutoName(shapefile + '_table')
    arcpy.MakeFeatureLayer_management(shapefile, shape_layer, workspace = workspace)
    
    # Add a join from the pollutant-relevant land use type to parcel database
    temp_join = arcpy.AddJoin_management(shape_layer, shapefield, table, tablefield, 'KEEP_ALL')
    tempout = AutoName('tempout')
    arcpy.CopyFeatures_management(temp_join, tempout)
    
    # Now fix field names.
    #   Get names as strings and remove the $ in Excel sheet names
    table_name = os.path.basename(os.path.normpath(table))
    shapefile_name = os.path.basename(os.path.normpath(shapefile))
    table_name = table_name.replace("$", "_")
    table_name_plus = table_name + '*'
    shapefile_name = shapefile_name.replace("$", "_")
    shapefile_name_plus = shapefile_name + '*'
    
    # Get all field names in result feature class
    
    fms = arcpy.FieldMappings()
    
    for field in arcpy.ListFields(tempout, table_name_plus):
        fm = arcpy.FieldMap()
        fm.addInputField(tempout, field.name)
        fname = fm.outputField
        fname.name = field.name[(len(table_name) + 1):]
        fname.alias = fname.name
        fm.outputField = fname
        fms.addFieldMap(fm)
        
    for field in arcpy.ListFields(tempout, shapefile_name_plus):
        fm = arcpy.FieldMap()
        fm.addInputField(tempout, field.name)
        fname = fm.outputField
        fname.name = field.name[(len(shapefile_name) + 1):]
        fname.aliasName = fname.name
        fm.outputField = fname
        fms.addFieldMap(fm)
        
    #fms.addFieldMap(fm)
    
    arcpy.FeatureClassToFeatureClass_conversion(tempout, arcpy.env.workspace, outputname, field_mapping = fms)
    
    # Delete intermediate products
    arcpy.Delete_management(tempout)

    return(outputname)
    
def generate_loadexpr(load_field, area_ft_field):
    # Generates a string expression that tells ArcGIS' field calculator how
    # to calculate pollutant load using Unit Area Loading method
    
    expr = load_field + '*' + '(' + area_ft_field + '/43560' + ')'
    
    return(expr)
    
def calc_pER(parcelfc, lookuptable, load_field, lutype_field, imp_p_field, area_field, hsg_field):
    # parceltable: Parcel feature class (attribute table) with HSG classification, impervious percent, and land use type fields
    # lookuptable: A table matching combinations of land use types, perviousness, HSG class with phosphorus export rates
    # load_field: the empty field in parceltable in which to store calculated phosphrous export rates from each parce.
    # lutype_field: Name of the field in parceltable that contains land use type classification for lookup in the lookuptable.
    # imp_p_field: Name of the impervious percent field in parceltable.
    # area_field: Name of the area field in parceltable (acres).
    # hsg_field: Name of the hsg class field in parceltable.
    
    def calcp(perviousrate, imperviousrate, area_ft2, impervpct):
        area = area_ft2/float(43560)    # convert area in square feet to acres
        impervpct = impervpct/100.0
        
        a_pervious = (1.0 - impervpct)*area
        a_impervious = impervpct*area
        
        pexpratelbs = (perviousrate*a_pervious) + (imperviousrate*a_impervious)
        pexpratelbsacres = pexpratelbs/area
        
        return(pexpratelbs, pexpratelbsacres)
    
    # Assume all is formatted as numpy structured arrays.
    parceltable = arcpy.da.FeatureClassToNumPyArray(parcelfc, ['Code_1_2', 'mapc_id', 'lot_areaft', 'pct_imperv', 'hsgtype', 'TP_lbacyr'])
    l = len(parceltable)
    loadtable = arcpy.da.TableToNumPyArray(lookuptable, ['Phosphorus_source_by_land_use', 'Land_Surface_Cover', 'HSG', 'P_load_export_rate__lbs_acre_year_'])
    
    pexpratelbs = list()
    pexprateperacre = list()
    for k in range(l):
        area = parceltable[area_field][k]
        impervpct = parceltable[imp_p_field][k]
        hsgtype = parceltable[hsg_field][k]
        lutype = parceltable[lutype_field][k]
        
        # Look up other info from lookup table
        typematch = np.where(loadtable['Phosphorus_source_by_land_use'] == lutype, True, False)
        soilmatch = np.where(loadtable['HSG'] == hsgtype, True, False)
        pervmatch = np.where(loadtable['Land_Surface_Cover'] == 'Pervious', True, False)
        impervmatch = np.where(loadtable['Land_Surface_Cover'] == 'Directly connected impervious', True, False)
        
        perviousind = typematch & soilmatch & pervmatch
        impervind = typematch & soilmatch & impervmatch
        
        if str(hsgtype) == 'UNC': impervpct = 100.0
        
        if sum(perviousind) == 0:
            perviousrate = 0.0
        else:
            perviousrate = loadtable['P_load_export_rate__lbs_acre_year_'][perviousind][0]
            
        if sum(impervind) == 0:
            imperviousrate = 0.0
        else:
            imperviousrate = loadtable['P_load_export_rate__lbs_acre_year_'][impervind][0]
            
        (pexplbstemp, pexplbacrestemp) = calcp(perviousrate, imperviousrate, area, impervpct)
        pexpratelbs.append(pexplbstemp)
        pexprateperacre.append(pexplbacrestemp)

    return(pexpratelbs, pexprateperacre)
        
        
        
    
        
    
def findindex(table, fieldname):
    ''' Function from https://gis.stackexchange.com/questions/101540/finding-the-index-of-a-field-with-its-name-using-arcpy
    to find the index of a table's fields from the field name '''
    return [i.name for i in arcpy.ListFields(table)].index(fieldname)


    
    

''' 
Set up 
'''

mxd = arcpy.mapping.MapDocument("CURRENT")

# Set up workspace
workspace = arcpy.GetParameterAsText(0)
# workspace = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb'
arcpy.env.workspace = workspace

outfolder = workspace

# Assemble layers
loadparcels = arcpy.GetParameterAsText(1)       # This should be the feature class
                                            # generated by running parcelassessor.py   
# loadparcels = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\parcels_withnutrientload4'

townpolys = arcpy.GetParameterAsText(2)
# townpolys = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\NepRWA_townpolys'


'''
# Calculate percentiles within each municipality
'''
    

    
def calcp(perviousrate, imperviousrate, area_ft2, impervpct):
    area = area_ft2/float(43560)    # convert area in square feet to acres
    impervpct = impervpct/100.0
    
    a_pervious = (1.0 - impervpct)*area
    a_impervious = impervpct*area
    
    pexpratelbs = (perviousrate*a_pervious) + (imperviousrate*a_impervious)
    pexpratelbsacres = pexpratelbs/area
    
    return(pexpratelbs, pexpratelbsacres)
    
def epctile(array):
    pctiles = np.zeros(len(array))
    for n in range(len(array)):
        pctiles[n] = 1.0 - (sum(array > array[n])/float(len(array)))
        
    return(pctiles)
    
def munipctile(parcelfc,
              townpolys,
              muniname,
              muninamecaps,
              Pload_field = 'TP_lbacyr',
              Nload_field = 'TN_lbacyr',
              TSSload_field = 'TSS_lbacyr'):

    # Create clip boundary
    munioutline = AutoName(muniname + '_outline')
    arcpy.Select_analysis(townpolys, munioutline, "town = '" + muninamecaps + "'")
    # Create a new file of parcels clipped to muni outline
    parcelmuniname = AutoName('clipparcels' + muniname)
    arcpy.AddMessage('Clipping parcels to ' + muniname + ' outline')
    arcpy.Clip_analysis(parcelfc, munioutline, parcelmuniname)     # ORIGINALLY USE "parcels" the global name, not "inparcels", the passed fuction argument.
    # "parcels" was parcelswithloadvals3. Is this correct? Failed on Walpole.
    

    ''' Transfer fields of interest to a numpy array so we can work with numbers more easily. '''
    # Hitting memory error at this line (MemoryError: cannot allocate array memory)
    parceltable = arcpy.da.FeatureClassToNumPyArray(parcelmuniname, [Pload_field, Nload_field, TSSload_field], null_value = np.nan)
    l = len(parceltable)
    
    # Create vectors for the percentile values.
    TNpctile = np.zeros(l)
    TPpctile = np.zeros(l)
    TSSpctile = np.zeros(l)
    
    # Fill in arrays with values calculated from parceltable. 
    TNpctile = epctile(parceltable[Nload_field])
    TPpctile = epctile(parceltable[Pload_field])
    TSSpctile = epctile(parceltable[TSSload_field])
    
    ''' Switch back to working with the feature class '''
    # Add fields in preparation
    arcpy.AddField_management(parcelmuniname, 'TN_pctile', 'DOUBLE')
    arcpy.AddField_management(parcelmuniname, 'TP_pctile', 'DOUBLE')
    arcpy.AddField_management(parcelmuniname, 'TSS_pctile', 'DOUBLE') 
    
    fields = ['TN_pctile', 'TP_pctile', 'TSS_pctile']
    
    # Input field values
    j = 0
    with arcpy.da.UpdateCursor(parcelmuniname, fields) as cursor:
        for row in cursor:
            row[0] = TNpctile[j]
            row[1] = TPpctile[j]
            row[2] = TSSpctile[j]
            j = j + 1
            cursor.updateRow(row)
            
    arcpy.Delete_management(munioutline)
    
    return(parcelmuniname)
    

# Get town names from "townpolys" feature class
townnames = unique_values(townpolys, 'town')
townnames = [x.title() for x in townnames]
townnames_caps = [x.upper() for x in townnames]
muniparcelnames = list()
for k in range(len(townnames_caps)):
    muniname = townnames[k]
    muninamecaps = townnames_caps[k]
    print('Starting ' + muniname + ' Phosphorus load calculations')
    print('Starting ' + muniname)
    muniparcelnames.append(munipctile(loadparcels, townpolys, muniname, muninamecaps))


    
arcpy.AddMessage("Completed all municipalities")
    
## Create an empty feature class with the desired schema
outfile = AutoName('Parcels_withnutrientpctiles')
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

