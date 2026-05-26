# Standard library
import os
import datetime

# Third-party libraries
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from scipy import interpolate, stats

# Local / specialized libraries
import arcpy

def read_layer(layer_name, set_workspace=True):
    """Read an ArcPy layer into a Pandas DataFrame and return metadata."""
    try:
        # Gather descriptive data
        desc = arcpy.Describe(layer_name)
        fc_full = desc.catalogPath
        fc_name = desc.baseName
        fc_gdb = desc.path
        fc_path = os.path.dirname(fc_gdb)

        # Convert to Pandas DataFrame
        fc_fields = [field.name for field in arcpy.ListFields(fc_full)]
        data = [row for row in arcpy.da.SearchCursor(fc_full, fc_fields)]
        df = pd.DataFrame(data, columns=fc_fields)

        # Optionally set environment
        if set_workspace:
            arcpy.env.workspace = fc_gdb

        # Preview output
        print(f"fc_name = {fc_name}")
        print(f"fc_gdb = {fc_gdb}")
        print(f"fc_path = {fc_path}")
        
        return fc_name, fc_gdb, fc_path, df

    except Exception as e:
        print(f"Error reading layer {layer_name}: {e}")
        return None

def long_plot(df, vcl_stations, elevation, interval=None, aspect=None, title=None):
    """
    Plot longitudinal profile with elevation statistics.

    Parameters:
        df (pd.DataFrame): Input data
        vcl_stations (str): Column name for station positions
        elevation (str): Column name for elevation values
        interval (int, optional): Segment length for subplots
        aspect (float or str, optional): Aspect ratio for plots
        title (str, optional): Plot title

    Returns:
        (fig, ax): Matplotlib figure and axis
    """
    x_max, x_min = df[vcl_stations].max(), df[vcl_stations].min()
    rise = df[elevation].max() - df[elevation].min()
    run = x_max - x_min
    slope = round((rise / run) * 100, 3) if run != 0 else None

    print(title)
    print(f"Profile Elevation Change = {rise:.2f} meters")
    print(f"Profile Length = {run:.2f} meters")
    print(f"Generic Slope (Rise/Run) = {slope if slope is not None else 'undefined'} %")
    print("-" * 50)

    def plot_segment(data, subtitle):
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.set_aspect(aspect if aspect is not None else 'auto')
        ax.set_title(subtitle)
        sns.lineplot(data=data.sort_values(vcl_stations), x=vcl_stations, y=elevation,
                     estimator='max', errorbar=None, color='red', linewidth=.5, linestyle='--', ax=ax, label='MAX')
        sns.lineplot(data=data.sort_values(vcl_stations), x=vcl_stations, y=elevation,
                     estimator='mean', errorbar='sd', color='orange', linewidth=.5, linestyle='--', ax=ax, label='MEAN ± 1STD')
        sns.lineplot(data=data.sort_values(vcl_stations), x=vcl_stations, y=elevation,
                     estimator='min', errorbar=None, color='blue', linewidth=.5, linestyle='--', ax=ax, label='MIN')
        ax.set(xlabel='VCL Station (m)', ylabel='Elevation (m)')
        ax.legend()
        return fig, ax

    if interval is None:
        fig, ax = plot_segment(df, title)
    else:
        for i in range(int(x_min), int(x_max), interval):
            subset = df.query(f"{vcl_stations} >= {i} & {vcl_stations} <= {i+interval}")
            fig, ax = plot_segment(subset, f"{title} [{i}-{i+interval}]")

    return fig, ax
    
def transect_plot(df, vcl_stations, transect_stations, elevation, transect, filtered_df=None, aspect=None):
    """
    Plot a single transect profile with transect and optional filtered statistics.

    Parameters:
        df (pd.DataFrame): Input data
        vcl_stations (str): Column name for valley centerline stations
        transect_stations (str): Column name for transect station positions
        elevation (str): Column name for elevation values
        transect (int/float): Transect identifier to filter
        filtered_df (pd.DataFrame, optional): Filtered table with mean/std values
        aspect (float or str, optional): Aspect ratio for plot

    Returns:
        fig (matplotlib.figure.Figure): Figure object
    """
    q = df.query(f"{vcl_stations} == {transect}")
    
    if q.empty:
        raise ValueError(f"No data found for transect {transect}")

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect(aspect if aspect is not None else 'auto')

    # Plot transect line
    sns.lineplot(
        data=q.sort_values(transect_stations),
        x=transect_stations, y=elevation,
        color="black", label="Surface", ax=ax
    )
    ax.set_title(f"Transect #{transect}")

    # Transect stats
    mean_val, std_val, min_val = q[elevation].mean(), q[elevation].std(), q[elevation].min()
    ax.axhline(y=mean_val, color="orange", linestyle=":", label="Transect Mean")
    ax.axhline(y=mean_val + std_val, color="orange", linestyle="--", linewidth=.75, label="Transect ±1 STD")
    ax.axhline(y=mean_val - std_val, color="orange", linestyle="--", linewidth=.75)
    ax.fill_between([q[transect_stations].min(), q[transect_stations].max()],
                    mean_val - std_val, mean_val + std_val, color="orange", alpha=.05)



    # Filtered stats
    if filtered_df is not None:
        # Filter filtered_df for the current transect
        e = filtered_df.query(f"{vcl_stations} == {transect}")
        
        if not e.empty:
            # Calculate mean and std from the elevation column
            filtered_mean = e[elevation].mean()
            filtered_std = e[elevation].std()

            # Plot filtered stats
            ax.axhline(y=filtered_mean, color="green", linestyle=":", linewidth=1.5, label="Filtered Mean")
            ax.axhline(y=filtered_mean + filtered_std, color="green", linestyle="--", linewidth=.75, label="Filtered ±1 STD")
            ax.axhline(y=filtered_mean - filtered_std, color="green", linestyle="--", linewidth=.75)
            ax.fill_between([q[transect_stations].min(), q[transect_stations].max()],
                            filtered_mean - filtered_std, filtered_mean + filtered_std, color="green", alpha=.05)



    # Min line
    ax.axhline(y=min_val, color="blue", linewidth=.75, label="Min")

    # Axis labels and grid
    ax.set(xlabel="Transect Station (m)", ylabel="Elevation (m)")
    ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
    ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
    ax.grid(which="major", color="grey", linewidth=0.5, alpha=0.5)
    ax.grid(which="minor", color="grey", linewidth=0.5, alpha=0.2)

    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    return fig, ax
    

def describe_stats(df, group, value, name):
    """
    Compute descriptive statistics for a grouped column.

    Parameters:
        df (pd.DataFrame): Input DataFrame
        group (str or list): Column(s) to group by
        value (str): Column to compute stats on
        name (str): Prefix for renamed stats columns

    Returns:
        pd.DataFrame: Grouped descriptive statistics with renamed columns and IQR
    """
    df_desc = (
        df.groupby(group)[value]
          .describe(percentiles=[.25, .50, .75])
          .rename(columns={
              'count': f'{name}_count',
              'mean': f'{name}_mean',
              'std': f'{name}_std',
              'min': f'{name}_min',
              '25%': f'{name}_25%',
              '50%': f'{name}_50%',
              '75%': f'{name}_75%',
              'max': f'{name}_max'
          })
          .reset_index()
    )
    df_desc[f'{name}_IQR'] = df_desc[f'{name}_75%'] - df_desc[f'{name}_25%']
    return df_desc

def boxplot(df, Field, Title= None):
    fig, ax = plt.subplots(figsize=(10, 5))
    print(df[Field].describe().round(3))
    sns.boxplot(x=df[Field], color='.75', width=.5, linewidth=.5, showmeans=True, meanprops={"marker":"x"},flierprops={'alpha':0.5,'markersize': 2, "marker": "."}, ax=ax).set_title(Title)
    ax.set(xlabel='Meters')
    plt.tight_layout()
    plt.show()
    return
    
def histplot(df, Field, Title=None, x_Label=None):
    
    fig, ax = plt.subplots(figsize = (10,5))
    mean = df[Field].mean()
    std = df[Field].std()
    sns.histplot(df[Field], binwidth=.2, color='black', stat="density", fill=False, linewidth=.5, kde=True).set_title(Title)
    plt.axvline(mean, 0,10,color='green')
    plt.axvline(mean+std, 0,10, color='green', linewidth=.5, linestyle='--')
    plt.axvline(mean-std, 0,10, color='green', linewidth=.5, linestyle='--')
    ax.fill_betweenx(y=np.linspace(0, ax.get_ylim()[1], 100), 
                        x1= mean - std, 
                        x2= mean + std,
                        color='green', 
                        alpha=0.05)
    if x_Label is None:
        ax.set(xlabel=f'{Field}')
    else:
       ax.set(xlabel=f'{x_Label}')
    plt.tight_layout()
    return
    

# Histplot compare
def histplot_compare(df, Field, Title=None, x_Label=None, filtered_df=None):
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot histogram and KDE for main DataFrame
    sns.histplot(df[Field], binwidth=.2, color='black', stat="density", fill=False, linewidth=.5, kde=True, ax=ax)
    ax.set_title(Title)

    # Plot mean and std for main DataFrame
    mean_main = df[Field].mean()
    std_main = df[Field].std()
    ax.axvline(mean_main, color='orange', label='Mean')
    ax.axvline(mean_main + std_main, color='orange', linewidth=.5, linestyle='--', label='±1 STD')
    ax.axvline(mean_main - std_main, color='orange', linewidth=.5, linestyle='--')



    # Plot mean and std for filtered DataFrame if provided
    if filtered_df is not None:
        mean_filtered = filtered_df[Field].mean()
        std_filtered = filtered_df[Field].std()
        ax.axvline(mean_filtered, color='green', label='Filtered Mean')
        ax.axvline(mean_filtered + std_filtered, color='green', linewidth=.5, linestyle='--', label='Filtered ±1 STD')
        ax.axvline(mean_filtered - std_filtered, color='green', linewidth=.5, linestyle='--')
        ax.fill_betweenx(y=np.linspace(0, ax.get_ylim()[1], 100),
                         x1=mean_filtered - std_filtered,
                         x2=mean_filtered + std_filtered,
                         color='green', alpha=0.05)

    # Set x-axis label
    if x_Label is None:
        ax.set(xlabel=f'{Field}')
    else:
        ax.set(xlabel=f'{x_Label}')

    ax.legend()
    plt.tight_layout()
    plt.show()



# Define a function to evalute GGL Spline fit
def spline_fit(df, x_col, y_col, k=3, s=None):
    """
    Fit a Univariate Spline to transect data.

    Parameters
    ----------
    df : DataFrame
        Input data containing x and y columns.
    x_col : str
        Column name for independent variable (station).
    y_col : str
        Column name for dependent variable (elevation).
    k : int, optional
        Polynomial order (default=3).
    s : float or None, optional
        Smoothing factor (default=None).

    Returns
    -------
    results : dict
        {
            "model": fitted spline object,
            "fits": DataFrame of fitted values,
            "figures": list of matplotlib figures
        }
    """

    # Prepare data
    x = df[x_col]
    y = df[y_col]
    model = interpolate.UnivariateSpline(x=x, y=y, k=k, s=s)

    # Fit values
    fit_col = f"Fit_{y_col}_poly{k}_s{s}"
    fit_col = fit_col.replace(".", "p")
    fits = pd.DataFrame({x_col: range(int(x.min()), int(x.max()))})
    fits[fit_col] = model(fits[x_col])
    knots = model.get_knots()
    
    # Residuals
    residuals = y - model(x)

    # Summary stats
    rise = y.max() - y.min()
    run = x.max() - x.min()
    slope_percent = (rise / run) * 100 if run != 0 else None

    print("**** SPLINE FIT RESULTS ****")
    print("-" * 25)
    print(f"Data Length = {x.count()}")
    print(f"Polynomial Order = {k}")
    print(f"Smoothing Factor = {s}")
    print("Total number of knots =", len(knots))
    print("-" * 25)
    print(f"Rise = {rise:.2f} m, Run = {run:.2f} m")
    print(f"Generic Slope = {slope_percent:.2f}%")
    print("-" * 25)
    print(f"Average Slope = {model(fits[x_col], 1).mean() * 100:.2f}%")
    print(f"Residual Sum of Squares = {model.get_residual():.4f}")
    print(f"Residual Variance = {model.get_residual()/len(x):.4f}")


    # Figures
    figs = []

    # Fit plot
    fig1, ax1 = plt.subplots(figsize=(12,6))
    ax1.plot(x, y, color="black", linewidth=0.8, label="Surface")
    ax1.plot(fits[x_col], fits[fit_col], "--", color="red", linewidth=0.8, label=f"Spline k={k}, s={s}")
#     ax1.scatter(model.get_knots(), model(model.get_knots()), color="orange", linewidth=0.8, marker="x", label="Knots")
    ax1.plot(knots, model(knots), marker='x' , markersize=10, color="orange", linewidth=.8, linestyle="-", label="Linear Knot Line")
    ax1.vlines(x=knots, ymin=y.min(), ymax=model(knots), color="orange", linewidth=1)
    ax1.set(xlabel="Station (m)", ylabel="Elevation (m)", title="Spline Fit")
    ax1.legend()
    figs.append(fig1)

    # Residual plot
    fig2, ax2 = plt.subplots(figsize=(12,6))
    ax2.plot(x, residuals, "--", color="red", linewidth=0.8)
    ax2.set(xlabel="Station (m)", ylabel="Residuals (m)", title="Residuals Plot")
    figs.append(fig2)

    # Residual distribution
    fig3, ax3 = plt.subplots(figsize=(12,6))
    sns.boxplot(x=residuals, color=".75", width=.5, showmeans=True,
                meanprops={"marker":"x"}, flierprops={'alpha':0.5,'markersize':2,"marker":"."}, ax=ax3)
    ax3.set(xlabel="Residuals (m)", title="Residuals Distribution")
    figs.append(fig3)

    # First derivative (slope)
    fig4, ax4 = plt.subplots(figsize=(12,6))
    ax4.plot(fits[x_col], model(fits[x_col], 1), "--", color="red", linewidth=0.8)
    ax4.set(xlabel="Station (m)", ylabel="Slope (%)", title="Spline Slope")
    ax4.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    figs.append(fig4)

    # Second derivative (only valid if k >= 2)
    if k >= 2:
        fig_curv, ax_curv = plt.subplots(figsize=(12,6))
        ax_curv.plot(fits[x_col], model(fits[x_col], 2), "--", color="red", linewidth=0.8)
        ax_curv.set(xlabel="Station (m)", ylabel="Curvature", title="Spline Curvature")
        figs.append(fig_curv)

    return (model, fits, figs)

def csv_join(df, dir_path, fc, join_field, do_join=True):
    """
    Save a DataFrame to CSV with today's date appended to the second column name.
    Optionally join the CSV to a feature class using arcpy, without duplicating the join field.
    """

    # Get second column name
    model_name = df.columns[1]

    # Format today's date as DDMMMYYYY (e.g., 01DEC2025)
    today_str = datetime.datetime.today().strftime("%d%b%Y").upper()

    # Build output filename safely
    output = os.path.join(dir_path, f"{model_name}_{today_str}.csv")

    # Write CSV
    df.to_csv(output, index=False)

    # Optionally join to feature class
    if do_join:
        # Only append fields that are NOT the join field
        fields_to_add = [f for f in df.columns if f != join_field]
        arcpy.management.JoinField(fc, join_field, output, join_field, fields_to_add)

    return output
    
def long_plot_compare(df, df_filtered, vcl_stations, elevation, interval=None, title="Longitudinal Profile"):
    x_max, x_min = df[vcl_stations].max(), df[vcl_stations].min()
    figs = []

    if interval is None:
        # Plot the entire dataset as one segment
        fig, ax = plt.subplots(figsize=(15, 8))

        # Full dataset
        sns.lineplot(
            data=df.sort_values(vcl_stations),
            x=vcl_stations, y=elevation,
            estimator='max', errorbar=None,
            color='darkred', linewidth=1, linestyle='--', ax=ax, label='Qvf (MAX)'
        )
        sns.lineplot(
            data=df.sort_values(vcl_stations),
            x=vcl_stations, y=elevation,
            estimator='mean', errorbar='sd',
            color='orange', linewidth=1, linestyle='--', ax=ax, label='Qvf (MEAN)'
        )
        sns.lineplot(
            data=df.sort_values(vcl_stations),
            x=vcl_stations, y=elevation,
            estimator='min', errorbar=None,
            color='darkblue', linewidth=1, linestyle='--', ax=ax, label='MIN'
        )

        # Filtered dataset
        sns.lineplot(
            data=df_filtered.sort_values(vcl_stations),
            x=vcl_stations, y=elevation,
            estimator='max', errorbar=None,
            color='red', linewidth=.5, linestyle='--', ax=ax, label='Qvf_filtered (Max)'
        )
        sns.lineplot(
            data=df_filtered.sort_values(vcl_stations),
            x=vcl_stations, y=elevation,
            estimator='mean', errorbar=("sd", 1),
            color='green', linewidth=.5, linestyle='--', ax=ax, label='Qvf_filtered (Mean)'
        )

        ax.set(xlabel='Centerline Station (m)', ylabel='Elevation (m)', title=title)
        ax.legend()
        figs.append(fig)

    else:
        # Plot in slices based on interval
        for i in range(int(x_min), int(x_max), interval):
            query_str = f"{vcl_stations} >= {i} & {vcl_stations} <= {i+interval}"
            fig, ax = plt.subplots(figsize=(15, 8))

            # Full dataset
            sns.lineplot(
                data=df.query(query_str).sort_values(vcl_stations),
                x=vcl_stations, y=elevation,
                estimator='max', errorbar=None,
                color='darkred', linewidth=1, linestyle='--', ax=ax, label='Qvf (MAX)'
            )
            sns.lineplot(
                data=df.query(query_str).sort_values(vcl_stations),
                x=vcl_stations, y=elevation,
                estimator='mean', errorbar='sd',
                color='orange', linewidth=1, linestyle='--', ax=ax, label='Qvf (MEAN)'
            )
            sns.lineplot(
                data=df.query(query_str).sort_values(vcl_stations),
                x=vcl_stations, y=elevation,
                estimator='min', errorbar=None,
                color='darkblue', linewidth=1, linestyle='--', ax=ax, label='MIN'
            )

            # Filtered dataset
            sns.lineplot(
                data=df_filtered.query(query_str).sort_values(vcl_stations),
                x=vcl_stations, y=elevation,
                estimator='max', errorbar=None,
                color='red', linewidth=.5, linestyle='--', ax=ax, label='Qvf_filtered (Max)'
            )
            sns.lineplot(
                data=df_filtered.query(query_str).sort_values(vcl_stations),
                x=vcl_stations, y=elevation,
                estimator='mean', errorbar=("sd", 1),
                color='green', linewidth=.5, linestyle='--', ax=ax, label='Qvf_filtered (Mean)'
            )

            ax.set(xlabel='Centerline Station (m)', ylabel='Elevation (m)', title=f"{title} [{i}-{i+interval}]")
            ax.legend()
            figs.append(fig)

    return figs

# def create_rem_from_tin(fc_name, height_field, lidar_dem, gdb, mask=None):
    # """
    # Create a Relative Elevation Model (REM) by:
    # 1. Building a TIN from transect station points.
    # 2. Converting the TIN to a raster surface with cell size matching the LiDAR DEM.
    # 3. Subtracting the rasterized TIN from the LiDAR DEM.
    # 4. Optionally clipping outputs to a polygon mask.
    # 5. Adding the REM to the active ArcGIS Pro map.

    # Parameters
    # ----------
    # fc_name : str
        # Path to the transect station feature class.
    # height_field : str
        # Field name used as elevation (e.g., column two from fit_vf_less8m_table).
    # lidar_dem : str
        # Path to the existing LiDAR DEM raster.
    # workspace : str
        # Folder or geodatabase where outputs will be saved.
    # mask : str, optional
        # Path to a polygon feature class or shapefile used to clip the raster outputs.
        # Default is None (no clipping).
    # """

    # # Describe output names
    # height_field= height_field.replace(".", "p")
    # out_tin = f"{gdb}/tin_{height_field}"
    # out_raster = f"{gdb}/tin_raster_{height_field}"
    # out_raster_clip = f"{gdb}/tin_raster_{height_field}_clip_{mask}"
    # out_raster_clip_layer = f"tin_raster_{height_field}_clip_{mask}"
    # out_rem = f"{gdb}/tin_rem_{height_field}"
    # out_rem_layer = f"tin_rem_{height_field}"
    # out_rem_clip = f"{gdb}/tin_rem_{height_field}_clip_{mask}"
    # out_rem_clip_layer = f"tin_rem_{height_field}_clip_{mask}"


    # # Describe input feature class to get spatial reference and extent
    # arcpy.env.overwriteOutput = True
    
    # desc = arcpy.Describe(fc_name)
    # extent = desc.extent
    # extent_str = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
    
    # desc_dem = arcpy.Describe(lidar_dem)
    # cell_size = desc_dem.meanCellHeight  # or meanCellWidth (usually square cells)`
    # spatial_ref = desc_dem.spatialReference

    # # Step 1: Create TIN
    # arcpy.ddd.CreateTin(
        # out_tin,
        # spatial_ref,
        # [[fc_name, height_field, "Mass_Points"]],
        # "CONSTRAINED_DELAUNAY"
    # )
    # print(f"TIN created:\n{out_tin}")
    # print("-" * 50)

    # # Step 2: Convert TIN to Raster with cell size from LiDAR DEM
    # arcpy.ddd.TinRaster(
        # out_tin,
        # out_raster,
        # "FLOAT",
        # "LINEAR",
        # f"CELLSIZE {cell_size}"
    # )
    # print(f"TIN converted to raster with cell size {cell_size}:\n{out_raster}")
    # print("-" * 50)

    # # Step 3: Subtract TIN raster from LiDAR DEM 
    # rem_raster = arcpy.sa.Raster(lidar_dem) - arcpy.sa.Raster(out_raster)

    # # Save REM raster
    # rem_raster.save(out_rem)
    # print(f"Relative Elevation Model created:\n{out_rem}")
    # print("-" * 50)

    # # Step 4: Clip outputs if mask is provided
    # if mask:
        # print(f"Mask enabled:\n{mask}")
        # print("-" * 50)
        # raster_clipped = arcpy.sa.ExtractByMask(out_raster, mask)
        # raster_clipped.save(out_raster_clip)
        # print(f"TIN Raster masked to {mask}:\n{out_rem}")
        # print("-" * 50)
        # rem_raster_clipped = arcpy.sa.ExtractByMask(rem_raster, mask)
        # rem_raster_clipped.save(out_rem_clip)
        # print(f"Relative Elevation Model masked to {mask}:\n{out_rem}")
        # print("-" * 50)
    
    # # Step 5: Add REM to active map
    # arcpy.MakeRasterLayer_management(out_raster_clip, out_raster_clip_layer)
    # arcpy.MakeRasterLayer_management(out_rem, out_rem_layer)
    # arcpy.MakeRasterLayer_management(out_rem_clip, out_rem_clip_layer)
    

def create_rem_from_tin(fc_name, height_field, lidar_dem, gdb, mask=None):
    """
    Create a Relative Elevation Model (REM) by:
    1. Building a TIN from transect station points.
    2. Converting the TIN to a raster surface with cell size matching the LiDAR DEM.
    3. Subtracting the rasterized TIN from the LiDAR DEM.
    4. Optionally clipping outputs to a polygon mask.
    5. Adding the REM to the active ArcGIS Pro map.

    Parameters
    ----------
    fc_name : str
        Path to the transect station feature class.
    height_field : str
        Field name used as elevation (e.g., column two from fit_vf_less8m_table).
    lidar_dem : str
        Path to the existing LiDAR DEM raster.
    gdb : str
        Folder or geodatabase where outputs will be saved.
    mask : str, optional
        Path to a polygon feature class or shapefile used to clip the raster outputs.
        Default is None (no clipping).
    """

        

    # Describe output names (sanitize field name for dataset naming)
    fc_path = os.path.dirname(gdb)
    height_field = height_field.replace(".", "p")
    out_tin = f"{fc_path}/tin_{height_field}"
    out_raster = f"{gdb}/tin_raster_{height_field}"
    out_rem = f"{gdb}/tin_rem_{height_field}"
    out_raster_layer = f"tin_raster_{height_field}"
    out_rem_layer = f"tin_rem_{height_field}"

    # ArcPy environment
    arcpy.env.overwriteOutput = True

    # Describe inputs
    desc = arcpy.Describe(fc_name)
    extent = desc.extent
    extent_str = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"

    desc_dem = arcpy.Describe(lidar_dem)
    cell_size = desc_dem.meanCellHeight  
    spatial_ref = desc_dem.spatialReference

    # Step 1: Create TIN
    arcpy.ddd.CreateTin(
        out_tin,
        spatial_ref,
        [[fc_name, height_field, "Mass_Points"]],
        "CONSTRAINED_DELAUNAY"
    )
    print(f"TIN created:\n{out_tin}")
    print("-" * 50)

    # Step 2: Convert TIN to Raster with cell size from LiDAR DEM
    arcpy.ddd.TinRaster(
        out_tin,
        out_raster,
        "FLOAT",
        "LINEAR",
        f"CELLSIZE {cell_size}"
    )
    print(f"TIN converted to raster with cell size {cell_size}:\n{out_raster}")
    print("-" * 50)

    # Step 3: Subtract TIN raster from LiDAR DEM → REM
    rem_raster = arcpy.sa.Raster(lidar_dem) - arcpy.sa.Raster(out_raster)

    # Save REM raster
    rem_raster.save(out_rem)
    print(f"Relative Elevation Model created:\n{out_rem}")
    print("-" * 50)

    # Step 4: Clip outputs if mask is provided
    if mask is not None:
        # Use a safe name for outputs derived from the mask dataset
        try:
            mask_name = arcpy.Describe(mask).baseName
        except Exception:
            # Fallback if Describe fails (e.g., if a bare string)
            mask_name = os.path.splitext(os.path.basename(str(mask)))[0]

        out_raster_clip = f"{gdb}/tin_raster_{height_field}_clip_{mask_name}"
        out_rem_clip = f"{gdb}/tin_rem_{height_field}_clip_{mask_name}"
        out_raster_clip_layer = f"tin_raster_{height_field}_clip_{mask_name}"
        out_rem_clip_layer = f"tin_rem_{height_field}_clip_{mask_name}"

        print(f"Mask enabled:\n{mask}")
        print("-" * 50)

        # Clip rasterized TIN
        raster_clipped = arcpy.sa.ExtractByMask(out_raster, mask)
        raster_clipped.save(out_raster_clip)
        print(f"TIN Raster masked to {mask}:\n{out_raster_clip}")
        print("-" * 50)

        # Clip REM
        rem_raster_clipped = arcpy.sa.ExtractByMask(rem_raster, mask)
        rem_raster_clipped.save(out_rem_clip)
        print(f"Relative Elevation Model masked to {mask}:\n{out_rem_clip}")
        print("-" * 50)

        # Step 5: Add layers to active map (clipped + unclipped REM)
        arcpy.MakeRasterLayer_management(out_raster_clip, out_raster_clip_layer)
        arcpy.MakeRasterLayer_management(out_rem, out_rem_layer)
        arcpy.MakeRasterLayer_management(out_rem_clip, out_rem_clip_layer)
    else:
        # Step 5: Add layers to active map (unclipped only)
        arcpy.MakeRasterLayer_management(out_raster, out_raster_layer)
        arcpy.MakeRasterLayer_management(out_rem, out_rem_layer)
