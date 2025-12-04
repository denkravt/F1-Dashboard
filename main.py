import streamlit as st
from pathlib import Path
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

# Circuit name mapping to standardized filenames
CIRCUIT_MAPPING = {
    "Bahrain": "bahrain",
    "Saudi Arabia": "jeddah",
    "Saudi Arabian": "jeddah",
    "Australia": "albert-park",
    "Australian": "albert-park",
    "Azerbaijan": "baku",
    "Miami": "miami",
    "Monaco": "monaco",
    "Spain": "barcelona",
    "Spanish": "barcelona",
    "Canada": "montreal",
    "Canadian": "montreal",
    "Austria": "red-bull-ring",
    "Austrian": "red-bull-ring",
    "Great Britain": "silverstone",
    "British": "silverstone",
    "Hungary": "hungaroring",
    "Hungarian": "hungaroring",
    "Belgium": "spa",
    "Belgian": "spa",
    "Netherlands": "zandvoort",
    "Dutch": "zandvoort",
    "Italy": "monza",
    "Italian": "monza",
    "Singapore": "marina-bay",
    "Japan": "suzuka",
    "Japanese": "suzuka",
    "Qatar": "losail",
    "United States": "cota",
    "USA": "cota",
    "Mexico": "mexico-city",
    "Mexican": "mexico-city",
    "Brazil": "interlagos",
    "Brazilian": "interlagos",
    "Las Vegas": "las-vegas",
    "Abu Dhabi": "yas-marina",
    "Emilia Romagna": "imola",
    "Emilia-Romagna": "imola",
    "Portugal": "portimao",
    "Portuguese": "portimao",
    "Turkey": "istanbul",
    "Turkish": "istanbul",
    "Styria": "red-bull-ring",
    "São Paulo": "interlagos",
    "China": "shanghai",
    "Chinese": "shanghai",
}


@st.cache_data
def load_circuit_svg(svg_path_str):
    """Load SVG content with caching based on file path."""
    with open(svg_path_str, 'r', encoding='utf-8') as f:
        return f.read()


def get_circuit_svg_path(country_name, circuit_name=None, meeting_name=None):
    """Get the path to the circuit SVG file based on country, circuit, or meeting name."""
    circuit_key = None
    
    # First, check for specific meeting names (highest priority for multi-venue countries)
    if meeting_name:
        meeting_lower = meeting_name.lower()
        # Check for specific US races
        if "miami" in meeting_lower:
            circuit_key = "miami"
        elif "las vegas" in meeting_lower:
            circuit_key = "las-vegas"
        elif "united states" in meeting_lower or "usa" in meeting_lower:
            circuit_key = "cota"
        # Check other specific cases
        elif "emilia romagna" in meeting_lower or "imola" in meeting_lower:
            circuit_key = "imola"
        elif "são paulo" in meeting_lower or "sao paulo" in meeting_lower:
            circuit_key = "interlagos"
        elif "british" in meeting_lower:
            circuit_key = "silverstone"
        elif "qatar" in meeting_lower:
            circuit_key = "losail"
    
    # Try circuit name next
    if not circuit_key and circuit_name:
        circuit_lower = circuit_name.lower()
        # Specific circuit name checks
        if "miami" in circuit_lower:
            circuit_key = "miami"
        elif "las vegas" in circuit_lower:
            circuit_key = "las-vegas"
        elif "cota" in circuit_lower or "americas" in circuit_lower:
            circuit_key = "cota"
        elif "losail" in circuit_lower or "lusail" in circuit_lower:
            circuit_key = "losail"
        elif "silverstone" in circuit_lower:
            circuit_key = "silverstone"
        elif "marina bay" in circuit_lower:
            circuit_key = "marina-bay"
        elif "yas marina" in circuit_lower:
            circuit_key = "yas-marina"
        elif "red bull ring" in circuit_lower:
            circuit_key = "red-bull-ring"
        elif "gilles villeneuve" in circuit_lower or "villeneuve" in circuit_lower:
            circuit_key = "montreal"
        elif "interlagos" in circuit_lower:
            circuit_key = "interlagos"
        elif "hungaroring" in circuit_lower:
            circuit_key = "hungaroring"
        elif "zandvoort" in circuit_lower:
            circuit_key = "zandvoort"
        elif "spa" in circuit_lower and "francorchamps" in circuit_lower:
            circuit_key = "spa"
        elif "monza" in circuit_lower:
            circuit_key = "monza"
        elif "suzuka" in circuit_lower:
            circuit_key = "suzuka"
        elif "albert park" in circuit_lower:
            circuit_key = "albert-park"
        elif "baku" in circuit_lower:
            circuit_key = "baku"
        elif "jeddah" in circuit_lower:
            circuit_key = "jeddah"
        elif "bahrain" in circuit_lower:
            circuit_key = "bahrain"
        elif "barcelona" in circuit_lower or "catalunya" in circuit_lower:
            circuit_key = "barcelona"
        elif "mexico" in circuit_lower:
            circuit_key = "mexico-city"
        elif "shanghai" in circuit_lower:
            circuit_key = "shanghai"
        elif "imola" in circuit_lower:
            circuit_key = "imola"
    
    # Finally try country name (lowest priority)
    if not circuit_key:
        circuit_key = CIRCUIT_MAPPING.get(country_name)
    
    if circuit_key:
        svg_path = Path(f"assets/circuits/{circuit_key}.svg")
        if svg_path.exists():
            return svg_path, circuit_key
    
    return None, None


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

# Circuit Layout Section
st.markdown("---")
meeting_details = all_meetings[all_meetings["meeting_key"] == selected_meeting_key].iloc[0]
st.markdown(f"### 🏁 {selected_meeting_name} Circuit Layout")

# Create columns for track info and image
track_col1, track_col2 = st.columns([1, 2])

with track_col1:
    st.markdown("**Circuit Information**")
    if "circuit_short_name" in meeting_details and meeting_details["circuit_short_name"]:
        st.write(f"🏎️ **Circuit:** {meeting_details['circuit_short_name']}")
    if "location" in meeting_details:
        st.write(f"📍 **Location:** {meeting_details['location']}")
    if "country_name" in meeting_details:
        st.write(f"🌍 **Country:** {meeting_details['country_name']}")
    if "date_start" in meeting_details:
        st.write(f"📅 **Date:** {meeting_details['date_start']}")

with track_col2:
    # Try to load circuit SVG
    country_name = meeting_details.get("country_name", "")
    circuit_name = meeting_details.get("circuit_short_name", "")
    meeting_name = meeting_details.get("meeting_name", "")
    
    svg_path, circuit_key = get_circuit_svg_path(country_name, circuit_name, meeting_name)
    
    if svg_path:
        # Read and display SVG with custom styling
        svg_content = load_circuit_svg(str(svg_path))
        
        # Add a unique key based on circuit to force re-render
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; padding: 20px;" data-circuit="{circuit_key}">
                {svg_content}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Show setup instructions
        st.info(
            f"""
            **Circuit layout not found**
            
            Looking for: `{CIRCUIT_MAPPING.get(country_name, 'unknown')}.svg`
            
            **Search criteria:**
            - Country: {country_name}
            - Circuit: {circuit_name}
            - Meeting: {meeting_name}
            
            To display circuit layouts:
            1. Create folder: `assets/circuits/`
            2. Add SVG file with the correct name
            
            **Expected filename:** `{CIRCUIT_MAPPING.get(country_name, 'circuit-name')}.svg`
            """
        )

st.markdown("---")

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