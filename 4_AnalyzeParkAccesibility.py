# ------------------------------------
# Name: 4_AnalyzeParkAccessibility.py
# Purpose: This script analyzes the accessibility of green space for each city district.
# ------------------------------------
import arcpy
import os
import sys
import csv
from datetime import datetime

# ------------------------------------
# Function to validate coordinate system consistency
# ------------------------------------
def validate_crs_consistency(layers, layer_names):
    """
    Validates that all input layers use the same coordinate system.
    Returns the common spatial reference if consistent, otherwise raises an error.
    """
    if not layers or len(layers) < 2:
        return None
    
    spatial_refs = []
    for i, layer in enumerate(layers):
        if not arcpy.Exists(layer):
            continue
        try:
            desc = arcpy.Describe(layer)
            sr = desc.spatialReference
            if sr:
                spatial_refs.append((sr, layer_names[i] if i < len(layer_names) else f"Layer {i+1}"))
        except Exception as e:
            arcpy.AddWarning(f"Could not read spatial reference from {layer}: {e}")
            continue
    
    if not spatial_refs:
        return None
    
    reference_sr, reference_name = spatial_refs[0]
    
    # Compare the spatial reference of each layer to the first one.
    for sr, name in spatial_refs[1:]:
        if sr.factoryCode != reference_sr.factoryCode:
            arcpy.AddError(
                f"Coordinate system mismatch detected!\n"
                f"  {reference_name}: {reference_sr.name} (EPSG: {reference_sr.factoryCode})\n"
                f"  {name}: {sr.name} (EPSG: {sr.factoryCode})\n"
                f"All input layers must use the same coordinate system for correct analysis results."
            )
            raise arcpy.ExecuteError("Coordinate system mismatch between input layers.")
    
    return reference_sr

# ------------------------------------
# Main analysis function
# ------------------------------------
def analyze_accessibility(accessibility_fc, input_fc, population_field, group_fields_raw,
                          output_gdb, distance_label, districts_fc, district_field, area_field=None):

    arcpy.env.overwriteOutput = True

    # --- Define output paths ---
    suffix = f"{distance_label}m"
    output_points_fc = os.path.join(output_gdb, f"points_accessibility_{suffix}")
    output_districts_fc = os.path.join(output_gdb, f"districts_accessibility_{suffix}")
    output_folder = os.path.dirname(output_gdb)

    arcpy.AddMessage("\n===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS START      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage(f"Walking distance threshold: {distance_label} m")
    arcpy.AddMessage("---------------------------------------------------")

    # --- Validate inputs ---
    for fc in [accessibility_fc, input_fc, districts_fc]:
        if not arcpy.Exists(fc):
            raise arcpy.ExecuteError(f"Input layer '{fc}' does not exist.")

    if not output_gdb or not output_gdb.lower().endswith(".gdb"):
        raise arcpy.ExecuteError("Invalid output geodatabase. Must be a File Geodatabase (.gdb).")
    
    # --- Validate coordinate systems ---
    validate_crs_consistency(
        [accessibility_fc, input_fc, districts_fc],
        ["Accessibility layer", "Input points layer", "Districts layer"]
    )
    arcpy.AddMessage("Coordinate systems validated.")

    # --- Determine accessible points using Spatial Join ---
    if not arcpy.Exists(output_points_fc):
        arcpy.AddMessage(f"Creating points accessibility layer: {output_points_fc}")
        arcpy.analysis.SpatialJoin(
            target_features=input_fc, join_features=accessibility_fc,
            out_feature_class=output_points_fc, join_type="KEEP_ALL", match_option="INTERSECT"
        )
    else:
        arcpy.AddMessage(f"Using existing points accessibility layer: {output_points_fc}")

    # --- Mark points inside the accessibility area ---
    arcpy.management.MakeFeatureLayer(output_points_fc, "output_layer_temp")
    if "near_park" not in [f.name for f in arcpy.ListFields(output_points_fc)]:
        arcpy.management.AddField(output_points_fc, "near_park", "SHORT")
    arcpy.management.SelectLayerByLocation("output_layer_temp", "WITHIN", accessibility_fc)
    arcpy.management.CalculateField("output_layer_temp", "near_park", 1, "PYTHON3")
    arcpy.management.SelectLayerByAttribute("output_layer_temp", "CLEAR_SELECTION")

    # --- Prepare a copy of the districts layer for results ---
    arcpy.management.CopyFeatures(districts_fc, output_districts_fc)

    # --- Find or calculate the area for each district ---
    district_fields = [f.name for f in arcpy.ListFields(output_districts_fc)]
    area_field_name = None
    common_area_names = ["Shape_Area", "SHAPE_Area", "Area"]
    if area_field and area_field.strip() in district_fields:
        area_field_name = area_field.strip()
    else:
        for name in common_area_names:
            if name in district_fields:
                area_field_name = name
                break
    if not area_field_name:
        area_field_name = "Shape_Area"
        arcpy.management.AddField(output_districts_fc, area_field_name, "DOUBLE")
        arcpy.management.CalculateGeometryAttributes(output_districts_fc, [[area_field_name, "AREA"]], area_unit="SQUARE_METERS")
    arcpy.AddMessage(f"Using '{area_field_name}' as the district area field.")

    # --- Optimized Analysis Workflow ---
    temp_layers = []
    try:
        # Create a layer of only accessible points.
        accessible_points_lyr = "accessible_points_lyr"
        arcpy.management.MakeFeatureLayer(output_points_fc, accessible_points_lyr, "near_park = 1")
        temp_layers.append(accessible_points_lyr)
        
        # Determine if population data is available for the analysis.
        existing_fields = [f.name for f in arcpy.ListFields(output_points_fc)]
        has_population_field = population_field in existing_fields
        sum_fields = [[population_field, "SUM"]] if has_population_field else []

        # --- 1. Summarize total and accessible points/population per district ---
        arcpy.AddMessage("Summarizing points and population within districts...")
        summary_total = os.path.join(output_gdb, f"summary_total_{suffix}")
        summary_accessible = os.path.join(output_gdb, f"summary_accessible_{suffix}")
        temp_layers.extend([summary_total, summary_accessible])
        
        arcpy.analysis.SummarizeWithin(districts_fc, output_points_fc, summary_total, "KEEP_ALL", sum_fields, group_field=district_field)
        arcpy.analysis.SummarizeWithin(districts_fc, accessible_points_lyr, summary_accessible, "KEEP_ALL", sum_fields, group_field=district_field)

        # --- 2. Calculate the accessible area within each district ---
        arcpy.AddMessage("Calculating accessible area per district...")
        intersect_result = os.path.join(output_gdb, f"intersect_area_{suffix}")
        temp_layers.append(intersect_result)
        arcpy.analysis.Intersect([districts_fc, accessibility_fc], intersect_result)
        arcpy.management.AddField(intersect_result, "AccessibleArea", "DOUBLE")
        arcpy.management.CalculateGeometryAttributes(intersect_result, [["AccessibleArea", "AREA"]], area_unit="SQUARE_METERS")
        
        # --- 3. Join all summarized results to the output districts layer ---
        arcpy.AddMessage("Joining results to districts layer...")
        arcpy.management.JoinField(output_districts_fc, district_field, summary_total, district_field, ["Point_Count"] + ([f"Sum_{population_field}"] if has_population_field else []))
        arcpy.management.JoinField(output_districts_fc, district_field, summary_accessible, district_field, ["Point_Count"] + ([f"Sum_{population_field}"] if has_population_field else []))
        arcpy.management.JoinField(output_districts_fc, district_field, intersect_result, district_field, ["AccessibleArea"])

        # --- 4. Rename fields and calculate final percentages ---
        arcpy.AddMessage("Calculating final statistics...")
        field_mappings = {
            "Point_Count": "Total_Points", "Point_Count_1": "Accessible_Points",
            f"Sum_{population_field}": "Total_Population", f"Sum_{population_field}_1": "Accessible_Population"
        }
        for old_name, new_name in field_mappings.items():
            if arcpy.ListFields(output_districts_fc, old_name):
                arcpy.management.AlterField(output_districts_fc, old_name, new_name, new_name)
        
        arcpy.management.AddField(output_districts_fc, "Area_Covered_Percent", "DOUBLE")
        arcpy.management.CalculateField(output_districts_fc, "Area_Covered_Percent", f"(!AccessibleArea! / !{area_field_name}!) * 100 if !{area_field_name}! > 0 else 0", "PYTHON3")

        # --- 5. Generate Text and CSV Reports ---
        arcpy.AddMessage("Generating reports...")
        report_fields = [district_field, "Area_Covered_Percent", "Total_Points", "Accessible_Points"]
        if has_population_field:
            report_fields += ["Total_Population", "Accessible_Population"]
        
        txt_lines = [f"PARK ACCESSIBILITY ANALYSIS ({distance_label}m)", "="*60]
        csv_lines = []
        csv_header = ["District", "Area_Covered_Percent"] + (["Population_Accessible"] if has_population_field else ["Points_Accessible"])

        with arcpy.da.SearchCursor(output_districts_fc, [f for f in report_fields if arcpy.ListFields(output_districts_fc, f)]) as cursor:
            for row in cursor:
                row_dict = dict(zip(cursor.fields, row))
                name = row_dict.get(district_field, "N/A")
                area_pct = row_dict.get("Area_Covered_Percent", 0) or 0
                
                txt_lines.append(f"\n--- {name} ---")
                txt_lines.append(f"Area Covered: {area_pct:.2f} %")
                
                if has_population_field:
                    total_pop = row_dict.get("Total_Population", 0) or 0
                    access_pop = row_dict.get("Accessible_Population", 0) or 0
                    txt_lines.append(f"Population: {int(access_pop)} / {int(total_pop)} accessible")
                    csv_lines.append([name, area_pct, access_pop])
                else:
                    total_pts = row_dict.get("Total_Points", 0) or 0
                    access_pts = row_dict.get("Accessible_Points", 0) or 0
                    txt_lines.append(f"Points: {int(access_pts)} / {int(total_pts)} accessible")
                    csv_lines.append([name, area_pct, access_pts])

        # --- Save report files ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        txt_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.txt")
        csv_path = os.path.join(output_folder, f"accessibility_summary_{suffix}_{timestamp}.csv")

        with open(txt_path, "w", encoding="utf-8") as f: f.write("\n".join(txt_lines))
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            writer.writerows(csv_lines)
            
        arcpy.AddMessage(f"TXT Report: {txt_path}")
        arcpy.AddMessage(f"CSV Report: {csv_path}")

    finally:
        # --- Final cleanup ---
        arcpy.AddMessage("Cleaning up temporary layers...")
        for layer in temp_layers + ["output_layer_temp", "district_layer"]:
            if arcpy.Exists(layer):
                arcpy.management.Delete(layer)

    arcpy.AddMessage("\n===================================================")
    arcpy.AddMessage("===      PARK ACCESSIBILITY ANALYSIS DONE      ===")
    arcpy.AddMessage("===================================================")

# ------------------------------------
# Script entry point
# ------------------------------------
if __name__ == "__main__":
    # --- Get parameters from ArcGIS tool ---
    accessibility_fc   = arcpy.GetParameterAsText(0)
    districts_fc       = arcpy.GetParameterAsText(1)
    district_field     = arcpy.GetParameterAsText(2)
    input_fc           = arcpy.GetParameterAsText(3)
    population_field   = arcpy.GetParameterAsText(4)
    group_fields_raw   = arcpy.GetParameterAsText(5)
    output_gdb         = arcpy.GetParameterAsText(6)
    distance_label     = arcpy.GetParameterAsText(7)
    area_field         = arcpy.GetParameterAsText(8) if arcpy.GetParameterCount() > 8 else None

    analyze_accessibility(accessibility_fc, input_fc, population_field,
                          group_fields_raw, output_gdb, distance_label,
                          districts_fc, district_field, area_field)

# Author: Petr MIKESKA
# Bachelor thesis (2025)
