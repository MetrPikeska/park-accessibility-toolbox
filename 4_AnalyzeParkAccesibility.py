# ------------------------------------
# Name: 4_AnalyzeParkAccessibility.py
# This script analyzes accessibility of green space within a defined walking distance for each city district.
# ------------------------------------

import arcpy
import os
from datetime import datetime

def analyze_accessibility(accessibility_fc, input_fc, population_field, group_fields_raw,
                          output_gdb, distance_label, districts_fc, district_field):
    arcpy.env.overwriteOutput = True

    suffix = f"{distance_label}m"
    output_points_fc = os.path.join(output_gdb, f"points_accessibility_{suffix}")
    output_districts_fc = os.path.join(output_gdb, f"districts_accessibility_{suffix}")
    access_area_clip = os.path.join("in_memory", f"access_area_clip_{suffix}")
    output_folder = os.path.dirname(output_gdb)

    # Header
    arcpy.AddMessage("")
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS START      ===")
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage(f"Walking distance threshold: {distance_label} m")
    arcpy.AddMessage("-" * 60)

    # Validate inputs
    for fc in [accessibility_fc, input_fc, districts_fc]:
        if not arcpy.Exists(fc):
            arcpy.AddError(f"❌ Input layer '{fc}' does NOT exist.")
            return
    if not output_gdb:
        arcpy.AddError("❌ Output geodatabase not set.")
        return

    # Prepare points
    arcpy.management.MakeFeatureLayer(input_fc, "input_layer_temp")
    arcpy.management.CopyFeatures("input_layer_temp", output_points_fc)
    arcpy.management.MakeFeatureLayer(output_points_fc, "output_layer_temp")

    # Add near_park field if missing
    if "near_park" not in [f.name for f in arcpy.ListFields(output_points_fc)]:
        arcpy.management.AddField(output_points_fc, "near_park", "SHORT")

    # Parse population fields
    group_fields = [f.strip() for f in group_fields_raw.split(";") if f.strip()] if group_fields_raw else []
    existing_fields = [f.name for f in arcpy.ListFields(output_points_fc)]
    valid_group_fields = [f for f in group_fields if f in existing_fields]
    has_population_field = population_field in existing_fields
    use_population_data = bool(valid_group_fields or has_population_field)

    # Dynamická terminologie a legenda
    if has_population_field or valid_group_fields:
        total_label = "Total population"
        accessible_label = "Accessible"
        csv_header = "District,PopulationAccessible,AreaCoveredPercent"
        legend_lines = [
            "- Total population = all people in district (if population data available)",
            "- Accessible = number of people within walking distance",
            "- Area covered = % of district area within walking distance"
        ]
    else:
        total_label = "Total points"
        accessible_label = "Accessible"
        csv_header = "District,PointsAccessible,AreaCoveredPercent"
        legend_lines = [
            "- Total points = all address locations in district (if no population data)",
            "- Accessible = number of address points within walking distance",
            "- Area covered = % of district area within walking distance"
        ]

    # Decide fields for analysis
    if use_population_data:
        if valid_group_fields:
            fields = valid_group_fields + ["near_park"]
            arcpy.AddMessage(f"→ Using age group fields: {', '.join(valid_group_fields)}")
        else:
            fields = [population_field, "near_park"]
            arcpy.AddMessage(f"→ Using population field: {population_field}")
    else:
        fields = ["near_park"]
        arcpy.AddMessage("→ No population data found – counting address points.")

    # === LEGEND AT START ===
    arcpy.AddMessage("")
    arcpy.AddMessage("Legend:")
    for line in legend_lines:
        arcpy.AddMessage(line)
    arcpy.AddMessage("-" * 60)

    # Mark points within accessibility polygon
    arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN", accessibility_fc, selection_type="NEW_SELECTION")
    arcpy.management.CalculateField("output_layer_temp", "near_park", 1, "PYTHON3")
    arcpy.management.SelectLayerByAttribute("output_layer_temp", "CLEAR_SELECTION")

    # Prepare district layer
    arcpy.management.CopyFeatures(districts_fc, output_districts_fc)
    arcpy.management.MakeFeatureLayer(output_districts_fc, "district_layer")
    if "near_park_district" not in [f.name for f in arcpy.ListFields(output_districts_fc)]:
        arcpy.management.AddField(output_districts_fc, "near_park_district", "SHORT")

    # Stats containers
    area_pcts, district_names = [], []
    txt_lines = []

    # HEADER FOR TXT
    txt_lines.append("PARK ACCESSIBILITY ANALYSIS")
    txt_lines.append(f"Walking distance: {distance_label} m")
    txt_lines.append("")
    txt_lines.append("Legend:")
    txt_lines.extend(legend_lines)
    txt_lines.append("-" * 60)
    txt_lines.append("")

    csv_lines = [csv_header]
    total_entrances_all = 0

    # Process each district
    with arcpy.da.UpdateCursor(output_districts_fc, [district_field, "SHAPE@", "near_park_district", "Shape_Area"]) as cursor:
        for name, geom, flag, district_area in cursor:
            arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN", geom, selection_type="NEW_SELECTION")

            count_total = 0
            count_accessible = 0
            group_totals = {f: 0 for f in valid_group_fields}
            group_accesses = {f: 0 for f in valid_group_fields}

            with arcpy.da.SearchCursor("output_layer_temp", fields) as p_cursor:
                for row in p_cursor:
                    if use_population_data:
                        if valid_group_fields:
                            for i, f in enumerate(valid_group_fields):
                                group_totals[f] += row[i]
                                if row[-1] == 1:
                                    group_accesses[f] += row[i]
                            count_total += sum(row[:len(valid_group_fields)])
                            if row[-1] == 1:
                                count_accessible += sum(row[:len(valid_group_fields)])
                        else:
                            count_total += row[0]
                            if row[1] == 1:
                                count_accessible += row[0]
                    else:
                        count_total += 1
                        if row[0] == 1:
                            count_accessible += 1

            total_entrances_all += count_total

            # Clip accessibility area with district
            arcpy.analysis.Clip(accessibility_fc, geom, access_area_clip)
            accessible_geom_area = sum(r[0] for r in arcpy.da.SearchCursor(access_area_clip, ["SHAPE@AREA"]))
            area_pct = round((accessible_geom_area / district_area) * 100, 2) if district_area > 0 else 0
            area_pcts.append(area_pct)
            district_names.append(name)

            # --- FORMAT DISTRICT BLOCK ---
            block_header = "-" * 60
            block_title = f"{name}"
            block_summary = f"{total_label}: {int(count_total):<8} {accessible_label}: {int(count_accessible):<8} Area covered: {area_pct:6.2f} %"

            # Print to ArcGIS log
            arcpy.AddMessage(block_header)
            arcpy.AddMessage(block_title)
            arcpy.AddMessage(block_summary)

            # Append to TXT
            txt_lines.append(block_header)
            txt_lines.append(block_title)
            txt_lines.append(block_summary)

            # Age groups table (only if available)
            if valid_group_fields:
                age_header = f"{'Age group':<10} {'Accessible':>10} / {'Total':<10} {'Percent':>8}"
                age_sep = "-" * len(age_header)
                arcpy.AddMessage(age_header)
                arcpy.AddMessage(age_sep)
                txt_lines.append(age_header)
                txt_lines.append(age_sep)

                for f in valid_group_fields:
                    label = f.replace("sum_", "").replace("_", "-").replace("65-", "65+")
                    total = group_totals[f]
                    access = group_accesses[f]
                    pct = round(access / total * 100, 2) if total > 0 else 0.0
                    line = f"{label:<10} {int(access):>10} / {int(total):<10} {pct:>6.2f} %"
                    arcpy.AddMessage(line)
                    txt_lines.append(line)

            txt_lines.append("")  # empty line after each district

            # CSV simple
            csv_lines.append(f"{name},{count_total},{area_pct}")
            cursor.updateRow((name, geom, 1 if count_accessible > 0 else 0, district_area))

    # === SUMMARY SECTION ===
    txt_lines.append("-" * 60)
    txt_lines.append("DISTRICT AREA COVERAGE SUMMARY")
    txt_lines.append("-" * 60)

    arcpy.AddMessage("-" * 60)
    arcpy.AddMessage("DISTRICT AREA COVERAGE SUMMARY")
    arcpy.AddMessage("-" * 60)

    if area_pcts:
        max_area = max(area_pcts)
        min_area = min(area_pcts)
        avg_area = round(sum(area_pcts) / len(area_pcts), 2)
        best_name = district_names[area_pcts.index(max_area)]
        worst_name = district_names[area_pcts.index(min_area)]

        txt_lines.append(f"Best coverage : {max_area:.2f} % ({best_name})")
        txt_lines.append(f"Worst coverage: {min_area:.2f} % ({worst_name})")
        txt_lines.append(f"Average       : {avg_area:.2f} %")
        if has_population_field:
            txt_lines.append(f"Total population (all districts): {int(total_entrances_all)}")
        else:
            txt_lines.append(f"Total points (all districts): {int(total_entrances_all)}")

        arcpy.AddMessage(f"Best coverage : {max_area:.2f} % ({best_name})")
        arcpy.AddMessage(f"Worst coverage: {min_area:.2f} % ({worst_name})")
        arcpy.AddMessage(f"Average       : {avg_area:.2f} %")
        if has_population_field:
            arcpy.AddMessage(f"Total population (all districts): {int(total_entrances_all)}")
        else:
            arcpy.AddMessage(f"Total points (all districts): {int(total_entrances_all)}")
    else:
        txt_lines.append("No district area data available.")
        arcpy.AddMessage("No district area data available.")

    # === LEGEND AGAIN AT END ===
    txt_lines.append("")
    txt_lines.append("Legend:")
    txt_lines.extend(legend_lines)
    txt_lines.append("")
    txt_lines.append("=" * 60)
    txt_lines.append("===      PARK ACCESSIBILITY ANALYSIS DONE      ===")
    txt_lines.append("=" * 60)

    arcpy.AddMessage("")
    arcpy.AddMessage("Legend:")
    for line in legend_lines:
        arcpy.AddMessage(line)

    # Save TXT/CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.txt")
    csv_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.csv")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    arcpy.AddMessage("\nSummary exported:")
    arcpy.AddMessage(f"→ TXT:  {txt_path}")
    arcpy.AddMessage(f"→ CSV:  {csv_path}")
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS DONE      ===")
    arcpy.AddMessage("=" * 60)

# Entry point
def main():
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

if __name__ == "__main__":
    main()

# Author: Petr MIKESKA
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
