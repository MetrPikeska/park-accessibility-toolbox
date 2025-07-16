# ------------------------------------
# Name: 3_NetworkAnalysis.py
# This script calculates pedestrian service areas for parks using a network dataset
# and dissolves them into a single polygon.
# ------------------------------------

import arcpy
import os
import sys

# Always overwrite outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Get input parameters from user
# ------------------------------------
network_dataset     = arcpy.GetParameterAsText(0)  # Network dataset
facilities_layer    = arcpy.GetParameterAsText(1)  # Access points (park entrances)
output_service_area = arcpy.GetParameterAsText(2)  # Output polygon
travel_distance     = arcpy.GetParameterAsText(3)  # Travel distance in meters

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS START       ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Network dataset:      {network_dataset}")
arcpy.AddMessage(f"Facilities layer:     {facilities_layer}")
arcpy.AddMessage(f"Output service area:  {output_service_area}")
arcpy.AddMessage(f"Travel distance:      {travel_distance} m")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate inputs
# ------------------------------------
if not arcpy.Exists(network_dataset):
    arcpy.AddError("❌ Network dataset does NOT exist.")
    sys.exit(1)

if not arcpy.Exists(facilities_layer):
    arcpy.AddError("❌ Facilities layer does NOT exist.")
    sys.exit(1)

# Validate travel distance
try:
    travel_distance_val = float(travel_distance)
    if travel_distance_val <= 0:
        raise ValueError
except:
    arcpy.AddError("❌ Invalid travel distance. Must be a positive number.")
    sys.exit(1)

# ------------------------------------
# Check Network Analyst Extension availability
# ------------------------------------
ext_status = arcpy.CheckExtension("Network")
if ext_status != "Available":
    arcpy.AddError("❌ Network Analyst Extension is NOT available. Check ArcGIS Pro license.")
    sys.exit(1)
else:
    arcpy.CheckOutExtension("Network")
    arcpy.AddMessage("✔ Network Analyst Extension is available and checked out.")

# ------------------------------------
# Validate that the dataset is a NetworkDataset
# ------------------------------------
desc_net = arcpy.Describe(network_dataset)
if desc_net.dataType != "NetworkDataset":
    arcpy.AddError("❌ The selected dataset is NOT a valid network dataset.")
    arcpy.AddError("   Please select a valid network dataset (.nd) and try again.")
    sys.exit(1)
else:
    arcpy.AddMessage("✔ Network dataset type is valid.")

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
# Add facilities
# ------------------------------------
arcpy.AddMessage("Adding facilities...")
facility_count = int(arcpy.management.GetCount(facilities_layer)[0])
arcpy.AddMessage(f"→ Number of facilities: {facility_count:,}")
arcpy.na.AddLocations(service_area_layer, "Facilities", facilities_layer)
arcpy.AddMessage("✔ Facilities added.")

# ------------------------------------
# Solve network analysis with error handling
# ------------------------------------
arcpy.AddMessage("Solving service area...")
try:
    arcpy.na.Solve(service_area_layer)
    arcpy.AddMessage("✔ Service area solved.")
except Exception as e:
    arcpy.AddError("❌ Service Area Solver failed. Possible reasons:")
    arcpy.AddError("   – The network dataset is NOT built (use 'Build Network Dataset' in ArcGIS Pro)")
    arcpy.AddError("   – Some facility locations are outside the network")
    arcpy.AddError("   – Licensing issues with the Network Analyst Extension")
    arcpy.AddError(f"Detailed error: {e}")
    sys.exit(1)

# ------------------------------------
# Save intermediate polygons
# ------------------------------------
gdb_path = os.path.dirname(os.path.dirname(network_dataset))
temp_polygons = os.path.join(gdb_path, "temp_service_area")
if arcpy.Exists(temp_polygons):
    arcpy.Delete_management(temp_polygons)

arcpy.CopyFeatures_management(service_area_layer + "\\Polygons", temp_polygons)
arcpy.AddMessage(f"✔ Temporary polygons saved: {temp_polygons}")

# ------------------------------------
# Dissolve polygons into one
# ------------------------------------
polygon_count = int(arcpy.management.GetCount(temp_polygons)[0])
arcpy.AddMessage(f"→ Polygons before dissolve: {polygon_count}")
if polygon_count == 0:
    arcpy.AddWarning("⚠ No polygons were created. Check inputs or distance.")

arcpy.AddMessage("Dissolving polygons...")
arcpy.Dissolve_management(temp_polygons, output_service_area)
arcpy.AddMessage(f"✔ Final dissolved output saved: {output_service_area}")

# ------------------------------------
# Add travel distance as metadata
# ------------------------------------
arcpy.AddMessage("Adding 'distance_m' field...")
arcpy.AddField_management(output_service_area, "distance_m", "DOUBLE")
arcpy.CalculateField_management(output_service_area, "distance_m", travel_distance, "PYTHON3")
arcpy.AddMessage("✔ Field 'distance_m' added.")

# ------------------------------------
# Final check
# ------------------------------------
final_count = int(arcpy.management.GetCount(output_service_area)[0])
arcpy.AddMessage(f"→ Final polygon count: {final_count}")
if final_count != 1:
    arcpy.AddWarning("⚠ Final output does NOT contain exactly one polygon.")

# ------------------------------------
# Clean up
# ------------------------------------
arcpy.Delete_management(temp_polygons)
arcpy.AddMessage("✔ Temporary data deleted.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS DONE        ===")
arcpy.AddMessage("===================================================")

# Clean memory
del network_dataset, facilities_layer, output_service_area, travel_distance
del service_area_layer, facility_count, temp_polygons, polygon_count, final_count, gdb_path, desc_net

# Author: Petr MIKESKA
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
