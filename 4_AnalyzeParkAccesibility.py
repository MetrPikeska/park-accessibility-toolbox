# ------------------------------------
# Name: 4_AnalyzeParkAccessibility.py
# Purpose: Analyze accessibility of urban green areas for city districts
# Author: Petr MIKESKA
# Bachelor thesis (2025)
# ------------------------------------

import arcpy
import os
import csv
from datetime import datetime

arcpy.env.overwriteOutput = True


# ------------------------------------
# CRS validation
# ------------------------------------
def validate_crs_consistency(layers, names):
    srs = []
    for lyr, name in zip(layers, names):
        if not arcpy.Exists(lyr):
            continue
        desc = arcpy.Describe(lyr)
        if desc.spatialReference:
            srs.append((desc.spatialReference, name))

    if not srs:
        return

    ref_sr, ref_name = srs[0]
    for sr, name in srs[1:]:
        if sr.factoryCode != ref_sr.factoryCode:
            raise arcpy.ExecuteError(
                f"Coordinate system mismatch:\n"
                f"{ref_name}: {ref_sr.name} (EPSG:{ref_sr.factoryCode})\n"
                f"{name}: {sr.name} (EPSG:{sr.factoryCode})"
            )


# ------------------------------------
# Main analysis
# ------------------------------------
def analyze_accessibility(
    accessibility_fc,
    districts_fc,
    district_field,
    input_points_fc,
    population_field,
    group_fields_raw,
    output_gdb,
    distance_label,
    area_field=None
):

    suffix = f"{distance_label}m"
    output_folder = os.path.dirname(output_gdb)

    summary_total = os.path.join(output_gdb, f"summary_total_{suffix}")
    summary_accessible = os.path.join(output_gdb, f"summary_accessible_{suffix}")
    accessible_points = os.path.join(output_gdb, f"accessible_points_{suffix}")
    intersect_area = os.path.join(output_gdb, f"accessible_area_{suffix}")

    arcpy.AddMessage("\n===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS START      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage(f"Walking distance threshold: {distance_label} m")
    arcpy.AddMessage("---------------------------------------------------")

    # --- Validate inputs ---
    for fc in [accessibility_fc, districts_fc, input_points_fc]:
        if not arcpy.Exists(fc):
            raise arcpy.ExecuteError(f"Missing input layer: {fc}")

    if not output_gdb.lower().endswith(".gdb"):
        raise arcpy.ExecuteError("Output must be a File Geodatabase (.gdb)")

    validate_crs_consistency(
        [accessibility_fc, districts_fc, input_points_fc],
        ["Accessibility", "Districts", "Input points"]
    )
    arcpy.AddMessage("Coordinate systems validated.")

    # --- Prepare fields ---
    group_fields = [f.strip() for f in group_fields_raw.split(";") if f.strip()] if group_fields_raw else []
    sum_fields = [[population_field, "SUM"]]
    for f in group_fields:
        sum_fields.append([f, "SUM"])

    # ------------------------------------
    # 1) TOTAL population (ALL address points)
    # ------------------------------------
    arcpy.AddMessage("Summarizing TOTAL population...")
    arcpy.analysis.SummarizeWithin(
        in_polygons=districts_fc,
        in_sum_features=input_points_fc,
        out_feature_class=summary_total,
        keep_all_polygons="KEEP_ALL",
        sum_fields=sum_fields,
        group_field=district_field
    )

    # ------------------------------------
    # 2) ACCESSIBLE population (points ∩ service areas)
    # ------------------------------------
    arcpy.AddMessage("Extracting ACCESSIBLE address points...")
    arcpy.analysis.Intersect(
        [input_points_fc, accessibility_fc],
        accessible_points
    )

    arcpy.AddMessage("Summarizing ACCESSIBLE population...")
    arcpy.analysis.SummarizeWithin(
        in_polygons=districts_fc,
        in_sum_features=accessible_points,
        out_feature_class=summary_accessible,
        keep_all_polygons="KEEP_ALL",
        sum_fields=sum_fields,
        group_field=district_field
    )

    # ------------------------------------
    # 3) Accessible area per district
    # ------------------------------------
    arcpy.AddMessage("Calculating accessible area...")
    arcpy.analysis.Intersect(
        [districts_fc, accessibility_fc],
        intersect_area
    )
    arcpy.management.AddField(intersect_area, "AccessibleArea", "DOUBLE")
    arcpy.management.CalculateGeometryAttributes(
        intersect_area,
        [["AccessibleArea", "AREA"]],
        area_unit="SQUARE_METERS"
    )

    # ------------------------------------
    # 4) Join results
    # ------------------------------------
    arcpy.AddMessage("Joining results...")
    result_fc = os.path.join(output_gdb, f"districts_accessibility_{suffix}")
    arcpy.management.CopyFeatures(districts_fc, result_fc)

    arcpy.management.JoinField(
        result_fc, district_field,
        summary_total, district_field
    )
    arcpy.management.JoinField(
        result_fc, district_field,
        summary_accessible, district_field
    )
    arcpy.management.JoinField(
        result_fc, district_field,
        intersect_area, district_field,
        ["AccessibleArea"]
    )

    # --- Area field ---
    if not area_field or area_field not in [f.name for f in arcpy.ListFields(result_fc)]:
        area_field = "Shape_Area"

    arcpy.management.AddField(result_fc, "Area_Covered_Percent", "DOUBLE")
    arcpy.management.CalculateField(
        result_fc,
        "Area_Covered_Percent",
        f"(!AccessibleArea! / !{area_field}!) * 100 if !{area_field}! > 0 else 0",
        "PYTHON3"
    )

    # ------------------------------------
    # 5) Report
    # ------------------------------------
    arcpy.AddMessage("Generating report...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.txt")
    csv_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.csv")

    fields = [district_field, "Area_Covered_Percent"]
    fields += [f"sum_{population_field}", f"sum_{population_field}_1"]
    for f in group_fields:
        fields += [f"sum_{f}", f"sum_{f}_1"]

    header = (
        f"{'District':<25} | {'Area %':>8} | {'Population %':>12} | "
        + " | ".join([f"{f:>12} %" for f in group_fields])
        + " |"
    )

    with open(txt_path, "w", encoding="utf-8") as txt, \
         open(csv_path, "w", encoding="utf-8", newline="") as csvf:

        writer = csv.writer(csvf)
        writer.writerow(["District", "Area %", "Population %"] + group_fields)

        txt.write(header + "\n")
        txt.write("-" * len(header) + "\n")

        with arcpy.da.SearchCursor(result_fc, fields) as cursor:
            for row in cursor:
                name = row[0]
                area_pct = row[1] or 0

                total_pop = row[2] or 0
                acc_pop = row[3] or 0
                pop_pct = (acc_pop / total_pop * 100) if total_pop > 0 else 0

                idx = 4
                group_pcts = []
                for _ in group_fields:
                    t = row[idx] or 0
                    a = row[idx + 1] or 0
                    pct = (a / t * 100) if t > 0 else 0
                    group_pcts.append(pct)
                    idx += 2

                txt.write(
                    f"{name:<25} | {area_pct:8.2f} | {pop_pct:12.1f} | "
                    + " | ".join([f"{p:12.1f}" for p in group_pcts])
                    + " |\n"
                )

                writer.writerow([name, area_pct, pop_pct] + group_pcts)

    arcpy.AddMessage(f"TXT Report: {txt_path}")
    arcpy.AddMessage(f"CSV Report: {csv_path}")

    arcpy.AddMessage("\n===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS DONE      ===")
    arcpy.AddMessage("===================================================")


# ------------------------------------
# Entry point
# ------------------------------------
if __name__ == "__main__":

    accessibility_fc = arcpy.GetParameterAsText(0)
    districts_fc     = arcpy.GetParameterAsText(1)
    district_field   = arcpy.GetParameterAsText(2)
    input_points_fc  = arcpy.GetParameterAsText(3)
    population_field = arcpy.GetParameterAsText(4)
    group_fields_raw = arcpy.GetParameterAsText(5)
    output_gdb       = arcpy.GetParameterAsText(6)
    distance_label   = arcpy.GetParameterAsText(7)

    area_field = None
    if arcpy.GetParameterCount() > 8:
        area_field = arcpy.GetParameterAsText(8)

    analyze_accessibility(
        accessibility_fc,
        districts_fc,
        district_field,
        input_points_fc,
        population_field,
        group_fields_raw,
        output_gdb,
        distance_label,
        area_field
    )
