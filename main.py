import streamlit as st
import requests
from pathlib import Path
from app.data_loader import (
    fetch_meetings,
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers,
    fetch_location_for_lap
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
    plot_pit_stop,
    plot_lap_comparison_on_track
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

# SVG ViewBox dimensions for each circuit (you may need to adjust these based on your SVGs)
CIRCUIT_VIEWBOX = {
    "bahrain": (0, 0, 3183, 2363),
    "jeddah": (0, 0, 3550, 2105),
    "albert-park": (0, 0, 3255, 1742),
    "baku": (0, 0, 3417, 1921),
    "miami": (0, 0, 3630, 1755),
    "monaco": (0, 0, 3125, 2559),
    "barcelona": (0, 0, 3467, 1250),
    "montreal": (0, 0, 3242, 1659),
    "red-bull-ring": (0, 0, 3896, 2292),
    "silverstone": (0, 0, 3084, 1913),
    "hungaroring": (0, 0, 2792, 2705),
    "spa": (0, 0, 3388, 2234),
    "zandvoort": (0, 0, 3234, 2696),
    "monza": (0, 0, 3363, 1563),
    "marina-bay": (0, 0, 3334, 2292),
    "suzuka": (0, 0, 2892, 3117),
    "losail": (0, 0, 3696, 2867),
    "cota": (0, 0, 3267, 2617),
    "mexico-city": (0, 0, 3342, 2205),
    "interlagos": (0, 0, 3463, 2305),
    "las-vegas": (0, 0, 3500, 2255),
    "yas-marina": (0, 0, 3350, 2105),
    "imola": (0, 0, 3417, 1984),
    "shanghai": (0, 0, 3530, 2400),
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


def _select_driver_and_lap(ordinal, key_suffix, driver_index, available_drivers, processed_df):
    """Render the driver + lap pickers for one side of a lap comparison.

    Returns (driver, lap, fastest_lap_num, fastest_lap_time).
    """
    driver = st.selectbox(
        f"Select {ordinal} Driver",
        options=available_drivers,
        index=driver_index,
        key=f"driver{key_suffix}_select"
    )

    driver_data = processed_df[processed_df["name_acronym"] == driver].copy()
    driver_laps = sorted(driver_data["lap_number"].unique())

    fastest = driver_data.loc[driver_data["lap_duration"].idxmin()]
    fastest_lap_num = int(fastest["lap_number"])
    fastest_lap_time = fastest["lap_duration"]

    options = ["Fastest Lap"] + [f"Lap {lap}" for lap in driver_laps]
    display = [f"Fastest Lap ({fastest_lap_num}) - {fastest_lap_time:.3f}s"] + [f"Lap {lap}" for lap in driver_laps]
    selection = st.selectbox(
        f"Select Lap for {ordinal} Driver",
        options=range(len(options)),
        format_func=lambda x: display[x],
        key=f"lap{key_suffix}_select"
    )

    if selection == 0:
        st.info(f"🏁 Fastest lap: **{fastest_lap_time:.3f}s**")
        lap = fastest_lap_num
    else:
        lap = driver_laps[selection - 1]

    return driver, lap, fastest_lap_num, fastest_lap_time


st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

st.title("🏎️ Formula 1 Strategy Dashboard")
st.markdown("_Powered by OpenF1.org • Built by Attila Bordan_")

# API Status Check
with st.spinner("Checking OpenF1 API status..."):
    try:
        test_url = "https://api.openf1.org/v1/meetings?year=2024"
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            st.success("✅ OpenF1 API is online")
        else:
            st.warning(f"⚠️ OpenF1 API returned status {response.status_code}")
    except requests.exceptions.Timeout:
        st.error("❌ OpenF1 API timeout - servers may be slow or down")
    except Exception as e:
        st.error(f"❌ Unable to connect to OpenF1 API: {str(e)}")

col1, col2 = st.columns(2)

with col1:
    # Step 1: Select Year dynamically
    available_years = [2023, 2024, 2025]
    selected_year = st.selectbox("Select Year", available_years, index=1)  # Default to 2024

    # Fetch all meetings for selected year (fetched via fetch_meetings, newest first)
    all_meetings = fetch_meetings(selected_year)

    if all_meetings.empty:
        st.error("⚠️ Unable to fetch meeting data. Please check:")
        st.info("""
        - The OpenF1 API may be experiencing downtime
        - Try selecting a different year (2024 or 2023 are more stable)
        - Check your internet connection
        - The API URL in your .env file is correct: `https://api.openf1.org/v1/`
        """)
        
        # Allow user to continue with cached data if available
        if st.button("🔄 Retry API Connection"):
            st.rerun()
        
        st.stop()

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

# Get circuit info
country_name = meeting_details.get("country_name", "")
circuit_name = meeting_details.get("circuit_short_name", "")
location = meeting_details.get("location", "")
meeting_name = meeting_details.get("meeting_name", "")

# Build info line
info_parts = []
if circuit_name:
    info_parts.append(f"🏎️ {circuit_name}")
if location:
    info_parts.append(f"📍 {location}")
if country_name:
    info_parts.append(f"🌍 {country_name}")
info_line = " • ".join(info_parts)

# Centered title and info
st.markdown(
    f"""
    <h3 style="text-align: center;">🏁 {selected_meeting_name} Circuit Layout</h3>
    <p style="text-align: center; color: #666; margin-bottom: 30px;">{info_line}</p>
    """,
    unsafe_allow_html=True
)

# Try to load circuit SVG
svg_path, circuit_key = get_circuit_svg_path(country_name, circuit_name, meeting_name)

if svg_path:
    # Read and display SVG centered with controlled size
    svg_content = load_circuit_svg(str(svg_path))
    
    st.markdown(
        f"""
        <style>
            .circuit-container {{
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px 0;
            }}
            .circuit-container svg {{
                max-width: 60%;
                height: auto;
            }}
        </style>
        <div class="circuit-container" data-circuit="{circuit_key}">
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
        st.plotly_chart(fig, width="stretch")

# Lap Comparison Feature - NEW!
st.markdown("---")
st.markdown("### 🏁 Lap Comparison - Track Overlay")

with st.expander("Compare Driver Laps on Circuit", expanded=False):
    st.markdown("""
    This feature allows you to compare lap trajectories of two drivers on the actual circuit layout.
    The visualization uses real position data (x, y coordinates) from the OpenF1 API.
    """)
    
    st.info("""
    ℹ️ **Location Data Availability:**
    - Location data is available for 2023-2024 Race sessions
    - Each request fetches data for a specific lap using time-based filtering
    - Best results with recent Grand Prix races (2024)
    - May take 10-30 seconds to load position data for each lap
    """)
    
    if not processed_df.empty:
        # Create driver selection
        available_drivers = sorted(processed_df['name_acronym'].unique())
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            driver1, lap1, fastest_lap1_num, fastest_lap1_time = _select_driver_and_lap(
                "First", "1", 0, available_drivers, processed_df
            )
        
        with col_comp2:
            driver2, lap2, fastest_lap2_num, fastest_lap2_time = _select_driver_and_lap(
                "Second", "2", min(1, len(available_drivers) - 1), available_drivers, processed_df
            )
        
        if st.button("🔄 Load and Compare Laps", width="stretch"):
            with st.spinner("Loading position data from OpenF1 API..."):
                # Get driver numbers
                driver1_number = driver_df[driver_df['name_acronym'] == driver1]['driver_number'].iloc[0]
                driver2_number = driver_df[driver_df['name_acronym'] == driver2]['driver_number'].iloc[0]
                
                # Fetch location data for both laps
                location1 = fetch_location_for_lap(selected_session_key, int(driver1_number), lap1, processed_df)
                location2 = fetch_location_for_lap(selected_session_key, int(driver2_number), lap2, processed_df)
                
                if location1.empty and location2.empty:
                    st.error("❌ No location data available for these laps. This data may not be available for all sessions.")
                elif location1.empty:
                    st.warning(f"⚠️ No location data found for {driver1} - Lap {lap1}")
                elif location2.empty:
                    st.warning(f"⚠️ No location data found for {driver2} - Lap {lap2}")
                else:
                    # Prepare data dictionary
                    location_data = {
                        driver1: location1,
                        driver2: location2
                    }
                    
                    # Get viewbox for current circuit
                    viewbox = CIRCUIT_VIEWBOX.get(circuit_key, (0, 0, 3500, 2000))
                    
                    # Create visualization
                    fig = plot_lap_comparison_on_track(location_data, driver_color_map, viewbox)
                    
                    if fig:
                        st.plotly_chart(fig, width="stretch")
                        
                        # Show some statistics
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        
                        with col_stat1:
                            lap1_time = processed_df[
                                (processed_df['name_acronym'] == driver1) & 
                                (processed_df['lap_number'] == lap1)
                            ]['lap_duration'].iloc[0]
                            lap1_label = f"Lap {lap1}" + (" (Fastest)" if lap1 == fastest_lap1_num else "")
                            st.metric(f"{driver1} - {lap1_label}", f"{lap1_time:.3f}s")
                        
                        with col_stat2:
                            lap2_time = processed_df[
                                (processed_df['name_acronym'] == driver2) & 
                                (processed_df['lap_number'] == lap2)
                            ]['lap_duration'].iloc[0]
                            lap2_label = f"Lap {lap2}" + (" (Fastest)" if lap2 == fastest_lap2_num else "")
                            st.metric(f"{driver2} - {lap2_label}", f"{lap2_time:.3f}s")
                        
                        with col_stat3:
                            time_diff = abs(lap1_time - lap2_time)
                            faster_driver = driver1 if lap1_time < lap2_time else driver2
                            st.metric("Time Difference", f"{time_diff:.3f}s", delta=f"{faster_driver} faster")
                        
                        # Additional comparison info
                        if lap1 == fastest_lap1_num and lap2 == fastest_lap2_num:
                            st.success("🏆 Comparing both drivers' fastest laps of the session!")
    else:
        st.info("Load lap data first to enable lap comparison.")

st.markdown("---")

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
        st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig, width="stretch")

if processed_df.empty:
    st.info("Lap data is not available for this session.")