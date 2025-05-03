#------------------------------------
# Name: 6_HexPopulationAcces.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Modified by: Vojtěch Svoboda, 2025
# This script calculates statistics for each hexagon based on address points,
# either summing population or counting address points if no population field is specified.
#------------------------------------

import arcpy
import sys

arcpy.env.overwriteOutput = True

# Input parameters
hex_layer           = arcpy.GetParameterAsText(0)
pop_points_input    = arcpy.GetParameterAsText(1)
access_polygon      = arcpy.GetParameterAsText(2)
pop_field           = arcpy.GetParameterAsText(3)
output_hex_layer    = arcpy.GetParameterAsText(4)

# Temporary paths
points_single       = "in_memory\\points_single"
points_flagged      = "in_memory\\points_with_access"
hex_copy            = "in_memory\\hex_copy"

# Logging
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===     ACCESSIBILITY POINT GENERATION START    ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("Author: Petr Mikeska ")
arcpy.AddMessage("---------------------------------------------------")

# Convert multipoints to single if needed
desc = arcpy.Describe(pop_points_input)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting Multipoint to Singlepoint...")
    arcpy.MultipartToSinglepart_management(pop_points_input, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_input, points_single)

# Spatial join: address points + accessibility polygon
arcpy.AddMessage("Joining address points to accessibility polygon...")
arcpy.analysis.SpatialJoin(
    target_features=points_single,
    join_features=access_polygon,
    out_feature_class=points_flagged,
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    match_option="INTERSECT"
)

# Add binary access flag
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)

# Prepare hexagon grid
arcpy.CopyFeatures_management(hex_layer, hex_copy)
fields = [f.name for f in arcpy.ListFields(hex_copy)]
needed_fields = {
    "pop_total": "DOUBLE",
    "pop_access": "DOUBLE",
    "pop_ratio": "DOUBLE",
    "points_with_access": "LONG",
    "points_without_access": "LONG"
}
for f, typ in needed_fields.items():
    if f not in fields:
        arcpy.AddField_management(hex_copy, f, typ)

arcpy.MakeFeatureLayer_management(points_flagged, "points_lyr")

# Main loop per hexagon
arcpy.AddMessage("Processing hexagons...")
with arcpy.da.UpdateCursor(hex_copy, [
    "OBJECTID", "SHAPE@",
    "pop_total", "pop_access", "pop_ratio",
    "points_with_access", "points_without_access"
]) as cursor:
    for row in cursor:
        geom = row[1]
        arcpy.SelectLayerByLocation_management("points_lyr", "WITHIN", geom, selection_type="NEW_SELECTION")

        total_pop = 0
        access_pop = 0
        count_with = 0
        count_without = 0

        if pop_field:
            fields_to_read = ["has_access", pop_field]
            with arcpy.da.SearchCursor("points_lyr", fields_to_read) as point_cursor:
                for point_row in point_cursor:
                    has_access, value = point_row
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
                for point_row in point_cursor:
                    has_access = point_row[0]
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
        cursor.updateRow(row)

# Final output and cleanup
arcpy.AddMessage("Saving output...")
arcpy.CopyFeatures_management(hex_copy, output_hex_layer)

arcpy.Delete_management(points_single)
arcpy.Delete_management(points_flagged)
arcpy.Delete_management(hex_copy)
arcpy.Delete_management("points_lyr")

arcpy.AddMessage(f"✔ Done! Output saved to: {output_hex_layer}")

del hex_layer, pop_points_input, access_polygon, pop_field, output_hex_layer
del points_single, points_flagged, hex_copy, fields, needed_fields
