#------------------------------------
# Name: 6_HexPopulationAcces.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script calculates population statistics for each hexagon, including total and accessible population,
# and number of entry points with or without access to urban green areas.
#------------------------------------

import arcpy
import sys

# General settings
arcpy.env.overwriteOutput = True

#------------------------------------
# Log basic info
#------------------------------------
# Input parameters
hex_layer           = arcpy.GetParameterAsText(0)    # Hexagon feature class
pop_points_input    = arcpy.GetParameterAsText(1)    # Address points
access_polygon      = arcpy.GetParameterAsText(2)    # Accessibility polygon
pop_field           = arcpy.GetParameterAsText(3)    # Field with population count (can be empty)
output_hex_layer    = arcpy.GetParameterAsText(4)    # Output feature class

# Temporary data paths
points_single       = "in_memory\\points_single"             # Flattened points if input is multipoint
points_flagged      = "in_memory\\points_with_access"        # Points with has_access field
hex_copy            = "in_memory\\hex_copy"                  # Copy of hex grid to store stats

#------------------------------------
# Prepare input data
#------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===     ACCESSIBILITY POINT GENERATION START    ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
arcpy.AddMessage("---------------------------------------------------")

# Convert Multipoint to Singlepoint if needed
desc = arcpy.Describe(pop_points_input)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting Multipoint to Singlepoint...")
    arcpy.MultipartToSinglepart_management(pop_points_input, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_input, points_single)

# Join address points with accessibility polygon
arcpy.AddMessage("Joining address points to accessibility polygon...")
arcpy.analysis.SpatialJoin(
    target_features=points_single,
    join_features=access_polygon,
    out_feature_class=points_flagged,
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    match_option="INTERSECT"
)

# Flag accessible points
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)

# Copy hex layer and prepare fields
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

# Make selectable layer from address points
arcpy.MakeFeatureLayer_management(points_flagged, "points_lyr")

#------------------------------------
# Loop over hexagons and calculate statistics
#------------------------------------
arcpy.AddMessage("Processing hexagons...")
with arcpy.da.UpdateCursor(hex_copy, [
    "OBJECTID", "SHAPE@",
    "pop_total", "pop_access", "pop_ratio",
    "points_with_access", "points_without_access"
]) as cursor:
    for row in cursor:
        oid        = row[0]
        geom       = row[1]

        # Select points inside the current hexagon
        arcpy.SelectLayerByLocation_management("points_lyr", "WITHIN", geom, selection_type="NEW_SELECTION")

        total_pop      = 0
        access_pop     = 0
        count_with     = 0
        count_without  = 0

        fields_to_read = ["has_access", pop_field] if pop_field else ["has_access"]
        with arcpy.da.SearchCursor("points_lyr", fields_to_read) as point_cursor:
            for point_row in point_cursor:
                has_access = point_row[0]
                value = 1 if not pop_field else point_row[1]
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

        ratio = (access_pop / total_pop) * 100 if total_pop > 0 else 0

        # Write statistics back to hexagon
        row[2] = total_pop
        row[3] = access_pop
        row[4] = ratio
        row[5] = count_with
        row[6] = count_without
        cursor.updateRow(row)

#------------------------------------
# Save results and cleanup
#------------------------------------
arcpy.AddMessage("Saving output...")
arcpy.CopyFeatures_management(hex_copy, output_hex_layer)

arcpy.Delete_management(points_single)
arcpy.Delete_management(points_flagged)
arcpy.Delete_management(hex_copy)
arcpy.Delete_management("points_lyr")

arcpy.AddMessage(f"✔ Done! Output saved to: {output_hex_layer}")

#------------------------------------
# Delete variables
#------------------------------------
del hex_layer, pop_points_input, access_polygon, pop_field, output_hex_layer
del points_single, points_flagged, hex_copy, fields, needed_fields
