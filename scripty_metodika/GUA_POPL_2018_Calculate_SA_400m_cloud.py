#----------------------------------------------------------------------------------
#Author: Veerle Martens
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

def unique_values(table , field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})

def convert(list):
    return tuple(list)

print "start: " + time.strftime("%H:%M:%S", time.localtime())

group_id = arcpy.GetParameterAsText(0)
pedestrian_path = arcpy.GetParameterAsText(1)
inPath = arcpy.GetParameterAsText(2)
outPath = arcpy.GetParameterAsText(3)
CODE_Fld = arcpy.GetParameterAsText(4)
UATL_ID_Fld = arcpy.GetParameterAsText(5)
nbMeters = arcpy.GetParameterAsText(6)

#Environment settings
arcpy.env.overwriteOutput = 'true'

try:

    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
    else:
        raise CustomError("The Network Analyst extension is not available.")

    ID_GROUP = "GROUP_" + group_id
    
    pedestrianNWpath = pedestrian_path + r"\NW_UATL_" + ID_GROUP + ".gdb\\" + ID_GROUP + r"\Network_ND"
    if not arcpy.Exists(pedestrianNWpath):
        raise CustomError("Featureclass " + pedestrianNWpath + " NOT FOUND")

    print "Processing GUA blocks within merged UATLs " + ID_GROUP

    FC_GROUP_UATL_MERGED = inPath + r"\UATL_2018_" + ID_GROUP

    if arcpy.Exists("UATLlayer"):
        arcpy.Delete_management("UATLlayer")
    whereclause = '"' + CODE_Fld + '"' + " = 14100 OR " + '"' + CODE_Fld + '"' + " = 30000 OR " + '"' + CODE_Fld + '"' + " = 31000"
    uatlLyr = arcpy.MakeFeatureLayer_management(FC_GROUP_UATL_MERGED, "UATLlayer", whereclause)
    ## Count number of GUA Blocks
    cnt = arcpy.GetCount_management(uatlLyr)
    print "nb record(s) in " + os.path.basename(FC_GROUP_UATL_MERGED) + " subset selection [" + CODE_Fld + "] IN (14100,30000,31000) : " +  cnt.getOutput(0)

    ## Create and Select points from GUA borders used to create SA
    print "Create points from GUA borders used to create SA"

##    fc_GUA_pt_50m = outPath + "\\GUA_pt_50m"
    fc_GUA_pt_50m = "in_memory\GUA_pt_50m"

    if arcpy.Exists(fc_GUA_pt_50m):
        arcpy.Delete_management(fc_GUA_pt_50m)
    print "GeneratePointsAlongLines Distance 50m from selected GUA in " + os.path.basename(FC_GROUP_UATL_MERGED) + " to " + os.path.basename(fc_GUA_pt_50m)
    arcpy.GeneratePointsAlongLines_management(uatlLyr, fc_GUA_pt_50m, 'DISTANCE', Distance='50 meters', Include_End_Points='END_POINTS')

    cnt = arcpy.GetCount_management(fc_GUA_pt_50m)
    nbrec = cnt.getOutput(0)
    print "nb generated points : " + nbrec

    if arcpy.Exists('GUA_PT_50m_lyr'):
        arcpy.Delete_management('GUA_PT_50m_lyr')
    arcpy.MakeFeatureLayer_management(fc_GUA_pt_50m, 'GUA_PT_50m_lyr') 

##    fc_GUA_pt_50m_nw_25m = outPath + "\\GUA_pt_50m_nw_25m"
    fc_GUA_pt_50m_nw_25m = "in_memory\GUA_pt_50m_nw_25m"

    if arcpy.Exists(fc_GUA_pt_50m_nw_25m):
        arcpy.Delete_management(fc_GUA_pt_50m_nw_25m)
    nw_Path = pedestrian_path + r"\NW_UATL_" + ID_GROUP + ".gdb" + "\\" + ID_GROUP + "\\nw"
    print "SelectLayerByLocation points in " + os.path.basename(fc_GUA_pt_50m) + " WITHIN_A_DISTANCE of 25 meters from " + os.path.basename(nw_Path)+ " to " + os.path.basename(fc_GUA_pt_50m_nw_25m)
    Selection = arcpy.SelectLayerByLocation_management('GUA_PT_50m_lyr', 'WITHIN_A_DISTANCE', nw_Path, "25 meters", "NEW_SELECTION")
    arcpy.CopyFeatures_management(Selection, fc_GUA_pt_50m_nw_25m) 
    
    UATL_Ids_GUAs_nw_25m = unique_values(fc_GUA_pt_50m_nw_25m, UATL_ID_Fld)

    desc = arcpy.Describe(uatlLyr)
    SR = desc.spatialReference
    flds = arcpy.ListFields(uatlLyr)
    UATL_FieldName_List = [fld.name for fld in flds if fld.name != desc.OIDFieldName and fld.type != 'Geometry' and fld.name != desc.areaFieldName and fld.name != desc.lengthFieldName]

##    fc_GUA_centroids_no_pt = outPath + "\\GUA_centroids_no_pt"
    fc_GUA_centroids_no_pt = r"in_memory\GUA_centroids_no_pt"

    if arcpy.Exists(fc_GUA_centroids_no_pt):
        arcpy.Delete_management(fc_GUA_centroids_no_pt)
    print "CreateFeatureclass " + os.path.basename(fc_GUA_centroids_no_pt)
    arcpy.CreateFeatureclass_management("in_memory", "GUA_centroids_no_pt", "POINT", "", "DISABLED", "DISABLED", SR, "", "0", "0", "0")

    idxfld = 0
    for fldnam in UATL_FieldName_List:
        for fldidx in range(0,len(flds)):
            if fldnam == flds[fldidx].name:
                typeF = flds[fldidx].type
                if typeF == 'String':
                    length_fld = flds[fldidx].length
                break
        if typeF in ['Integer']:
            arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='LONG')
        elif typeF == 'SmallInteger':
            arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='SHORT')
        elif typeF == 'String':
            arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='TEXT',field_length=length_fld)
        elif typeF == 'Double':
           arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='DOUBLE')
        elif typeF == 'Single':
            arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='FLOAT')
        elif typeF == 'Date':
           arcpy.AddField_management(fc_GUA_centroids_no_pt,fldnam,field_type='DATE')
        idxfld += 1
    
    fields = []
    fields.append("SHAPE@")
    for fldnam in UATL_FieldName_List:
        fields.append(fldnam)
    print "Insert centroids where no point in " + os.path.basename(fc_GUA_pt_50m_nw_25m)
    cursor = arcpy.da.InsertCursor(fc_GUA_centroids_no_pt, fields)  
    for row in arcpy.da.SearchCursor(uatlLyr, fields):
        if row[1] not in UATL_Ids_GUAs_nw_25m:
            list_row = list(row)
            list_row[0] = row[0].centroid
            cursor.insertRow(convert(list_row))  
    del row,cursor

    fc_GUA_mem_pt_all = "in_memory\GUA_pt_ALL"

    if arcpy.Exists(fc_GUA_mem_pt_all):
        arcpy.Delete_management(fc_GUA_mem_pt_all)
    print "CopyFeatures from " + os.path.basename(fc_GUA_pt_50m_nw_25m) + " in "  + fc_GUA_mem_pt_all
    arcpy.CopyFeatures_management(fc_GUA_pt_50m_nw_25m, fc_GUA_mem_pt_all) 
    print "append " + os.path.basename(fc_GUA_centroids_no_pt) + " in " + os.path.basename(fc_GUA_mem_pt_all)
    arcpy.Append_management(fc_GUA_centroids_no_pt, fc_GUA_mem_pt_all, "NO_TEST")

    cnt = arcpy.GetCount_management(fc_GUA_mem_pt_all)
    nbrec = cnt.getOutput(0)
    print "nb points in " + os.path.basename(fc_GUA_mem_pt_all) + " : " + nbrec
    
    #Loop through to prevent memory errors
    if int(nbrec) > 1000:
        i = 0
        while i <= int(nbrec):
            j = i + 1000
            print "processing [OID] in (" + str(i) + " , " + str(j) + ")"

            expr = "\"OID\" >= " + str(i) + " AND \"OID\" < " + str(j)
            if arcpy.Exists("GUA_points_layer"):
                arcpy.Delete_management("GUA_points_layer")
            GUA_pt_lyr = arcpy.MakeFeatureLayer_management(fc_GUA_mem_pt_all, "GUA_points_layer", expr)
            #Calculate service areas
            print "creating network layer"
            salyr = arcpy.MakeServiceAreaLayer_na(pedestrianNWpath, ID_GROUP + '_SA_400m', "Meters", "TRAVEL_FROM", nbMeters, "DETAILED_POLYS", "NO_MERGE", "DISKS", "NO_LINES", "", "", "", "", "ALLOW_UTURNS", "", "NO_TRIM_POLYS", "", "")
            arcpy.AddLocations_na(salyr, "Facilities", GUA_pt_lyr, "Name " + UATL_ID_Fld + " #", "500 Meters", "", "", "MATCH_TO_CLOSEST", "APPEND", "NO_SNAP", "", "EXCLUDE", "")
            print "solving network analysis"
            arcpy.Solve_na(salyr, "SKIP")
            if i == 0:
                fc_SA = outPath + "\\" + ID_GROUP + "_sa"
                if arcpy.Exists(fc_SA):
                    arcpy.Delete_management(fc_SA)
                saFC = arcpy.CopyFeatures_management(ID_GROUP + "_SA_400m\\Polygons", fc_SA)
            else:
                tmpFC = arcpy.CopyFeatures_management(ID_GROUP + "_SA_400m\\Polygons", "in_memory\\" + ID_GROUP + "_sa")
                arcpy.Append_management(tmpFC, saFC, "NO_TEST")
                arcpy.Delete_management(tmpFC)
            arcpy.Delete_management(salyr)
            i = i + 1000
    else:
        #Calculate service areas
        print "creating network layer"
        if arcpy.Exists("GUA_points_layer"):
            arcpy.Delete_management("GUA_points_layer")
        GUA_pt_lyr = arcpy.MakeFeatureLayer_management(fc_GUA_mem_pt_all, "GUA_points_layer")
        if arcpy.Exists(ID_GROUP + "_SA_400m"):
            arcpy.Delete_management(ID_GROUP + "_SA_400m")
        salyr = arcpy.MakeServiceAreaLayer_na(pedestrianNWpath, ID_GROUP + '_SA_400m', "Meters", "TRAVEL_FROM", nbMeters, "DETAILED_POLYS", "NO_MERGE", "DISKS", "NO_LINES", "", "", "", "", "ALLOW_UTURNS", "", "NO_TRIM_POLYS", "", "")
        arcpy.AddLocations_na(salyr, "Facilities", GUA_pt_lyr, "Name " + UATL_ID_Fld + " #", "500 Meters", "", "", "MATCH_TO_CLOSEST", "APPEND", "NO_SNAP", "", "EXCLUDE", "")
        print "solving network analysis"
        arcpy.Solve_na(salyr, "SKIP")
        if arcpy.Exists(outPath + "\\" + ID_GROUP + "_sa"):
            arcpy.Delete_management(outPath + "\\" + ID_GROUP + "_sa")
        saFC = arcpy.CopyFeatures_management(ID_GROUP + "_SA_400m\\Polygons", outPath + "\\" + ID_GROUP + "_sa")
        arcpy.Delete_management(salyr)

    fc_GUA_pt_all = outPath + "\\GUA_" + ID_GROUP + "_pt_ALL"
    if arcpy.Exists(fc_GUA_pt_all):
        arcpy.Delete_management(fc_GUA_pt_all)
    print "CopyFeatures from " + os.path.basename(fc_GUA_mem_pt_all) + " in "  + fc_GUA_pt_all
    arcpy.CopyFeatures_management(fc_GUA_mem_pt_all, fc_GUA_pt_all)
    
    saFC = outPath + "\\" + ID_GROUP + "_sa"
    print "adding and calculating field [" + UATL_ID_Fld + "] to " + os.path.basename(saFC)
    arcpy.AddField_management(saFC, UATL_ID_Fld, "TEXT", "", "", 18)
    arcpy.CalculateField_management(saFC, UATL_ID_Fld, "!Name!.split(':')[0].rstrip()", "PYTHON")

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
finally:
    arcpy.CheckInExtension("Network")
