# ------------------------------------
# Name: 1_NetworkDataset.py
# Purpose: Creates and builds a network dataset from an input road layer.
# The same name is consistently used for the Geodatabase, Feature Dataset and Network Dataset.
# ------------------------------------

import arcpy
import arcpy.na
import os
import sys

# Allow overwriting outputs to facilitate script re-runs.
arcpy.env.overwriteOutput = True

# ------------------------------------
# Function to generate a unique path for a GDB
# ------------------------------------
def get_unique_path(output_folder, name):
    """
    Returns a unique path for a geodatabase (.gdb).
    If the file already exists, it appends a numerical suffix (_1, _2, etc.).
    This prevents unintentional overwriting of existing data.
    """
    i = 1
    candidate = os.path.join(output_folder, f"{name}.gdb")
    while arcpy.Exists(candidate):
        candidate = os.path.join(output_folder, f"{name}_{i}.gdb")
        i += 1
    return candidate

# ------------------------------------
# Main function to create the network dataset
# ------------------------------------
def create_network_dataset(input_roads, output_folder, network_name_raw):
    """
    Main logic of the script: creates a geodatabase, feature dataset, and network dataset.
    """
    arcpy.AddMessage("")
    arcpy.AddMessage("===================================================")
    arcpy.AddMessage("===         NETWORK DATASET CREATION START     ===")
    arcpy.AddMessage("===================================================")

    # Clean the network name (remove any path, leaving only the file name)
    network_name = os.path.basename(network_name_raw.strip())
    extension_checked_out = False  # Flag to check if the extension was activated

    try:
        # --- Check for and check out the Network Analyst extension ---
        extension_status = arcpy.CheckExtension("Network")
        arcpy.AddMessage(f"Network Analyst extension status: {extension_status}")
        
        if extension_status == "Available":
            arcpy.CheckOutExtension("Network")
            extension_checked_out = True
            arcpy.AddMessage("Network Analyst extension checked out successfully.")
        elif extension_status == "NotLicensed":
            arcpy.AddError(
                "Network Analyst extension is not licensed. "
                "Your ArcGIS Pro license does not include Network Analyst. "    
                "Required: ArcGIS Pro Advanced or Network Analyst extension license."
            )
            raise arcpy.ExecuteError("Network Analyst extension is not licensed.")
        elif extension_status == "Unavailable":
            arcpy.AddError(
                "Network Analyst extension is currently unavailable (already in use). "
                "Please close other applications using this extension."
            )
            raise arcpy.ExecuteError("Network Analyst extension is unavailable.")
        else:
            arcpy.AddError(
                f"Network Analyst extension status: {extension_status}. "
                "Please verify your ArcGIS Pro license or enable the extension in Project > Licensing."
            )
            raise arcpy.ExecuteError(f"Network Analyst extension is not available: {extension_status}")

        # --- Validate the geometry type of the input layer (must be polyline) ---
        desc_input = arcpy.Describe(input_roads)
        if desc_input.shapeType != "Polyline":
            arcpy.AddError(
                f"Invalid geometry type: {desc_input.shapeType}. "
                "The input road network must be a polyline feature class."
            )
            raise arcpy.ExecuteError(f"Invalid geometry type. Expected Polyline.")

        # --- Log the detected coordinate reference system (CRS) ---
        # It's important to ensure all layers in the analysis use the same CRS.
        sr = desc_input.spatialReference
        arcpy.AddMessage(f"Detected coordinate system: {sr.name} (EPSG: {sr.factoryCode})")
        arcpy.AddMessage("---------------------------------------------------")

        # --- Create the output folder if it doesn't exist ---
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            arcpy.AddMessage(f"Output folder created: {output_folder}")

        # --- Create a file geodatabase with a unique name ---
        gdb_path = get_unique_path(output_folder, network_name)
        if gdb_path != os.path.join(output_folder, f"{network_name}.gdb"):
            arcpy.AddMessage(f"A geodatabase named '{network_name}.gdb' already exists. Using unique name: {os.path.basename(gdb_path)}")
        
        arcpy.management.CreateFileGDB(os.path.dirname(gdb_path), os.path.basename(gdb_path).replace(".gdb", ""))
        arcpy.AddMessage(f"Geodatabase created: {os.path.basename(gdb_path)}")

        # --- Create a Feature Dataset inside the geodatabase ---
        # A feature dataset is a container required to store a network dataset.
        feature_dataset = os.path.join(gdb_path, network_name)
        arcpy.management.CreateFeatureDataset(gdb_path, network_name, sr)
        arcpy.AddMessage(f"Feature dataset '{network_name}' created.")

        # --- Copy the road network into the Feature Dataset ---
        arcpy.conversion.FeatureClassToFeatureClass(input_roads, feature_dataset, "Roads")
        arcpy.AddMessage("Road layer copied into the feature dataset.")

        # --- Create and build the network dataset ---
        network_dataset_path = os.path.join(feature_dataset, network_name)
        arcpy.AddMessage("Creating Network Dataset...")
        
        # Using correct Network Analyst tool syntax with proper parameters
        arcpy.na.CreateNetworkDataset(
            feature_dataset,
            network_name,
            ["Roads"],
            "ELEVATION_FIELDS"
        )
        arcpy.AddMessage("Network Dataset created.")
        
        # Building the network is crucial for calculations and analyses.
        arcpy.na.BuildNetwork(network_dataset_path)
        arcpy.AddMessage("Network Dataset built successfully.")
        
        # --- Final log with key information about the outputs ---
        arcpy.AddMessage("---------------------------------------------------")
        arcpy.AddMessage(f"Output Geodatabase:   {gdb_path}")
        arcpy.AddMessage(f"Full network path:    {network_dataset_path}")
        arcpy.AddMessage("===================================================")
        arcpy.AddMessage("===         NETWORK DATASET CREATION DONE      ===")
        arcpy.AddMessage("===================================================")

        return network_dataset_path

    except Exception as e:
        # Handle generic errors and report them to the user.
        arcpy.AddError(f"An error occurred: {e}")
        raise

    finally:
        # The 'finally' block always executes, whether an error occurred or not.
        # This ensures the Network Analyst extension is always checked back in.
        if extension_checked_out:
            arcpy.CheckInExtension("Network")
            arcpy.AddMessage("Network Analyst extension checked back in.")

# ------------------------------------
# Script entry point when run from ArcGIS
# ------------------------------------
if __name__ == "__main__":
    try:
        # Load parameters from the ArcGIS Pro dialog
        input_roads = arcpy.GetParameterAsText(0)      # Input road network layer
        output_folder = arcpy.GetParameterAsText(1)    # Target folder for the GDB
        network_name_raw = arcpy.GetParameterAsText(2) # Desired name for the network dataset

        # Debug output
        arcpy.AddMessage("Script started successfully")
        arcpy.AddMessage(f"Python version: {sys.version}")
        arcpy.AddMessage(f"ArcPy version: {arcpy.GetInstallInfo()['Version']}")
        
        # Run the main function with the loaded parameters
        network_dataset = create_network_dataset(input_roads, output_folder, network_name_raw)
    except Exception as e:
        arcpy.AddError(f"Script failed with error: {str(e)}")
        arcpy.AddError(f"Error type: {type(e).__name__}")
        import traceback
        arcpy.AddError(traceback.format_exc())
        raise

# Author: Petr Mikeska
# Bachelor thesis:
#   Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst (2025)
#   Assessing the availability of green spaces and parks for urban residents (2025)
