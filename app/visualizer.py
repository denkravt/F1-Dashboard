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


def _cumulative_distance(df):
    """Cumulative straight-line distance along a driver's path (from the x, y coordinates)."""
    x = df['x'].to_numpy()
    y = df['y'].to_numpy()
    if len(x) <= 1:
        return np.zeros(len(x), dtype=float)
    seg_lengths = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
    return np.concatenate([[0.0], np.cumsum(seg_lengths)])


def _space_delta(driver_df, other_df, driver_name, other_name):
    """For each point on one driver's lap, find the closest point on the other
    driver's lap (by % of track distance) and compute the elapsed-time gap.

    Returns the driver DataFrame enriched with `elapsed_time`, `distance_pct`,
    `time_delta` (seconds; negative = this driver was ahead) and `faster_driver`.
    """
    d = driver_df.sort_values('date').copy().reset_index(drop=True)
    o = other_df.sort_values('date').copy().reset_index(drop=True)

    d['elapsed_time'] = (d['date'] - d['date'].min()).dt.total_seconds()
    o['elapsed_time'] = (o['date'] - o['date'].min()).dt.total_seconds()

    d_dist = _cumulative_distance(d)
    o_dist = _cumulative_distance(o)
    d['distance_pct'] = d_dist / d_dist.max() * 100 if d_dist.max() > 0 else 0.0
    o['distance_pct'] = o_dist / o_dist.max() * 100 if o_dist.max() > 0 else 0.0

    # Nearest point on the other driver's path per distance % (vectorized),
    # then the time gap = this driver's elapsed time minus the other's.
    d['_orig_idx'] = np.arange(len(d))
    left = d[['_orig_idx', 'distance_pct', 'elapsed_time']].sort_values('distance_pct')
    right = o[['distance_pct', 'elapsed_time']].sort_values('distance_pct').rename(
        columns={'elapsed_time': 'other_elapsed'}
    )
    matched = pd.merge_asof(left, right, on='distance_pct', direction='nearest')

    d['time_delta'] = 0.0
    d.loc[matched['_orig_idx'], 'time_delta'] = (
        matched['elapsed_time'].to_numpy() - matched['other_elapsed'].to_numpy()
    )
    # Negative delta = this driver reached that track point faster (ahead).
    d['faster_driver'] = np.where(d['time_delta'] < 0, driver_name, other_name)
    return d.drop(columns='_orig_idx')


def calculate_time_delta_by_position(driver1_data, driver2_data, driver1_name, driver2_name):
    """Compute per-section time deltas and the faster driver for both drivers,
    evaluated at each driver's own path points."""
    d1 = _space_delta(driver1_data, driver2_data, driver1_name, driver2_name)
    d2 = _space_delta(driver2_data, driver1_data, driver2_name, driver1_name)
    return d1, d2


def _overlay_runs(faster, target):
    """Indices of contiguous runs where `faster == target`, as inclusive (start, end)
    pairs — lets us draw the colour-coded sections with one trace per run instead
    of one trace per point."""
    runs, start = [], None
    for i, f in enumerate(faster):
        if f == target and start is None:
            start = i
        elif f != target and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(faster) - 1))
    return runs


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
    
    # Base lap line for driver 1 (carries the per-point delta hover).
    fig.add_trace(go.Scatter(
        x=d1_plot['x_svg'], y=d1_plot['y_svg'], mode='lines',
        name=driver1, line=dict(color=color1, width=8), opacity=0.7,
        showlegend=False,
        hovertemplate=f"<b>{driver1}</b> - Lap {lap_num1}<br>" +
                     "Delta: %{customdata:.3f}s<br><extra></extra>",
        customdata=d1_plot['time_delta']
    ))
    # Re-colour the sections where driver 2 was ahead (solid underline).
    for start, end in _overlay_runs(d1_plot['faster_driver'], driver2):
        fig.add_trace(go.Scatter(
            x=d1_plot['x_svg'].iloc[start:end + 1],
            y=d1_plot['y_svg'].iloc[start:end + 1],
            mode='lines', line=dict(color=color2, width=8), opacity=0.7,
            showlegend=False, hoverinfo='skip'
        ))

    # Base lap line for driver 2.
    fig.add_trace(go.Scatter(
        x=d2_plot['x_svg'], y=d2_plot['y_svg'], mode='lines',
        name=driver2, line=dict(color=color2, width=6, dash='dot'), opacity=0.5,
        showlegend=False,
        hovertemplate=f"<b>{driver2}</b> - Lap {lap_num2}<br>" +
                     "Delta: %{customdata:.3f}s<br><extra></extra>",
        customdata=d2_plot['time_delta']
    ))
    # Re-colour the sections where driver 1 was ahead (dotted underline).
    for start, end in _overlay_runs(d2_plot['faster_driver'], driver1):
        fig.add_trace(go.Scatter(
            x=d2_plot['x_svg'].iloc[start:end + 1],
            y=d2_plot['y_svg'].iloc[start:end + 1],
            mode='lines', line=dict(color=color1, width=6, dash='dot'), opacity=0.5,
            showlegend=False, hoverinfo='skip'
        ))

    # Legend entries
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