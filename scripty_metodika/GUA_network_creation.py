#Title: Green Urban Areas accessibility - creation of a city pedestrian network
#Author: Veerle Martens
#Modified by ER on 21/08/2015
#
#Purpose: Create a pedestrian network dataset for a city
#-------------------------------------------------------------------------------

#create error handler
class CustomError(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def displaytime(text, seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    print text + "%d:%02d:%02d" % (h, m, s)

import sys, arcpy, time,traceback,os
 
print "start: " + time.strftime("%H:%M:%S", time.localtime())

# Script arguments
# ---------------------------------------------------------------------------
Group_Id = arcpy.GetParameterAsText(0)
Pedestrian_Clip_Mode = arcpy.GetParameterAsText(1)
inputPolyFcl = arcpy.GetParameterAsText(2)
inputRoadLineFcl = arcpy.GetParameterAsText(3)
templateNetwork = arcpy.GetParameterAsText(4)
outputFolder = arcpy.GetParameterAsText(5)

# Variables and environment parameters
# ---------------------------------------------------------------------------

sep = os.path.sep
projR = arcpy.SpatialReference('ETRS 1989 LAEA')

try:

    startTime = time.clock()
    
    arcpy.env.overwriteOutput = True
    if arcpy.CheckExtension("Network"):
        arcpy.CheckOutExtension("Network")
    else:
        raise CustomError("The Network Analyst extension is not available.")
    
    # Process
    # ---------------------------------------------------------------------------
    # Make the output FGDB

    print "Make the output FGDB for GROUP_ID " + Group_Id

##    inputPolyFclQuery = "GROUP_ID = " + Group_Id
##    print "inputPolyFclQuery = <" + inputPolyFclQuery + ">"

    ID_GROUP = str(int(Group_Id))
    inputPolyFclQuery = """{0} = {1}""".format(arcpy.AddFieldDelimiters(inputPolyFcl, "GROUP_ID"), ID_GROUP)
    print "inputPolyFclQuery = <" + inputPolyFclQuery + ">"
    
    gdbName = "NW_UATL_GROUP_" + Group_Id + ".gdb"
    areaCodePL = "GROUP_" + Group_Id + "_Buff_PL"
    if not arcpy.Exists(outputFolder + sep + gdbName):
        arcpy.CreateFileGDB_management(outputFolder, gdbName, "CURRENT")
    if not arcpy.Exists(outputFolder + sep + "NW_UATL_GROUP_" + Group_Id + ".gdb" + sep + "GROUP_" + Group_Id):
        arcpy.CreateFeatureDataset_management(outputFolder + sep + gdbName, "GROUP_" + Group_Id, projR)
    workspace = outputFolder + sep + gdbName + sep + "GROUP_" + Group_Id
    print "Input Road Line fc       : " + inputRoadLineFcl
    print "Process Mode             : " + Pedestrian_Clip_Mode
    print "Output Network workspace : " + workspace
    arcpy.env.workspace = workspace

    # Import the road lines
    print "Import the road lines"
    arcpy.MakeFeatureLayer_management(inputPolyFcl, "inputPolyFcl_layer", inputPolyFclQuery)
    print "Buffer 5km with " + os.path.basename(inputPolyFcl) + " in " + areaCodePL
    arcpy.Buffer_analysis("inputPolyFcl_layer", r"J:\usersworkspace\er\2021_GUA\Data.gdb" + sep + areaCodePL, "5000 Meters", "FULL", "FLAT", "ALL", "")
    print "Clip " + os.path.basename(inputRoadLineFcl) + " with " + areaCodePL
    clip_fc = r"J:\usersworkspace\er\2021_GUA\Data.gdb" + sep + areaCodePL
    if arcpy.Exists(clip_fc):
        arcpy.Delete_management(clip_fc)
    arcpy.Clip_analysis(inputRoadLineFcl, clip_fc, "nw")
    arcpy.Delete_management("inputPolyFcl_layer")
    arcpy.Delete_management(clip_fc)

    t1 = time.clock()
    displaytime("intermediate elapsed time in seconds : ",t1 - startTime)
    
    if Pedestrian_Clip_Mode == "SELECT_PEDESTRIAN_AND_CLIP":

        # Delete the road lines not accessible for pedestrians
        print "Delete the road lines not accessible for pedestrians"
        arcpy.MakeFeatureLayer_management("nw", "nw_layer")
        expr1 = '("FOW" <> 1 AND "FRC" not in (0, 1, 2) AND "FEATTYP" <> 4165 ) AND ("F_ELEV" <>-1 AND "T_ELEV" <>-1)'
        expr2 = '"FOW" = 3'
        expr3 = '"SPEEDCAT" >= 6'
        arcpy.SelectLayerByAttribute_management("nw_layer", "NEW_SELECTION", expr1)
        arcpy.SelectLayerByAttribute_management("nw_layer", "ADD_TO_SELECTION", expr2)
        arcpy.SelectLayerByAttribute_management("nw_layer", "ADD_TO_SELECTION", expr3)
        arcpy.SelectLayerByAttribute_management("nw_layer", "SWITCH_SELECTION", "")
        arcpy.DeleteFeatures_management("nw_layer")
        arcpy.Delete_management("nw_layer")

        # Add a field ped_minutes
        print "Add a field ped_minutes"
        arcpy.AddField_management("nw", "ped_minutes", "DOUBLE")
        arcpy.CalculateField_management("nw", "ped_minutes", "!Shape_Length!*60/5000", "PYTHON_9.3")

        t2 = time.clock()
        displaytime("intermediate elapsed time in seconds : ", t2 -t1)
    else:
        t2 = t1
        
    arcpy.CheckOutExtension("network")
    xml_template = outputFolder + "NDTemplate.xml"
    print "CreateTemplateFromNetworkDataset"
    arcpy.na.CreateTemplateFromNetworkDataset(templateNetwork, xml_template)
    print "CreateNetworkDatasetFromTemplate"
    arcpy.na.CreateNetworkDatasetFromTemplate(xml_template, outputFolder + sep + gdbName + sep + "GROUP_" + Group_Id)
    t3 = time.clock()
    displaytime("intermediate elapsed time in seconds : ",t3 - t2)
    print "Build the network"
    arcpy.na.BuildNetwork(outputFolder + sep + gdbName + sep + "GROUP_" + Group_Id + sep + "Network_ND")
    t4 = time.clock()
    displaytime("intermediate elapsed time in seconds : ",t4 - t3)

    #add final message
    print "end: " + time.strftime("%H:%M:%S", time.localtime())
    displaytime("total elapsed time in seconds : ",t3 - startTime)

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
    print pymsg
    arcpy.AddError(msgs)
    print msgs
    
finally:
    arcpy.CheckInExtension("Network")
