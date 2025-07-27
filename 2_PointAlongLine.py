# ------------------------------------
# Name: 2_PointsAlongLine.py
# Purpose: Generates entrance points along park boundaries using EU methodology.
# Output is used in accessibility analysis (Tool 3 – NetworkAnalysis).
# ------------------------------------

import arcpy
import os
import sys

# Always overwrite existing outputs
arcpy.env.overwriteOutput = True

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

    # ------------------------------------
    # Validate output workspace
    # ------------------------------------
    if not output_gdb.lower().endswith(".gdb"):
        arcpy.AddError(
            "Invalid output workspace. The output must be a File Geodatabase (.gdb). "
            "Please provide a valid geodatabase path."
        )
        sys.exit(1)

    # Validate output name
    if not out_name:
        arcpy.AddError("No output layer base name provided. Please specify a valid name.")
        sys.exit(1)

    # ------------------------------------
    # Step 1: Aggregate input park polygons
    # ------------------------------------
    arcpy.AddMessage("Aggregating park polygons with a 10 m distance threshold...")
    aggregated_parks = "in_memory/aggregated_parks"
    arcpy.cartography.AggregatePolygons(
        in_features=parks_layer,
        out_feature_class=aggregated_parks,
        aggregation_distance="10 Meters",
        minimum_area="0 SquareMeters",
        minimum_hole_size="0 SquareMeters",
        orthogonality_option="NON_ORTHOGONAL"
    )

    # Save aggregated parks to GDB
    aggregated_parks_out = os.path.join(output_gdb, f"{out_name}_AGGREGATED")
    if arcpy.Exists(aggregated_parks_out):
        arcpy.AddMessage(f"An existing dataset '{aggregated_parks_out}' will be replaced.")
        arcpy.management.Delete(aggregated_parks_out)
    arcpy.management.CopyFeatures(aggregated_parks, aggregated_parks_out)
    arcpy.AddMessage(f"Aggregated parks saved to: {aggregated_parks_out}")

    # ------------------------------------
    # Step 2: Calculate area of polygons in m²
    # ------------------------------------
    arcpy.AddMessage("Calculating polygon areas (m²)...")
    aggregated_parks_lyr = "aggregated_parks_lyr"
    area_field = "area_m2"
    arcpy.management.MakeFeatureLayer(aggregated_parks, aggregated_parks_lyr)
    if area_field not in [f.name for f in arcpy.ListFields(aggregated_parks_lyr)]:
        arcpy.management.AddField(aggregated_parks_lyr, area_field, "DOUBLE")
    arcpy.management.CalculateField(aggregated_parks_lyr, area_field, "!shape.area!", "PYTHON3")

    # ------------------------------------
    # Step 3: Select large parks ≥ 1 ha
    # ------------------------------------
    arcpy.AddMessage("Selecting parks ≥ 1 ha (P1HA)...")
    arcpy.management.SelectLayerByAttribute(
        aggregated_parks_lyr, "NEW_SELECTION", f'"{area_field}" >= 10000'
    )
    arcpy.management.CopyFeatures(aggregated_parks_lyr, "in_memory/parks_large")
    count_large = int(arcpy.management.GetCount("in_memory/parks_large")[0])
    arcpy.AddMessage(f"Parks ≥ 1 ha: {count_large:,}")

    # ------------------------------------
    # Step 4: Optionally include all parks
    # ------------------------------------
    if include_small_parks:
        arcpy.AddMessage("Including all parks (ALLP, including < 1 ha)...")
        arcpy.management.SelectLayerByAttribute(aggregated_parks_lyr, "CLEAR_SELECTION")
        arcpy.management.CopyFeatures(aggregated_parks_lyr, "in_memory/parks_all")
        count_all = int(arcpy.management.GetCount("in_memory/parks_all")[0])
        arcpy.AddMessage(f"All parks processed: {count_all:,}")

    arcpy.AddMessage("---------------------------------------------------")

    # ------------------------------------
    # Helper function to generate points from park polygons
    # ------------------------------------
    def process(parks_fc, suffix):
        label = f"{out_name}_{suffix}"
        arcpy.AddMessage(f"--- Processing park category: {label} ---")

        # Convert polygon to line boundaries
        boundaries = f"in_memory/boundaries_{suffix}"
        arcpy.management.FeatureToLine(parks_fc, boundaries)

        # Generate points every 50 m along boundaries
        points = f"in_memory/points_{suffix}"
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=boundaries,
            Output_Feature_Class=points,
            Point_Placement="DISTANCE",
            Distance=50,
            Include_End_Points="END_POINTS"
        )

        # Select points within 25 m of the pedestrian network
        points_layer = f"points_lyr_{suffix}"
        arcpy.management.MakeFeatureLayer(points, points_layer)
        arcpy.management.SelectLayerByLocation(
            in_layer=points_layer,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=streets_layer,
            search_distance="25 Meters",
            selection_type="NEW_SELECTION"
        )

        # Save final output to GDB
        out_path = os.path.join(output_gdb, label)
        if arcpy.Exists(out_path):
            arcpy.AddMessage(f"Existing output '{label}' will be replaced.")
            arcpy.management.Delete(out_path)
        arcpy.management.CopyFeatures(points_layer, out_path)
        arcpy.AddMessage(f"Output saved to: {out_path}")
        arcpy.AddMessage("---------------------------------------------------")

    # Always generate for large parks (≥ 1 ha)
    process("in_memory/parks_large", "P1HA")

    # Optionally generate for all parks
    if include_small_parks:
        process("in_memory/parks_all", "ALLP")

    arcpy.AddMessage("Accessibility point generation completed successfully.")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

# ------------------------------------
# Script entry point – parameters from ArcGIS Toolbox
# ------------------------------------
if __name__ == "__main__":
    parks_layer         = arcpy.GetParameterAsText(0)  # Park polygons
    streets_layer       = arcpy.GetParameterAsText(1)  # Street network
    output_gdb          = arcpy.GetParameterAsText(2)  # Output geodatabase
    include_small_parks = arcpy.GetParameter(3)        # Boolean flag for small parks
    out_name            = arcpy.GetParameterAsText(4)  # Base name for output layers

    generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks, out_name)

    del parks_layer, streets_layer, output_gdb, include_small_parks, out_name

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
