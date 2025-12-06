import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np


# Utility Formatters
def format_lap_time(seconds):
    """Format lap time in MM:SS.mmm format for human-readable tooltips."""
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{minutes:02}:{sec:02}.{millis:03}"


def format_seconds_to_mmss(seconds):
    """Format seconds into MM:SS string for Y-axis tick labels."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02}:{secs:02}"


# Lap Time Chart
def plot_lap_times(lap_time_df: pd.DataFrame, color_map: dict):
    """
    Create a line chart showing lap times per driver over the race distance.

    Input data comes from OpenF1's /laps endpoint, processed and filtered.
    Pit exit laps (e.g. out-laps) are flagged and marked in tooltips.

    Args:
        lap_time_df (pd.DataFrame): Cleaned lap data.
        color_map (dict): Driver acronym to team color.

    Returns:
        Plotly Figure object
    """
    if lap_time_df.empty:
        st.warning("No lap data available for this session.")
        return None

    lap_time_df["formatted_lap_time"] = lap_time_df["lap_duration"].apply(format_lap_time)
    lap_time_df["is_pit_out_lap"] = lap_time_df["is_pit_out_lap"].fillna(False).astype(bool)

    fig = go.Figure()

    for driver in lap_time_df["name_acronym"].unique():
        driver_data = lap_time_df[lap_time_df["name_acronym"] == driver].copy()
        driver_data = driver_data.sort_values("lap_number")

        # Custom tooltip for each data point
        hover_texts = [
            f"<b>{driver}: {row['driver_number']}</b><br>"
            f"Lap: {row['lap_number']}<br>"
            f"Lap Time: {row['formatted_lap_time']}"
            + ("<br>🔧 PIT" if row['is_pit_out_lap'] else "")
            for _, row in driver_data.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=driver_data["lap_number"],
            y=driver_data["lap_duration"],
            mode="lines+markers",
            name=driver,
            marker=dict(color=color_map.get(driver, "gray")),
            line=dict(color=color_map.get(driver, "gray")),
            hoverinfo="text",
            hovertext=hover_texts,
        ))

    fig.update_layout(
        title="Lap Times by Driver",
        xaxis_title="Lap",
        yaxis_title="Lap Time (MM:SS)",
        hovermode="closest",
        height=600,
    )

    # Format Y-axis to readable MM:SS format
    tick_vals = sorted(lap_time_df["lap_duration"].dropna().unique())
    tick_vals = [round(val, 0) for val in tick_vals if 60 <= val <= 180]  # clean range
    tick_vals = sorted(set(tick_vals))[::5]  # fewer ticks, every ~5 sec

    fig.update_yaxes(
        tickvals=tick_vals,
        ticktext=[format_seconds_to_mmss(val) for val in tick_vals],
    )

    return fig


# Tire Strategy Chart
# Map Pirelli compounds to colors matches standard F1 graphics
COMPOUND_COLORS = {
    "SOFT": "red",
    "MEDIUM": "yellow",
    "HARD": "white",
    "INTERMEDIATE": "green",
    "WET": "blue",
    "Unknown": "gray"
}


def plot_tire_strategy(stints_df, color_map: dict):
    """
    Show tire compound strategy for each driver using horizontal bars.

    Uses OpenF1 /stints endpoint to show start/end lap and compound used.

    Args:
        stints_df (pd.DataFrame): Cleaned tire stint data.
        color_map (dict): Driver acronym to team color.

    Returns:
        Plotly Figure object
    """
    if stints_df.empty:
        st.warning("No stint data available.")
        return None

    fig = go.Figure()

    for _, row in stints_df.iterrows():
        compound = row["compound"].upper()
        acronym = row["name_acronym"]

        fig.add_trace(go.Bar(
            x=[row["lap_count"]],  # Width of bar = number of laps
            y=[acronym],  # One row per driver
            base=row["lap_start"],  # Start lap (bar offset)
            orientation="h",
            marker=dict(color=COMPOUND_COLORS.get(compound, "gray")),
            hovertemplate=(
                f"{acronym}: {row['driver_number']}<br>"
                f"Compound: {compound}<br>"
                f"Laps: {row['lap_count']}<br>"
                f"Start Lap: {row['lap_start']}<br>"
                f"End Lap: {row['lap_end']}"
            ),
            name="",
            showlegend=False
        ))

        # Add colored annotations instead of y-ticks
    y_labels = stints_df["name_acronym"].unique()
    for acronym in y_labels:
        fig.add_annotation(
            x=-3,  # offset left
            y=acronym,
            xref="x",
            yref="y",
            text=f"<b>{acronym}</b>",
            showarrow=False,
            font=dict(
                color=color_map.get(acronym, "#AAA"),  # driver color from map
                size=12
            ),
            align="right"
        )

    fig.update_layout(
        title="Tire Strategy by Driver",
        xaxis_title="Lap Number",
        yaxis_title="",
        barmode="stack",
        height=600,
        margin=dict(l=120),  # make room for left-side labels
    )

    # Hide original Y ticks
    fig.update_yaxes(showticklabels=False)

    return fig


# Pit Stop Duration Chart
def plot_pit_stop(pit_stop_df: pd.DataFrame, color_map: dict):
    """
    Compare pit stop durations across drivers.

    Data comes from OpenF1 /pit endpoint, with pit_duration per lap.

    Args:
        pit_stop_df (pd.DataFrame): Cleaned pit stop data.
        color_map (dict): Driver acronym to team color.

    Returns:
        Plotly Figure object
    """
    if pit_stop_df.empty:
        st.warning("No pit stop data available for this session.")
        return None

    pit_stop_df["driver_number"] = pit_stop_df["driver_number"].astype(str)

    # Combine acronym + number in one column for labeling
    pit_stop_df["driver_label"] = pit_stop_df["name_acronym"] + ": " + pit_stop_df["driver_number"]

    fig = px.bar(
        pit_stop_df,
        x="lap_number",
        y="pit_duration",
        color="name_acronym",
        color_discrete_map=color_map,
        hover_data={
            "driver_label": False,
            "lap_number": False,  # We'll handle this in custom_data
            "pit_duration": False,  # We'll handle this in custom_data
            "name_acronym": False,  # We'll handle this in custom_data
            "driver_number": False,  # We'll handle this in custom_data
        },
        custom_data=["name_acronym", "driver_number", "lap_number", "pit_duration"],
        labels={
            "lap_number": "Lap",
            "pit_duration": "Time in pit lane (s)",
        }
    )

    # Customize the hover template
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}: %{customdata[1]}</b><br>" +
                      "Lap: %{customdata[2]}<br>" +
                      "Time in pit lane (s): %{customdata[3]:.1f}<br>" +
                      "<extra></extra>"  # Removes the trace box
    )
    fig.update_layout(
        title="Pit Stop Times by Driver",
        hovermode="closest",
        barmode="group",
        height=600)
    return fig


def normalize_coordinates(location_df):
    """
    Normalize x, y coordinates to fit within SVG viewBox dimensions.
    
    Args:
        location_df (pd.DataFrame): DataFrame with x, y, z coordinates
    
    Returns:
        pd.DataFrame: DataFrame with normalized coordinates
    """
    if location_df.empty or 'x' not in location_df.columns or 'y' not in location_df.columns:
        return location_df
    
    df = location_df.copy()
    
    # Remove any rows with missing coordinates
    df = df.dropna(subset=['x', 'y'])
    
    if df.empty:
        return df
    
    # Get coordinate ranges
    x_min, x_max = df['x'].min(), df['x'].max()
    y_min, y_max = df['y'].min(), df['y'].max()
    
    # Avoid division by zero
    x_range = x_max - x_min if x_max != x_min else 1
    y_range = y_max - y_min if y_max != y_min else 1
    
    # Normalize to 0-1 range
    df['x_norm'] = (df['x'] - x_min) / x_range
    df['y_norm'] = (df['y'] - y_min) / y_range
    
    return df


def calculate_time_delta_by_position(driver1_data, driver2_data, driver1_name, driver2_name):
    """
    Calculate which driver was ahead at each point on track by comparing elapsed time.
    
    Args:
        driver1_data (pd.DataFrame): Location data for driver 1
        driver2_data (pd.DataFrame): Location data for driver 2
        driver1_name (str): Name of driver 1
        driver2_name (str): Name of driver 2
    
    Returns:
        tuple: (driver1_processed, driver2_processed)
    """
    # Sort by date to get chronological order
    d1 = driver1_data.sort_values('date').copy().reset_index(drop=True)
    d2 = driver2_data.sort_values('date').copy().reset_index(drop=True)
    
    # Calculate elapsed time from start of lap for each driver
    d1['elapsed_time'] = (d1['date'] - d1['date'].min()).dt.total_seconds()
    d2['elapsed_time'] = (d2['date'] - d2['date'].min()).dt.total_seconds()
    
    # Add distance traveled (approximate using cumulative distance between points)
    d1['distance'] = 0.0
    d2['distance'] = 0.0
    
    for i in range(1, len(d1)):
        dx = d1.loc[i, 'x'] - d1.loc[i-1, 'x']
        dy = d1.loc[i, 'y'] - d1.loc[i-1, 'y']
        d1.loc[i, 'distance'] = d1.loc[i-1, 'distance'] + np.sqrt(dx**2 + dy**2)
    
    for i in range(1, len(d2)):
        dx = d2.loc[i, 'x'] - d2.loc[i-1, 'x']
        dy = d2.loc[i, 'y'] - d2.loc[i-1, 'y']
        d2.loc[i, 'distance'] = d2.loc[i-1, 'distance'] + np.sqrt(dx**2 + dy**2)
    
    # Normalize distance to percentage (0-100)
    max_dist_1 = d1['distance'].max()
    max_dist_2 = d2['distance'].max()
    
    if max_dist_1 > 0:
        d1['distance_pct'] = (d1['distance'] / max_dist_1) * 100
    else:
        d1['distance_pct'] = 0
        
    if max_dist_2 > 0:
        d2['distance_pct'] = (d2['distance'] / max_dist_2) * 100
    else:
        d2['distance_pct'] = 0
    
    # For each point on driver 1's path, find closest point on driver 2's path
    # and compare elapsed times
    d1['time_delta'] = 0.0
    d1['faster_driver'] = driver1_name
    
    for i in range(len(d1)):
        dist_pct = d1.loc[i, 'distance_pct']
        # Find closest matching distance percentage in driver 2
        idx = (d2['distance_pct'] - dist_pct).abs().idxmin()
        
        time_diff = d1.loc[i, 'elapsed_time'] - d2.loc[idx, 'elapsed_time']
        d1.loc[i, 'time_delta'] = time_diff
        
        # Negative means driver 1 took less time = driver 1 is faster
        if time_diff < 0:
            d1.loc[i, 'faster_driver'] = driver1_name
        else:
            d1.loc[i, 'faster_driver'] = driver2_name
    
    # Do the same for driver 2
    d2['time_delta'] = 0.0
    d2['faster_driver'] = driver2_name
    
    for i in range(len(d2)):
        dist_pct = d2.loc[i, 'distance_pct']
        idx = (d1['distance_pct'] - dist_pct).abs().idxmin()
        
        time_diff = d2.loc[i, 'elapsed_time'] - d1.loc[idx, 'elapsed_time']
        d2.loc[i, 'time_delta'] = time_diff
        
        if time_diff < 0:
            d2.loc[i, 'faster_driver'] = driver2_name
        else:
            d2.loc[i, 'faster_driver'] = driver1_name
    
    return d1, d2


def plot_lap_comparison_on_track(location_data_dict, color_map, svg_viewbox=(0, 0, 3500, 2000)):
    """
    Create an overlay visualization of driver laps on the track using Plotly.
    Shows who was faster at each section using color coding.
    
    Args:
        location_data_dict (dict): Dictionary mapping driver names to their location DataFrames
        color_map (dict): Driver acronym to team color mapping
        svg_viewbox (tuple): SVG viewBox dimensions (x, y, width, height)
    
    Returns:
        Plotly Figure object
    """
    if not location_data_dict or all(df.empty for df in location_data_dict.values()):
        st.warning("No location data available for comparison.")
        return None
    
    drivers = list(location_data_dict.keys())
    if len(drivers) != 2:
        st.warning("This comparison requires exactly 2 drivers.")
        return None
    
    driver1, driver2 = drivers
    driver1_data = location_data_dict[driver1].copy()
    driver2_data = location_data_dict[driver2].copy()
    
    if driver1_data.empty or driver2_data.empty:
        st.warning("Missing location data for one or both drivers.")
        return None
    
    # Add driver column to each dataset
    driver1_data['driver'] = driver1
    driver2_data['driver'] = driver2
    
    # Calculate time deltas
    d1_processed, d2_processed = calculate_time_delta_by_position(
        driver1_data, driver2_data, driver1, driver2
    )
    
    # Combine for normalization
    combined_df = pd.concat([d1_processed, d2_processed], ignore_index=True)
    combined_df = normalize_coordinates(combined_df)
    
    if combined_df.empty:
        st.warning("Unable to process location data.")
        return None
    
    # Scale to SVG viewBox
    vb_x, vb_y, vb_width, vb_height = svg_viewbox
    combined_df['x_svg'] = combined_df['x_norm'] * vb_width + vb_x
    combined_df['y_svg'] = combined_df['y_norm'] * vb_height + vb_y
    
    # Split back into individual drivers
    d1_plot = combined_df[combined_df['driver'] == driver1].sort_values('date').reset_index(drop=True)
    d2_plot = combined_df[combined_df['driver'] == driver2].sort_values('date').reset_index(drop=True)
    
    # Create figure
    fig = go.Figure()
    
    # Get colors for each driver
    color1 = color_map.get(driver1, '#27AE60')  # Default green
    color2 = color_map.get(driver2, '#3498DB')  # Default blue
    
    lap_num1 = d1_plot['lap_number'].iloc[0] if 'lap_number' in d1_plot.columns else "N/A"
    lap_num2 = d2_plot['lap_number'].iloc[0] if 'lap_number' in d2_plot.columns else "N/A"
    
    # Create continuous color array based on who's faster
    # Driver 1's line colored by who was faster
    colors_d1 = [color1 if faster == driver1 else color2 for faster in d1_plot['faster_driver']]
    
    # Plot driver 1's complete path as one line with color gradient
    fig.add_trace(go.Scatter(
        x=d1_plot['x_svg'],
        y=d1_plot['y_svg'],
        mode='lines',
        name=driver1,
        line=dict(
            color=colors_d1[0],  # Base color
            width=8
        ),
        opacity=0.7,
        showlegend=False,
        hovertemplate=f"<b>{driver1}</b> - Lap {lap_num1}<br>" +
                     "Delta: %{customdata:.3f}s<br>" +
                     "<extra></extra>",
        customdata=d1_plot['time_delta']
    ))
    
    # Overlay segments in different color where driver 2 was faster
    for i in range(1, len(d1_plot)):
        if d1_plot.loc[i, 'faster_driver'] == driver2:
            fig.add_trace(go.Scatter(
                x=d1_plot.loc[i-1:i, 'x_svg'],
                y=d1_plot.loc[i-1:i, 'y_svg'],
                mode='lines',
                line=dict(color=color2, width=8),
                opacity=0.7,
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # Driver 2's line colored by who was faster
    colors_d2 = [color2 if faster == driver2 else color1 for faster in d2_plot['faster_driver']]
    
    # Plot driver 2's complete path
    fig.add_trace(go.Scatter(
        x=d2_plot['x_svg'],
        y=d2_plot['y_svg'],
        mode='lines',
        name=driver2,
        line=dict(
            color=colors_d2[0],
            width=6,
            dash='dot'
        ),
        opacity=0.5,
        showlegend=False,
        hovertemplate=f"<b>{driver2}</b> - Lap {lap_num2}<br>" +
                     "Delta: %{customdata:.3f}s<br>" +
                     "<extra></extra>",
        customdata=d2_plot['time_delta']
    ))
    
    # Overlay segments in different color where driver 1 was faster
    for i in range(1, len(d2_plot)):
        if d2_plot.loc[i, 'faster_driver'] == driver1:
            fig.add_trace(go.Scatter(
                x=d2_plot.loc[i-1:i, 'x_svg'],
                y=d2_plot.loc[i-1:i, 'y_svg'],
                mode='lines',
                line=dict(color=color1, width=6, dash='dot'),
                opacity=0.5,
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # Add legend manually
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        name=f"{driver1} faster",
        line=dict(color=color1, width=8),
        showlegend=True
    ))
    
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        name=f"{driver2} faster",
        line=dict(color=color2, width=8),
        showlegend=True
    ))
    
    # Update layout
    fig.update_layout(
        title=f"Lap Comparison - {driver1} vs {driver2}<br><sub>Line color shows who was faster at each section</sub>",
        xaxis=dict(
            range=[vb_x, vb_x + vb_width],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            range=[vb_y + vb_height, vb_y],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='rgba(245,245,250,1)',
        paper_bgcolor='white',
        height=700,
        hovermode='closest',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="gray",
            borderwidth=1
        )
    )
    
    return fig