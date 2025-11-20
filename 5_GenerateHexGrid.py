# ------------------------------------
# Name: 5_GenerateHexGrid.py
# Purpose: Generates a hexagonal grid over a specified area and clips it to the input boundary.
# ------------------------------------

import arcpy
import sys
import os

# Allow overwriting outputs.
arcpy.env.overwriteOutput = True

# ------------------------------------
# Get input parameters from the ArcGIS tool dialog
# ------------------------------------
workspace         = arcpy.GetParameterAsText(0)    # Output Geodatabase
input_feature     = arcpy.GetParameterAsText(1)    # Polygon layer defining the analysis extent
output_feature    = arcpy.GetParameterAsText(2)    # Name for the output hexagon layer
hex_size_value    = arcpy.GetParameterAsText(3)    # Desired hexagon size in hectares

# ------------------------------------
# Header log for user feedback
# ------------------------------------
arcpy.AddMessage("\n===================================================")
arcpy.AddMessage("===          STARTING HEXAGON GENERATION        ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Input polygon:        {input_feature}")
arcpy.AddMessage(f"Output name:          {output_feature}")
arcpy.AddMessage(f"Hexagon size:         {hex_size_value} ha")
arcpy.AddMessage("---------------------------------------------------")

# --- Validate workspace ---
if not workspace or not workspace.lower().endswith(".gdb"):
    raise arcpy.ExecuteError("An existing File Geodatabase (.gdb) must be specified as the output workspace.")
arcpy.env.workspace = workspace
arcpy.AddMessage(f"Output geodatabase:   {workspace}")

# --- Validate output feature name ---
if not output_feature or not output_feature.strip():
    raise arcpy.ExecuteError("An output feature name must be provided.")
final_output_path = os.path.join(workspace, output_feature)
arcpy.AddMessage(f"Final output path:    {final_output_path}")

# --- Validate input feature ---
if not arcpy.Exists(input_feature):
    raise arcpy.ExecuteError(f"Input feature '{input_feature}' does not exist.")
desc = arcpy.Describe(input_feature)
if desc.shapeType != "Polygon":
    raise arcpy.ExecuteError(f"Input must be a polygon layer, but got {desc.shapeType}.")

# --- Get extent and spatial reference from input ---
extent        = desc.extent
extent_string = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
spatial_ref   = desc.spatialReference

# --- Validate coordinate system ---
if spatial_ref.type != "Projected":
    raise arcpy.ExecuteError("A projected coordinate system is required to accurately calculate area in hectares.")
arcpy.AddMessage(f"Coordinate system:    {spatial_ref.name}")

# --- Validate hexagon size ---
try:
    hex_size_val = float(hex_size_value)
    if hex_size_val <= 0:
        raise ValueError
    hex_size = f"{hex_size_val} Hectares"
except (ValueError, TypeError):
    raise arcpy.ExecuteError("Hexagon size must be a positive number.")

# ------------------------------------
# Generate hexagonal tessellation
# ------------------------------------
arcpy.AddMessage("Generating hexagonal grid...")
temp_hex = "in_memory/temp_hex"
arcpy.management.GenerateTessellation(temp_hex, extent_string, "HEXAGON", hex_size, spatial_ref)

if not arcpy.Exists(temp_hex):
    raise arcpy.ExecuteError("Hexagon generation failed.")
arcpy.AddMessage("Hexagonal grid generated successfully.")

# ------------------------------------
# Clip hexagons to the input boundary
# ------------------------------------
arcpy.AddMessage("Clipping hexagons to the input feature boundary...")
arcpy.analysis.Clip(temp_hex, input_feature, final_output_path)
arcpy.AddMessage(f"Clipped hexagons saved to: {final_output_path}")

# --- Try to add the result to the current map ---
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    m.addDataFromPath(final_output_path)
    arcpy.AddMessage("Output layer added to the map.")
except Exception:
    arcpy.AddMessage("Note: Could not automatically add the output layer to the map.")

# --- Clean up temporary data ---
try:
    if arcpy.Exists(temp_hex):
        arcpy.management.Delete(temp_hex)
    arcpy.AddMessage("Temporary data cleaned up.")
except Exception as e:
    arcpy.AddWarning(f"Could not delete temporary data: {e}")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         HEXAGON GENERATION COMPLETED        ===")
arcpy.AddMessage("===================================================")

# Author: Petr Mikeska
# Bachelor thesis (2025)
