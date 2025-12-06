import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("BASE_API_URL")


def fetch_data(endpoint, params=None, max_retries=3, timeout=30):
    """
    Fetch data from the OpenF1 API and return it as a DataFrame.

    Args:
        endpoint (str): API endpoint (e.g., "meetings", "sessions").
        params (dict): Optional query parameters for the API.
        max_retries (int): Maximum number of retry attempts.
        timeout (int): Request timeout in seconds.

    Returns:
        pd.DataFrame: DataFrame containing the API response data.

    Notes:
        The OpenF1 API requires properly URL-encoded query strings,
        especially when using complex filters (e.g., strings with spaces).
        Using `requests.get(url, params=params)` sometimes causes issues with
        formatting, so we manually prepare the full URL using `requests.Request`.
    """
    if params is None:
        params = {}

    url = f"{BASE_URL}{endpoint}"
    full_url = requests.Request('GET', url, params=params).prepare().url
    
    for attempt in range(max_retries):
        try:
            response = requests.get(full_url, timeout=timeout)
            response.raise_for_status()
            return pd.DataFrame(response.json())
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Request timed out (attempt {attempt + 1}/{max_retries}). Retrying...")
                continue
            else:
                st.error(f"❌ API request timed out after {max_retries} attempts. The OpenF1 API may be experiencing issues.")
                return pd.DataFrame()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 504:
                if attempt < max_retries - 1:
                    st.warning(f"⏱️ Server timeout (attempt {attempt + 1}/{max_retries}). Retrying...")
                    continue
                else:
                    st.error(f"❌ OpenF1 API server timeout after {max_retries} attempts. Please try again later or select a different year.")
                    return pd.DataFrame()
            elif e.response.status_code == 422:
                # 422 usually means invalid parameters or data not available
                st.error(f"❌ HTTP Error 422: {str(e)}\n\n**Possible reasons:**\n- Location data may not be available for this session\n- The session may be too old (pre-2023)\n- Parameters may be invalid\n\nURL: {full_url}")
                return pd.DataFrame()
            else:
                st.error(f"❌ HTTP Error {e.response.status_code}: {str(e)}")
                return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Network error: {str(e)}")
            return pd.DataFrame()
    
    return pd.DataFrame()


# Cached API calls using Streamlit's cache_data decorator

@st.cache_data
def fetch_meetings(year):
    # The 'meetings' endpoint returns all information for meetings in a specified year.
    # Removed country filter - now fetches all Grand Prix events for the year.
    with st.spinner(f"Fetching meetings for {year}..."):
        df = fetch_data("meetings", {"year": year})
    
    if df.empty:
        st.error(f"⚠️ No meeting data found for {year}. The API may be down or the year has no data.")
        return pd.DataFrame()

    # Create a label for easier dropdown display
    df["label"] = df["meeting_name"] + " - " + df["location"]
    df = df.sort_values(by="meeting_key", ascending=False)

    # Return minimal relevant fields
    return df[["meeting_key", "label", "year"]].drop_duplicates()


@st.cache_data
def fetch_sessions(meeting_key):
    # The 'sessions' endpoint returns all session types (FP1, Qualifying, Race) for a specific Grand Prix.
    # Filtered here using 'meeting_key' from the 'meetings' endpoint.
    df = fetch_data("sessions", {"meeting_key": meeting_key})

    # Combine session name and start date for display
    df["label"] = df["session_name"] + " (" + df["date_start"] + ")"

    # Only keep necessary columns for dropdowns
    return df[["session_key", "label"]].drop_duplicates()


@st.cache_data
def fetch_laps(session_key):
    # Retrieves detailed lap timing data for a given session
    return fetch_data("laps", {"session_key": session_key})


@st.cache_data
def fetch_stints(session_key):
    # Fetches tire stint data, which includes tire compound and start/end laps
    return fetch_data("stints", {"session_key": session_key})


@st.cache_data
def fetch_pit_stop(session_key):
    # Returns pit stop information, including duration and lap number
    return fetch_data("pit", {"session_key": session_key})


@st.cache_data
def fetch_drivers(session_key):
    # Provides driver metadata such as name, number, and team color
    return fetch_data("drivers", {"session_key": session_key})


@st.cache_data
def fetch_location_for_lap(session_key, driver_number, lap_number, lap_data):
    """
    Fetch location data for a specific lap by filtering based on lap start/end times.
    
    Args:
        session_key (int): Session identifier
        driver_number (int): Driver number
        lap_number (int): Lap number
        lap_data (pd.DataFrame): DataFrame containing lap timing data
    
    Returns:
        pd.DataFrame: Filtered location data for the specific lap
    """
    try:
        # Find the specific lap timing info
        lap_info = lap_data[
            (lap_data['driver_number'] == str(driver_number)) & 
            (lap_data['lap_number'] == lap_number)
        ]
        
        if lap_info.empty:
            st.error(f"No lap timing data found for driver {driver_number}, lap {lap_number}")
            return pd.DataFrame()
        
        # Get lap start time
        lap_start = pd.to_datetime(lap_info['date_start'].iloc[0])
        
        # Calculate lap end time (start + duration)
        if 'lap_duration' in lap_info.columns and pd.notna(lap_info['lap_duration'].iloc[0]):
            lap_duration_seconds = lap_info['lap_duration'].iloc[0]
            lap_end = lap_start + pd.Timedelta(seconds=lap_duration_seconds)
        else:
            # If duration not available, try to use next lap's start time
            next_lap = lap_data[
                (lap_data['driver_number'] == str(driver_number)) & 
                (lap_data['lap_number'] == lap_number + 1)
            ]
            if not next_lap.empty:
                lap_end = pd.to_datetime(next_lap['date_start'].iloc[0])
            else:
                # Default to 2 minutes after start if no end time available
                lap_end = lap_start + pd.Timedelta(minutes=2)
        
        # Format dates for API (ISO format)
        date_start_str = lap_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]  # Remove microseconds to milliseconds
        date_end_str = lap_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        
        # Fetch location data with date range to limit data size
        params = {
            "session_key": session_key,
            "driver_number": driver_number,
            "date>": date_start_str,
            "date<": date_end_str
        }
        
        with st.spinner(f"Fetching location data for driver {driver_number}, lap {lap_number}..."):
            location_df = fetch_data("location", params, max_retries=2, timeout=60)
        
        if location_df.empty:
            st.warning(f"No location data returned for driver {driver_number}, lap {lap_number}")
            return pd.DataFrame()
        
        # Convert date column to datetime
        if 'date' in location_df.columns:
            location_df['date'] = pd.to_datetime(location_df['date'])
        
        # Add lap number for reference
        location_df['lap_number'] = lap_number
        
        return location_df
        
    except Exception as e:
        st.error(f"Error fetching location data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame()