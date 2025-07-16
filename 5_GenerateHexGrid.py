# ------------------------------------
# Name: 5_GenerateHexGrid.py
# This script generates a hexagonal tessellation over a polygon feature and clips it to its extent.
# ------------------------------------

import arcpy
import sys
import os

# Always overwrite existing outputs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Get input parameters
# ------------------------------------
workspace         = arcpy.GetParameterAsText(0)    # Output Geodatabase
input_feature     = arcpy.GetParameterAsText(1)    # Analysis Extent (Polygon Layer)
output_feature    = arcpy.GetParameterAsText(2)    # Output Feature Name (in GDB)
hex_size_value    = arcpy.GetParameterAsText(3)    # Hexagon size in hectares

# ------------------------------------
# Header log
# ------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         ZAČÁTEK GENEROVÁNÍ HEXAGONŮ        ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage(f"Vstupní polygon:   {input_feature}")
arcpy.AddMessage(f"Zadaný výstupní název: {output_feature}")
arcpy.AddMessage(f"Velikost hexagonu: {hex_size_value} ha")

# Set output geodatabase
if not workspace:
    arcpy.AddError("❌ Nebyla zadána výstupní geodatabáze. Vyberte platnou GDB.")
    sys.exit(1)
arcpy.env.workspace = workspace
arcpy.AddMessage(f"Výstupní geodatabáze: {workspace}")

# Validate output name
if not output_feature or output_feature.strip() == "":
    arcpy.AddError("❌ Musíte zadat název výstupní vrstvy (Output Feature Name).")
    sys.exit(1)

# Always save into selected geodatabase
final_output_path = os.path.join(workspace, output_feature)
arcpy.AddMessage(f"Výsledná vrstva bude uložena do: {final_output_path}")
arcpy.AddMessage("---------------------------------------------------")

# ------------------------------------
# Validate input geometry type
# ------------------------------------
desc = arcpy.Describe(input_feature)
if desc.shapeType != "Polygon":
    arcpy.AddError(f"❌ {input_feature} není polygonová vrstva. Skript se ukončí.")
    sys.exit(1)

# Get extent and spatial reference
extent        = desc.extent
extent_string = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
spatial_ref   = desc.spatialReference

# ------------------------------------
# Validate hexagon size (> 0)
# ------------------------------------
try:
    hex_size_val = float(hex_size_value)
    if hex_size_val <= 0:
        arcpy.AddError("❌ Velikost hexagonu musí být větší než 0 ha. Zadejte platnou hodnotu.")
        sys.exit(1)
    hex_size = f"{hex_size_val} Hectares"
except ValueError:
    arcpy.AddError(f"❌ Neplatná hodnota pro velikost hexagonu: {hex_size_value}. Zadejte číselnou hodnotu > 0.")
    sys.exit(1)

# ------------------------------------
# Generate tessellation
# ------------------------------------
arcpy.AddMessage(f"Generuji hexagonální mřížku ({hex_size})...")
temp_hex = "in_memory\\temp_hex"
arcpy.management.GenerateTessellation(temp_hex, extent_string, "HEXAGON", hex_size, spatial_ref)

# Check tessellation
if not arcpy.Exists(temp_hex):
    arcpy.AddError("❌ Generování hexagonů selhalo. Nebyl vytvořen žádný výstup.")
    sys.exit(1)

desc_output = arcpy.Describe(temp_hex)
if desc_output.shapeType != "Polygon":
    arcpy.AddError("❌ Výstup není polygonová vrstva. Skript se ukončí.")
    sys.exit(1)

arcpy.AddMessage("✔ Hexagonální mřížka úspěšně vygenerována.")

# ------------------------------------
# Clip hexagons to input boundary
# ------------------------------------
arcpy.AddMessage("Ořezávám hexagony na hranice vstupního polygonu...")
arcpy.analysis.Clip(temp_hex, input_feature, final_output_path)
arcpy.AddMessage(f"✔ Hexagony oříznuty. Výsledná vrstva: {final_output_path}")

# ------------------------------------
# Add final layer to current map
# ------------------------------------
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    m.addDataFromPath(final_output_path)
    arcpy.AddMessage("✔ Výsledná vrstva byla automaticky přidána do mapy.")
except:
    arcpy.AddWarning("⚠ Výslednou vrstvu se nepodařilo automaticky přidat do mapy.")


# ------------------------------------
# Clean up temporary data
# ------------------------------------
arcpy.Delete_management(temp_hex)
arcpy.AddMessage("✔ Dočasná data smazána.")

# ------------------------------------
# Footer log
# ------------------------------------
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         GENEROVÁNÍ HEXAGONŮ DOKONČENO       ===")
arcpy.AddMessage("===================================================")

# Clean variables
del workspace, input_feature, output_feature, final_output_path, hex_size_value
del extent, extent_string, spatial_ref, hex_size
del temp_hex, desc, desc_output

# Author: Petr MIKESKA
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
