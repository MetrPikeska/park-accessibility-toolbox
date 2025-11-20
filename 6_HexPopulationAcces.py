# ------------------------------------
# Name: 6_HexPopulationAccess.py
# Purpose: Calculates population and accessibility statistics for each hexagon.
# ------------------------------------
import arcpy
import sys

# Allow overwriting outputs.
arcpy.env.overwriteOutput = True

# ------------------------------------
# Function to reproject a layer if its CRS doesn't match a target CRS
# ------------------------------------
def reproject_layer_if_needed(layer_path, target_sr, layer_name):
    """
    Reprojects a layer to a target spatial reference if they do not match.
    Returns the path to the reprojected layer (or the original path if no reprojection was needed).
    """
    try:
        desc = arcpy.Describe(layer_path)
        source_sr = desc.spatialReference
        
        if source_sr.factoryCode != target_sr.factoryCode:
            output_layer = f"in_memory/{layer_name}_reprojected"
            arcpy.AddMessage(f"Reprojecting '{layer_name}' to '{target_sr.name}'...")
            arcpy.management.Project(layer_path, output_layer, target_sr)
            return output_layer
    except Exception as e:
        raise arcpy.ExecuteError(f"Failed to reproject {layer_name}: {e}")
    
    return layer_path

# ------------------------------------
# Function to validate coordinate system consistency
# ------------------------------------
def validate_crs_consistency(layers, layer_names):
    """
    Validates that all input layers share the same coordinate system.
    """
    if not layers or len(layers) < 2:
        return None
    
    # Collect spatial references from all valid layers.
    spatial_refs = []
    for i, layer in enumerate(layers):
        if arcpy.Exists(layer):
            desc = arcpy.Describe(layer)
            if desc.spatialReference:
                spatial_refs.append((desc.spatialReference, layer_names[i]))
    
    if not spatial_refs:
        return None
    
    # Compare each layer's CRS to the first one.
    reference_sr, reference_name = spatial_refs[0]
    for sr, name in spatial_refs[1:]:
        if sr.factoryCode != reference_sr.factoryCode:
            raise arcpy.ExecuteError(f"Coordinate system mismatch between '{reference_name}' and '{name}'.")
    
    return reference_sr

# ------------------------------------
# Get input parameters
# ------------------------------------
hex_layer        = arcpy.GetParameterAsText(0)
pop_points_input = arcpy.GetParameterAsText(1)
access_polygon   = arcpy.GetParameterAsText(2)
pop_field        = arcpy.GetParameterAsText(3)
output_hex_layer = arcpy.GetParameterAsText(4)
ratio_threshold  = float(arcpy.GetParameterAsText(5) or 0)

# Define temporary layer paths.
points_single  = "in_memory/points_single"
points_flagged = "in_memory/points_with_access"

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("\n===================================================")
arcpy.AddMessage("===   HEXAGON POPULATION ACCESSIBILITY START   ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Input hexagons:        {hex_layer}")
arcpy.AddMessage(f"Address points:        {pop_points_input}")
arcpy.AddMessage(f"Accessibility polygon: {access_polygon}")
arcpy.AddMessage("---------------------------------------------------")

# --- Validate inputs ---
if not arcpy.Exists(hex_layer): raise arcpy.ExecuteError("Input hexagon layer does not exist.")
if not arcpy.Exists(pop_points_input): raise arcpy.ExecuteError("Address points layer does not exist.")
if not arcpy.Exists(access_polygon): raise arcpy.ExecuteError("Accessibility polygon does not exist.")

# --- Ensure all layers use the same coordinate system ---
hex_desc = arcpy.Describe(hex_layer)
target_sr = hex_desc.spatialReference
pop_points_reprojected = reproject_layer_if_needed(pop_points_input, target_sr, "Address_points")
access_polygon_reprojected = reproject_layer_if_needed(access_polygon, target_sr, "Accessibility_polygon")
validate_crs_consistency(
    [hex_layer, pop_points_reprojected, access_polygon_reprojected],
    ["Hexagon layer", "Address points layer", "Accessibility polygon"]
)
arcpy.AddMessage(f"Coordinate system validated: {target_sr.name}")

# --- Validate population field if provided ---
if pop_field:
    input_fields = [f.name for f in arcpy.ListFields(pop_points_input)]
    if pop_field not in input_fields:
        raise arcpy.ExecuteError(f"Population field '{pop_field}' not found in the input points layer.")
    
    field_info = arcpy.ListFields(pop_points_input, pop_field)[0]
    if field_info.type not in ["Double", "Float", "Single", "Integer", "SmallInteger"]:
        arcpy.AddWarning(f"Population field '{pop_field}' is not a numeric type.")
    else:
        arcpy.AddMessage(f"Population field validated: '{pop_field}'")

# --- Convert multipoint features to single points ---
desc = arcpy.Describe(pop_points_reprojected)
if desc.shapeType == "Multipoint":
    arcpy.AddMessage("Converting multipoint features to single points...")
    arcpy.MultipartToSinglepart_management(pop_points_reprojected, points_single)
else:
    arcpy.CopyFeatures_management(pop_points_reprojected, points_single)

# --- Flag points within the accessibility polygon using a Spatial Join ---
arcpy.AddMessage("Flagging points within the accessibility area...")
arcpy.analysis.SpatialJoin(
    target_features=points_single, join_features=access_polygon_reprojected,
    out_feature_class=points_flagged, join_type="KEEP_ALL", match_option="INTERSECT"
)

# --- Add a 'has_access' field (1 for accessible, 0 for not) ---
arcpy.AddField_management(points_flagged, "has_access", "SHORT")
with arcpy.da.UpdateCursor(points_flagged, ["Join_Count", "has_access"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] and row[0] > 0 else 0
        cursor.updateRow(row)
arcpy.AddMessage("Address points flagged for accessibility.")

# ------------------------------------
# Summarize points and population within hexagons
# ------------------------------------
arcpy.AddMessage("Summarizing data within hexagons...")
sum_fields = []
if pop_field:
    # Create a temporary field to hold the population of accessible points only.
    arcpy.management.AddField(points_flagged, "accessible_pop", "DOUBLE")
    arcpy.management.CalculateField(points_flagged, "accessible_pop", f"!{pop_field}! if !has_access! == 1 else 0", "PYTHON3")
    sum_fields = [[pop_field, "SUM"], ["accessible_pop", "SUM"], ["has_access", "SUM"]]
else:
    sum_fields = [["has_access", "SUM"]]

# Use SummarizeWithin for efficient aggregation.
arcpy.analysis.SummarizeWithin(
    in_polygons=hex_layer, in_sum_features=points_flagged,
    out_feature_class=output_hex_layer, keep_all_polygons="KEEP_ALL",
    sum_fields=sum_fields, add_group_percent="NO_PERCENT"
)
arcpy.AddMessage("Aggregation complete.")

# ------------------------------------
# Rename and calculate final output fields
# ------------------------------------
arcpy.AddMessage("Calculating final statistics...")
# Rename fields generated by SummarizeWithin for clarity.
field_mappings = {"Point_Count": "Total_Points", f"Sum_{pop_field}": "Total_Population",
                  "Sum_accessible_pop": "Accessible_Population", "Sum_has_access": "Points_With_Access"}
if not pop_field:
    field_mappings["Sum_has_access"] = "Accessible_Points"

for old_name, new_name in field_mappings.items():
    if arcpy.ListFields(output_hex_layer, old_name):
        arcpy.management.AlterField(output_hex_layer, old_name, new_name, new_name)

# --- Define and add any missing fields ---
needed_fields = { "Accessibility_Percent": "DOUBLE", "Points_Without_Access": "LONG", "Above_Threshold": "SHORT" }
if pop_field:
    needed_fields.update({"Total_Population": "DOUBLE", "Accessible_Population": "DOUBLE", "Points_With_Access": "LONG"})
else:
    needed_fields.update({"Total_Points": "LONG", "Accessible_Points": "LONG"})

for field, ftype in needed_fields.items():
    if not arcpy.ListFields(output_hex_layer, field):
        arcpy.management.AddField(output_hex_layer, field, ftype)

# --- Calculate final derived fields ---
if pop_field:
    arcpy.management.CalculateField(output_hex_layer, "Points_Without_Access", "!Total_Points! - !Points_With_Access!", "PYTHON3")
    arcpy.management.CalculateField(output_hex_layer, "Accessibility_Percent", "(!Accessible_Population! / !Total_Population!) * 100 if !Total_Population! > 0 else 0", "PYTHON3")
else:
    arcpy.management.CalculateField(output_hex_layer, "Points_Without_Access", "!Total_Points! - !Accessible_Points!", "PYTHON3")
    arcpy.management.CalculateField(output_hex_layer, "Accessibility_Percent", "(!Accessible_Points! / !Total_Points!) * 100 if !Total_Points! > 0 else 0", "PYTHON3")

# Calculate whether the hexagon is above the specified threshold.
arcpy.management.CalculateField(output_hex_layer, "Above_Threshold", f"1 if !Accessibility_Percent! >= {ratio_threshold} else 0", "PYTHON3")
arcpy.AddMessage("Final statistics calculated.")

# ------------------------------------
# Clean up temporary data
# ------------------------------------
arcpy.AddMessage("Cleaning up temporary data...")
for item in [points_single, points_flagged, "points_lyr"]:
    if arcpy.Exists(item):
        arcpy.management.Delete(item)

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("\n===================================================")
arcpy.AddMessage("===  HEXAGON POPULATION ACCESSIBILITY COMPLETED ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Final layer saved to: {output_hex_layer}")

# Author: Petr Mikeska
# Bachelor thesis (2025)
