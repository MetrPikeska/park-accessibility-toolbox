#------------------------------------
# Name: 1_NetworkDataset.py
# Author: Petr MIKESKA, Department of Geoinformatics, Faculty of Science, Palacký University Olomouc, 2025
# Bachelor thesis title (EN): Assessing the availability of green spaces and parks for urban residents
# Bachelor thesis title (CZ): Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst
# This script creates and builds a network dataset from input roads.
#------------------------------------

import arcpy
import os
import sys

#------------------------------------
# General settings
#------------------------------------
arcpy.env.overwriteOutput = True
# Allow overwriting outputs

#------------------------------------
# Check and activate Network Analyst extension
#------------------------------------
if arcpy.CheckExtension("Network") == "Available":
    arcpy.CheckOutExtension("Network")
    # Activate Network Analyst
    arcpy.AddMessage("✔ Network Analyst extension checked out.")
else:
    arcpy.AddError("❌ Network Analyst extension is not available.")
    raise SystemExit()
    # Stop script if extension is missing

#------------------------------------
# Print header
#------------------------------------
arcpy.AddMessage("")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("===         NETWORK DATASET CREATION START     ===")
arcpy.AddMessage("===================================================")
arcpy.AddMessage("Author: Petr Mikeska (Bachelor's thesis)")
arcpy.AddMessage("---------------------------------------------------")

def create_network_dataset(input_roads, output_path):
    if not output_path.endswith(".gdb"):
        output_path = os.path.join(output_path, "NetworkDataset.gdb")
    # Ensure output is a geodatabase

    gdb_folder      = os.path.dirname(output_path)
    # Path to folder

    gdb_name        = os.path.basename(output_path)
    # GDB file name

    feature_dataset = os.path.join(output_path, "NetworkData")
    # Path to feature dataset

    network_name    = "NetworkDataset"
    # Name of network dataset

    network_dataset = os.path.join(feature_dataset, network_name)
    # Full path to network dataset

    network_roads   = os.path.join(feature_dataset, "Roads")
    # Path to copied roads

    arcpy.AddMessage(f"Input roads:        {input_roads}")
    arcpy.AddMessage(f"Output folder:      {gdb_folder}")
    arcpy.AddMessage(f"GDB name:           {gdb_name}")
    arcpy.AddMessage(f"Network name:       {network_name}")
    arcpy.AddMessage("---------------------------------------------------")

    if not arcpy.Exists(output_path):
        if not os.path.exists(gdb_folder):
            os.makedirs(gdb_folder)
        # Create folder if missing

        arcpy.management.CreateFileGDB(gdb_folder, gdb_name)
        # Create file geodatabase
        arcpy.AddMessage("Geodatabase created.")

    sr = arcpy.Describe(input_roads).spatialReference
    # Get spatial reference from input

    if not arcpy.Exists(feature_dataset):
        arcpy.management.CreateFeatureDataset(output_path, "NetworkData", sr)
        # Create feature dataset if missing
        arcpy.AddMessage("Feature dataset 'NetworkData' created.")

    if arcpy.Exists(network_roads):
        arcpy.AddWarning("Roads already exist, skipping copy.")
        # Avoid overwriting existing data
    else:
        arcpy.conversion.FeatureClassToFeatureClass(input_roads, feature_dataset, "Roads")
        # Copy input roads
        arcpy.AddMessage("Roads copied to 'NetworkData' dataset.")

    if not arcpy.Exists(network_dataset):
        try:
            arcpy.na.CreateNetworkDataset(
                feature_dataset=feature_dataset,
                out_name=network_name,
                source_feature_class_names="Roads",
                elevation_model="ELEVATION_FIELDS"
            )
            # Create network dataset

            arcpy.na.BuildNetwork(network_dataset)
            # Build network dataset

            arcpy.AddMessage("Network dataset created and built successfully.")
        except arcpy.ExecuteError:
            arcpy.AddError(arcpy.GetMessages(2))
            raise SystemExit()
            # Stop on failure

    arcpy.AddMessage("---------------------------------------------------")
    arcpy.AddMessage(f"Output GDB:         {output_path}")
    arcpy.AddMessage(f"Output network:     {network_dataset}")

    return network_dataset
    # Return final network path

#------------------------------------
# Main script execution
#------------------------------------
if __name__ == "__main__":
    input_roads = arcpy.GetParameterAsText(0)
    # Input road layer

    output_path = arcpy.GetParameterAsText(1)
    # Output folder or GDB

    network_dataset = create_network_dataset(input_roads, output_path)
    # Run main creation function

    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION DONE      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

    del input_roads, output_path
    del network_dataset
    # Clean up
