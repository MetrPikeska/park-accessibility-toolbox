# ------------------------------------
# Name: 5_GenerateHexGrid.py
# This script generates a hexagonal tessellation over a polygon feature 
# and clips it to the input extent.
# ------------------------------------

import arcpy
import sys
import os

# Always overwrite existing outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Get input parameters
# ------------------------------------
workspace         = arcpy.GetParameterAsText(0)    # Output Geodatabase
input_feature     = arcpy.GetParameterAsText(1)    # Analysis extent (Polygon Layer)
output_feature    = arcpy.GetParameterAsText(2)    # Output Feature Name (in GDB)
hex_size_value    = arcpy.GetParameterAsText(3)    # Hexagon size in hectares

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===          STARTING HEXAGON GENERATION        ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Input polygon:        {input_feature}")
arcpy.AddMessage(f"Requested output:     {output_feature}")
arcpy.AddMessage(f"Hexagon size:         {hex_size_value} ha")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate workspace
# ------------------------------------
if not workspace or not workspace.lower().endswith(".gdb"):
    arcpy.AddError(
        "No valid output geodatabase specified. Please select an existing File Geodatabase (.gdb)."
    )
    sys.exit(1)

arcpy.env.workspace = workspace
arcpy.AddMessage(f"Output geodatabase:   {workspace}")

# ------------------------------------
# Validate output feature name
# ------------------------------------
if not output_feature or output_feature.strip() == "":
    arcpy.AddError("Output feature name is missing. Please specify a valid name for the output layer.")
    sys.exit(1)

# Always save into selected geodatabase
final_output_path = os.path.join(workspace, output_feature)
arcpy.AddMessage(f"Final output will be saved as: {final_output_path}")

# ------------------------------------
# Validate input geometry type
# ------------------------------------
if not arcpy.Exists(input_feature):
    arcpy.AddError(
        f"The input feature '{input_feature}' does not exist. Please check the dataset path."
    )
    sys.exit(1)

desc = arcpy.Describe(input_feature)
if desc.shapeType != "Polygon":
    arcpy.AddError(
        f"The input layer '{input_feature}' is not a polygon feature class. Please provide a polygon layer."
    )
    sys.exit(1)

# Get extent and spatial reference
extent        = desc.extent
extent_string = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
spatial_ref   = desc.spatialReference

# ------------------------------------
# Validate hexagon size (> 0)
# ------------------------------------
try:
    hex_size_val = float(hex_size_value)
    if hex_size_val <= 0:
        arcpy.AddError("Hexagon size must be greater than 0 hectares. Please enter a valid positive value.")
        sys.exit(1)
    hex_size = f"{hex_size_val} Hectares"
except ValueError:
    arcpy.AddError(f"Invalid hexagon size value: '{hex_size_value}'. Please enter a numeric value greater than 0.")
    sys.exit(1)

# ------------------------------------
# Generate tessellation
# ------------------------------------
arcpy.AddMessage(f"Generating hexagonal tessellation ({hex_size}) for the input extent...")
temp_hex = "in_memory\\temp_hex"
arcpy.management.GenerateTessellation(temp_hex, extent_string, "HEXAGON", hex_size, spatial_ref)

# Check tessellation result
if not arcpy.Exists(temp_hex):
    arcpy.AddError("Hexagon tessellation failed. No output was created. Please check the input parameters.")
    sys.exit(1)

desc_output = arcpy.Describe(temp_hex)
if desc_output.shapeType != "Polygon":
    arcpy.AddError("The tessellation output is not a polygon feature class. Script will terminate.")
    sys.exit(1)

arcpy.AddMessage("Hexagonal tessellation successfully generated.")

# ------------------------------------
# Clip hexagons to input boundary
# ------------------------------------
arcpy.AddMessage("Clipping hexagons to the exact boundary of the input polygon...")
arcpy.analysis.Clip(temp_hex, input_feature, final_output_path)
arcpy.AddMessage(f"Hexagons clipped successfully. Final output layer: {final_output_path}")

# ------------------------------------
# Try to add final layer to current map (ArcGIS Pro)
# ------------------------------------
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    m.addDataFromPath(final_output_path)
    arcpy.AddMessage("Final output layer has been automatically added to the map.")
except Exception:
    arcpy.AddMessage("The final output layer could not be automatically added to the map. This step is optional.")

# ------------------------------------
# Clean up temporary data
# ------------------------------------
arcpy.Delete_management(temp_hex)
arcpy.AddMessage("Temporary data deleted.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         HEXAGON GENERATION COMPLETED        ===")
arcpy.AddMessage("===================================================")

# Clean variables
del workspace, input_feature, output_feature, final_output_path, hex_size_value
del extent, extent_string, spatial_ref, hex_size
del temp_hex, desc, desc_output

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
