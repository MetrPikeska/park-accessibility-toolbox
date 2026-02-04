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

MERGED_UATL_TABLE = r"J:\usersworkspace\er\2021_GUA\Data.gdb\MERGED_UATL_TABLE"

sde_connection = r"Database Connections\prd-gisregio.sde"
input_UATL_2018_FDS = sde_connection + "\\GISREGIO.UATL_2018"
POP_Field = "POPL_2018"

HDENS_CLST_FC   = sde_connection + "\\GISREGIO.HDENS_CLST_2011_RG"
UATL_FC = input_UATL_2018_FDS + "\\GISREGIO.UATL_RG_2018"

PedestrianPath = r'L:\Pedestrian\ByCountry\TomTom-2019'
Pedestrian_UATL_GROUP_Path = r"J:\usersworkspace\er\2021_GUA\Pedestrians"

outPath = r'J:\usersworkspace\er\2021_GUA\GUA_SA_10m_POP_2018.gdb'

UATL_ID_fld = "UATL_ID"
UATL_POP_2018_fld = "POPL_2018"
nbMinutes = "10"
CODE_Fld = "CODE_2018"

SR = 3035 #WKID ETRS_1989_LAEA

#Environment settings
arcpy.env.overwriteOutput = 'true'

if not arcpy.Exists(outPath):
    print "creating " + os.path.basename(outPath)
    arcpy.CreateFileGDB_management(os.path.dirname(outPath), os.path.basename(outPath), "CURRENT")

#Process: Finds python.exe  
pythonExePath = ""  
for path in sys.path:  
    if os.path.exists(os.path.join(path, "python.exe")) == True:  
        pythonExePath = os.path.join(path, "python.exe")
print "pythonExePath = " + pythonExePath
if pythonExePath == "":  
    print "ERROR: Python executable not found! Exiting script...."; sys.exit()  

try:

        
    env=os.environ.copy()
    env['PATH']='%s;%s;%s' %(pythonExePath,env['WINDIR'],env['WINDIR']+'\\system32')

    
    listfields = ["UATL_MERGED_GROUP","CROSS_CNTR","LIST_CNTR","TOUCH_NGHBR_CNTR","HDC_2011_AVALAIBLE"]
    with arcpy.da.SearchCursor(MERGED_UATL_TABLE, listfields,sql_clause=(None,"ORDER BY UATL_MERGED_GROUP")) as cursor:
        for row in cursor:

            Multi_Countries_Pedestrian = False
            cntr = ""
            
            if row[4] == 1:                             ## HDC(s) 2011 covered by UATL GROUP

                ID_UATL_GROUP = row[0]
                group_id_str = str(ID_UATL_GROUP).zfill(3)
                
                if row[1] == 1 or row[3] == 1:          ## UATL GROUP crossing or touching country boundaries
                    Multi_Countries_Pedestrian = True
                else:
                    cntr = row[2]

                if Multi_Countries_Pedestrian:
                    inputRoadLineFcl = r"L:\TomTom-2019\NW_europe_2019_SP.gdb\Routing\Streets"
                    Pedestrian_Clip_Mode = "SELECT_PEDESTRIAN_AND_CLIP"
                else:
                    inputRoadLineFcl = PedestrianPath + "\\NW_" + cntr + ".gdb\\" + cntr  + "\\nw"
                    if not arcpy.Exists(inputRoadLineFcl):
                        inputRoadLineFcl = r"L:\TomTom-2019\NW_europe_2019_SP.gdb\Routing\Streets"
                        Pedestrian_Clip_Mode = "SELECT_PEDESTRIAN_AND_CLIP"
                    else:
                        Pedestrian_Clip_Mode = "ONLY_CLIP"

                inputPolyFcl = r"J:\usersworkspace\er\2021_GUA\Data.gdb\UATL_2018_GROUP_RG_DIS"
                template_network_path = r"L:\Pedestrian\NW_LU001L.gdb\LU001L\Network_ND"

                pedestrianNWpath = Pedestrian_UATL_GROUP_Path + "\\NW_UATL_GROUP_" + group_id_str + ".gdb\\GROUP_" + group_id_str  + "\\Network_ND"            
                     
                if not arcpy.Exists(pedestrianNWpath):
                    slaveScript = r"J:\usersworkspace\er\2021_GUA\GUA_network_creation.py"
                    LOG_FILENAME = r"J:\usersworkspace\er\2021_GUA\GUA_network_creation_" + group_id_str + ".log"
                    cmd = pythonExePath + " " + slaveScript + " " + group_id_str  + " " + Pedestrian_Clip_Mode + " " + inputPolyFcl + " " + inputRoadLineFcl + " " + template_network_path + " " + Pedestrian_UATL_GROUP_Path  + r" > " + "\"" + LOG_FILENAME + "\""
                    print "    - subprocess : " + os.path.basename(slaveScript) + " for UATL_GROUP_" + group_id_str
                    proc = subprocess.Popen(cmd,shell=True,env=env)
                    proc.wait()

                    # Print entire console log file so we know what happene):
                    logFile = open(LOG_FILENAME, "r")
                    for line in logFile:
                        line = line.strip('\n')
                        print line
                ##else:
                ##    print "pedestrian Network " + pedestrianNWpath + " already exist"
                                                 
    del row,cursor

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

