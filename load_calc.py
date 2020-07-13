# -*- coding: utf-8 -*-
"""
@author: cspence

Name:        Nutrient Load Calculator
Purpose:     Combines potential BMP parcels with other data to assign
             suitability attributes to each parcel. This step of the toolbox
             combines the parcel database with BMP-relevant attributes.
             The attributes added to the parcel database at this step require 
             pre-processing or other preliminary calculations before being 
             joined to the parcel database.

Author:      cspence

Created:     Tue Nov 13 09:42:42 2018
Updated:     Thurs. May 21 11:26:00 2020

"""

# Import packages 
import arcpy
import numpy as np
import os


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
    # This functino joins a table and feature class ("shapefile" based on the 
    # join key in "tablefield" and "shapefield." Saves the joined result as a 
    # new feature class named "outputname."
    
    # Create spatial dataset to Feature Layer 
    shape_layer = AutoName(shapefile + '_table')
    arcpy.MakeFeatureLayer_management(shapefile, shape_layer, workspace = workspace)
    
    # Add a join from the table to the newly created feature layer
    temp_join = arcpy.AddJoin_management(shape_layer, shapefield, table, tablefield, 'KEEP_ALL')
    tempout = AutoName('tempout')
    # To make the join permanent, copy the result to a new feature class "tempout"
    arcpy.CopyFeatures_management(temp_join, tempout)
    
    # Now clean up field names, which at present are messy
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
    # parcelfc: Parcel feature class (attribute table) with HSG classification, impervious percent, and land use type fields
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

# set final output name
outfolder = workspace

# Assemble layers
bmpparcels = arcpy.GetParameterAsText(1)       # This should be the feature class
                                            # generated by running parcel_combine.py   
# bmpparcels = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\Parcels_Reunited2'
                                            
                                            
loadmaptable = arcpy.GetParameterAsText(2)  # Table of land uses matched to nutrient loads
# loadmaptable = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\loadmaptable'

luloadtable = arcpy.GetParameterAsText(3)   # Table matching standard use codes to 
                                            # loadmaptable land use categories
# luloadtable = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\luloadtable'

plulookup = arcpy.GetParameterAsText(4)     # Land use lookup for P calculations
# plulookup = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\plulookup'

table_1_2 = arcpy.GetParameterAsText(5)     # P export rate table by LU and HGS type 
# table_1_2 = 'K:\\DataServices\\Projects\\Current_Projects\\Environment\\Neponset\\IDDE_Task_FY19\\BMP_Prioritization\\Data\\Spatial\\ParcelDB_creation.gdb\\table_1_2'

townpolys = arcpy.GetParameterAsText(6)
# townpolys = 'K:\DataServices\Projects\Current_Projects\Environment\Neponset\IDDE_Task_FY19\BMP_Prioritization\Data\Spatial\ParcelDB_creation.gdb\NepRWA_townpolys'

# Set up names from paths
bmpparcels_name = os.path.basename(os.path.normpath(bmpparcels))
loadmaptable_name = os.path.basename(os.path.normpath(loadmaptable))
luloadtable_name = os.path.basename(os.path.normpath(luloadtable))
plu_table_name = os.path.basename(os.path.normpath(plulookup))
pload_name = os.path.basename(os.path.normpath(table_1_2))


''' Calculate load for each parcel'''

# 1. Join luloadtable to bmpparcels to get code from 3-12 to attach nutrient export rates
keepfields = ['Code_3_12']  
outname = AutoName('parcels_with_loadusecode')
bmp_with312code = join_table_shapefile(loadmaptable, 'Code_Parcel_Database', bmpparcels, 'luc_adj_1', outname)
bmp_with312code_name = os.path.basename(os.path.normpath(bmp_with312code))

# Repeat with EPA table/guidelines for calculating MS4 phosphorus export rates: add table 1-2
outname2 = AutoName('parcels_with_plutype')
parcel_w_12_lutype = join_table_shapefile(plulookup, 'Code_Parcel_Database', bmp_with312code, 'luc_adj_1', outname2)
parcel_w_12_lutype_name = os.path.basename(os.path.normpath(parcel_w_12_lutype))

# 1a.1 Validate table to replace FEE, ROW parcels with "Low-Priority Loading" (Total N, Total Suspended Solids)
# or "Highway" or "Water" classes (table 1-2)

lucode = 'luc_adj_1'
codename = 'Code_3_12'
codePname = 'Code_1_2'
wetland_p = 'wetland_p'
area_ft = 'lot_areaft'

fields = [lucode, codename, codePname, wetland_p, area_ft]

with arcpy.da.UpdateCursor(parcel_w_12_lutype, fields) as cursor:
    for row in cursor:
        if row[0] is None or row[0] == ' ':
            row[1] = 'Low Priority Loading'
            row[2] = 'Open Land'
        elif row[3] >= 0.9: # If parcel 90% wetland or more
            row[1] = 'Low Priority Loading'
            row[2] = 'Forest'
        cursor.updateRow(row)

# 1a. Validate table to make sure FEE, ROW parcels are correctly encoded

polyname = 'poly_typ'
codename = 'Code_3_12'
codePname = 'Code_1_2'

fields = [polyname, codename, codePname]

with arcpy.da.UpdateCursor(parcel_w_12_lutype, fields) as cursor:
    for row in cursor:
        if row[0] == "ROW":
            row[1] = 'Highway'
            row[2] = 'Highway'
            
        elif row[0] == "PRIV_ROW":
            row[1] = 'Highway'
            row[2] = 'Highway'
            
        elif row[0] == "RAIL_ROW":
            row[1] = 'Highway'
            row[2] = 'Highway'
            
        elif row[0] == "WATER":
            row[1] = 'Low Priority Loading'
            row[2] = 'Water'
            
        cursor.updateRow(row)
        


print "ROW, PRIV_ROW, WATER codes updated"
arcpy.AddMessage("ROW, PRIV_ROW, WATER codes updated")

# 1b. Use new, fully filled out dataset to calculate nutrient loads
outname_new = AutoName('parcels_with_loadvals')
bmp_withloadval = join_table_shapefile(luloadtable, 'LU_Type', parcel_w_12_lutype, codename, outname_new)

# 2. Calculalate nutrient loads based on table 3-12 figures & LU categories, impervious cover percentage
# 2a. Add fields with appropriate settings

arcpy.AddField_management(bmp_withloadval, 'TN_lbyr', 'DOUBLE')
arcpy.AddField_management(bmp_withloadval, 'TP_lbyr', 'DOUBLE')
arcpy.AddField_management(bmp_withloadval, 'TSS_lbyr', 'DOUBLE')

# 2b. Fill in fields with new calculations for total Nitrogen, suspended solids load
tn_field = '!TN_lbacyr!'
tp_field = '!TP_lbacyr!'
tss_field = '!TSS_lbacyr!'

areaft = '!lot_areaft!'  

expr_N = generate_loadexpr(tn_field, areaft)
expr_TSS = generate_loadexpr(tss_field, areaft)

expr_type = "PYTHON"

arcpy.CalculateField_management(bmp_withloadval, 'TN_lbyr', expr_N, expr_type)
arcpy.CalculateField_management(bmp_withloadval, 'TSS_lbyr', expr_TSS, expr_type)

'''
# Estimate total P export rate based on EPA MS4 method
'''
    
def calcp(perviousrate, imperviousrate, area_ft2, impervpct):
    area = area_ft2/float(43560)    # convert area in square feet to acres
    impervpct = impervpct/100.0
    
    a_pervious = (1.0 - impervpct)*area
    a_impervious = impervpct*area
    
    pexpratelbs = (perviousrate*a_pervious) + (imperviousrate*a_impervious)
    pexpratelbsacres = pexpratelbs/area
    
    return(pexpratelbs, pexpratelbsacres)
    
def muniPload(parcelfc,
              townpolys,
              muniname,
              muninamecaps,
              lookuptable = table_1_2,
              load_field = 'TP_lbacyr',
              lutype_field = 'Code_1_2',
              imp_p_field = 'pct_imperv',
              area_field = 'lot_areaft',
              hsg_fields = ['hsgA_ac', 'hsgB_ac', 'hsgC_ac', 'hsgCD_ac', 'hsgD_ac', 'hsgUNC_ac']):

    # Create clip boundary
    munioutline = AutoName(muniname + '_outline')
    arcpy.Select_analysis(townpolys, munioutline, "town = '" + muninamecaps + "'")
    # Create a new file of parcels clipped to muni outline
    parcelmuniname = AutoName('clipparcels' + muniname)
    arcpy.AddMessage('Clipping parcels to ' + muniname + ' outline')
    arcpy.Clip_analysis(parcelfc, munioutline, parcelmuniname)
    
    parceltable = arcpy.da.FeatureClassToNumPyArray(parcelmuniname, ['Code_1_2', 'mapc_id', 'lot_areaft', 'pct_imperv', 'hsgA_ac', 'hsgB_ac', 'hsgC_ac', 'hsgCD_ac', 'hsgD_ac', 'hsgUNC_ac', 'TP_lbacyr'])
    l = len(parceltable)
    loadtable = arcpy.da.TableToNumPyArray(lookuptable, ['Phosphorus_source_by_land_use', 'Land_Surface_Cover', 'HSG', 'P_load_export_rate__lbs_acre_year_'])
    
    pexpratelbs = list()
    pexprateperacre = list()
    for n in range(l):
        area = parceltable[area_field][n]
        impervpct = parceltable[imp_p_field][n]
        lutype = parceltable[lutype_field][n]
        hsgA = parceltable[hsg_fields[0]][n]
        hsgB = parceltable[hsg_fields[1]][n]
        hsgC = parceltable[hsg_fields[2]][n]
        hsgCD = parceltable[hsg_fields[3]][n]
        hsgD = parceltable[hsg_fields[4]][n]
        hsgUNC = parceltable[hsg_fields[5]][n]
        hsgareas = np.asarray([hsgA, hsgB, hsgC, hsgCD, hsgD, hsgUNC])
        if np.max(hsgareas) == hsgA:
            hsgtype = 'A'
        elif np.max(hsgareas) == hsgB:
            hsgtype = 'B'
        elif np.max(hsgareas) == hsgC:
            hsgtype = 'C'
        elif np.max(hsgareas) == hsgCD:
            hsgtype = 'C/D'
        elif np.max(hsgareas) == hsgD:
            hsgtype = 'D'
        else:
            hsgtype = 'D'
        lutype = parceltable[lutype_field][n]
        
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
    
    loadname_lbs = 'TP_lbyr'
    loadname_lbacres = 'TP_lbacyr'
    
    fields = [loadname_lbs, loadname_lbacres]
    
    j = 0
    with arcpy.da.UpdateCursor(parcelmuniname, fields) as cursor:
        for row in cursor:
            row[0] = pexpratelbs[j]
            row[1] = pexprateperacre[j]
            j = j + 1
            cursor.updateRow(row)
            
    arcpy.Delete_management(munioutline)
    
    return(parcelmuniname)

# Get town names from "townpolys" feature class
townnames = unique_values(townpolys, 'town')
townnames = [x.title() for x in townnames]
townnames_caps = [x.upper() for x in townnames]

# Loop through all municipalities and estimate loads in each.
muniparcelnames = list()
for k in range(len(townnames_caps)):
    muniname = townnames[k]
    muninamecaps = townnames_caps[k]
    arcpy.AddMessage('Starting ' + muniname + ' Phosphorus load calculations')
    print('Starting ' + muniname + ' Phosphorus load calculations')
    print('Starting ' + muniname)
    muniparcelnames.append(muniPload(bmp_withloadval, townpolys, muniname, muninamecaps))
    
arcpy.AddMessage("Completed all municipalities")

# Combine results for each municipality into one feature class.

# Create an empty feature class with the desired schema
outfile = AutoName('Parcels_withnutrientload')
arcpy.CopyFeatures_management(muniparcelnames[0], outfile)
arcpy.DeleteRows_management(outfile)    # Empty the output file

# Append all municipal files onto empty feature class with appropriate schema
arcpy.AddMessage("Re-merging municipalities")
arcpy.Append_management(muniparcelnames, outfile, schema_type = "TEST")
arcpy.AddMessage("Municipalities Merged")

# Now that results have been combined, delete individual municipal results.
# Also delete other layers that have outlived their usefulness.
arcpy.Delete_management(bmp_with312code)
arcpy.Delete_management(parcel_w_12_lutype)
arcpy.Delete_management(bmp_withloadval)
for k in range(len(muniparcelnames)):
    arcpy.Delete_management(muniparcelnames[k])

# Clean up results further.
# Check geometry for issues.
outtable = AutoName('geomtable')
arcpy.AddMessage('Checking ' + outfile + ' geometry...')
arcpy.CheckGeometry_management(outfile, outtable)

#Repair geometry problems
arcpy.AddMessage('Repairing ' + outfile + ' geometry...')
arcpy.RepairGeometry_management(outfile)
arcpy.Delete_management(outtable)

# Clean results further by deleting extraneous fields
arcpy.DeleteField_management(outfile, 'OBJECTID')
arcpy.DeleteField_management(outfile, 'LU_type')
arcpy.DeleteField_management(outfile, 'OBJECTID_1')
arcpy.DeleteField_management(outfile, 'Code_3_12')
arcpy.DeleteField_management(outfile, 'Code_1_2')
arcpy.DeleteField_management(outfile, 'Code_Parcel_Database')
arcpy.DeleteField_management(outfile, 'OBJECTID_12')
arcpy.DeleteField_management(outfile, 'Code_3_12_13')
arcpy.DeleteField_management(outfile, 'Code_Parcel_Database_1')
arcpy.DeleteField_management(outfile, 'Desc_Parcel_Database_1')
arcpy.DeleteField_management(outfile, 'Desc_full_1')
arcpy.DeleteField_management(outfile, 'temp')

# Fin

