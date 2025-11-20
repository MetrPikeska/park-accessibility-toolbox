# Park Accessibility Toolbox for ArcGIS Pro

This repository contains an ArcGIS Pro toolbox designed to assess the accessibility of urban green spaces. The tools automate key geoprocessing tasks, from creating a network dataset to analyzing population access within a specified walking distance. The methodology is based on the European Commission's 2021 guide, "A short walk to the park?".

This project was developed as part of a bachelor's thesis at the Department of Geoinformatics, Palacký University Olomouc (2025).

---

## Workflow Overview

The toolbox follows a sequential workflow, where the output of one tool often serves as the input for another.

```
[Input Data]
     |
     v
[1. Network Dataset] -> Creates pedestrian network from roads.
     |
     v
[2. Park Entrances] -> Generates access points to parks.
     |
     v
[3. Service Area] -> Calculates walkable areas around parks.
     |   \
     |    \__________________________________________
     |                                             |
     v                                             v
[4. District Analysis] -> Aggregates results by   [6. Hexagon Analysis] -> Aggregates results
     |                     administrative unit.        |                     into a uniform grid.
     |                                             |
[Reports & Maps]                                [5. Hexagon Grid] -> Creates the grid for analysis.
```

---

## Toolbox Scripts

The toolbox consists of six main Python scripts:

| # | Script Name                 | Description                                                                                              |
|---|-----------------------------|----------------------------------------------------------------------------------------------------------|
| 1 | `1_NetworkDataset.py`         | Creates a routable pedestrian network dataset from a road layer.                                         |
| 2 | `2_PointAlongLine.py`         | Generates potential park entrance points along park boundaries that are close to the road network.       |
| 3 | `3_NetworkAnalysis.py`        | Calculates the service area (walkable zone) from the park entrances using the network dataset.           |
| 4 | `4_AnalyzeParkAccesibility.py`| Analyzes accessibility by administrative districts, calculating population and area coverage statistics. |
| 5 | `5_GenerateHexGrid.py`        | Creates a hexagonal grid over the study area for spatially uniform analysis.                             |
| 6 | `6_HexPopulationAcces.py`     | Assigns population and accessibility statistics to each hexagon in the grid.                               |

---

## Requirements

-   **ArcGIS Pro** (version 3.0 or later recommended)
-   **Network Analyst Extension** (licensed and enabled)
-   Prepared input datasets (see Usage section)

---

## How to Use

1.  **Prepare Your Data:**
    -   A **road network** feature class (polylines).
    -   A **parks** feature class (polygons).
    -   **Population points** or address points (points).
    -   **District boundaries** (polygons, for district-level analysis).
    *Ensure all layers are in the same projected coordinate system.*

2.  **Set Up the Toolbox:**
    -   Clone or download this repository.
    -   In ArcGIS Pro, add the `Accessibility_of_urban_greenery.atbx` toolbox to your project.

3.  **Run the Tools Sequentially:**
    -   **Tool 1: Network Dataset:** Use your road network to create the pedestrian network.
    -   **Tool 2: Park Entrances:** Generate park access points using the parks and road layers.
    -   **Tool 3: Service Area:** Calculate the walkable area from the park entrances.
    -   **Tool 4 or 6:** Choose your analysis unit:
        -   Run **Tool 4** for analysis by administrative districts.
        -   Run **Tool 5** and then **Tool 6** for a hexagon-based analysis.

---

## Author & Contact

**Petr Mikeska**  
Department of Geoinformatics, Palacký University Olomouc  
-   **Website:** [petrmikeska.cz](https://petrmikeska.cz)
-   **GitHub:** [MetrPikeska](https://github.com/MetrPikeska)
-   **Email:** piter.mikeska@gmail.com
-   **Instagram:** [@petamikeska](https://www.instagram.com/petamikeska)

This work is based on the bachelor's thesis "Assessing the availability of green spaces and parks for urban residents" (2025).  
**Thesis Web:** [https://www.geoinformatics.upol.cz/dprace/bakalarske/mikeska25/](https://www.geoinformatics.upol.cz/dprace/bakalarske/mikeska25/)

---

## License

This project is licensed under the **MIT License**.
