import streamlit as st
from app.data_loader import (
    fetch_data,
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers
)
from app.data_processor import (
    process_lap_data,
    process_stints,
    process_pit_stops,
    build_driver_color_map
)
from app.visualizer import (
    plot_lap_times,
    plot_tire_strategy,
    plot_pit_stop
)

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

st.title("🏎️ Formula 1 Strategy Dashboard")
st.markdown("_Powered by OpenF1.org • Built by Attila Bordan_")

col1, col2 = st.columns(2)

with col1:
    # Step 1: Select Year dynamically
    available_years = [2023, 2024, 2025]
    selected_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1)

    # Fetch all meetings for selected year
    all_meetings = fetch_data("meetings", {"year": selected_year})

    if all_meetings.empty:
        st.error("No meetings found for this year.")
        st.stop()

    # Create a label for Grand Prix selection
    all_meetings["label"] = all_meetings["meeting_name"] + " - " + all_meetings["location"]
    all_meetings = all_meetings.sort_values(by="meeting_key", ascending=False)

    # Select Grand Prix directly
    selected_meeting = st.selectbox("Select Grand Prix", all_meetings["label"])
    selected_meeting_key = all_meetings.loc[
        all_meetings["label"] == selected_meeting, "meeting_key"
    ].values[0]
    
    # Extract meeting name for display
    selected_meeting_name = all_meetings.loc[
        all_meetings["label"] == selected_meeting, "meeting_name"
    ].values[0]

    # Fetch sessions for the selected Grand Prix
    sessions = fetch_sessions(selected_meeting_key)
    
    # Extract session type for easier filtering
    sessions["session_type"] = sessions["label"].str.extract(r"^(.*?)\s\(")
    
    # Find the Race session index, default to 0 if not found
    race_rows = sessions[sessions["session_type"].str.contains("Race", case=False, na=False)]
    default_index = int(race_rows.index[0]) if len(race_rows) > 0 else 0
    
    selected_session = st.selectbox("Select Session", sessions["label"], index=default_index)
    selected_session_type = sessions.loc[sessions["label"] == selected_session, "session_type"].values[0]
    selected_session_key = sessions.loc[sessions["label"] == selected_session, "session_key"].values[0]

st.markdown(f"### 📊 Session Overview: `{selected_session}`")
with st.expander("📋 Session Details", expanded=False):
    st.write(f"**Meeting Key:** {selected_meeting_key}")
    st.write(f"**Session Key:** {selected_session_key}")

# Fetch and preprocess driver info
driver_df = fetch_drivers(selected_session_key)
driver_df["driver_number"] = driver_df["driver_number"].astype(str)
driver_color_map = build_driver_color_map(driver_df)
driver_info = driver_df[["driver_number", "name_acronym"]]

# Lap Times
with st.expander(f"📈 Lap Time Chart for {selected_session_type} at {selected_meeting_name} {selected_year}",
                 expanded=True):
    lap_df = fetch_laps(selected_session_key)
    processed_df = process_lap_data(lap_df)

    # Merge name_acronym into the lap data
    processed_df["driver_number"] = processed_df["driver_number"].astype(str)
    processed_df = processed_df.merge(driver_info, on="driver_number", how="left")

    if processed_df.empty:
        st.warning("No lap time data found.")
    else:
        fig = plot_lap_times(processed_df, driver_color_map)
        st.plotly_chart(fig, use_container_width=True)

# Tire Strategy
with st.expander(f"🛞 Tire strategy for {selected_session_type} at {selected_meeting_name} {selected_year}", expanded=True):
    stints = fetch_stints(selected_session_key)
    stints_df = process_stints(stints)
    stints_df["driver_number"] = stints_df["driver_number"].astype(str)
    stints_df = stints_df.merge(driver_info, on="driver_number", how="left")

    if stints_df.empty:
        st.warning("No tire strategy data found.")
    else:
        fig = plot_tire_strategy(stints_df, driver_color_map)
        st.plotly_chart(fig, use_container_width=True)

# Pit Stops
with st.expander(f"⏱ Pit stop durations for {selected_session_type} at {selected_meeting_name} {selected_year}",
                 expanded=True):
    pit_stop = fetch_pit_stop(selected_session_key)
    pit_stop_df = process_pit_stops(pit_stop)
    pit_stop_df["driver_number"] = pit_stop_df["driver_number"].astype(str)
    pit_stop_df = pit_stop_df.merge(driver_info, on="driver_number", how="left")

    if pit_stop_df.empty:
        st.warning("No pit stop data found.")
    else:
        fig = plot_pit_stop(pit_stop_df, driver_color_map)
        st.plotly_chart(fig, use_container_width=True)

if processed_df.empty:
    st.info("Lap data is not available for this session.")
