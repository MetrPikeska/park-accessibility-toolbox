#------------------------------------
# Name: 3_NetworkAnalysis.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script calculates pedestrian service areas for parks using a network dataset and dissolves them into a single accessibility polygon.
#------------------------------------

import arcpy
import os

# Input parameters
gdb_path             = arcpy.GetParameterAsText(0)                                                       # Path to File Geodatabase
network_dataset      = os.path.join(gdb_path, "NetworkData", "NetworkDataset")                           # Path to Network Dataset
facilities_layer     = arcpy.GetParameterAsText(1)                                                       # Park access points
output_service_area  = arcpy.GetParameterAsText(2)                                                       # Output polygon feature class
travel_distance      = arcpy.GetParameterAsText(3)                                                       # Travel distance in meters

# General settings
arcpy.env.overwriteOutput = True

# Log basic info
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS START       ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
arcpy.AddMessage("---------------------------------------------------")
arcpy.AddMessage(f"Geodatabase:          {gdb_path}")
arcpy.AddMessage(f"Network dataset:      {network_dataset}")
arcpy.AddMessage(f"Facilities layer:     {facilities_layer}")
arcpy.AddMessage(f"Output service area:  {output_service_area}")
arcpy.AddMessage(f"Travel distance:      {travel_distance} meters")
arcpy.AddMessage("---------------------------------------------------")

# Validate existence of input layers
arcpy.AddMessage("Checking input data...")
if not arcpy.Exists(network_dataset):
    arcpy.AddError("Network dataset does not exist.")
    raise SystemExit()
if not arcpy.Exists(facilities_layer):
    arcpy.AddError("Facilities layer does not exist.")
    raise SystemExit()
arcpy.AddMessage("Input data check passed.")

# Create service area analysis layer
arcpy.AddMessage("Creating service area layer...")
service_area_layer = "Service_Area_Output"
arcpy.na.MakeServiceAreaLayer(
    in_network_dataset          = network_dataset,
    out_network_analysis_layer  = service_area_layer,
    impedance_attribute         = "Length",
    travel_from_to              = "TRAVEL_FROM",
    default_break_values        = travel_distance,
    polygon_type                = "DETAILED_POLYS",
    merge                       = "NO_MERGE",
    nesting_type                = "RINGS"
)
arcpy.AddMessage("Service area layer created.")

# Add facilities to the analysis
arcpy.AddMessage("Adding facilities to the analysis...")
facility_count = int(arcpy.GetCount_management(facilities_layer)[0])
arcpy.AddMessage(f"   Number of input facilities: {facility_count}")
arcpy.na.AddLocations(service_area_layer, "Facilities", facilities_layer)
arcpy.AddMessage("Facilities successfully added.")

# Run network analysis
arcpy.AddMessage("Solving network analysis...")
arcpy.na.Solve(service_area_layer)
arcpy.AddMessage("Network analysis completed.")

# Export resulting polygons
arcpy.AddMessage("Exporting service area polygons...")
temp_polygons = os.path.join(gdb_path, "temp_service_area")
arcpy.CopyFeatures_management(service_area_layer + "\\Polygons", temp_polygons)
arcpy.AddMessage(f"Temporary polygons saved to: {temp_polygons}")

# Dissolve polygons into one output
polygon_count = int(arcpy.GetCount_management(temp_polygons)[0])
arcpy.AddMessage(f"   Number of polygons created: {polygon_count}")
if polygon_count == 0:
    arcpy.AddWarning("No polygons were created. Analysis may have failed.")

arcpy.AddMessage("Dissolving polygons into single output...")
arcpy.Dissolve_management(temp_polygons, output_service_area)
arcpy.AddMessage(f"Final dissolved output saved to: {output_service_area}")

# Check result and cleanup
final_count = int(arcpy.GetCount_management(output_service_area)[0])
arcpy.AddMessage(f"   Final polygon count: {final_count}")
if final_count != 1:
    arcpy.AddWarning("Final result does not contain exactly one polygon.")

arcpy.AddMessage("Cleaning up temporary data...")
arcpy.Delete_management(temp_polygons)
arcpy.AddMessage("Temporary data deleted.")

# Final log
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS DONE        ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("")

# Delete variables
del gdb_path, network_dataset, facilities_layer, output_service_area, travel_distance
del service_area_layer, facility_count, temp_polygons, polygon_count, final_count
