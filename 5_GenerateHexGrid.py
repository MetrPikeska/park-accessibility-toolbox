# ------------------------------------
# Name: 5_GenerateHexGrid.py
# This script generates a hexagonal tessellation over a polygon feature and clips it to its extent.
# ------------------------------------

import arcpy
import sys

# Always overwrite outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Get input parameters
# ------------------------------------
workspace         = arcpy.GetParameterAsText(0)    # Optional workspace
input_feature     = arcpy.GetParameterAsText(1)    # Input polygon
output_feature    = arcpy.GetParameterAsText(2)    # Output clipped hex grid
hex_size_value    = arcpy.GetParameterAsText(3)    # Size in hectares

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         HEXAGON GRID GENERATION START      ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Input polygon: {input_feature}")
arcpy.AddMessage(f"Output grid:   {output_feature}")
arcpy.AddMessage(f"Hex size:      {hex_size_value} ha")
if workspace:
    arcpy.env.workspace = workspace
    arcpy.AddMessage(f"Workspace set: {workspace}")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate geometry type
# ------------------------------------
desc = arcpy.Describe(input_feature)
if desc.shapeType != "Polygon":
    arcpy.AddError(f"❌ {input_feature} is not a polygon layer. Exiting.")
    sys.exit(1)

# Get extent and spatial reference
extent        = desc.extent
extent_string = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
spatial_ref   = extent.spatialReference

# ------------------------------------
# Validate hex size
# ------------------------------------
try:
    float(hex_size_value)
    hex_size = f"{hex_size_value} Hectares"
except ValueError:
    arcpy.AddError(f"❌ Invalid hex size value: {hex_size_value}. Enter a numeric value.")
    sys.exit(1)

# ------------------------------------
# Generate tessellation
# ------------------------------------
arcpy.AddMessage(f"Generating hexagonal tessellation ({hex_size})...")
temp_hex = "in_memory\\temp_hex"
arcpy.management.GenerateTessellation(temp_hex, extent_string, "HEXAGON", hex_size, spatial_ref)

# Check tessellation result
if not arcpy.Exists(temp_hex):
    arcpy.AddError("❌ Tessellation failed. No output generated.")
    sys.exit(1)

desc_output = arcpy.Describe(temp_hex)
if desc_output.shapeType != "Polygon":
    arcpy.AddError("❌ Output is not a polygon layer. Exiting.")
    sys.exit(1)

arcpy.AddMessage("✔ Hexagonal tessellation generated.")

# ------------------------------------
# Clip hexagons to input boundary
# ------------------------------------
arcpy.AddMessage("Clipping hexagons to polygon boundary...")
arcpy.analysis.Clip(temp_hex, input_feature, output_feature)
arcpy.AddMessage(f"✔ Hexagons clipped. Final output: {output_feature}")

# ------------------------------------
# Cleanup
# ------------------------------------
arcpy.Delete_management(temp_hex)
arcpy.AddMessage("✔ Temporary data deleted.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===          HEXAGON GRID GENERATION DONE       ===")
arcpy.AddMessage("===================================================")

# Clean variables
del workspace, input_feature, output_feature, hex_size_value
del extent, extent_string, spatial_ref, hex_size
del temp_hex, desc, desc_output

# Author: Petr MIKESKA
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
