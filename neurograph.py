import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime

# --- DB SETUP ---
conn = sqlite3.connect("neurograph.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS neurograph (
    timestamp TEXT,
    sitrep TEXT,
    activity TEXT,
    heart_race REAL,
    shakiness REAL,
    chest_tight REAL,
    stomach REAL,
    meds TEXT
)
""")
conn.commit()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Neurograph Builder", layout="wide")
st.title("🧠 Neurograph Builder + Meds Tracking")

# --- INPUTS ---
st.sidebar.header("New Sitrep Entry")
sitrep = st.sidebar.text_area("Sitrep (current state)")
activity = st.sidebar.selectbox("Activity / Task", ["Resting", "Walking", "Cooking", "Working", "Other"])

st.sidebar.subheader("Core Panic Metrics")
heart_race = st.sidebar.slider("Heart racing", 0, 10, 0)
shakiness = st.sidebar.slider("Shakiness", 0, 10, 0)
chest_tight = st.sidebar.slider("Chest tightness", 0, 10, 0)
stomach = st.sidebar.slider("Stomach discomfort", 0, 10, 0)

st.sidebar.subheader("Medications Taken")
med_name = st.sidebar.text_input("Medication Name")
med_dose = st.sidebar.text_input("Dose (mg / units)")
med_time = datetime.now().strftime("%H:%M")
st.sidebar.text(f"Time taken: {med_time}")

if st.sidebar.button("Log Sitrep"):
    meds_str = f"{med_name} {med_dose} at {med_time}" if med_name else ""
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO neurograph VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (timestamp, sitrep, activity, heart_race, shakiness, chest_tight, stomach, meds_str))
    conn.commit()
    st.sidebar.success("Logged successfully!")

# --- FETCH DATA ---
df = pd.read_sql("SELECT * FROM neurograph ORDER BY timestamp", conn)

# --- TRANSFORM FOR ALTair ---
df_long = df.melt(
    id_vars=["timestamp"],
    value_vars=["heart_race", "shakiness", "chest_tight", "stomach"],
    var_name="Metric",
    value_name="Value"
)

# --- ALTair PLOT ---
st.subheader("Neurograph Metrics Over Time")
chart = alt.Chart(df_long).mark_line(point=True).encode(
    x=alt.X("timestamp:T", title="Timestamp"),
    y=alt.Y("Value:Q", title="Metric Value"),
    color="Metric:N",
    tooltip=["timestamp", "Metric", "Value"]
).interactive()

st.altair_chart(chart, use_container_width=True)

# --- VIEW LOG ---
st.subheader("All Logged Sitreps")
st.dataframe(df)