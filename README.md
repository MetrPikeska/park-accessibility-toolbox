# Park Accessibility Toolbox

Toolbox for assessing the availability of green spaces and parks for urban residents using network analysis and GIS scripts. This toolbox was developed as part of the bachelor's thesis at the Department of Geoinformatics, Faculty of Science, Palacký University Olomouc.

---

## Author
**Petr Mikeska**  
Department of Geoinformatics, Faculty of Science, Palacký University Olomouc  
Bachelor Thesis  
Year: 2025  

- Instagram: [@petamikeska](https://www.instagram.com/petamikeska)
- Email: piter.mikeska@gmail.com

---

## Thesis Title
**English:** Assessing the availability of green spaces and parks for urban residents  
**Czech:** Hodnocení dostupnosti zelených ploch a parků pro obyvatele měst

### Thesis Assignment
The goal of the thesis is to calculate the accessibility of green areas and parks within a city based on the methodology of the European Commission Directorate General for Regional and Urban Policy (updated 2021 version). Alternative procedures and input data will also be considered. Suitable available data will be selected, and the results influenced by different inputs and methodologies will be compared and evaluated. The student will use and, if necessary, modify scripts for ArcGIS Pro available as part of the updated 2021 methodology. Any modifications will be described and justified. The accessibility will be assessed for the city of Olomouc and one other selected city in the Czech Republic.

---

## Toolbox Content
This repository contains Python scripts for ArcGIS Pro environment:

- **1_NetworkDataset.py**  
  Creates a network dataset from road input data for pedestrian analysis.

- **2_PointAlongLine.py**  
  Generates points along park boundaries and selects those near road networks.

- **3_NetworkAnalysis.py**  
  Calculates pedestrian service areas for parks using a network dataset and dissolves them into accessibility zones.

- **4_AnalyzeParkAccesibility.py**  
  Analyzes green space accessibility within city districts, calculates covered population ratios.

- **5_GenerateHexGrid.py**  
  Generates a hexagonal tessellation over a study area and clips it accordingly.

- **6_HexPopulationAcces.py**  
  Calculates population statistics per hexagon, distinguishing between accessible and non-accessible populations.

---

## Requirements
- ArcGIS Pro (2.9+ recommended)
- Python 3.x (ArcGIS Pro environment)
- ArcPy library
- Network Analyst Extension (licensed)

---

## Usage
Each script is intended to be run independently with parameters provided through ArcGIS Pro toolboxes or Python command line. Ensure proper datasets are prepared (roads, parks, address points, etc.) before running the scripts.

The scripts assume that input data follow basic spatial data quality rules (correct projection, topology, attribute integrity).

---

## License
This repository and its content are provided under the MIT License.

---

## Acknowledgements
This work was developed in the context of the bachelor's thesis at Palacký University Olomouc and based on the European Commission's updated green space accessibility methodology (Poelman, Robe, 2021).

---

For any questions regarding this toolbox, please contact **Petr Mikeska**:  
- Instagram: [@petamikeska](https://www.instagram.com/petamikeska)  
- Email: piter.mikeska@gmail.com
