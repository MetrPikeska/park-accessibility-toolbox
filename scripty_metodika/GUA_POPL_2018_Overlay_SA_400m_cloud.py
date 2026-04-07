#####----------------------------------------------------------------------------------
###Author: Veerle Martens
#Date: may 2012
#
#Purpose: Create service areas around each building block and find out the area of
#         green urban area that can be reached.
#---------------------------------------------------------------------------------

#create error handler
class CustomError(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)

import sys, arcpy, time, traceback, os.path

def printMessage(msg):
    print(msg) # in Python shell
    ##arcpy.AddMessage(msg) # in ArcGIS

def fastJoinFields(targetTable, targetCommonField, sourceTable, sourceCommonField, joinFields):
    count = int(arcpy.GetCount_management(targetTable).getOutput(0))
    progressorBreaks = [int(float(count)*float(br)/100.0) for br in range(10,100,10)]
    printMessage("Making the dictionary...")
    sourceFieldNameList = sourceCommonField.split() + joinFields.split(';')  # like: ["OID","FieldA","FieldB"]
    valueDict = {r[0]:(r[1:]) for r in arcpy.da.SearchCursor(sourceTable, sourceFieldNameList)}  # like: {BE456:(254,5253)}
    printMessage(" Adding join field(s)...")
    originalTargetFieldNameList = [f1.name for f1 in arcpy.ListFields(targetTable)]
    fList = []
    for fieldName in joinFields.split(';'): 
        field_i = arcpy.ListFields(sourceTable, fieldName)
        fList = fList + field_i
    # Check the name of the fields to add and add them in the targetTable
    joinFieldNameList = []
    for i in range(len(fList)):
        nameF = fList[i].name
        if nameF in originalTargetFieldNameList:
            nameF = nameF + "_1"
            if nameF in originalTargetFieldNameList:
                nameF = nameF.replace(nameF[-1:],str(int(nameF[-1:])+1))
        if arcpy.Describe(targetTable).dataType in ["ShapeFile", "DbaseTable"]:
            nameF = nameF[0:9] + "_"
        typeF = fList[i].type
        if typeF in ['Integer','OID']:
            arcpy.AddField_management(targetTable,nameF,field_type='LONG')
        elif typeF == 'SmallInteger':
            arcpy.AddField_management(targetTable,nameF,field_type='SHORT')
        elif typeF == 'String':
            arcpy.AddField_management(targetTable,nameF,field_type='TEXT',field_length=fList[i].length)
        elif typeF == 'Double':
            arcpy.AddField_management(targetTable,nameF,field_type='DOUBLE')
        elif typeF == 'Single':
            arcpy.AddField_management(targetTable,nameF,field_type='FLOAT')
        elif typeF == 'Date':
            arcpy.AddField_management(targetTable,nameF,field_type='DATE')
        else:
            arcpy.AddError('\nUnknown field type: {0} for field: {1}'.format(typeF,nameF))
        joinFieldNameList = joinFieldNameList + nameF.split()
    joinFieldNameList = targetCommonField.split() + joinFieldNameList
    # Copy the values  from the dictionary to the updated fields
    printMessage(" Populating the field(s)...")
    ct = 0
    with arcpy.da.UpdateCursor(targetTable, joinFieldNameList) as updateRows:
        for updateRow in updateRows:
            ct+=1
            if ct in progressorBreaks:
                printMessage(" " + str(int(round(ct*100.0/count))) + ' percent complete...')
            keyValue = updateRow[0]
            if keyValue in valueDict:
                for j in range(len(fList)):
                    updateRow[j+1] = valueDict[keyValue][j]
                updateRows.updateRow(updateRow)

def fieldExists(inFeatureClass, inFieldName):
    for fld in arcpy.Describe(inFeatureClass).fields:
        if fld.name.lower() == inFieldName.lower():
            return True
    return False

print "start: " + time.strftime("%H:%M:%S", time.localtime())

inPath = arcpy.GetParameterAsText(0)
outPath = arcpy.GetParameterAsText(1)
UATL_POPL_2018_fld = arcpy.GetParameterAsText(2)
UATL_ID_Fld = arcpy.GetParameterAsText(3)
CODE_Fld = arcpy.GetParameterAsText(4)
group_id = arcpy.GetParameterAsText(5)
HDENS_2011_CODE_fld = arcpy.GetParameterAsText(6)
URAU_CITY_2020_CODE_fld = arcpy.GetParameterAsText(7)
URAU_GC_2020_CODE_fld = arcpy.GetParameterAsText(8)

#Environment settings
arcpy.env.overwriteOutput = 'true'

try:

    ID_GROUP = "GROUP_" + group_id
    saFC = outPath + "\\" + ID_GROUP + "_SA"
    
    fc_DIS = outPath + "\\SA_DIS_MP"
    ##fc_DIS = "in_memory\SA_DIS_MP"
    if arcpy.Exists(fc_DIS):
        arcpy.Delete_management(fc_DIS)
    print 'Dissolve the service areas by [' + UATL_ID_Fld + '] of the green urban areas (to get a single service area for each GUA)'
    arcpy.Dissolve_management(saFC, fc_DIS, UATL_ID_Fld, "", "MULTI_PART", "DISSOLVE_LINES")

    fc_GUA = outPath + "\\GUA"
    if arcpy.Exists(fc_GUA):
        arcpy.Delete_management(fc_GUA)
                              
    FC_GROUP_UATL_MERGED = inPath + r"\UATL_2018_" + ID_GROUP
##    cnt = arcpy.GetCount_management(FC_GROUP_UATL_MERGED)
##    nbrec = cnt.getOutput(0)
##    print "nb features in " + os.path.basename(FC_GROUP_UATL_MERGED) + " : " + nbrec
                           
    if arcpy.Exists("UATLlayer"):
        arcpy.Delete_management("UATLlayer")
    whereclause = '"' + CODE_Fld + '"' + " = 14100 OR " + '"' + CODE_Fld + '"' + " = 30000 OR " + '"' + CODE_Fld + '"' + " = 31000"
    print "Copy Features from " + os.path.basename(FC_GROUP_UATL_MERGED) + " with " + whereclause + " in " + os.path.basename(fc_GUA)
    uatlLyr = arcpy.MakeFeatureLayer_management(FC_GROUP_UATL_MERGED, "UATLlayer", whereclause)

    arcpy.CopyFeatures_management(uatlLyr, fc_GUA)
                              
##    cnt = arcpy.GetCount_management(fc_GUA)
##    nbrec = cnt.getOutput(0)
##    print "nb features in " + os.path.basename(fc_GUA) + " : " + nbrec

    print "Add and Calculate [GUA_Area] = SHAPE_Area in " + os.path.basename(fc_GUA)
    arcpy.AddField_management(fc_GUA, "GUA_Area", field_type='DOUBLE')

    arcpy.CalculateField_management(fc_GUA, "GUA_Area", "!SHAPE_Area!", "PYTHON")
   
##    ##
##    ## [GUA_Area] added in UATL_14100 based on [Shape_Area]
##    ##
    print "Joining field [GUA_Area] from " + os.path.basename(fc_GUA) + " in " + os.path.basename(fc_DIS)
    fastJoinFields(fc_DIS, UATL_ID_Fld, fc_GUA, UATL_ID_Fld, "GUA_Area")
    arcpy.Delete_management(fc_GUA)

    # Make the geometric union of the service areas
##    fc_UNION = outPath + "\\SA_UNION"
    fc_UNION = "in_memory\SA_UNION"
    if arcpy.Exists(fc_UNION):
        arcpy.Delete_management(fc_UNION)
    printMessage('Make the geometric union of the service areas')
    arcpy.Union_analysis(fc_DIS, fc_UNION, "ALL", "", "GAPS")
    arcpy.Delete_management(fc_DIS)

    # Make a new feature class from SA_union with only singlepart features to simplify complex shapes
    printMessage('Make a new feature class from SA_union with only singlepart features to simplify complex shapes')
    fc_SP = outPath + "\\SA_SP"
    if arcpy.Exists(fc_SP):
        arcpy.Delete_management(fc_SP)
    arcpy.MultipartToSinglepart_management(fc_UNION, fc_SP)
    arcpy.RepairGeometry_management(fc_SP)

    # At intersection (where Union creates identical polygons), SUM of GUA Areas
    # For this purpose, add a text field with the combined XY coordinates of the polygon centroid, from fields INSIDE_X and INSIDE_Y
    # The tool Dissolve is not used because of possible crash with complex topology.

    printMessage('Add and Calculate a field with the combined XY coordinates of the polygon centroid')
    arcpy.AddGeometryAttributes_management(fc_SP, "CENTROID_INSIDE")
    arcpy.AddField_management(fc_SP, "CENTROID_COORD", "TEXT", "", "", "40")
    arcpy.CalculateField_management(fc_SP, "CENTROID_COORD", "str(!INSIDE_X!) + '_' + str(!INSIDE_Y!)", "PYTHON_9.3")
    arcpy.AddIndex_management (fc_SP, "CENTROID_COORD", "CENTROID_COORD")

    # Make a table with the SUM of GUA Areas observed at each location
    table_STAT = outPath + "\\SA_STAT"
    ##table_STAT = "in_memory\SA_STAT"
    if arcpy.Exists(table_STAT):
        arcpy.Delete_management(table_STAT)
    basenameSP = os.path.basename(fc_SP)
    basenameSTAT = os.path.basename(table_STAT)
    statsFields = [["GUA_Area", "SUM"]]
    caseFields = ["CENTROID_COORD"]
    print "Statistics_analysis in " + basenameSP + " with " + basenameSTAT + " statsFields : " + str(statsFields) + " caseFields : " + str(caseFields)
    arcpy.Statistics_analysis(fc_SP, table_STAT, statsFields, caseFields)

    printMessage('Add an attribute index for a faster JOIN')
    arcpy.AddIndex_management(table_STAT, "CENTROID_COORD", "centroid_X_Y_ID", "UNIQUE", "ASCENDING")

    # Using  tool DeleteIdentical to keep one polygon when OVERLAP.
    fields = ["CENTROID_COORD"]
    printMessage('DeleteIdentical in '+ basenameSP)
    arcpy.DeleteIdentical_management(fc_SP, fields)
    
    printMessage('Make a new feature class from ' + basenameSTAT)
    printMessage('for join with ' +  basenameSP + " where Overlaping polygons are deleted")
    printMessage('based on [CENTROID_COORD] to add the [SUM_GUA_Area] value')
    print "Joining field [SUM_GUA_Area] from " + basenameSTAT + " in " + basenameSP + " based on [CENTROID_COORD]"
    fastJoinFields(fc_SP, "CENTROID_COORD", table_STAT, "CENTROID_COORD", "SUM_GUA_Area")

    printMessage("Intersect the combined SA dataset with the dataset containing the population")
    if arcpy.Exists("input_popl_Layer"):
        arcpy.Delete_management("input_popl_Layer")
    whereclause = '"' + UATL_POPL_2018_fld + '" > 0'
    arcpy.MakeFeatureLayer_management(FC_GROUP_UATL_MERGED, "input_popl_Layer", whereclause, "", UATL_POPL_2018_fld + " " + UATL_POPL_2018_fld + " VISIBLE RATIO")
    #Count number of Blocks with population figures
    cnt = arcpy.GetCount_management("input_popl_Layer")
    nbrec = cnt.getOutput(0)
    print "nb blocks(s) with [" + UATL_POPL_2018_fld + "] <> NULL  : " + nbrec
    

##    # Option "RATIO" to distribute population between cut polygons when using the Union command
    fc_SP_Union = outPath + "\\" + ID_GROUP  + "_SA_SP_UNION"
    if arcpy.Exists(fc_SP_Union):
        arcpy.Delete_management(fc_SP_Union)
    printMessage('Make the geometric union of the service areas single parts')
    inFeatures = ["input_popl_Layer", fc_SP]
    arcpy.Union_analysis(inFeatures, fc_SP_Union, "ALL", "", "GAPS")

    # Summary statistis group by HDC_2011_code and sum_GUA_area: calculate sum of population
    table_UNION_STAT =  outPath + "\\" + ID_GROUP  + "_SA_SP_UNION_STAT"
    if arcpy.Exists(table_UNION_STAT):
        arcpy.Delete_management(table_UNION_STAT)
    statsFields = [[UATL_POPL_2018_fld, "SUM"]]
    caseFields = [HDENS_2011_CODE_fld,URAU_CITY_2020_CODE_fld,URAU_GC_2020_CODE_fld,"SUM_GUA_Area"]

    print "Statistics_analysis in " + os.path.basename(table_UNION_STAT) + " with " + os.path.basename(fc_SP_Union) + " statsFields : " + str(statsFields) + " caseFields : " + str(caseFields)
    arcpy.Statistics_analysis(fc_SP_Union, table_UNION_STAT, statsFields, caseFields)

    arcpy.Delete_management("input_popl_Layer")
    arcpy.Delete_management(table_STAT)
    arcpy.Delete_management(fc_SP)
    arcpy.Delete_management(fc_UNION)
                              
    print "end: " + time.strftime("%H:%M:%S", time.localtime())

except CustomError as ce:
    arcpy.AddError(ce.value)
    print ce.value
except arcpy.ExecuteError:
    msgs = arcpy.GetMessages(2)
    arcpy.AddError(msgs)
    print msgs
except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
    arcpy.AddError(pymsg)
    print msgs
    arcpy.AddError(msgs)
    print pymsg
