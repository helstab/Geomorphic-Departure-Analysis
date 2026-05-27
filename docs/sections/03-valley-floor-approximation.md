# 3 Valley Floor Approximation (Qvf)

Objective : Develop a polygon approximation of the Quaternary valley floor.

Purpose : Isolating the area of analysis to the valley floor allows for easier evaluation and relatability of surface types/origins within.


!!! note
    Notes: Many tools are available for identifying valley floors; this method employs a straightforward valley-filling strategy using an Inverse Distance Weighted Relative Elevation Model (IDW-REM), which represents the height above the primary flowline.


!!! note
    The complexity of surfaces within the boundary is highly variable (e.g., glacial, volcanic, tectonic, hillslope, etc.) and is dependent on local watershed forming processes over geologic timescales. The more accurately we can identify and classify surfaces by type/origin, the more confident we can be in our assessment of the GGL.


!!! note
    The initial Qvf polygon should be an overestimate rather than an underestimate, meaning it should include initial hillslopes and tributaries. The idea is that it will be easier to remove unhelpful data as more is learned about the valley.

Data Needs:

- LiDAR Digital Elevation Model
- Flowlines

Generalized Workflow:

1. Gather flowlines
2. Generate IDW-REM
3. Generate valley floor polygon
4. Generate valley floor features (centerline, transects, and stations)


## 3.1 Hydrography (Flowline) Preparation

Objective: Develop polyline approximation of the primary flowline of the Middle Fork Teanaway River, (current condition).

Purpose: Used to build flowline stations with elevation values to inspect longitudinal profile and build a relative elevation model that will be used to approximate the alluvial valley.


!!! note
    Notes: Bathymetric LiDAR was used in this example, approximating the thalweg rather than the water surface. The difference is assumed to be negligible in this example given very low surface flows (<5 cfs) and shallow pool depths at the time of LiDAR data acquisition. Users can also use non-bathymetric data but should consider how the results might impact the number of surface classes.


!!! note
    This approach can be expanded to include multiple flowlines within a catchment for broader valley bottom delineation.

Generalized Workflow:

1. Gather flowlines
2. Generate points (stations) along flow lines
3. Extract DEM values to points
4. Update and clean attribute table
5. Plot longitudinal profile
6. Identify and label valley segments


### 3.1.1 Gather flowlines (existing dataset, modeled, or user drawn) (e.g., NHD (3DEP) or LiDAR-derived flowlines)


![Figure 7](../figures/figure_07.png)

<small>**Figure 7**.</small>


!!! note
    Note: LiDAR-derived flowlines are used in this example. The main channel segments were merged into a single feature, and all dangling segments removed.


### 3.1.2 Generate stations (points) along the flow line (Generate Points Along a Line).


![Figure 8](../figures/figure_08.png)

<small>**Figure 8**.</small>


### 3.1.3 Extract LiDAR elevation to flow line stations (Extract Multi Values to Points).


![Figure 9](../figures/figure_09.png)

<small>**Figure 9**.</small>


!!! note
    Note : Multiple LiDAR datasets can be appended at the same time.


### 3.1.4 Alter (rename) Accumulation Fields (Alter Field)


![Figure 10](../figures/figure_10.png)

<small>**Figure 10**.</small>


![Figure 11](../figures/figure_11.png)

<small>**Figure 11**.</small>


### 3.1.5 Add “Valley_ID” Field with Data Type “Text”


![Figure 12](../figures/figure_12.png)

<small>**Figure 12**.</small>


### 3.1.6 Make a Scatter Plot and Inspect Flowline Longitudinal Profile (Make a Chart)


![Figure 13](../figures/figure_13.png)

<small>**Figure 13**.</small>


!!! note
    Notes : Select and investigate potential slope breaks and erroneous (non-thalweg) locations.


![Figure 14](../figures/figure_14.png)

<small>**Figure 14**.</small>


!!! note
    Notes : Upstream most slope break is a known geomorphic control where bedrock geology transitions from volcanic basalts to sedimentary sandstone. Middle highlighted points are erroneously high due to proximity to undercut hillslope. Lower slope break is the known downstream geomorphic control at the confluence of the Middle and West Forks of the Teanaway.


### 3.1.7 Highlight (select) and label stations by Valley ID using Calculate Field in the Attribute Table


![Figure 15](../figures/figure_15.png)

<small>**Figure 15**.</small>


![Figure 16](../figures/figure_16.png)

<small>**Figure 16**.</small>


![Figure 17](../figures/figure_17.png)

<small>**Figure 17**.</small>


![Figure 18](../figures/figure_18.png)

<small>**Figure 18**.</small>


![Figure 19](../figures/figure_19.png)

<small>**Figure 19**.</small>


!!! note
    Note: Alternatively, the user can create subsets of the station groups.


## 3.2 Inverse Distance Weighted Relative Elevation Model (IDW-REM)

Objective : Generate an IDW-REM by applying Inverse Distance Weighted interpolation to bathymetric flowline elevation data and subtracting results from surface elevations (DEM). Purpose : This first REM will be used to approximate the Qvf boundary by classifying elevations that are more likely within the Qvf. The filtered IDW-REM will then be used to create a Qvf polygon.


!!! note
    Note : Classification (grouping) of IDW-REM values is generally more accurate when evaluated between geomorphic controls (within a contiguous valley), meaning that the slope profile within the valley is distinct from the upstream and downstream reaches.


!!! note
    It is also important to note that the IDW-REM will initially extend beyond the area (laterally and longitudinally). The goal is to explore that data and identify the most likely valley floor boundaries.


!!! note
    A bathymetric IDW-REM ideally has a minimum value of zero, however the interpolated surface is rather coarse and will likely produce some values less than zero. Another explanation for values less than zero could be gravel pits dug below the thalweg in the valley floor and slope breaks between stations.


!!! note
    Symbology Tip: While the raster layer is highlighted, click the “Raster Layer” tab and set “resampling Type” to “Bilinear”, and set “Layer Blend” to “Multiply.”


![Figure 20](../figures/figure_20.png)

<small>**Figure 20**.</small>

General Workflow:

1. Generate IDW interpolated surface from flowline station elevations.
2. Generate Relative Elevation Model by subtracting IDW from DEM.
3. Identify relative elevation of hillslope break from IDW-REM symbology and 3D analyst.
4. Reclassify IDW-REM to group valley floor surfaces.
5. Convert reclassified raster to polygon.
6. Manually inspect and clean valley floor polygon.


### 3.2.1 Build Inverse Distance Weighted (IDW) interpolated raster from flowline station LiDAR elevations, where Valley_ID = Sandstone.


![Figure 21](../figures/figure_21.png)

<small>**Figure 21**.</small>


!!! note
    Notes : Depending on the extent of your LiDAR DEM and flowline(s) it may be beneficial to set a fixed search radius, as was done in this example, by first measuring the apparent maximum valley width (600m). Additionally, setting the Environments to align the IDW Raster with the LiDAR dataset produces cleaner results.


![Figure 22](../figures/figure_22.png)

<small>**Figure 22**.</small>


![Figure 23](../figures/figure_23.png)

<small>**Figure 23**.</small>


### 3.2.2 Generate Relative Elevation Model from IDW (IDW-REM) (Minus).


![Figure 24](../figures/figure_24.png)

<small>**Figure 24**.</small>


#### 3.2.2.1 SET the Environments to match the IDW-Raster


![Figure 25](../figures/figure_25.png)

<small>**Figure 25**.</small>


![Figure 26](../figures/figure_26.png)

<small>**Figure 26**.</small>


### 3.2.3 Manually classify REM symbology to determine the relative elevation value that fills the valley floor to the hillslope edge, or Qvf perimeter. ***

1. Leave primary symbology as “Stretch”
2. Choose a multi-band Color Scheme (Bathymetric displayed)
3. Set Stretch Type as Minimum Maximum
4. Check “Edit min/max values”
5. Adjust the Min and Max values to focus on valley floor


![Figure 27](../figures/figure_27.png)

<small>**Figure 27**.</small>

Min = 0m and Max = 10m


![Figure 28](../figures/figure_28.png)

<small>**Figure 28**.</small>


### 3.2.4 Inspect and Confirm Max value with IDW-REM Elevation Profiles in Exploratory Analysis

1. Add Elevation Source Layer (LiDAR).
2. Open Exploratory Analysis from “Analysis” Tab.
3. Draw and inspect profiles across the full extent of the valley floor.
4. Identify IDW-REM value at the hillslope edge.


![Figure 29](../figures/figure_29.png)

<small>**Figure 29**.</small>


!!! note
    Note: Hover over the profile to identify IDW-REM value at hillslope boundary.


![Figure 30](../figures/figure_30.png)

<small>**Figure 30**.</small>


![Figure 31](../figures/figure_31.png)

<small>**Figure 31**.</small>

Based on the elevation profile it appears the alluvial valleys relative elevations are safely less than 8m in vertical height from the bathymetric flowline.


### 3.2.5 Reclassify the IDW-REM using the valley floor fill threshold relative elevations (Reclassify).


!!! note
    Primary Symbology = Classify


!!! note
    Method = Manual Interval


!!! note
    Classes = 2


!!! note
    Upper Value = 8


![Figure 32](../figures/figure_32.png)

<small>**Figure 32**.</small>


![Figure 33](../figures/figure_33.png)

<small>**Figure 33**.</small>


### 3.2.6 Convert Reclassified Raster to Polygon (Raster to Polygon).


![Figure 34](../figures/figure_34.png)

<small>**Figure 34**.</small>


![Figure 35](../figures/figure_35.png)

<small>**Figure 35**.</small>


### 3.2.7 Manually Inspect and clean/simplify the valley floor polygon.*** Eliminate Polygon Part


![Figure 36](../figures/figure_36.png)

<small>**Figure 36**.</small>

Manual Editing using primary with the “Reshape” editing tool.


![Figure 37](../figures/figure_37.png)

<small>**Figure 37**.</small>


![Figure 38](../figures/figure_38.png)

<small>**Figure 38**.</small>


### 3.2.8 Discussion


## 3.3 Valley Floor Centerline, Stations, and Transects

Objective : Use the Polygon and supporting data*** to generate the valley centerline, centerline stations, transects, and transect stations.

Purpose : These products are fundamental to the analysis. The primary purpose of the valley centerline is to inform the orientation of the valley transects and their stations. In later steps we will classify transect stations based on their most plausible geomorphic origin, aiming to describe and isolate the Holocene fluvial process space (T1) from other surfaces within the alluvial valley. This will allow us to restrict, and fit Geomorphic Grade Line to the mean elevation of the T1 classified geomorphic surface.


!!! note
    Notes: Supporting data may include existing geomorphic/geologic/soil assessments, as well as intermediate GIS-derived features (e.g., contours, slope, aerial imagery), to inform the centerline position. In the MF Teanaway River example, we are incorporating work from Schanz, et al, 2019 to help with our interpretation of these surfaces.

General Workflow:

1. Generate valley floor centerline and stations.
2. Extract DEM values to stations.
3. Update and clean attribute table.
4. Generate transects along valley floor centerline.
5. Update and clean attribute table.
6. Inspect and clean transects.
7. Spatial join valley floor stations to transects.
8. Generate transect stations
9. Update and clean attribute table.
10. Extract DEM values to stations.


### 3.3.1 Create/Draw valley floor centerline. ***


![Figure 39](../figures/figure_39.png)

<small>**Figure 39**.</small>


!!! note
    Note: There are tools in ArcGIS Pro to identify the centerline of a polygon, but they require additional licenses. In this example there is a manually drawn polyline.


### 3.3.2 Generate stations along the centerline.


![Figure 40](../figures/figure_40.png)

<small>**Figure 40**.</small>


### 3.3.3 Alter Accumulation Fields


![Figure 41](../figures/figure_41.png)

<small>**Figure 41**.</small>


![Figure 42](../figures/figure_42.png)

<small>**Figure 42**.</small>


### 3.3.4 Add “Surface_Type” Field with Data Type “Text”


![Figure 43](../figures/figure_43.png)

<small>**Figure 43**.</small>

1. Extract LiDAR and IDW-REM values to Valley Centerline Stations ( Extract Multi Values to Points ).


![Figure 44](../figures/figure_44.png)

<small>**Figure 44**.</small>

1. Generate Valley Centerline Transects (Generate Transects Along Lines)


![Figure 45](../figures/figure_45.png)

<small>**Figure 45**.</small>


![Figure 46](../figures/figure_46.png)

<small>**Figure 46**.</small>


### 3.3.5 Inspect and modify transect orientation as needed by selecting the transect and using “Edit Vertices” editing tool.

- Valley curvature requires some transect modification to better orient a transect and

also present transect from crossing the valley floor twice


![Figure 47](../figures/figure_47.png)

<small>**Figure 47**.</small>


![Figure 48](../figures/figure_48.png)

<small>**Figure 48**.</small>


![Figure 49](../figures/figure_49.png)

<small>**Figure 49**.</small>


![Figure 50](../figures/figure_50.png)

<small>**Figure 50**.</small>


### 3.3.6 Clip Transects to Valley Floor Polygon using Modify Features Clip Tool, which will modify the existing feature rather than creating a new feature.


![Figure 51](../figures/figure_51.png)

<small>**Figure 51**.</small>

- Input Features: MFT_Flowline_GPAL_1m_Sandstone_VFP_Less8m_EPP
- Buffer Distance: 10m
- “Preserve”


![Figure 52](../figures/figure_52.png)

<small>**Figure 52**.</small>

- Target Features: MFT_VCL_GTAL_100m (Select All)


![Figure 53](../figures/figure_53.png)

<small>**Figure 53**.</small>


![Figure 54](../figures/figure_54.png)

<small>**Figure 54**.</small>


![Figure 55](../figures/figure_55.png)

<small>**Figure 55**.</small>


### 3.3.7 Spatially Join valley centerline stations IDs to transects. Right-click on Transect Layer > Join and Relates > Add Spatial Join.

- Target Features: Transects
- Join Features: VCL Stations
- Check “Keep All Target Features”
- Match Option: Intersect
- Check Permanently Join Fields
- Search Radius: 0.5m (half your VCL station interval)


![Figure 56](../figures/figure_56.png)

<small>**Figure 56**.</small>


![Figure 57](../figures/figure_57.png)

<small>**Figure 57**.</small>


!!! note
    Note: Set the search radius to half your station interval length (0.5m in this example)


### 3.3.8 Label Transects by Station Length


![Figure 58](../figures/figure_58.png)

<small>**Figure 58**.</small>


### 3.3.9 Flip (Orient) Transect Station IDs to make increasing upstream.


### 3.3.10 Right-Click on Station Attribute > Calculate Field.

- Code = where “n” is equal to the total number of transects.


![Figure 59](../figures/figure_59.png)

<small>**Figure 59**.</small>


![Figure 60](../figures/figure_60.png)

<small>**Figure 60**.</small>


![Figure 61](../figures/figure_61.png)

<small>**Figure 61**.</small>


### 3.3.11 Generate stations along transects (Generate Points Along Lines)


![Figure 62](../figures/figure_62.png)

<small>**Figure 62**.</small>


### 3.3.12 Alter Accumulation Fields and Delete unneeded Fields for a cleaner table (ORIG_ID, ORIG_FID, Join_Count, ORIG_FID).


![Figure 63](../figures/figure_63.png)

<small>**Figure 63**.</small>


![Figure 64](../figures/figure_64.png)

<small>**Figure 64**.</small>


### 3.3.13 Add surface elevation to transect stations (Extract Multi Values to Points).


![Figure 65](../figures/figure_65.png)

<small>**Figure 65**.</small>
