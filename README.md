# Beijing Urban Flood Inundation Simulation (SCS-CN Model)
# 北京市中心城区雨洪淹没风险模拟框架 (Version 2)

## 1. Project Overview (项目简介)
This project implements a **Passive Inundation Simulation** workflow based on the **SCS-CN (Soil Conservation Service Curve Number)** hydrological model. 
It focuses on the **Six Urban Districts of Beijing** (Dongcheng, Xicheng, Chaoyang, Haidian, Fengtai, Shijingshan) to assess flood risks under extreme rainfall scenarios (100-year return period).

**Key Features:**
*   **Comparative Analysis:** Simulates flood risks for **2021** vs. **2031** land use scenarios.
*   **High-Resolution:** Utilizes Level-12 micro-watersheds (HydroATLAS) and 30m DEM.
*   **Dynamic Mapping:** Implements dynamic Land Use-to-CN mapping within the Python pipeline.
*   **Output:** Flood inundation depth (meters) for 100-year return period events.

---

## 2. Methodology & Data (方法与数据)

### 2.1 Core Algorithm
1.  **Runoff Generation:** SCS-CN Model ($Q = \frac{(P-Ia)^2}{P-Ia+S}$).
2.  **Inundation Process:** Passive Inundation (Bathtub Model) using Binary Search to match runoff volume with terrain depression volume.

### 2.2 Scenarios (情景设置)
| Scenario Name | Year | Rainfall (P) | Land Use Data | Description |
| :--- | :--- | :--- | :--- | :--- |
| **2021_100yr** | 2021 | 297.343 mm | `LU_2021.tif` | Baseline Scenario |
| **2031_100yr** | 2031 | 313.994 mm | `LU_2031.tif` | Future Projection |

### 2.3 CN Value Mapping Rules (CN参数表)
Based on collaborator specifications (Converted to 0-100 scale):
*   **Code 1-4 (Green Space/Permeable):** CN = 15
*   **Code 5 (Impervious/Built-up):** CN = 100
*   **Code 7 (Water Bodies):** CN = 30
*   **Code 8 (Semi-permeable):** CN = 85

---

## 3. Directory Structure (工程目录)

To run this project, please ensure the local directory follows this structure:

```text
Project_Root/
├── 00_Doc/              # Documentation & References
├── 01_Input/
│   └── version 2/       # [Large Files] Input Data (Not on GitHub)
│       ├── Beijing_DEM_30m.tif
│       ├── Beijing_SixDistricts_Watersheds_L12.shp
│       ├── LU_2021.tif
│       └── LU_2031.tif
├── 03_Output/
│   └── version 2/       # [Large Files] Simulation Results (Not on GitHub)
│       └── Merged_Results/
└── 04_Scripts/          # Source Code
    ├── GEE_Data_Prep_v2.js        # Google Earth Engine Script
    ├── Local_Simulation_v2.py     # Main Simulation Logic
    └── Local_Merge_v2.py          # Result Merging Script
```

---

## 4. Usage (使用指南)

### Step 1: Data Preparation (GEE)
*   Run `04_Scripts/GEE_Data_Prep_v2.js` in Google Earth Engine.
*   Export the DEM and Watersheds (Level 12) to `01_Input/version 2`.

### Step 2: Local Simulation (Python in QGIS)
*   Open **QGIS 3.36** -> Python Console.
*   Load `04_Scripts/Local_Simulation_v2.py`.
*   **Configuration:** Update `BASE_DIR` in the script to your local path.
*   Run the script. It will iterate through all micro-watersheds and calculate flood depths for both 2021 and 2031 scenarios.

### Step 3: Merge Results
*   Run `04_Scripts/Local_Merge_v2.py` in QGIS.
*   The final merged raster files will be generated in `03_Output/version 2/Merged_Results`.

---

## 5. Requirements
*   QGIS 3.x (with PyQGIS)
*   Python Libraries: `numpy`, `gdal` (Bundled with QGIS)

## 6. Data Access
The datasets used in this project are available upon request. Please send an email to **`evanpan.labs+GithubFloodData@gmail.com`** to obtain the download link.

---
*Author: Evan Pan @ PKU-CAL*
*Last Updated: Dec 18, 2025*