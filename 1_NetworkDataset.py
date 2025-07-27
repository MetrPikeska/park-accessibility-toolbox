# ------------------------------------
# Name: 1_NetworkDataset.py
# Purpose: Creates and builds a network dataset from an input road layer.
# The same name is consistently used for the Geodatabase, Feature Dataset and Network Dataset.
# ------------------------------------

import arcpy
import os
import sys

# Always overwrite outputs to allow re-runs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Generate a unique GDB path (append _1, _2 if needed)
# ------------------------------------
def get_unique_path(base_path, name):
    """
    Returns a unique GDB path by appending a number if needed.
    Ensures that no existing geodatabase is overwritten unintentionally.
    """
    i = 1
    candidate = os.path.join(base_path, f"{name}.gdb")
    while arcpy.Exists(candidate):
        candidate = os.path.join(base_path, f"{name}_{i}.gdb")
        i += 1
    return candidate

# ------------------------------------
# Main function that creates the network dataset
# ------------------------------------
def create_network_dataset(input_roads, output_folder, network_name_raw):
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION START     ===")
    arcpy.AddMessage("===================================================")

    # Clean network name (remove unwanted paths if present)
    network_name = os.path.basename(network_name_raw.strip())

    # ------------------------------------------------------------------
    # Check if the Network Analyst extension is available
    # ------------------------------------------------------------------
    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
        arcpy.AddMessage("Network Analyst extension checked out successfully.")
    else:
        arcpy.AddError(
            "Network Analyst extension is not available. "
            "Please verify your ArcGIS Pro license or enable the extension."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Validate geometry type (must be polyline)
    # ------------------------------------------------------------------
    desc_input = arcpy.Describe(input_roads)
    shape_type = desc_input.shapeType
    if shape_type != "Polyline":
        arcpy.AddError(
            f"Invalid geometry type: {shape_type}. "
            "The input road network must be a polyline feature class. "
            "Please provide a valid line geometry layer and try again."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Log detected spatial reference (important for further analyses)
    # ------------------------------------------------------------------
    sr = desc_input.spatialReference
    arcpy.AddMessage(f"Detected coordinate system: {sr.name} (EPSG: {sr.factoryCode})")
    arcpy.AddMessage(
        "Note: All input layers (roads, parks, address points) must use the same coordinate system "
        "to ensure correct network analysis results."
    )
    arcpy.AddMessage("---------------------------------------------------")

    # ------------------------------------------------------------------
    # Create output folder if it does not exist
    # ------------------------------------------------------------------
    if not os.path.exists(output_folder):
        arcpy.AddMessage(f"Output folder does not exist. Creating: {output_folder}")
        os.makedirs(output_folder)

    # Define intended GDB path and generate unique name if needed
    intended_gdb_path = os.path.join(output_folder, f"{network_name}.gdb")
    gdb_path = get_unique_path(output_folder, network_name)

    # Warn if the geodatabase name was modified to avoid conflicts
    if gdb_path != intended_gdb_path:
        arcpy.AddMessage(
            f"A geodatabase named '{network_name}.gdb' already exists. "
            f"A unique name will be used: {os.path.basename(gdb_path)}"
        )

    # ------------------------------------------------------------------
    # Create File GDB
    # ------------------------------------------------------------------
    gdb_name = os.path.basename(gdb_path)
    arcpy.CreateFileGDB_management(output_folder, gdb_name)
    arcpy.AddMessage(f"Geodatabase created: {gdb_name}")

    # ------------------------------------------------------------------
    # Create Feature Dataset with the same spatial reference
    # ------------------------------------------------------------------
    feature_dataset = os.path.join(gdb_path, network_name)
    arcpy.CreateFeatureDataset_management(gdb_path, network_name, sr)
    arcpy.AddMessage(f"Feature dataset '{network_name}' created successfully.")

    # ------------------------------------------------------------------
    # Copy roads into Feature Dataset
    # ------------------------------------------------------------------
    arcpy.FeatureClassToFeatureClass_conversion(input_roads, feature_dataset, "Roads")
    arcpy.AddMessage("Road layer copied into the Feature Dataset.")

    # Full path for Network Dataset
    network_dataset_path = os.path.join(feature_dataset, network_name)

    # ------------------------------------------------------------------
    # Create and build Network Dataset
    # ------------------------------------------------------------------
    try:
        arcpy.AddMessage("Creating Network Dataset...")
        arcpy.na.CreateNetworkDataset(
            feature_dataset=feature_dataset,
            out_name=network_name,
            source_feature_class_names="Roads",
            elevation_model="ELEVATION_FIELDS"  # Required by European Commission methodology
        )
        arcpy.na.BuildNetwork(network_dataset_path)
        arcpy.AddMessage("Network Dataset created and built successfully.")
    except arcpy.ExecuteError:
        arcpy.AddError("Network Dataset creation failed due to an ArcGIS execution error:")
        arcpy.AddError(arcpy.GetMessages(2))
        sys.exit(1)

    # ------------------------------------------------------------------
    # Final log with key information
    # ------------------------------------------------------------------
    arcpy.AddMessage("---------------------------------------------------")
    arcpy.AddMessage(f"Output Geodatabase:   {gdb_path}")
    arcpy.AddMessage(f"Network name:         {network_name}")
    arcpy.AddMessage(f"Full network path:    {network_dataset_path}")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION DONE      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

    return network_dataset_path

# ------------------------------------
# Script entry point for ArcGIS parameters
# ------------------------------------
if __name__ == "__main__":
    input_roads = arcpy.GetParameterAsText(0)      # Road network layer
    output_folder = arcpy.GetParameterAsText(1)    # Output folder for GDB
    network_name_raw = arcpy.GetParameterAsText(2) # Desired name for network dataset

    network_dataset = create_network_dataset(input_roads, output_folder, network_name_raw)

    del input_roads, output_folder, network_name_raw, network_dataset

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
