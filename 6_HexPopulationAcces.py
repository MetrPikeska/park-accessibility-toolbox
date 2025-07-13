# ------------------------------------
# Name: 6_HexPopulationAcces.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script calculates statistics for each hexagon based on address points,
# either summing population or counting address points if no population field is specified.
# Optionally flags hexagons above a defined accessibility threshold.
# ------------------------------------

import arcpy
import sys

# ------------------------------------
# General settings
# ------------------------------------
arcpy.env.overwriteOutput = True

# ------------------------------------
# Input parameters
# ------------------------------------
hex_layer        = arcpy.GetParameterAsText(0)  # Input hexagon layer
pop_points_input = arcpy.GetParameterAsText(1)  # Input address or population points
access_polygon   = arcpy.GetParameterAsText(2)  # Accessibility polygon
pop_field        = arcpy.GetParameterAsText(3)  # Population field (optional)
output_hex_layer = arcpy.GetParameterAsText(4)  # Output hexagon layer
ratio_threshold  = float(arcpy.GetParameterAsText(5) or 0)  # Optional threshold (%)

# ------------------------------------
# Temporary in-memory layers
# ------------------------------------
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
arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Convert multipoints to single points if needed
# ------------------------------------
desc = arcpy.Describe(pop_points_input)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting Multipoint to Singlepoint...")
    arcpy.MultipartToSinglepart_management(pop_points_input, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_input, points_single)

# ------------------------------------
# Spatial join: address points + accessibility polygon
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

# ------------------------------------
# Add access flag (1 = accessible, 0 = not accessible)
# ------------------------------------
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)

# ------------------------------------
# Prepare hexagon copy with needed fields
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
# Make feature layer from points for selection
# ------------------------------------
arcpy.MakeFeatureLayer_management(points_flagged, "points_lyr")

# ------------------------------------
# Main loop: Calculate stats for each hexagon
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

        total_pop = 0
        access_pop = 0
        count_with = 0
        count_without = 0

        if pop_field:
            with arcpy.da.SearchCursor("points_lyr", ["has_access", pop_field]) as point_cursor:
                for has_access, value in point_cursor:
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
            with arcpy.da.SearchCursor("points_lyr", ["has_access"]) as point_cursor:
                for (has_access,) in point_cursor:
                    total_pop += 1
                    if has_access == 1:
                        access_pop += 1
                        count_with += 1
                    else:
                        count_without += 1

        ratio = (access_pop / total_pop) * 100 if total_pop > 0 else 0

        row[2] = total_pop
        row[3] = access_pop
        row[4] = ratio
        row[5] = count_with
        row[6] = count_without
        row[7] = 1 if ratio_threshold > 0 and ratio >= ratio_threshold else 0 if ratio_threshold > 0 else None
        cursor.updateRow(row)

# ------------------------------------
# Save output and clean up
# ------------------------------------
arcpy.AddMessage("Saving output to final feature class...")
arcpy.CopyFeatures_management(hex_copy, output_hex_layer)

arcpy.Delete_management(points_single)
arcpy.Delete_management(points_flagged)
arcpy.Delete_management(hex_copy)
arcpy.Delete_management("points_lyr")

# ------------------------------------
# Final footer
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("→ Final output:")
arcpy.AddMessage(f"{output_hex_layer}")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===           HEXAGON GRID COMPLETED           ===")
arcpy.AddMessage("===================================================")

# ------------------------------------
# Clear memory
# ------------------------------------
del hex_layer, pop_points_input, access_polygon, pop_field, output_hex_layer, ratio_threshold
del points_single, points_flagged, hex_copy, fields, needed_fields
