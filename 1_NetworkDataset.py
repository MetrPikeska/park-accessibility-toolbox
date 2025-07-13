# ------------------------------------
# Name: 1_NetworkDataset.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script creates and builds a network dataset from input roads.
# Network name is used consistently for GDB, feature dataset and network dataset.
# ------------------------------------

import arcpy
import os

# Always overwrite outputs to allow re-runs
arcpy.env.overwriteOutput = True

# ------------------------------------
# Function to generate a unique GDB path (e.g. append _1, _2 if needed)
# Avoids overwrite conflicts when user chooses existing name
# ------------------------------------
def get_unique_path(base_path, name):
    """Returns a unique GDB path by appending a number if needed."""
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
    # Print header
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION START     ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
    arcpy.AddMessage("---------------------------------------------------")

    # Clean network name (remove unwanted paths if present)
    network_name = os.path.basename(network_name_raw.strip())

    # Check if the Network Analyst extension is available and activate it
    arcpy.AddMessage("Checking availability of Network Analyst Extension...")
    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
        arcpy.AddMessage("✔ Network Analyst extension successfully checked out.")
    else:
        arcpy.AddError("❌ Network Analyst extension is not available. The script will now exit.")
        raise SystemExit()

    # Validate geometry type of input roads (must be polyline)
    if arcpy.Describe(input_roads).shapeType != "Polyline":
        arcpy.AddError("❌ Input roads must be a polyline (line) feature class.")
        raise SystemExit()

    # Create the output folder if it does not exist
    if not os.path.exists(output_folder):
        arcpy.AddWarning(f"Output folder does not exist. Creating: {output_folder}")
        os.makedirs(output_folder)

    # Define intended path and generate unique name if needed
    intended_gdb_path = os.path.join(output_folder, f"{network_name}.gdb")
    gdb_path = get_unique_path(output_folder, network_name)

    # Warn user if the name had to be changed
    if gdb_path != intended_gdb_path:
        arcpy.AddWarning(f"⚠ A geodatabase named '{network_name}.gdb' already exists.")
        arcpy.AddWarning(f"→ The output will be saved as: {os.path.basename(gdb_path)} instead.")

    # Create the File Geodatabase
    gdb_name = os.path.basename(gdb_path)
    arcpy.CreateFileGDB_management(output_folder, gdb_name)
    arcpy.AddMessage(f"✔ Geodatabase created: {gdb_name}")

    # Get spatial reference from input roads
    sr = arcpy.Describe(input_roads).spatialReference

    # Create Feature Dataset with correct spatial reference
    feature_dataset = os.path.join(gdb_path, network_name)
    arcpy.CreateFeatureDataset_management(gdb_path, network_name, sr)
    arcpy.AddMessage(f"✔ Feature dataset '{network_name}' created.")

    # Copy input roads to feature dataset as "Roads"
    arcpy.FeatureClassToFeatureClass_conversion(input_roads, feature_dataset, "Roads")
    arcpy.AddMessage("✔ Roads copied to feature dataset.")

    # Define full path for the resulting network dataset
    network_dataset_path = os.path.join(feature_dataset, network_name)

    # Create and build network dataset from the Roads layer
    try:
        arcpy.na.CreateNetworkDataset(
            feature_dataset=feature_dataset,
            out_name=network_name,
            source_feature_class_names="Roads",
            elevation_model="ELEVATION_FIELDS"  # Required by EC methodology
        )
        arcpy.na.BuildNetwork(network_dataset_path)
        arcpy.AddMessage("✔ Network dataset created and built successfully.")
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise

    # Final log summary of outputs
    arcpy.AddMessage("---------------------------------------------------")
    arcpy.AddMessage(f"Output GDB:         {gdb_path}")
    arcpy.AddMessage(f"Network name:       {network_name}")
    arcpy.AddMessage(f"Full network path:  {network_dataset_path}")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION DONE      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

    return network_dataset_path

# ------------------------------------
# Script entry point (parameter input from user)
# ------------------------------------
if __name__ == "__main__":
    input_roads      = arcpy.GetParameterAsText(0)  # Input road layer (Line)
    output_folder    = arcpy.GetParameterAsText(1)  # Output folder for GDB
    network_name_raw = arcpy.GetParameterAsText(2)  # Desired name for network dataset

    network_dataset = create_network_dataset(input_roads, output_folder, network_name_raw)

    # Clean up
    del input_roads, output_folder, network_name_raw, network_dataset
