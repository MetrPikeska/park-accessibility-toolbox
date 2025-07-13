# ------------------------------------
# Name: 2_PointsAlongLine.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script generates entrance points along park boundaries using the EU methodology.
# Output is used in accessibility analysis (Tool 3 – NetworkAnalysis).
# ------------------------------------

import arcpy
import os

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
    arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
    arcpy.AddMessage("---------------------------------------------------")

    # Validate output workspace
    if not output_gdb.lower().endswith(".gdb"):
        arcpy.AddError("❌ Output workspace must be a File Geodatabase (.gdb).")
        raise ValueError("Output must be GDB")

    # Validate output name
    if not out_name:
        arcpy.AddError("❌ Output layer base name is required.")
        raise ValueError("Missing output name.")

    # Step 1: Aggregate input park polygons (to dissolve internal gaps)
    arcpy.AddMessage("Aggregating input polygons using 10-meter distance...")
    aggregated_parks = "in_memory/aggregated_parks"
    arcpy.cartography.AggregatePolygons(
        in_features=parks_layer,
        out_feature_class=aggregated_parks,
        aggregation_distance="10 Meters",
        minimum_area="0 SquareMeters",
        minimum_hole_size="0 SquareMeters",
        orthogonality_option="NON_ORTHOGONAL"
    )

    # Step 2: Calculate area of each polygon in m²
    arcpy.AddMessage("Calculating area of aggregated polygons...")
    aggregated_parks_lyr = "aggregated_parks_lyr"
    area_field = "area_m2"

    arcpy.management.MakeFeatureLayer(aggregated_parks, aggregated_parks_lyr)
    if area_field not in [f.name for f in arcpy.ListFields(aggregated_parks_lyr)]:
        arcpy.management.AddField(aggregated_parks_lyr, area_field, "DOUBLE")
    arcpy.management.CalculateField(aggregated_parks_lyr, area_field, "!shape.area!", "PYTHON3")

    # Step 3: Select large parks ≥ 1 ha
    arcpy.AddMessage("Selecting parks ≥ 1 ha...")
    arcpy.management.SelectLayerByAttribute(aggregated_parks_lyr, "NEW_SELECTION", f'"{area_field}" >= 10000')
    arcpy.management.CopyFeatures(aggregated_parks_lyr, "in_memory/parks_large")
    count_large = int(arcpy.management.GetCount("in_memory/parks_large")[0])
    arcpy.AddMessage(f"✔ Parks ≥ 1 ha: {count_large:,}")

    # Step 4: Optionally include small parks
    if include_small_parks:
        arcpy.AddMessage("Copying all parks (incl. < 1 ha)...")
        arcpy.management.SelectLayerByAttribute(aggregated_parks_lyr, "CLEAR_SELECTION")
        arcpy.management.CopyFeatures(aggregated_parks_lyr, "in_memory/parks_all")
        count_all = int(arcpy.management.GetCount("in_memory/parks_all")[0])
        arcpy.AddMessage(f"✔ All parks:    {count_all:,}")

    arcpy.AddMessage("---------------------------------------------------")

    # ------------------------------------
    # Helper function to generate points from park polygons
    # ------------------------------------
    def process(parks_fc, suffix):
        label = f"{out_name}_{suffix}"
        arcpy.AddMessage(f"--- Processing: {label} ---")

        # Convert polygon to line boundaries
        boundaries = f"in_memory/boundaries_{suffix}"
        arcpy.management.FeatureToLine(parks_fc, boundaries)

        # Generate points along line every 50 m
        points = f"in_memory/points_{suffix}"
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=boundaries,
            Output_Feature_Class=points,
            Point_Placement="DISTANCE",
            Distance=50,
            Include_End_Points="END_POINTS"
        )

        # Select only points within 25 meters of the pedestrian network
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
            arcpy.AddWarning(f"⚠ Output {label} already exists and will be overwritten.")
        arcpy.management.CopyFeatures(points_layer, out_path)
        arcpy.AddMessage(f"✔ Output saved to: {out_path}")
        arcpy.AddMessage("---------------------------------------------------")

    # Always generate for large parks
    process("in_memory/parks_large", "large")

    # Optionally generate for all parks
    if include_small_parks:
        process("in_memory/parks_all", "all")

    arcpy.AddMessage("===   ACCESSIBILITY POINT GENERATION COMPLETE   ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

# ------------------------------------
# Script entry point – parameters passed from ArcGIS Toolbox
# ------------------------------------
if __name__ == "__main__":
    parks_layer         = arcpy.GetParameterAsText(0)
    streets_layer       = arcpy.GetParameterAsText(1)
    output_gdb          = arcpy.GetParameterAsText(2)
    include_small_parks = arcpy.GetParameter(3)
    out_name            = arcpy.GetParameterAsText(4)

    generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks, out_name)

    # Clean up
    del parks_layer, streets_layer, output_gdb, include_small_parks, out_name
