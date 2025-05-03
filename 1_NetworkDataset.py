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

# General settings
arcpy.env.overwriteOutput = True

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
    # Determine output GDB
    if not output_path.endswith(".gdb"):
        output_path = os.path.join(output_path, "NetworkDataset.gdb")

    # Paths and names
    gdb_folder      = os.path.dirname(output_path)
    gdb_name        = os.path.basename(output_path)
    feature_dataset = os.path.join(output_path, "NetworkData")
    network_name    = "NetworkDataset"
    network_dataset = os.path.join(feature_dataset, network_name)
    network_roads   = os.path.join(feature_dataset, "Roads")

    # Logging input/output
    arcpy.AddMessage(f"Input roads:        {input_roads}")
    arcpy.AddMessage(f"Output folder:      {gdb_folder}")
    arcpy.AddMessage(f"GDB name:           {gdb_name}")
    arcpy.AddMessage(f"Network name:       {network_name}")
    arcpy.AddMessage("---------------------------------------------------")

    # Create output GDB if it doesn't exist
    if not arcpy.Exists(output_path):
        if not os.path.exists(gdb_folder):
            os.makedirs(gdb_folder)
        arcpy.CreateFileGDB_management(gdb_folder, gdb_name)
        arcpy.AddMessage("Geodatabase created.")

    # Create feature dataset
    sr = arcpy.Describe(input_roads).spatialReference
    if not arcpy.Exists(feature_dataset):
        arcpy.CreateFeatureDataset_management(output_path, "NetworkData", sr)
        arcpy.AddMessage("Feature dataset 'NetworkData' created.")

    # Copy input roads into the dataset
    if arcpy.Exists(network_roads):
        arcpy.AddWarning("Roads already exist, skipping copy.")
    else:
        arcpy.FeatureClassToFeatureClass_conversion(input_roads, feature_dataset, "Roads")
        arcpy.AddMessage("Roads copied to 'NetworkData' dataset.")

    # Create and build network dataset
    if not arcpy.Exists(network_dataset):
        try:
            arcpy.na.CreateNetworkDataset(
                feature_dataset=feature_dataset,
                out_name=network_name,
                source_feature_class_names="Roads",
                elevation_model="ELEVATION_FIELDS"
            )
            arcpy.na.BuildNetwork(network_dataset)
            arcpy.AddMessage("Network dataset created and built successfully.")
        except arcpy.ExecuteError:
            arcpy.AddError(arcpy.GetMessages(2))
            raise SystemExit()

    # Log final output paths
    arcpy.AddMessage("---------------------------------------------------")
    arcpy.AddMessage(f"Output GDB:         {output_path}")
    arcpy.AddMessage(f"Output network:     {network_dataset}")

    return network_dataset

#------------------------------------
# Main script execution
#------------------------------------
if __name__ == "__main__":
    input_roads = arcpy.GetParameterAsText(0)    # Input road layer
    output_path = arcpy.GetParameterAsText(1)    # Output folder or GDB

    network_dataset = create_network_dataset(input_roads, output_path)

    # Final message
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION DONE      ===")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("")

    #------------------------------------
    # Clean up variables
    #------------------------------------
    del input_roads, output_path
    del network_dataset
