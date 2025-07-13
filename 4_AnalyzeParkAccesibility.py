import arcpy
import os
from datetime import datetime

#------------------------------------
# Name: 4_AnalyzeParkAccessibility.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script analyzes accessibility of green space within a defined walking distance for each city district.
#------------------------------------


#------------------------------------
# Main analysis function
#------------------------------------
def analyze_accessibility(accessibility_fc, input_fc, population_field, group_fields_raw,
                          output_gdb, distance_label, districts_fc, district_field):
    arcpy.env.overwriteOutput = True  # Allow overwriting outputs

    # Prepare naming suffix
    distance_label = str(distance_label)
    suffix = f"{distance_label}m"

    # Define output feature class paths
    output_points_fc = os.path.join(output_gdb, f"points_accessibility_{suffix}")
    output_districts_fc = os.path.join(output_gdb, f"districts_accessibility_{suffix}")
    access_area_clip = os.path.join("in_memory", f"access_area_clip_{suffix}")
    output_folder = os.path.dirname(output_gdb)

    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===       PARK ACCESSIBILITY ANALYSIS START     ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
    arcpy.AddMessage(f"Methodology: A short walk to the park – {distance_label} meters to green space")
    arcpy.AddMessage("---------------------------------------------------")

    #------------------------------------
    # Log all input parameters
    #------------------------------------
    arcpy.AddMessage("INPUT PARAMETERS")
    arcpy.AddMessage(f"  - accessibility_fc: {accessibility_fc}")
    arcpy.AddMessage(f"  - input_fc:         {input_fc}")
    arcpy.AddMessage(f"  - population_field: {population_field}")
    arcpy.AddMessage(f"  - group_fields_raw: {group_fields_raw}")
    arcpy.AddMessage(f"  - output_gdb:       {output_gdb}")
    arcpy.AddMessage(f"  - distance_label:   {distance_label}")
    arcpy.AddMessage(f"  - districts_fc:     {districts_fc}")
    arcpy.AddMessage(f"  - district_field:   {district_field}")
    arcpy.AddMessage("---------------------------------------------------")


    #------------------------------------
    # Validate input data
    #------------------------------------
    for fc in [accessibility_fc, input_fc, districts_fc]:
        if not arcpy.Exists(fc):
            arcpy.AddError(f"ERROR: Input layer '{fc}' does not exist.")
            return
    if not output_gdb:
        arcpy.AddError("ERROR: Output geodatabase not set.")
        return

    #------------------------------------
    # Prepare input layers
    #------------------------------------
    arcpy.management.MakeFeatureLayer(input_fc, "input_layer_temp")
    arcpy.management.CopyFeatures("input_layer_temp", output_points_fc)
    arcpy.management.MakeFeatureLayer(output_points_fc, "output_layer_temp")

    if "near_park" not in [f.name for f in arcpy.ListFields(output_points_fc)]:
        arcpy.management.AddField(output_points_fc, "near_park", "SHORT")
    # Add field for accessibility

    # Parse group fields
    group_fields = [f.strip() for f in group_fields_raw.split(";") if f.strip()] if group_fields_raw else []
    existing_fields = [f.name for f in arcpy.ListFields(output_points_fc)]
    valid_group_fields = [f for f in group_fields if f in existing_fields]
    has_population_field = population_field in existing_fields
    use_population_data = bool(valid_group_fields or has_population_field)

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

    # Mark points within accessibility polygon
    arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN",
                                       accessibility_fc, selection_type="NEW_SELECTION")
    arcpy.management.CalculateField("output_layer_temp", "near_park", 1, "PYTHON3")
    arcpy.management.SelectLayerByAttribute("output_layer_temp", "CLEAR_SELECTION")

    # Prepare district layer
    arcpy.management.CopyFeatures(districts_fc, output_districts_fc)
    arcpy.management.MakeFeatureLayer(output_districts_fc, "district_layer")

    if "near_park_district" not in [f.name for f in arcpy.ListFields(output_districts_fc)]:
        arcpy.management.AddField(output_districts_fc, "near_park_district", "SHORT")

    #------------------------------------
    # Initialize statistics
    #------------------------------------
    area_pcts = []
    district_names = []
    txt_lines = []
    csv_lines = ["District,Entrances,AreaCoveredPct"]
    total_entrances_all = 0

    #------------------------------------
    # Process each district
    #------------------------------------
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

            arcpy.analysis.Clip(accessibility_fc, geom, access_area_clip)
            accessible_geom_area = sum(row[0] for row in arcpy.da.SearchCursor(access_area_clip, ["SHAPE@AREA"]))
            area_pct = round((accessible_geom_area / district_area) * 100, 2) if district_area > 0 else 0

            area_pcts.append(area_pct)
            district_names.append(name)

            # Output per district
            if valid_group_fields:
                header_msg = f"{name:<20} total: {int(count_total)}   with access: {int(count_accessible)}   ({area_pct:.2f}% area covered)"
                arcpy.AddMessage(header_msg)
                txt_lines.append(header_msg)
                for f in valid_group_fields:
                    label = f.replace("sum_", "Age ").replace("_", "-").replace("65-", "65+")
                    total = group_totals[f]
                    access = group_accesses[f]
                    pct = round(access / total * 100, 2) if total > 0 else 0.0
                    line = f"  - {label:<10}: {access} / {total}   | {pct:.2f}%"
                    arcpy.AddMessage(line)
                    txt_lines.append(line)
            else:
                if has_population_field:
                    msg = f"{name:<20} population: {int(count_total):<6} | area covered: {area_pct:>5.2f}%"
                else:
                    msg = f"{name:<20} entrances:  {int(count_total):<6} | area covered: {area_pct:>5.2f}%"
                arcpy.AddMessage(msg)
                txt_lines.append(msg)

            csv_lines.append(f"{name},{count_total},{area_pct}")
            cursor.updateRow((name, geom, 1 if count_accessible > 0 else 0, district_area))

    #------------------------------------
    # Summary outputs
    #------------------------------------
    arcpy.AddMessage("\nDISTRICT AREA COVERAGE SUMMARY")
    arcpy.AddMessage("" + "-" * 80)

    if area_pcts:
        max_area = max(area_pcts)
        min_area = min(area_pcts)
        avg_area = round(sum(area_pcts) / len(area_pcts), 2)
        best_name = district_names[area_pcts.index(max_area)]
        worst_name = district_names[area_pcts.index(min_area)]

        arcpy.AddMessage(f"→ Best coverage:    {max_area}% ({best_name})")
        arcpy.AddMessage(f"→ Worst coverage:   {min_area}% ({worst_name})")
        arcpy.AddMessage(f"→ Average coverage: {avg_area}%")

        if has_population_field:
            arcpy.AddMessage(f"→ Total population: {total_entrances_all}")
        else:
            arcpy.AddMessage(f"→ Total entrances:  {total_entrances_all}")

        txt_lines.extend(["", "COVERAGE SUMMARY",
                           f"Best:   {best_name} ({max_area}%)",
                           f"Worst:  {worst_name} ({min_area}%)",
                           f"Average: {avg_area}%"]
        )
        if has_population_field:
            txt_lines.append(f"Total population: {total_entrances_all}")
        else:
            txt_lines.append(f"Total entrances: {total_entrances_all}")
    else:
        arcpy.AddMessage("→ No area data available.")

    #------------------------------------
    # Save TXT and CSV outputs
    #------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.txt")
    csv_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.csv")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    arcpy.AddMessage("\nExported summary:")
    arcpy.AddMessage(f"→ TXT:  {txt_path}")
    arcpy.AddMessage(f"→ CSV:  {csv_path}")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS DONE       ===")
    arcpy.AddMessage("===================================================")

#------------------------------------
# Script entry point
#------------------------------------
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
