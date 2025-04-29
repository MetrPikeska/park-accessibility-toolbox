#------------------------------------
# Name: 4_AnalyzeParkAccessibility.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script analyzes accessibility of green space within a defined walking distance for each city district.
#------------------------------------

import arcpy
import os
from datetime import datetime

def analyze_accessibility(accessibility_fc, input_fc, population_field, group_fields_raw,
                          output_gdb, distance_label, districts_fc, district_field):
    arcpy.env.overwriteOutput = True
    # Allow overwriting outputs

    distance_label = str(distance_label)
    suffix = f"{distance_label}m"
    # Prepare suffix for file names

    output_points_fc = os.path.join(output_gdb, f"points_accessibility_{suffix}")
    output_districts_fc = os.path.join(output_gdb, f"districts_accessibility_{suffix}")
    access_area_clip = os.path.join("in_memory", f"access_area_clip_{suffix}")
    output_folder = os.path.dirname(output_gdb)
    # Paths for output files and in-memory workspace

    # Print analysis header
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===       PARK ACCESSIBILITY ANALYSIS START     ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
    arcpy.AddMessage(f"Methodology: A short walk to the park – {distance_label} meters to green space")
    arcpy.AddMessage("---------------------------------------------------")

    # Check input data existence
    for fc in [accessibility_fc, input_fc, districts_fc]:
        if not arcpy.Exists(fc):
            arcpy.AddError(f"ERROR: Input layer '{fc}' does not exist.")
            return
    if not output_gdb:
        arcpy.AddError("ERROR: Output geodatabase not set.")
        return

    # Prepare and copy input layer
    arcpy.management.MakeFeatureLayer(input_fc, "input_layer_temp")
    arcpy.management.CopyFeatures("input_layer_temp", output_points_fc)
    arcpy.management.MakeFeatureLayer(output_points_fc, "output_layer_temp")

    # Add field for accessibility flag
    if "near_park" not in [f.name for f in arcpy.ListFields(output_points_fc)]:
        arcpy.management.AddField(output_points_fc, "near_park", "SHORT")

    # Parse group fields and validate
    group_fields = [f.strip() for f in group_fields_raw.split(";") if f.strip()] if group_fields_raw else []
    existing_fields = [f.name for f in arcpy.ListFields(output_points_fc)]
    valid_group_fields = [f for f in group_fields if f in existing_fields]
    has_population_field = population_field in existing_fields
    use_population_data = bool(valid_group_fields or has_population_field)

    # Decide which fields to use for statistics
    if use_population_data:
        if valid_group_fields:
            fields = valid_group_fields + ["near_park"]
            arcpy.AddMessage(f"→ Using age group fields: {', '.join(valid_group_fields)}")
        else:
            fields = [population_field, "near_park"]
            arcpy.AddMessage(f"→ Using population field: {population_field}")
    else:
        fields = ["near_park"]
        arcpy.AddMessage("→ No population data found – switching to entrance count mode.")

    # Mark points within accessible area
    arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN", accessibility_fc, selection_type="NEW_SELECTION")
    arcpy.management.CalculateField("output_layer_temp", "near_park", 1, "PYTHON3")
    arcpy.management.SelectLayerByAttribute("output_layer_temp", "CLEAR_SELECTION")

    # Prepare output districts layer
    arcpy.management.CopyFeatures(districts_fc, output_districts_fc)
    arcpy.management.MakeFeatureLayer(output_districts_fc, "district_layer")

    if "near_park_district" not in [f.name for f in arcpy.ListFields(output_districts_fc)]:
        arcpy.management.AddField(output_districts_fc, "near_park_district", "SHORT")

    # Initialize statistics
    area_pcts = []
    district_names = []
    txt_lines = []
    csv_lines = ["District,Entrances,AreaCoveredPct"]
    total_entrances_all = 0

    # Loop through districts and compute statistics
    with arcpy.da.UpdateCursor(output_districts_fc, [district_field, "SHAPE@", "near_park_district", "Shape_Area"]) as cursor:
        for name, geom, flag, district_area in cursor:
            arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN", geom, selection_type="NEW_SELECTION")

            count_total = 0
            count_accessible = 0

            with arcpy.da.SearchCursor("output_layer_temp", fields) as p_cursor:
                for row in p_cursor:
                    if use_population_data:
                        if valid_group_fields:
                            group_sum = sum(row[i] for i in range(len(valid_group_fields)))
                            count_total += group_sum
                            if row[-1] == 1:
                                count_accessible += group_sum
                        else:
                            count_total += row[0]
                            if row[1] == 1:
                                count_accessible += row[0]
                    else:
                        count_total += 1
                        if row[0] == 1:
                            count_accessible += 1

            total_entrances_all += count_total

            arcpy.analysis.Clip(accessibility_fc, geom, access_area_clip)
            accessible_geom_area = sum(row[0] for row in arcpy.da.SearchCursor(access_area_clip, ["SHAPE@AREA"]))
            area_pct = round((accessible_geom_area / district_area) * 100, 2) if district_area > 0 else 0

            area_pcts.append(area_pct)
            district_names.append(name)

            msg = f"{name:<20} entrances: {count_total:<6} | area covered: {area_pct:>5}%"
            arcpy.AddMessage(msg)
            txt_lines.append(msg)
            csv_lines.append(f"{name},{count_total},{area_pct}")

            cursor.updateRow((name, geom, 1 if count_accessible > 0 else 0, district_area))

    # Summary outputs
    arcpy.AddMessage("")
    arcpy.AddMessage("DISTRICT AREA COVERAGE SUMMARY")
    arcpy.AddMessage("-" * 80)

    if area_pcts:
        max_area = max(area_pcts)
        min_area = min(area_pcts)
        avg_area = round(sum(area_pcts) / len(area_pcts), 2)
        best_name = district_names[area_pcts.index(max_area)]
        worst_name = district_names[area_pcts.index(min_area)]

        arcpy.AddMessage(f"→ Best coverage:    {max_area}% ({best_name})")
        arcpy.AddMessage(f"→ Worst coverage:   {min_area}% ({worst_name})")
        arcpy.AddMessage(f"→ Average coverage: {avg_area}%")
        arcpy.AddMessage(f"→ Total entrances:  {total_entrances_all}")

        txt_lines.append("")
        txt_lines.append("COVERAGE SUMMARY")
        txt_lines.append(f"Best:   {best_name} ({max_area}%)")
        txt_lines.append(f"Worst:  {worst_name} ({min_area}%)")
        txt_lines.append(f"Average: {avg_area}%")
        txt_lines.append(f"Total entrances: {total_entrances_all}")
    else:
        arcpy.AddMessage("→ No area data available.")

    # Save results to TXT and CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.txt")
    csv_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.csv")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    arcpy.AddMessage("")
    arcpy.AddMessage("Exported summary:")
    arcpy.AddMessage(f"→ TXT:  {txt_path}")
    arcpy.AddMessage(f"→ CSV:  {csv_path}")

    # Final footer
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS DONE       ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

#------------------------------------
# Script entry point
#------------------------------------
if __name__ == "__main__":
    accessibility_fc   = arcpy.GetParameterAsText(0)
    districts_fc       = arcpy.GetParameterAsText(1)
    district_field     = arcpy.GetParameterAsText(2)
    input_fc           = arcpy.GetParameterAsText(3)
    population_field   = arcpy.GetParameterAsText(4)
    group_fields_raw   = arcpy.GetParameterAsText(5)
    output_gdb         = arcpy.GetParameterAsText(6)
    distance_label     = arcpy.GetParameterAsText(7)

    analyze_accessibility(accessibility_fc, input_fc, population_field,
                          group_fields_raw, output_gdb, distance_label,
                          districts_fc, district_field)

    del accessibility_fc, input_fc, population_field, group_fields_raw
    del output_gdb, distance_label, districts_fc, district_field
    # Clean up variables
