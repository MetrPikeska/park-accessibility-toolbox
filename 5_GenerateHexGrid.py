#------------------------------------
# Name: 5_GenerateHexGrid.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script generates a hexagonal tessellation over a polygon feature and clips it to its extent.
#------------------------------------

import arcpy
import sys

#------------------------------------
# General settings
#------------------------------------
arcpy.env.overwriteOutput = True

arcpy.AddMessage("===================================================")
arcpy.AddMessage("===       HEXAGON GRID GENERATION START         ===")
arcpy.AddMessage("===================================================")

#------------------------------------
# Get input parameters
#------------------------------------
workspace         = arcpy.GetParameterAsText(0)    # Optional workspace (can be empty)
input_feature     = arcpy.GetParameterAsText(1)    # Input polygon feature class
output_feature    = arcpy.GetParameterAsText(2)    # Output clipped hex grid
hex_size_value    = arcpy.GetParameterAsText(3)    # Size in hectares (numeric as string)

arcpy.AddMessage(f"→ Input polygon layer: {input_feature}")
arcpy.AddMessage(f"→ Output hex grid:     {output_feature}")
arcpy.AddMessage(f"→ Hexagon size:        {hex_size_value} ha")

# Set workspace if provided
if workspace:
    arcpy.env.workspace = workspace
    arcpy.AddMessage(f"→ Workspace set to:    {workspace}")

#------------------------------------
# Validate geometry type
#------------------------------------
desc = arcpy.Describe(input_feature)
if desc.shapeType != "Polygon":
    arcpy.AddError(f"Error: `{input_feature}` is not a polygon layer. Script will terminate.")
    sys.exit(1)

# Extract extent and spatial reference
extent         = desc.extent
extent_string  = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
spatial_ref    = extent.spatialReference

#------------------------------------
# Validate and format hex size input
#------------------------------------
try:
    float(hex_size_value)  # ensure it's a number
    hex_size = f"{hex_size_value} Hectares"
except ValueError:
    arcpy.AddError(f"Invalid hexagon size value: {hex_size_value}. Please enter a numeric value.")
    sys.exit(1)

#------------------------------------
# Generate tessellation
#------------------------------------
arcpy.AddMessage(f"→ Generating hexagonal tessellation with size {hex_size}...")
temp_hex = "in_memory\\temp_hex"
arcpy.management.GenerateTessellation(temp_hex, extent_string, "HEXAGON", hex_size, spatial_ref)

# Check if tessellation was successful
if not arcpy.Exists(temp_hex):
    arcpy.AddError("Error: Tessellation failed. No output generated.")
    sys.exit(1)

# Validate output geometry
desc_output = arcpy.Describe(temp_hex)
if desc_output.shapeType != "Polygon":
    arcpy.AddError("Error: Output is not a polygon layer.")
    sys.exit(1)

arcpy.AddMessage("✔ Hexagonal tessellation generated.")

#------------------------------------
# Clip hexagons to input polygon boundary
#------------------------------------
arcpy.AddMessage("→ Clipping hexagons to input polygon boundary...")
arcpy.analysis.Clip(temp_hex, input_feature, output_feature)
arcpy.AddMessage("✔ Hexagons successfully clipped.")

#------------------------------------
# Final cleanup and logging
#------------------------------------
arcpy.Delete_management(temp_hex)  # Remove in-memory layer
arcpy.AddMessage(f"✔ Hexagonal grid generation complete.")
arcpy.AddMessage(f"→ Final output: {output_feature}")

arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         HEXAGON GRID COMPLETED             ===")
arcpy.AddMessage("===================================================")

#------------------------------------
# Clean up variables
#------------------------------------
del workspace, input_feature, output_feature, hex_size_value
del extent, extent_string, spatial_ref, hex_size
del temp_hex, desc, desc_output
