#------------------------------------
# Name: 2_PointsAlongLine.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script generates points along the park boundaries and selects only those that are within walking distance of the road network.
#------------------------------------

import arcpy
import os

#------------------------------------
# Main function
#------------------------------------
def generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks):
    arcpy.env.overwriteOutput = True
    # Allow overwriting outputs

    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===     ACCESSIBILITY POINT GENERATION START    ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
    arcpy.AddMessage("---------------------------------------------------")

    if not output_gdb.lower().endswith(".gdb"):
        arcpy.AddError("Output workspace must be a File Geodatabase (.gdb).")
        raise SystemExit()
        # Ensure the output is a file geodatabase

    arcpy.management.MakeFeatureLayer(parks_layer, "parks_lyr")
    # Create temporary layer from input polygons

    candidate_fields = ["Shape_Area", "geom_Area", "area"]
    # Potential fields with park area

    existing_fields = [f.name for f in arcpy.ListFields("parks_lyr")]
    # Get list of available fields

    area_field = next((field for field in candidate_fields if field in existing_fields), None)
    # Choose first available area field

    if not area_field:
        arcpy.AddError("Field with park area not found (Shape_Area, geom_Area, or area).")
        raise SystemExit()
    else:
        arcpy.AddMessage(f"Using area field: '{area_field}'")

    arcpy.AddMessage("Selecting parks ≥ 1 ha...")
    arcpy.management.SelectLayerByAttribute("parks_lyr", "NEW_SELECTION", f'"{area_field}" >= 10000')
    # Select parks larger than 1 ha

    arcpy.management.CopyFeatures("parks_lyr", "in_memory/parks_large")
    # Copy selected large parks

    count_large = int(arcpy.management.GetCount("in_memory/parks_large")[0])
    arcpy.AddMessage(f"   Parks ≥ 1 ha:       {count_large:,}")

    arcpy.AddMessage("Copying all parks...")
    arcpy.management.SelectLayerByAttribute("parks_lyr", "CLEAR_SELECTION")
    arcpy.management.CopyFeatures("parks_lyr", "in_memory/parks_all")
    # Copy all parks

    count_all = int(arcpy.management.GetCount("in_memory/parks_all")[0])
    arcpy.AddMessage(f"   All parks:          {count_all:,}")
    arcpy.AddMessage("---------------------------------------------------")

    def process_parks(parks_fc, output_name):
        arcpy.AddMessage(f"--- Processing: {output_name} ---")

        boundaries = f"in_memory/boundaries_{output_name}"
        arcpy.management.FeatureToLine(parks_fc, boundaries)
        # Convert polygons to boundaries

        points = f"in_memory/points_{output_name}"
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=boundaries,
            Output_Feature_Class=points,
            Point_Placement="DISTANCE",
            Distance=50,
            Include_End_Points="END_POINTS"
        )
        # Generate points every 50 meters

        total_points = int(arcpy.management.GetCount(points)[0])
        arcpy.AddMessage(f"   Total points generated:   {total_points:,}")

        # CREATE FEATURE LAYER FOR SPATIAL SELECTION
        points_layer = f"points_lyr_{output_name}"
        arcpy.management.MakeFeatureLayer(points, points_layer)

        arcpy.management.SelectLayerByLocation(
            in_layer=points_layer,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=streets_layer,
            search_distance="25 Meters",
            selection_type="NEW_SELECTION"
        )
        # Select only points within 25 meters from roads

        near_street_count = int(arcpy.management.GetCount(points_layer)[0])
        arcpy.AddMessage(f"   Points near streets:      {near_street_count:,}")

        output_path = os.path.join(output_gdb, output_name)
        arcpy.management.CopyFeatures(points_layer, output_path)
        # Export final result

        arcpy.AddMessage(f"   Output saved to:          {output_path}")
        arcpy.AddMessage("---------------------------------------------------")

    if include_small_parks:
        process_parks("in_memory/parks_all", "access_points_parks_all_sizes")
        # Include all parks if checkbox checked
    else:
        process_parks("in_memory/parks_large", "access_points_parks_large_only")
        # Only large parks otherwise

    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===   ACCESSIBILITY POINT GENERATION COMPLETE   ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

#------------------------------------
# Script entry point
#------------------------------------
if __name__ == "__main__":
    parks_layer         = arcpy.GetParameterAsText(0)
    # Input: Parks polygon layer

    streets_layer       = arcpy.GetParameterAsText(1)
    # Input: Streets line layer

    output_gdb          = arcpy.GetParameterAsText(2)
    # Output: File geodatabase

    include_small_parks = arcpy.GetParameter(3)
    # Checkbox: include parks < 1 ha

    generate_analysis_points(parks_layer, streets_layer, output_gdb, include_small_parks)
    # Execute main function

    del parks_layer, streets_layer, output_gdb, include_small_parks
    # Clean up variables
