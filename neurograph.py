import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from LSG import fetch_sitrep  # Your existing LSG API module

# --- Streamlit Page Config ---
st.set_page_config(page_title="Neurograph Builder", layout="wide")
st.title("🧠 Neurograph Builder")

# --- Database Setup ---
conn = sqlite3.connect("neurograph.db", check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute("""
CREATE TABLE IF NOT EXISTS neurograph_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    anxiety INTEGER,
    shakiness INTEGER,
    chest INTEGER,
    breath INTEGER,
    nausea INTEGER,
    triggers TEXT,
    activity TEXT,
    latitude REAL,
    longitude REAL,
    timezone TEXT
)
""")
conn.commit()

# --- Sidebar Inputs ---
st.sidebar.header("Input Metrics")

# Symptom sliders
anxiety = st.sidebar.slider("Anxiety / fear", 0, 10, 0)
shakiness = st.sidebar.slider("Shakiness / tremors", 0, 10, 0)
chest = st.sidebar.slider("Chest tightness", 0, 10, 0)
breath = st.sidebar.slider("Breathlessness", 0, 10, 0)
nausea = st.sidebar.slider("Nausea / stomach discomfort", 0, 10, 0)

# Sitrep inputs
triggers = st.sidebar.text_area("Current triggers / situational notes")
activity = st.sidebar.selectbox("Activity / Task", ["Cooking", "Walking", "Work", "Rest", "Shopping", "Other"])

# Fetch LSG metrics for current sitrep
if st.sidebar.button("Fetch & Log Sitrep Metrics 🚀"):
    sitrep_data = fetch_sitrep(latitude=-15.3875, longitude=28.3228, current_weather=True, hourly=["temperature_2m","relative_humidity_2m","windspeed_10m"], timezone="Africa/Lusaka")
    lat = sitrep_data["latitude"]
    lon = sitrep_data["longitude"]
    tz = sitrep_data["timezone"]
    
    # Log to SQLite
    timestamp = datetime.now().isoformat()
    c.execute("""
        INSERT INTO neurograph_logs 
        (timestamp, anxiety, shakiness, chest, breath, nausea, triggers, activity, latitude, longitude, timezone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, anxiety, shakiness, chest, breath, nausea, triggers, activity, lat, lon, tz))
    conn.commit()
    st.success("Metrics logged successfully!")

# --- Main Panel: Time-Series Plots ---
st.subheader("Neurograph Time-Series Overview")

df = pd.read_sql_query("SELECT * FROM neurograph_logs ORDER BY timestamp ASC", conn)

if not df.empty:
    metrics = ["anxiety", "shakiness", "chest", "breath", "nausea"]
    fig, ax = plt.subplots(len(metrics), 1, figsize=(12, 3*len(metrics)), sharex=True)

    for i, metric in enumerate(metrics):
        ax[i].plot(pd.to_datetime(df["timestamp"]), df[metric], marker="o")
        ax[i].set_ylabel(metric.capitalize())
        ax[i].grid(True)

        # Overlay triggers if present
        for idx, trigger in enumerate(df["triggers"]):
            if trigger.strip():
                ax[i].annotate(trigger, (pd.to_datetime(df["timestamp"].iloc[idx]), df[metric].iloc[idx]),
                               textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, rotation=45)

    plt.xlabel("Timestamp")
    st.pyplot(fig)
else:
    st.info("No logged metrics yet. Fetch & log metrics to see the neurograph.")

# Optional: Show raw data table
with st.expander("Show Raw Logs"):
    st.dataframe(df)
