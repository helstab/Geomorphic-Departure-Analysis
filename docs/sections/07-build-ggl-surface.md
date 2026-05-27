# 7 Build GGL Surface


## 7.1 Conditional GGL Filling


### 7.1.1 Fill to Zero

Use Raster Calculator and Con function to create a new raster where cells with relative elevation values less than or equal to zero are replaced with GGL-Raster values, and all other cells remain as LiDAR DEM.

Con(GGL_REM <=0, GGL_Raster, DEM)


![](../figures/figure_143.png)


![](../figures/figure_144.png)


### 7.1.2 Fill to -1STD

Where REM is less than -0.45m, fill to zero, else DEM

Con( (REM < x) & (REM


![](../figures/figure_145.png)


![](../figures/figure_146.png)


## 7.2 Reclassify GGL-REM by Surface Types


![](../figures/figure_147.png)


![](../figures/figure_148.png)


## 7.3 Design Surface Polygons


![](../figures/figure_149.png)


### 7.3.1 Add Fields


![](../figures/figure_150.png)

Update “Design_Surface_Type”

- -1 = “Potential Fill”
- 0 = “Target”
- +1 = “Potential Cut”


![](../figures/figure_151.png)

Update Design Surface Types from Filled2MinusSTD REM


![](../figures/figure_152.png)


## 7.4 Volume Calculations


### 7.4.1 Zonal Statistics as a Table


![](../figures/figure_153.png)


### 7.4.2 Join Table to Feature


![](../figures/figure_154.png)


![](../figures/figure_155.png)


### 7.4.3 Calculate Field for “Cy”


![](../figures/figure_156.png)


### 7.4.4 Calculate Geometry for “Acres”


![](../figures/figure_157.png)


![](../figures/figure_158.png)
