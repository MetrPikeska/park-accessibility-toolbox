# ------------------------------------
# Name: 6_HexPopulationAccess.py
# This script calculates population/accessibility statistics for each hexagon
# based on address points (original data) and a Service Area polygon (Tool 3 output).
# ------------------------------------
import arcpy
import sys

# Always overwrite outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Input parameters
# ------------------------------------
hex_layer        = arcpy.GetParameterAsText(0)  # Input hexagon layer (Tool 5 output)
pop_points_input = arcpy.GetParameterAsText(1)  # Address/population points (original data)
access_polygon   = arcpy.GetParameterAsText(2)  # Accessibility polygon (Tool 3 output)
pop_field        = arcpy.GetParameterAsText(3)  # Optional population field
output_hex_layer = arcpy.GetParameterAsText(4)  # Output hexagon layer
ratio_threshold  = float(arcpy.GetParameterAsText(5) or 0)  # Optional threshold %

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
arcpy.AddMessage(f"Input hexagons:        {hex_layer}")
arcpy.AddMessage(f"Address points:        {pop_points_input}")
arcpy.AddMessage(f"Accessibility polygon: {access_polygon}")
arcpy.AddMessage(f"Output hexagons:       {output_hex_layer}")
arcpy.AddMessage(f"Threshold:             {ratio_threshold} %")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate inputs
# ------------------------------------
if not arcpy.Exists(hex_layer):
    arcpy.AddError("The input hexagon layer does not exist. Please check the path or run Tool 5 first.")
    sys.exit(1)

if not arcpy.Exists(pop_points_input):
    arcpy.AddError("The address points layer does not exist. Please verify the dataset.")
    sys.exit(1)

if not arcpy.Exists(access_polygon):
    arcpy.AddError("The accessibility polygon (Service Area) does not exist. Please run Tool 3 first.")
    sys.exit(1)

# ------------------------------------
# Convert multipoints to singlepoints if needed
# ------------------------------------
desc = arcpy.Describe(pop_points_input)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting Multipoint features to individual Singlepoints...")
    arcpy.MultipartToSinglepart_management(pop_points_input, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_input, points_single)

# ------------------------------------
# Spatial join: points + accessibility polygon
# ------------------------------------
arcpy.AddMessage("Joining address points to the accessibility polygon (Service Area)...")
arcpy.analysis.SpatialJoin(
    target_features=points_single,
    join_features=access_polygon,
    out_feature_class=points_flagged,
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    match_option="INTERSECT"
)

# Add access flag: 1 = inside Service Area, 0 = outside
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)
arcpy.AddMessage("Address points have been flagged for accessibility (inside/outside Service Area).")

# ------------------------------------
# Prepare hexagon copy with required output fields
# ------------------------------------
arcpy.CopyFeatures_management(hex_layer, hex_copy)
fields = [f.name for f in arcpy.ListFields(hex_copy)]

# Decide which output fields are needed based on population availability
if pop_field:
    needed_fields = {
        "Total_Population": "DOUBLE",
        "Accessible_Population": "DOUBLE",
        "Accessibility_Percent": "DOUBLE",
        "Points_With_Access": "LONG",
        "Points_Without_Access": "LONG",
        "Above_Threshold": "SHORT"
    }
    arcpy.AddMessage("Population field detected – calculating number of residents per hexagon.")
else:
    needed_fields = {
        "Total_Points": "LONG",
        "Accessible_Points": "LONG",
        "Accessibility_Percent": "DOUBLE",
        "Points_With_Access": "LONG",
        "Points_Without_Access": "LONG",
        "Above_Threshold": "SHORT"
    }
    arcpy.AddMessage("No population field provided – counting only number of address points per hexagon.")

# Add missing fields to hexagons
for field, ftype in needed_fields.items():
    if field not in fields:
        arcpy.AddField_management(hex_copy, field, ftype)

# ------------------------------------
# Make layer from flagged points
# ------------------------------------
arcpy.MakeFeatureLayer_management(points_flagged, "points_lyr")

# ------------------------------------
# Main loop: calculate stats for each hexagon
# ------------------------------------
arcpy.AddMessage("Processing hexagons and calculating accessibility statistics...")
total_hex = int(arcpy.management.GetCount(hex_copy)[0])
processed = 0

with arcpy.da.UpdateCursor(hex_copy, ["OBJECTID", "SHAPE@"] + list(needed_fields.keys())) as cursor:
    for row in cursor:
        geom = row[1]
        arcpy.SelectLayerByLocation_management(
            "points_lyr", "WITHIN", geom, selection_type="NEW_SELECTION"
        )

        total_val, access_val = 0, 0
        count_with, count_without = 0, 0

        # If population field is provided → sum it; otherwise count points
        if pop_field:
            with arcpy.da.SearchCursor("points_lyr", ["has_access", pop_field]) as pc:
                for has_access, value in pc:
                    try:
                        value = float(value)
                    except:
                        continue
                    total_val += value
                    if has_access == 1:
                        access_val += value
                        count_with += 1
                    else:
                        count_without += 1
        else:
            with arcpy.da.SearchCursor("points_lyr", ["has_access"]) as pc:
                for (has_access,) in pc:
                    total_val += 1
                    if has_access == 1:
                        access_val += 1
                        count_with += 1
                    else:
                        count_without += 1

        # Calculate % accessibility
        ratio = (access_val / total_val) * 100 if total_val > 0 else 0

        # Fill output row based on available fields
        i = 2  # starting index in UpdateCursor row
        if pop_field:
            row[i] = total_val               # Total_Population
            row[i+1] = access_val            # Accessible_Population
        else:
            row[i] = total_val               # Total_Points
            row[i+1] = access_val            # Accessible_Points
        row[i+2] = ratio                     # Accessibility_Percent
        row[i+3] = count_with                # Points_With_Access
        row[i+4] = count_without             # Points_Without_Access
        row[i+5] = 1 if ratio_threshold > 0 and ratio >= ratio_threshold else 0 if ratio_threshold > 0 else None
        cursor.updateRow(row)

        # Progress log every 100 hexagons
        processed += 1
        if processed % 100 == 0:
            arcpy.AddMessage(f"Processed {processed}/{total_hex} hexagons ({round(processed/total_hex*100,1)} %)")

# ------------------------------------
# Save final output and clean temporary data
# ------------------------------------
arcpy.CopyFeatures_management(hex_copy, output_hex_layer)

arcpy.Delete_management(points_single)
arcpy.Delete_management(points_flagged)
arcpy.Delete_management(hex_copy)
arcpy.Delete_management("points_lyr")

# ------------------------------------
# Inform about 0% hexagons
# ------------------------------------
arcpy.AddMessage(
    "Note: Hexagons with 0% accessibility may still be near parks but contain no address points or no population."
)

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===  HEXAGON POPULATION ACCESSIBILITY COMPLETED ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Final layer saved to: {output_hex_layer}")

# Clean variables
del hex_layer, pop_points_input, access_polygon, pop_field, output_hex_layer, ratio_threshold
del points_single, points_flagged, hex_copy, fields, needed_fields