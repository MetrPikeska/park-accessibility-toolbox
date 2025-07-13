# ------------------------------------
# Name: 3_NetworkAnalysis.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script calculates pedestrian service areas for parks using a network dataset and dissolves them into a single polygon.
# ------------------------------------

import arcpy
import os

# ------------------------------------
# General settings
# ------------------------------------
arcpy.env.overwriteOutput = True  # Allow overwriting outputs

# ------------------------------------
# Get input parameters from user
# ------------------------------------
network_dataset     = arcpy.GetParameterAsText(0)  # Input network dataset
facilities_layer    = arcpy.GetParameterAsText(1)  # Point layer of access points
output_service_area = arcpy.GetParameterAsText(2)  # Output polygon feature class
travel_distance     = arcpy.GetParameterAsText(3)  # Travel threshold in meters

# ------------------------------------
# Print header information
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS START       ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
arcpy.AddMessage("---------------------------------------------------")
arcpy.AddMessage(f"Network dataset:      {network_dataset}")
arcpy.AddMessage(f"Facilities layer:     {facilities_layer}")
arcpy.AddMessage(f"Output service area:  {output_service_area}")
arcpy.AddMessage(f"Travel distance:      {travel_distance} meters")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate input existence
# ------------------------------------
if not arcpy.Exists(network_dataset):
    arcpy.AddError("❌ Network dataset does not exist.")
    raise SystemExit()

if not arcpy.Exists(facilities_layer):
    arcpy.AddError("❌ Facilities layer does not exist.")
    raise SystemExit()

# ------------------------------------
# Validate travel distance parameter
# ------------------------------------
try:
    travel_distance_val = float(travel_distance)
    if travel_distance_val <= 0:
        raise ValueError
except:
    arcpy.AddError("❌ Invalid travel distance. Must be a positive number.")
    raise SystemExit()

# ------------------------------------
# Create service area layer
# ------------------------------------
arcpy.AddMessage("Creating service area layer...")
service_area_layer = "Service_Area_Layer"

arcpy.na.MakeServiceAreaLayer(
    in_network_dataset=network_dataset,
    out_network_analysis_layer=service_area_layer,
    impedance_attribute="Length",
    travel_from_to="TRAVEL_FROM",
    default_break_values=travel_distance,
    polygon_type="DETAILED_POLYS",
    merge="NO_MERGE",
    nesting_type="RINGS"
)
arcpy.AddMessage("✔ Service area layer created.")

# ------------------------------------
# Add facilities to analysis
# ------------------------------------
arcpy.AddMessage("Adding facilities...")
facility_count = int(arcpy.management.GetCount(facilities_layer)[0])
arcpy.AddMessage(f"   → Number of facilities: {facility_count:,}")
arcpy.na.AddLocations(service_area_layer, "Facilities", facilities_layer)
arcpy.AddMessage("✔ Facilities added.")

# ------------------------------------
# Solve service area
# ------------------------------------
arcpy.AddMessage("Solving service area...")
arcpy.na.Solve(service_area_layer)
arcpy.AddMessage("✔ Service area solved.")

# ------------------------------------
# Save intermediate polygons to GDB
# ------------------------------------
gdb_path = os.path.dirname(os.path.dirname(network_dataset))
temp_polygons = os.path.join(gdb_path, "temp_service_area")

if arcpy.Exists(temp_polygons):
    arcpy.Delete_management(temp_polygons)

arcpy.CopyFeatures_management(service_area_layer + "\\Polygons", temp_polygons)
arcpy.AddMessage(f"✔ Temporary polygons saved to: {temp_polygons}")

# ------------------------------------
# Dissolve polygons into one output
# ------------------------------------
polygon_count = int(arcpy.management.GetCount(temp_polygons)[0])
arcpy.AddMessage(f"   → Polygons before dissolve: {polygon_count}")

if polygon_count == 0:
    arcpy.AddWarning("⚠ No polygons were created. Check input data or travel distance.")

arcpy.AddMessage("Dissolving polygons...")
arcpy.Dissolve_management(temp_polygons, output_service_area)
arcpy.AddMessage(f"✔ Final dissolved output saved to: {output_service_area}")

# ------------------------------------
# Add distance field for metadata
# ------------------------------------
arcpy.AddMessage("Adding 'distance_m' field...")
arcpy.AddField_management(output_service_area, "distance_m", "DOUBLE")
arcpy.CalculateField_management(output_service_area, "distance_m", travel_distance, "PYTHON3")
arcpy.AddMessage("✔ Field 'distance_m' added.")

# ------------------------------------
# Final check on resulting polygon
# ------------------------------------
final_count = int(arcpy.management.GetCount(output_service_area)[0])
arcpy.AddMessage(f"   → Final polygon count: {final_count}")
if final_count != 1:
    arcpy.AddWarning("⚠ Final output does not contain exactly one polygon.")

# ------------------------------------
# Clean up temporary data
# ------------------------------------
arcpy.Delete_management(temp_polygons)
arcpy.AddMessage("✔ Temporary data deleted.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS DONE        ===")
arcpy.AddMessage("===================================================")

# ------------------------------------
# Clean memory
# ------------------------------------
del network_dataset, facilities_layer, output_service_area, travel_distance
del service_area_layer, facility_count, temp_polygons, polygon_count, final_count, gdb_path
