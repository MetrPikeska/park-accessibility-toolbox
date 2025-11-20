# ------------------------------------
# Name: 2_PointsAlongLine.py
# Purpose: Generates entrance points along park boundaries using EU methodology.
# Output is used in accessibility analysis (Tool 3 – NetworkAnalysis).
# ------------------------------------

import arcpy
import os
import re

# Always overwrite existing outputs to allow for script re-runs.
arcpy.env.overwriteOutput = True

# ------------------------------------
# Sanitize feature class name for ArcGIS Pro
# ------------------------------------
def sanitize_fc_name(name):
    """
    Sanitizes a feature class name to ensure it's valid for ArcGIS Pro.
    - Cannot start with a number.
    - Can only contain letters, numbers, and underscores.
    - Maximum 64 characters.
    - Cannot be a reserved word.
    """
    # Remove invalid characters (keep only alphanumeric and underscores).
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # If the name starts with a number, prefix with "FC_".
    if sanitized and sanitized[0].isdigit():
        sanitized = f"FC_{sanitized}"
    
    # Ensure it doesn't start with an underscore; prefer a letter prefix.
    if sanitized.startswith('_'):
        sanitized = f"FC{sanitized}"
    
    # Truncate to 64 characters to comply with ArcGIS Pro limits.
    if len(sanitized) > 64:
        sanitized = sanitized[:64]
    
    # Ensure the name is not empty.
    if not sanitized:
        sanitized = "FeatureClass"
    
    return sanitized

# ------------------------------------
# Main function: generates entrance points for park accessibility
# ------------------------------------
def generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks, out_name):
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===     ACCESSIBILITY POINT GENERATION START    ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("Processing park categories:")
    arcpy.AddMessage("  - P1HA  = Parks ≥ 1 ha (≥ 10,000 m²)")
    arcpy.AddMessage("  - ALLP  = All parks (no size threshold)")
    arcpy.AddMessage("---------------------------------------------------")

    # List to track all temporary layers for robust cleanup.
    temp_layers = []
    
    try:
        # --- Validate the output workspace ---
        if not output_gdb.lower().endswith(".gdb"):
            raise arcpy.ExecuteError("Invalid output workspace. Must be a File Geodatabase (.gdb).")

        # Sanitize the output name to ensure it is a valid feature class name.
        out_name = sanitize_fc_name(out_name.strip() if out_name else "park_points")
        arcpy.AddMessage(f"Using sanitized base name for outputs: '{out_name}'")

        # --- Step 1: Aggregate input park polygons ---
        arcpy.AddMessage("Aggregating park polygons (10m threshold)...")
        aggregated_parks = "in_memory/aggregated_parks"
        temp_layers.append(aggregated_parks)
        arcpy.cartography.AggregatePolygons(
            in_features=parks_layer,
            out_feature_class=aggregated_parks,
            aggregation_distance="10 Meters"
        )
        # Save a copy of the aggregated parks to the output geodatabase.
        aggregated_parks_out = os.path.join(output_gdb, f"{out_name}_AGGREGATED")
        arcpy.management.CopyFeatures(aggregated_parks, aggregated_parks_out)
        arcpy.AddMessage(f"Aggregated parks saved to: {aggregated_parks_out}")

        # --- Step 2: Calculate area in square meters ---
        arcpy.AddMessage("Calculating polygon areas...")
        area_field = "area_m2"
        if area_field not in [f.name for f in arcpy.ListFields(aggregated_parks)]:
            arcpy.management.AddField(aggregated_parks, area_field, "DOUBLE")
        arcpy.management.CalculateField(aggregated_parks, area_field, "!shape.area!", "PYTHON3")

        # --- Step 3: Create layers for different park categories based on size ---
        parks_large = "in_memory/parks_large"
        temp_layers.append(parks_large)
        arcpy.analysis.Select(aggregated_parks, parks_large, f'"{area_field}" >= 10000')
        arcpy.AddMessage(f"Parks ≥ 1 ha (P1HA): {int(arcpy.management.GetCount(parks_large)[0]):,}")

        parks_all = ""
        if include_small_parks:
            parks_all = "in_memory/parks_all"
            temp_layers.append(parks_all)
            arcpy.management.CopyFeatures(aggregated_parks, parks_all)
            arcpy.AddMessage(f"All parks (ALLP): {int(arcpy.management.GetCount(parks_all)[0]):,}")
        
        arcpy.AddMessage("---------------------------------------------------")

        # --- Helper function to process each park category ---
        def process_category(parks_fc, suffix):
            label = f"{out_name}_{sanitize_fc_name(suffix)}"
            arcpy.AddMessage(f"--- Processing: {label} ---")
            
            # Create temporary layers for boundaries and points.
            boundaries = f"in_memory/boundaries_{suffix}"
            points = f"in_memory/points_{suffix}"
            points_lyr = f"points_lyr_{suffix}"
            temp_layers.extend([boundaries, points])

            # Generate points every 50 meters along park boundaries.
            arcpy.management.FeatureToLine(parks_fc, boundaries)
            arcpy.management.GeneratePointsAlongLines(boundaries, points, "DISTANCE", "50 Meters", True)
            
            # Select only those points that are within 25 meters of a street.
            arcpy.management.MakeFeatureLayer(points, points_lyr)
            arcpy.management.SelectLayerByLocation(points_lyr, "WITHIN_A_DISTANCE", streets_layer, "25 Meters")
            
            # Save the final points to the output geodatabase.
            out_path = os.path.join(output_gdb, label)
            arcpy.management.CopyFeatures(points_lyr, out_path)
            arcpy.AddMessage(f"Output saved to: {out_path}")
            arcpy.management.Delete(points_lyr) # Delete the layer view, keeping the in-memory data for cleanup.
            arcpy.AddMessage("--- Done ---")
            
        # Process the mandatory category (parks >= 1 ha).
        process_category(parks_large, "P1HA")

        # Process the optional category (all parks) if requested.
        if include_small_parks and parks_all:
            process_category(parks_all, "ALLP")

        arcpy.AddMessage("===================================================")
        arcpy.AddMessage("===  ACCESSIBILITY POINT GENERATION COMPLETED   ===")
        arcpy.AddMessage("===================================================")

    except Exception as e:
        arcpy.AddError(f"An error occurred: {e}")
        raise
        
    finally:
        # --- Robust cleanup of all temporary in-memory layers ---
        arcpy.AddMessage("Cleaning up temporary data...")
        deleted_count = 0
        for layer in temp_layers:
            try:
                if arcpy.Exists(layer):
                    arcpy.management.Delete(layer)
                    deleted_count += 1
            except Exception:
                arcpy.AddWarning(f"Could not delete temporary layer: {layer}")
        arcpy.AddMessage(f"{deleted_count} temporary layers cleaned up.")

# ------------------------------------
# Script entry point – parameters from ArcGIS Toolbox
# ------------------------------------
if __name__ == "__main__":
    # Load parameters from the ArcGIS tool dialog.
    parks_layer         = arcpy.GetParameterAsText(0)  # Input park polygons
    streets_layer       = arcpy.GetParameterAsText(1)  # Input street network
    output_gdb          = arcpy.GetParameterAsText(2)  # Output geodatabase
    include_small_parks = arcpy.GetParameter(3)        # Boolean flag to include small parks
    out_name            = arcpy.GetParameterAsText(4)  # Base name for output layers

    # Run the main function with the provided parameters.
    generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks, out_name)

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
