# -*- coding: utf-8 -*-
"""

Name:        Parcel Prioritization Tool
Purpose:     Given a shapefile of parcels and an input table of criteria, 
             weights, and ranks, this toolbox will calculate a prioritization 
             score of each parcel, rank the parcels by score, and generate a 
             rank-sorted parcel table.
            
Created on Thu Dec 27 09:14:07 2018

@author: cspence
"""

# set environments, etc

import arcpy
from arcpy import env
import xlrd
import numpy as np
from numpy.lib.recfunctions import rec_append_fields
import os

mxd = arcpy.mapping.MapDocument("CURRENT")

workspace = arcpy.GetParameterAsText(0)
workspace = 'K:\\DataServices\\Projects\\Current_Projects\\Environment\\Neponset\\IDDE_Task_FY19\BMP_Prioritization\\Data\\Spatial\\ParcelDB_creation.gdb'
arcpy.env.workspace = workspace

# Assemble layers
parcels = arcpy.GetParameterAsText(1)   # This is the "MA Land Parcel Database:
                                        # Stormwater Edition" created by running
                                        # the load_calc, nutrientmuni_pctile, and 
                                        # parcel_combine
#parcels = 'K:\\DataServices\\Projects\\Current_Projects\\Environment\\Neponset\\IDDE_Task_FY19\BMP_Prioritization\\Data\\Spatial\\ParcelDB_creation.gdb\\Parcels_withnutrientpctiles'
                                        
table = arcpy.GetParameterAsText(2)     # This table includes categorizations,
                                        # weights, and ranks of each criterion
#table = 'K:\\DataServices\\Projects\\Current_Projects\\Environment\\Neponset\\IDDE_Task_FY19\BMP_Prioritization\\Data\\Tabular\\entry_template_TN_20200_04_30.xlsx'
                                        
theme = arcpy.GetParameterAsText(3)     # Short (ideally < 3 character) descriptive 
                                        # string identifying priority theme
#theme = 'TN'
                                        


                                    
'''
Define useful functions
'''

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
    
def calc_catscr(parcels, fieldname, cattype, threshs, weights):
    
#    print(fieldname)
    
    def findindex(table, fieldname):
        ''' Function from https://gis.stackexchange.com/questions/101540/finding-the-index-of-a-field-with-its-name-using-arcpy
        to find the index of a table's fields from the field name '''
        return [i.name for i in arcpy.ListFields(table)].index(fieldname)

    num_groups = len(threshs)
    threshs = [str(t) for t in threshs]
    
    # Add a new field for the categorization score
    scrname = fieldname + '_scr'
    arcpy.AddField_management(parcels, scrname, 'DOUBLE')
    
    # Go through and calculate new value based on  original score and table cats
    fields = [fieldname, scrname]
    with arcpy.da.UpdateCursor(parcels, fields) as cursor:
        for row in cursor:
            if cattype == 'categorical':
                threshs = [str(t) for t in threshs]
                if num_groups >= 2:
                    if row[0] == threshs[0]:
                        row[1] = weights[0]
                    elif row[0] == threshs[1]:
                        row[1] = weights[1]
                        
                    if num_groups > 2:
                        if row[0] == threshs[2]:
                            row[1] = weights[2]
                        else:
                            pass
                        
                        if num_groups > 3:
                            if row[0] == threshs[3]:
                                row[1] = weights[3]
                            else:
                                pass
                        
                            if num_groups > 4:
                                if row[0] == threshs[4]:
                                    row[1] = weights[4]
                                else:
                                    pass
                        
                                if num_groups > 5:
                                    if row[0] == threshs[5]:
                                        row[1] = weights[5]
                                    else:
                                        pass
                        
                                    if num_groups > 6:
                                        if row[0] == threshs[6]:
                                            row[1] = weights[6]
                                        else:
                                            pass
                        
                                        if num_groups > 7:
                                            if row[0] == threshs[7]:
                                                row[1] = weights[7]
                                            else:
                                                pass
                        
                                            if num_groups > 8:
                                                if row[0] == threshs[8]:
                                                    row[1] = weights[8]
                                                else:
                                                    pass
                                            else:   # Pair: if 8
                                                pass
                                        else:   # Pair: if 7
                                            pass
                                    else:   # Pair: if 6
                                        pass   
                                else:    # Pair: if 5
                                    pass
                            else:   # Pair: if 4
                                pass
                        else:   # Pair: if 3
                            pass
                    else:   # Pair: if 2
                        pass
                else:
                    arcpy.AddMessage('ERROR: Criterion must have at least two categories')
                    
            elif cattype == 'numeric':
                threshs = [float(t) for t in threshs]
                if num_groups == 2:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
#                        print(weights[0])
                    else:
                        row[1] = weights[1]
#                        print(weights[1])
                elif num_groups == 3:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    else:
                        row[1] = weights[2]
                elif num_groups == 4:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    elif row[0] > threshs[2]:
                        row[1] = weights[2]
                    else:
                        row[1] = weights[3]
                elif num_groups == 5:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    elif row[0] > threshs[2]:
                        row[1] = weights[2]
                    elif row[0] > threshs[3]:
                        row[1] = weights[3]
                    else:
                        row[1] = weights[4]
                elif num_groups == 6:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    elif row[0] > threshs[2]:
                        row[1] = weights[2]
                    elif row[0] > threshs[3]:
                        row[1] = weights[3]
                    elif row[0] > threshs[4]:
                        row[1] = weights[4]
                    else:
                        row[1] = weights[5]
                elif num_groups == 7:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    elif row[0] > threshs[2]:
                        row[1] = weights[2]
                    elif row[0] > threshs[3]:
                        row[1] = weights[3]
                    elif row[0] > threshs[4]:
                        row[1] = weights[4]
                    elif row[0] > threshs[5]:
                        row[1] = weights[5]
                    else:
                        row[1] = weights[6]
                elif num_groups == 8:
                    if row[0] > threshs[0]:
                        row[1] = weights[0]
                    elif row[0] > threshs[1]:
                        row[1] = weights[1]
                    elif row[0] > threshs[2]:
                        row[1] = weights[2]
                    elif row[0] > threshs[3]:
                        row[1] = weights[3]
                    elif row[0] > threshs[4]:
                        row[1] = weights[4]
                    elif row[0] > threshs[5]:
                        row[1] = weights[5]
                    elif row[0] > threshs[6]:
                        row[1] = weights[6]
                    else:
                        row[1] = weights[7]
                else:
                    arcpy.AddMessage('ERROR: Number of thresholds is not an integer between 1 and 8')
                    
            elif cattype == 'binary':
                threshs = [str(t) for t in threshs]
                if row[0] is None or row[0] == ' ' or row[0] == 0:
                    row[1] = weights[0]
                else:
                    row[1] = weights[1]
            else:
                arcpy.AddMessage('ERROR: Category type (cattype) not recognized. Type must be "binary", "categorical", or "numeric." Check for typos or capitalization errors.')
            cursor.updateRow(row)
            
    return(scrname)
    
def prioritize_parcels(parcels, fieldnames, scrnames, field_weight, soilind):
    ''' Updates "parcels".'''
    
    # Add a new field for the categorization score
    arcpy.AddField_management(parcels, 'pri_scr', 'DOUBLE')
    
    # Calculate normalized weights
    total_weight = np.sum(field_weight)
    
    namelist = list()
    soillist = list()
    
    # Calculate the normalized weight for all criteria
    for k in range(len(fieldnames)):
        if field_weight[k] == 0:
            pass
        else:
            # # Add a weight field and normalize by total weight
            # wtfld = str(fieldnames[k]) + '_wt'
            # # soillist.append(soilind[k])
            # namelist.append(wtfld)
            # expr_type = "PYTHON"
            # expr = str(field_weight[k]) + '*(1.0/' + str(total_weight) + ')'
            # arcpy.AddField_management(parcels, wtfld, 'DOUBLE')
            # arcpy.CalculateField_management(parcels, wtfld, expr, expr_type)
            # Add a weight field
            wtfld = str(fieldnames[k]) + '_wt'
            # soillist.append(soilind[k])
            namelist.append(wtfld)
            expr_type = "PYTHON"
            expr = str(field_weight[k])
            arcpy.AddField_management(parcels, wtfld, 'DOUBLE')
            arcpy.CalculateField_management(parcels, wtfld, expr, expr_type)
            
    arcpy.AddMessage(str(namelist))
    arcpy.AddMessage(str(soillist))
    
    # add prioritization field
    expr_pri = ''
    expr_soil = 'max(['
    for k in range(len(namelist)):
        if soilind[k]:
            # If a soil field, add to the list of soil fields.
            expr_soil = expr_soil + '!' + scrnames[k] + '!*!' + namelist[k] + '!, '
        else:
            # If not, add to the calculation.
            expr_pri = expr_pri + ' + ' + '!' + scrnames[k] + '!*!' + namelist[k] + '!'
    
    # Done with list: Take max of soil fields.
    
    expr_soil = expr_soil[:-2]  # Strip last comma and space
    expr_soil = expr_soil + '])'# Conclude the "Max"
    if sum(soilind) == 0: 
        # If all soils weighted 0, don't add them to score.
        expr_pri = expr_pri[3:]     # Strip ' + ' from front of expr_pri.
    else:
        expr_pri = expr_pri[3:]     # Strip ' + ' from front of expr_pri.
        expr_pri = expr_pri + ' + ' + expr_soil

    arcpy.AddMessage(expr_pri)
    arcpy.CalculateField_management(parcels, 'pri_scr', expr_pri, expr_type)
    
    # remove unneeded fields
    for k in range(len(namelist)):
        arcpy.DeleteField_management(parcels, namelist[k])
    
    return()
    
def categorizebmp(parcellyr, table):
    # Function to convert original values of criteria in parcel database to 
    # score-relevant values based on user-defined table
    
    numcats = arcpy.GetCount_management(table)
    numcats = int(numcats[0])
    
    cols = [[r[0] for r in arcpy.da.SearchCursor(table, field.name)] for field in arcpy.ListFields(table)]
#    inds = cols[0]
#    criteria = cols[1]
    field_name = cols[2]
    field_weight = cols[3]
    num_groups = cols[4]
    cat_type = cols[5]
    threshs = np.concatenate([np.array(i) for i in cols[6:15]])
    threshs = np.reshape(threshs, (numcats, 9), order = 'F')    # use rows-first indexing (Fortran-like)
    
    weights = np.concatenate([np.array(i) for i in cols[15:]])
    weights = np.reshape(weights, (numcats, 9), order = 'F')    # Fortran-like indexing
    
    # Ensure soils correctly accounted for
    scrnames = list()
    numsoils = np.zeros(numcats, dtype = bool)
    deleteinds = list()
    for k in range(numcats):
        weight = field_weight[k]        
        if weight == 0:
            deleteinds.append(k)
        else:       # Calculate categories for that field
            fieldname = str(field_name[k])
            if fieldname.startswith('hsg'): numsoils[k] = True
            arcpy.AddMessage(fieldname + ' ' + str(numsoils[k]))
            cattype = str(cat_type[k])
            ngroups = num_groups[k]
            threshs_crit = threshs[k,0:ngroups]
            weights_crit = weights[k,0:ngroups]
            scrname = calc_catscr(parcellyr, fieldname, cattype, threshs_crit, weights_crit)
            scrnames.append(scrname)
            
    numsoils = np.delete(numsoils, deleteinds)
    
    # scrnames = np.asarray(scrnames) # Convert to a numpy array for easier handling.
    # soilscores = np.multiply(scrnames, numsoils)    # Multiply by array with 1 at soil scores to convert others to 0
    # maxind = np.max(soilscores)         # Get index where highest absolute value score is located
    # arcpy.AddMessage(str(soilscores))
    # arcpy.AddMessage(str(maxind))
    # numsoils = numsoils - maxind                # Convert the array indexing soil scores to indexing soil scores we do not want to keep
    # keepinds = numsoils == False                # Invert that array so that it indexes all the scores (not just soil scores) we DO want to keep
    # scrnames = np.multiply(scrnames, keepinds)      # Multiply previous array element-wise by previous so that only one soil score remains alongside other scores
    
    # # Convert back to a list.
    # scrnames = scrnames.tolist()
            
    prioritize_parcels(parcellyr, field_name, scrnames, field_weight, numsoils) # Adds prioritization score to each parcel
            
    return()
    
def importallsheets(in_excel, out_gdb):
    # Function taken from ESRI documentation http://pro.arcgis.com/en/pro-app/tool-reference/conversion/excel-to-table.htm
    workbook = xlrd.open_workbook(in_excel)
    sheets = [sheet.name for sheet in workbook.sheets()]

    print('{} sheets found: {}'.format(len(sheets), ','.join(sheets)))
    for sheet in sheets:
        # The out_table is based on the input excel file name
        # a underscore (_) separator followed by the sheet name
        out_table = os.path.join(
            out_gdb,
            arcpy.ValidateTableName(
                "{0}_{1}".format(os.path.basename(in_excel), sheet),
                out_gdb))

        print('Converting {} to {}'.format(sheet, out_table))

        # Perform the conversion
        arcpy.ExcelToTable_conversion(in_excel, out_table, sheet)
    return()
            
                                        
'''

Begin the Calculations

'''
# 0. Convert excel table to esri table
entrytable = AutoName('entryform')
result = arcpy.ExcelToTable_conversion(table, entrytable, "Data_Entry")
entrytable = result.getOutput(0)


# 1. Select records from only desired muni
# Get town names from "townpolys" feature class
townnames = unique_values(parcels, 'muni')
townnames = [x.title() for x in townnames]
townnames_caps = [x.upper() for x in townnames]

muniparcelnames = list()
for k in range(len(townnames_caps)):
    muni = townnames[k]
    muniname = AutoName('parcels' + muni)
    arcpy.Select_analysis(parcels, muniname, "muni = '" + muni + "'")
    arcpy.AddMessage("Working with " + muni + " parcels")

    # 2. Calculate scores for each criterion by threshold
    outname = AutoName('bmpcats_' + muniname)
    categorizebmp(muniname, entrytable) #outname
    arcpy.AddMessage("Categorized " + muni + " bmp criteria")

    # 3. Calculate percentiles, sort, and export to table
    parceltable = arcpy.da.TableToNumPyArray(muniname, '*', null_value = 0)

    nparcels = len(parceltable['pri_scr'])
    pripct = list()
    for j in range(nparcels):
        pripct.append(1.0 - (np.sum(parceltable['pri_scr'] > parceltable['pri_scr'][j])/float(nparcels)))
    
    new_table = rec_append_fields(parceltable, 'pri_pct', data = pripct, dtypes = '<f8')
    new_table = new_table[new_table['pri_pct'].argsort()]

    ranktable = AutoName(muni + '_rnkst')
    out_table = os.path.join(workspace, os.path.basename(ranktable))
    arcpy.da.NumPyArrayToTable(new_table, out_table)
    muniparcelnames.append(out_table)
    arcpy.Delete_management(muniname)
    arcpy.AddMessage("Finished scoring " + muni + " parcels")
    
    
## Create an empty feature class with the desired schema
outfile = AutoName('Parcels_' + theme)
arcpy.CreateTable_management(workspace, outfile, muniparcelnames[0])

# Append all municipal files onto empty feature class with appropriate schema
arcpy.AddMessage("Re-merging municipalities")
arcpy.Append_management(muniparcelnames, outfile, schema_type = "TEST")

dropfields = ["TN_pctile_scr", "TP_pctile_scr", "TSS_pctile_scr", "aulsite_scr",
              "hsgtype_scr", "OBJECTID_1", "Shape_1", "Shape_2", "LU_type",
              "Code_3_12", "Code_1_2", "Code_Parcel_Database", 
              "Desc_Parcel_Database", "Desc_full"]
arcpy.DeleteField_management(outfile, dropfields)

for k in range(len(muniparcelnames)):
    arcpy.Delete_management(muniparcelnames[k])


