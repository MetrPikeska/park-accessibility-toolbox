# ------------------------------------
# Name: 3_NetworkAnalysis.py
# Purpose: Calculates pedestrian service areas for parks using a network dataset
# and dissolves them into a single polygon.
# ------------------------------------

import arcpy
import os

# Always overwrite outputs to allow for script re-runs.
arcpy.env.overwriteOutput = True

# ------------------------------------
# Apply green symbology to a polygon layer
# ------------------------------------
def apply_green_symbology(layer_name):
    """
    Applies a default green symbology to a polygon layer in the current map.
    If no map is available or active, the function continues without error.
    """
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        
        # Find the layer in the map by its name.
        layer_found = None
        for lyr in m.listLayers():
            if lyr.name == layer_name or os.path.basename(lyr.dataSource) == os.path.basename(layer_name):
                layer_found = lyr
                break
        
        if layer_found and layer_found.isFeatureLayer:
            # Get the layer's symbology object.
            sym = layer_found.symbology
            if sym.renderer.type != 'SimpleRenderer':
                # Ensure the renderer is simple before applying color.
                sym.updateRenderer('SimpleRenderer')
            
            # Define colors for the fill and outline.
            green_color = {'RGB': [76, 230, 0, 100]}  # Bright green with some transparency
            dark_green_outline = {'RGB': [38, 115, 0, 255]}  # Darker green outline
            
            # Apply the defined colors to the symbol.
            sym.renderer.symbol.color = green_color
            sym.renderer.symbol.outlineColor = dark_green_outline
            sym.renderer.symbol.outlineWidth = 1
            
            layer_found.symbology = sym
            arcpy.AddMessage("Green symbology applied to the output layer.")
    except Exception as e:
        # Continue silently if symbology cannot be applied (e.g., when run as a background script).
        arcpy.AddMessage(f"Note: Could not apply symbology automatically: {str(e)}")

# ------------------------------------
# Get input parameters from the user via the ArcGIS tool dialog
# ------------------------------------
network_dataset     = arcpy.GetParameterAsText(0)  # Input Network dataset (.nd)
facilities_layer    = arcpy.GetParameterAsText(1)  # Input access points (e.g., park entrances)
output_service_area = arcpy.GetParameterAsText(2)  # Output feature class for the service area polygon
travel_distance     = arcpy.GetParameterAsText(3)  # Travel distance (e.g., "500 Meters")

# ------------------------------------
# Header log for script execution tracking
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
# Validate the input parameters
# ------------------------------------
if not arcpy.Exists(network_dataset):
    arcpy.AddError("The specified network dataset does not exist.")
    raise arcpy.ExecuteError("Network dataset does not exist.")

if not arcpy.Exists(facilities_layer):
    arcpy.AddError("The specified facilities layer (park entrances) does not exist.")
    raise arcpy.ExecuteError("Facilities layer does not exist.")

try:
    travel_distance_val = float(travel_distance)
    if travel_distance_val <= 0:
        raise ValueError
except ValueError:
    arcpy.AddError("Invalid travel distance. The value must be a positive number.")
    raise arcpy.ExecuteError("Invalid travel distance.")

# ------------------------------------
# Main execution block with robust error handling and cleanup
# ------------------------------------
extension_checked_out = False
service_area_layer = "Service_Area_Layer"
temp_polygons = ""

try:
    # --- Check for and check out the Network Analyst extension ---
    if arcpy.CheckExtension("Network") != "Available":
        arcpy.AddError("Network Analyst Extension is not available.")
        raise arcpy.ExecuteError("Network Analyst Extension is not available.")
    
    arcpy.CheckOutExtension("Network")
    extension_checked_out = True
    arcpy.AddMessage("Network Analyst Extension checked out successfully.")

    # --- Validate that the input is a NetworkDataset ---
    desc_net = arcpy.Describe(network_dataset)
    if desc_net.dataType != "NetworkDataset":
        arcpy.AddError("The selected dataset is not a valid network dataset.")
        raise arcpy.ExecuteError("Input is not a valid network dataset.")
    
    arcpy.AddMessage("Network dataset type is valid.")

    # --- Create the Service Area analysis layer ---
    arcpy.AddMessage("Creating a service area analysis layer...")
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
    arcpy.AddMessage("Service area layer created successfully.")

    # --- Add facility locations (e.g., park entrances) to the analysis ---
    arcpy.AddMessage("Adding facility locations to the analysis...")
    facility_count = int(arcpy.management.GetCount(facilities_layer)[0])
    arcpy.AddMessage(f"Number of facilities: {facility_count:,}")
    arcpy.na.AddLocations(service_area_layer, "Facilities", facilities_layer)
    arcpy.AddMessage("Facility locations added.")

    # --- Solve the network analysis ---
    arcpy.AddMessage("Solving service area network analysis...")
    arcpy.na.Solve(service_area_layer)
    arcpy.AddMessage("Service area analysis solved successfully.")

    # --- Save the resulting polygons temporarily ---
    gdb_path = os.path.dirname(os.path.dirname(network_dataset))
    temp_polygons = os.path.join(gdb_path, "temp_service_area")
    
    # Access the 'Polygons' sub-layer of the network analysis layer.
    polygons_path = arcpy.na.GetNAClassName(service_area_layer, "Polygons")
    if not polygons_path:
        polygons_path = f"{service_area_layer}/Polygons"

    arcpy.management.CopyFeatures(polygons_path, temp_polygons)
    arcpy.AddMessage(f"Temporary polygons saved to: {temp_polygons}")

    # --- Dissolve all service area polygons into a single feature ---
    polygon_count = int(arcpy.management.GetCount(temp_polygons)[0])
    arcpy.AddMessage(f"Polygons before dissolve: {polygon_count}")
    if polygon_count == 0:
        arcpy.AddWarning("No service area polygons were generated.")

    arcpy.AddMessage("Dissolving polygons into a single output...")
    arcpy.Dissolve_management(temp_polygons, output_service_area)
    arcpy.AddMessage(f"Final dissolved service area saved to: {output_service_area}")

    # --- Add a field with the travel distance for metadata ---
    arcpy.AddMessage("Adding 'distance_m' field for metadata...")
    arcpy.AddField_management(output_service_area, "distance_m", "DOUBLE")
    arcpy.CalculateField_management(output_service_area, "distance_m", travel_distance, "PYTHON3")
    arcpy.AddMessage("Metadata field 'distance_m' added.")

    # --- Add the output layer to the map and apply symbology ---
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        layer_name = os.path.basename(output_service_area)
        m.addDataFromPath(output_service_area)
        arcpy.AddMessage("Output layer added to the current map.")
        apply_green_symbology(layer_name)
    except Exception:
        arcpy.AddMessage("Note: Could not add the layer to the map automatically.")

    # --- Final validation check on the output ---
    final_count = int(arcpy.management.GetCount(output_service_area)[0])
    arcpy.AddMessage(f"Final polygon count: {final_count}")
    if final_count != 1:
        arcpy.AddWarning("The final output does not contain exactly one polygon, which may indicate disconnected service areas.")

except Exception as e:
    arcpy.AddError(f"An error occurred: {e}")
    raise

finally:
    # --- Cleanup temporary data and check in the extension ---
    try:
        if temp_polygons and arcpy.Exists(temp_polygons):
            arcpy.management.Delete(temp_polygons)
        if arcpy.Exists(service_area_layer):
            arcpy.management.Delete(service_area_layer)
        arcpy.AddMessage("Temporary data has been deleted.")
    except Exception as e:
        arcpy.AddWarning(f"Could not delete some temporary data: {e}")

    if extension_checked_out:
        arcpy.CheckInExtension("Network")
        arcpy.AddMessage("Network Analyst Extension checked back in.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           SERVICE AREA ANALYSIS DONE        ===")
arcpy.AddMessage("===================================================")

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
