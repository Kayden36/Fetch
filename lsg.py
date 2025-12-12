import streamlit as st
import requests
import json
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="LSG Weather Logger", layout="wide")
st.title("🌍 LSG Weather Logger & Graph")

# --- DATABASE SETUP ---
conn = sqlite3.connect("lsg_weather.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS lsg_metrics (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    temperature REAL,
    humidity REAL,
    windspeed REAL
)
""")
conn.commit()

# --- SIDEBAR INPUTS ---
st.sidebar.header("Open-Meteo LSG Request")
latitude = st.sidebar.number_input("Latitude", value=-15.3875)
longitude = st.sidebar.number_input("Longitude", value=28.3228)
current_weather = st.sidebar.checkbox("Current Weather", value=True)
timezone = st.sidebar.text_input("Timezone", value="Africa/Lusaka")
send_button = st.sidebar.button("Fetch & Log LSG Metrics 🚀")

# --- BUILD QUERY PARAMS ---
params = {
    "latitude": latitude,
    "longitude": longitude,
    "current_weather": current_weather,
    "hourly": ["temperature_2m", "relative_humidity_2m", "windspeed_10m"],
    "timezone": timezone
}

base_url = "https://api.open-meteo.com/v1/forecast"

# --- SEND REQUEST ---
if send_button:
    try:
        response = requests.get(base_url, params=params)
        res_json = response.json()
        st.json(res_json)

        # --- LOG CURRENT WEATHER TO DB ---
        if "current_weather" in res_json:
            cw = res_json["current_weather"]
            c.execute("""
                INSERT INTO lsg_metrics (timestamp, temperature, humidity, windspeed)
                VALUES (?, ?, ?, ?)
            """, (
                cw.get("time"),
                cw.get("temperature"),
                None,  # hourly humidity will be logged below
                cw.get("windspeed")
            ))
            conn.commit()

        # --- LOG HOURLY METRICS ---
        if "hourly" in res_json:
            hourly = res_json["hourly"]
            times = hourly["time"]
            temps = hourly.get("temperature_2m", [])
            hums = hourly.get("relative_humidity_2m", [])
            winds = hourly.get("windspeed_10m", [])
            for t, temp, hum, wind in zip(times, temps, hums, winds):
                c.execute("""
                    INSERT INTO lsg_metrics (timestamp, temperature, humidity, windspeed)
                    VALUES (?, ?, ?, ?)
                """, (t, temp, hum, wind))
            conn.commit()

        st.success("Metrics logged successfully!")

    except Exception as e:
        st.error(f"Failed to fetch LSG data: {e}")

# --- GRAPH ---
st.subheader("LSG Metrics Graph Over Time")
df = pd.read_sql_query("SELECT * FROM lsg_metrics ORDER BY timestamp", conn)
if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Melt for Altair
    df_melted = df.melt('timestamp', value_vars=['temperature', 'humidity', 'windspeed'],
                        var_name='Metric', value_name='Value')
    
    chart = alt.Chart(df_melted).mark_line(point=True).encode(
        x='timestamp:T',
        y='Value:Q',
        color='Metric:N',
        tooltip=['timestamp', 'Metric', 'Value']
    ).interactive()

    st.altair_chart(chart, use_container_width=True)
else:
    st.write("No metrics logged yet. Click 'Fetch & Log LSG Metrics 🚀' to start.")
