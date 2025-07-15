# ------------------------------------
# Name: 6_HexPopulationAcces.py
# This script calculates population/accessibility statistics for each hexagon 
# based on address points and an accessibility polygon.
# ------------------------------------

import arcpy
import sys

# Always overwrite outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Input parameters
# ------------------------------------
hex_layer        = arcpy.GetParameterAsText(0)  # Input hexagon layer
pop_points_input = arcpy.GetParameterAsText(1)  # Address/population points
access_polygon   = arcpy.GetParameterAsText(2)  # Accessibility polygon
pop_field        = arcpy.GetParameterAsText(3)  # Optional population field
output_hex_layer = arcpy.GetParameterAsText(4)  # Output hexagon layer
ratio_threshold  = float(arcpy.GetParameterAsText(5) or 0)  # Threshold %

# Temporary in-memory layers
points_single  = "in_memory\\points_single"
points_flagged = "in_memory\\points_with_access"
hex_copy       = "in_memory\\hex_copy"

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===   HEXAGON POPULATION ACCESSIBILITY START   ===")
arcpy.AddMessage("===================================================")

# ------------------------------------
# Convert multipoints if needed
# ------------------------------------
desc = arcpy.Describe(pop_points_input)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting Multipoint to Singlepoint...")
    arcpy.MultipartToSinglepart_management(pop_points_input, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_input, points_single)

# ------------------------------------
# Spatial join: points + accessibility polygon
# ------------------------------------
arcpy.AddMessage("Joining address points to accessibility polygon...")
arcpy.analysis.SpatialJoin(
    target_features=points_single,
    join_features=access_polygon,
    out_feature_class=points_flagged,
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    match_option="INTERSECT"
)

# Add access flag
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)

# ------------------------------------
# Prepare hexagon copy with required fields
# ------------------------------------
arcpy.CopyFeatures_management(hex_layer, hex_copy)
fields = [f.name for f in arcpy.ListFields(hex_copy)]
needed_fields = {
    "pop_total": "DOUBLE",
    "pop_access": "DOUBLE",
    "pop_ratio": "DOUBLE",
    "points_with_access": "LONG",
    "points_without_access": "LONG",
    "above_threshold": "SHORT"
}
for field, ftype in needed_fields.items():
    if field not in fields:
        arcpy.AddField_management(hex_copy, field, ftype)

# ------------------------------------
# Make layer from points
# ------------------------------------
arcpy.MakeFeatureLayer_management(points_flagged, "points_lyr")

# ------------------------------------
# Main loop: calculate stats for each hexagon
# ------------------------------------
arcpy.AddMessage("Processing hexagons...")
with arcpy.da.UpdateCursor(hex_copy, [
    "OBJECTID", "SHAPE@",
    "pop_total", "pop_access", "pop_ratio",
    "points_with_access", "points_without_access", "above_threshold"
]) as cursor:
    for row in cursor:
        geom = row[1]
        arcpy.SelectLayerByLocation_management("points_lyr", "WITHIN", geom, selection_type="NEW_SELECTION")

        total_pop, access_pop = 0, 0
        count_with, count_without = 0, 0

        # If population field is provided, sum it; otherwise just count points
        if pop_field:
            with arcpy.da.SearchCursor("points_lyr", ["has_access", pop_field]) as pc:
                for has_access, value in pc:
                    try:
                        value = float(value)
                    except:
                        continue
                    total_pop += value
                    if has_access == 1:
                        access_pop += value
                        count_with += 1
                    else:
                        count_without += 1
        else:
            with arcpy.da.SearchCursor("points_lyr", ["has_access"]) as pc:
                for (has_access,) in pc:
                    total_pop += 1
                    if has_access == 1:
                        access_pop += 1
                        count_with += 1
                    else:
                        count_without += 1

        ratio = (access_pop / total_pop) * 100 if total_pop > 0 else 0

        # Update row stats
        row[2] = total_pop
        row[3] = access_pop
        row[4] = ratio
        row[5] = count_with
        row[6] = count_without
        row[7] = 1 if ratio_threshold > 0 and ratio >= ratio_threshold else 0 if ratio_threshold > 0 else None
        cursor.updateRow(row)

# ------------------------------------
# Save output and clean temp
# ------------------------------------
arcpy.AddMessage("Saving output to final feature class...")
arcpy.CopyFeatures_management(hex_copy, output_hex_layer)

arcpy.Delete_management(points_single)
arcpy.Delete_management(points_flagged)
arcpy.Delete_management(hex_copy)
arcpy.Delete_management("points_lyr")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage(f"✔ Final output saved: {output_hex_layer}")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===    HEXAGON POPULATION ACCESSIBILITY DONE   ===")
arcpy.AddMessage("===================================================")

# Clean vars
del hex_layer, pop_points_input, access_polygon, pop_field, output_hex_layer, ratio_threshold
del points_single, points_flagged, hex_copy, fields, needed_fields

# Author: Petr MIKESKA
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
