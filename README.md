Park Accessibility Toolbox
Toolbox for assessing the availability of green spaces and parks for urban residents using network analysis and GIS scripts. This toolbox was developed as part of the bachelor's thesis at the Department of Geoinformatics, Faculty of Science, Palacký University Olomouc.

Author
Petr Mikeska
Department of Geoinformatics, Faculty of Science, Palacký University Olomouc
Bachelor Thesis
Year: 2025

Instagram: @petamikeska

Email: piter.mikeska@gmail.com

Thesis Title
English: Assessing the availability of green spaces and parks for urban residents
Czech: Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst

Thesis Assignment
The goal of the thesis is to calculate the accessibility of green areas and parks within a city based on the methodology of the European Commission Directorate General for Regional and Urban Policy (A short walk to the park?, updated 2021 version). Alternative procedures and input data are also considered. Suitable datasets are selected and the results influenced by different approaches and data sources are compared.

The scripts for ArcGIS Pro, provided by the updated 2021 methodology, are used and modified where necessary. All modifications are described and justified. The accessibility is assessed for the city of Olomouc and two additional Czech cities — Brno and Ostrava — to evaluate the applicability of the methodology in the local context.

Toolbox Content
This repository contains Python scripts for the ArcGIS Pro environment:

1_NetworkDataset.py
Creates a pedestrian network dataset from input road data (excluding highways). Based on Copernicus/Urban Atlas assumptions and Network Analyst standards.

2_PointAlongLine.py
Generates entry points along the park polygon boundaries (≥1 ha), selecting only those within 25 meters of the road network.

3_NetworkAnalysis.py
Calculates 400 m service areas from the park entry points using the network dataset. Dissolves output into one polygon representing the accessible green zone.

4_AnalyzeParkAccesibility.py
Analyzes accessibility for each administrative district: calculates share of population and area within 400 m from green areas.

5_GenerateHexGrid.py
Creates a hexagonal tessellation (e.g., 250 m resolution) for spatially neutral analysis of accessibility over the entire city.

6_HexPopulationAcces.py
Assigns population statistics to hexagons: total vs. accessible population, including entry point availability.

Requirements
ArcGIS Pro (3.0+ recommended)

Python 3.x (installed with ArcGIS Pro)

ArcPy library

Network Analyst Extension (licensed)

Usage
Each script can be run independently via ArcGIS Pro toolbox or the Python command line. Before running the scripts, ensure you have prepared appropriate datasets:

Road network (with walkable attributes)

Parks polygon layer (preferably with area in m²)

Address or population points (with optional age/household attributes)

District boundaries (for district-based analysis)

The scripts assume all data are projected correctly and topologically valid. All accessibility calculations are based on a 400 meter walking distance, in accordance with SDG 11.7.1 and the updated European Commission methodology (Poelman & Robe, 2021).

License
This repository and its content are provided under the MIT License.

Acknowledgements
This work was developed in the context of a bachelor's thesis at Palacký University Olomouc, based on the updated European Commission methodology for assessing access to green urban areas:
Poelman, H. & Robe, E. (2021): A short walk to the park?

Also inspired by:

Copernicus Urban Atlas methodology (DG REGIO, 2018)

UN-Habitat guidelines for SDG 11.7.1

Academic literature on socio-spatial accessibility (Jogdande & Bandyopadhyay, 2022; Ferenchak & Barney, 2024)

For any questions regarding this toolbox, please contact Petr Mikeska:

Instagram: @petamikeska

Email: piter.mikeska@gmail.com

