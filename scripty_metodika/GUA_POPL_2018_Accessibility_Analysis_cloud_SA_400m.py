import sys, arcpy, time, traceback, os.path, subprocess

#create error handler
class CustomError(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def fieldExists(inFeatureClass, inFieldName):
    for fld in arcpy.Describe(inFeatureClass).fields:
        if fld.name.lower() == inFieldName.lower():
            return True
    return False


print "start: " + time.strftime("%H:%M:%S", time.localtime())
arcpy.AddMessage("start: " + time.strftime("%H:%M:%S", time.localtime()))

#Define parameters

MERGED_UATL_TABLE = r"Data.gdb\MERGED_UATLS_2018_TABLE"

POP_Field = "POPL_2018"

PedestrianPath = r'Pedestrians'

UATL_ID_fld = "UATL_ID"
UATL_POP_2018_fld = "POPL_2018"
nbMeters = "400"
CODE_Fld = "CODE_2018"
FUA_2018_CODE_fld = "FUA_ID"
HDENS_2011_CODE_fld = "HDENS_2011_CODE"
URAU_CITY_2020_CODE_fld = "URAU_CITY_2020_CODE"
URAU_GC_2020_CODE_fld = "URAU_GC_2020_CODE"

SR = 3035 #WKID ETRS_1989_LAEA

#Environment settings
arcpy.env.overwriteOutput = 'true'  

pythonExePath ="C:\Python27\ArcGISx6410.8\python.exe"

inPath = "Data.gdb"
outPath = "GUA_POP_2018_SA_400m.gdb"

try:

    listfields = ["UATL_MERGED_GROUP","CROSS_CNTR","LIST_CNTR","TOUCH_NGHBR_CNTR","HDC_2011_AVALAIBLE","UATL_TO_PROCESS","NB_UATL"]
    with arcpy.da.SearchCursor(MERGED_UATL_TABLE, listfields,sql_clause=(None,"ORDER BY UATL_MERGED_GROUP")) as cursor:
        for row in cursor:

            group_uatl_to_process = row[5]
            hdc_2011_available = row[4]
            
            if hdc_2011_available == 1 and group_uatl_to_process == 1:
 
                ID_UATL_GROUP = row[0]
                group_id_str = str(ID_UATL_GROUP).zfill(3)
                GROUP_ID = "GROUP_" + group_id_str
                fc_SA = outPath + "\\" + GROUP_ID + "_sa"
                if not arcpy.Exists(fc_SA):
                    
                    slaveScript = r"GUA_POPL_2018_Calculate_SA_400m_cloud.py"                    
                    LOG_FILENAME = r"GUA_POPL_2018_Calculate_SA_400m_cloud_UATL_" + group_id_str + ".log"
                    cmd = [pythonExePath, slaveScript, group_id_str, PedestrianPath, inPath, outPath, CODE_Fld, UATL_ID_fld, nbMeters]
                    print "    - subprocess : " + os.path.basename(slaveScript) + " for UATL_GROUP_" + group_id_str
                    with open(LOG_FILENAME, 'w') as f:
                        myPopen = subprocess.Popen(cmd, shell=True, stdout=f, stderr=f)
                        myPopen.wait()
                    f.close()
                    status = myPopen.returncode
                    print('status: ' + str(status))
                    ## Print entire console log file so we know what happene):
                    logFile = open(LOG_FILENAME, "r")
                    for line in logFile:
                        line = line.strip('\n')
                        print line
                else:
                    print "SA " + fc_SA + " already exists"  

                table_UNION_STAT =  outPath + "\\" + GROUP_ID  + "_SA_SP_UNION_STAT"
                if not arcpy.Exists(table_UNION_STAT):
                    slaveScript = r"GUA_POPL_2018_Overlay_SA_400m_cloud.py"
                    LOG_FILENAME = r"GUA_POPL_2018_Overlay_SA_400m_UATL_" + group_id_str + ".log"
                    cmd = [pythonExePath, slaveScript, inPath, outPath, UATL_POP_2018_fld, UATL_ID_fld, CODE_Fld, group_id_str, HDENS_2011_CODE_fld, URAU_CITY_2020_CODE_fld, URAU_GC_2020_CODE_fld]
                    print "    - subprocess : " + os.path.basename(slaveScript) + " for UATL_GROUP_" + group_id_str
                    with open(LOG_FILENAME, 'w') as f:
                        myPopen = subprocess.Popen(cmd, shell=True, stdout=f, stderr=f)
                        myPopen.wait()
                    f.close()
                    status = myPopen.returncode
                    print('status: ' + str(status))
                    ## Print entire console log file so we know what happene):
                    logFile = open(LOG_FILENAME, "r")
                    for line in logFile:
                        line = line.strip('\n')
                        print line
                else:
                    print "Table " + table_UNION_STAT + " already exists"  

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

