# Test skript pro přímé spuštění mimo toolbox
import arcpy
import sys

# Nastavení parametrů přímo v kódu
input_roads = r"StreetNet_Olomouc"  # Změňte na plnou cestu pokud potřeba
output_folder = r"c:\Users\Metr\Documents\GitHub\park-accessibility-toolbox\toolbox"
network_name = "test1"

try:
    arcpy.AddMessage("=== TEST START ===")
    arcpy.AddMessage(f"Python: {sys.version}")
    arcpy.AddMessage(f"ArcPy: {arcpy.GetInstallInfo()['Version']}")
    
    # Test Network Analyst extension
    status = arcpy.CheckExtension("Network")
    arcpy.AddMessage(f"Network Analyst status: {status}")
    
    if status == "Available":
        arcpy.CheckOutExtension("Network")
        arcpy.AddMessage("Extension checked out!")
        
        # Test import arcpy.na
        import arcpy.na
        arcpy.AddMessage("arcpy.na imported successfully!")
        
        arcpy.AddMessage("=== TEST PASSED ===")
    else:
        arcpy.AddError(f"Extension not available: {status}")
        
except Exception as e:
    arcpy.AddError(f"ERROR: {str(e)}")
    import traceback
    arcpy.AddError(traceback.format_exc())
