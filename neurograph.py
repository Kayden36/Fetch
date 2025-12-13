import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
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
    stomach REAL
)
""")
conn.commit()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Neurograph Builder", layout="wide")
st.title("🧠 Neurograph Builder")

# --- INPUTS ---
st.sidebar.header("New Sitrep Entry")
sitrep = st.sidebar.text_area("Sitrep (current state)")
activity = st.sidebar.selectbox("Activity / Task", ["Resting", "Walking", "Cooking", "Working", "Other"])

st.sidebar.subheader("Core Panic Metrics")
heart_race = st.sidebar.slider("Heart racing", 0, 10, 0)
shakiness = st.sidebar.slider("Shakiness", 0, 10, 0)
chest_tight = st.sidebar.slider("Chest tightness", 0, 10, 0)
stomach = st.sidebar.slider("Stomach discomfort", 0, 10, 0)

if st.sidebar.button("Log Sitrep"):
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO neurograph VALUES (?, ?, ?, ?, ?, ?, ?)",
              (timestamp, sitrep, activity, heart_race, shakiness, chest_tight, stomach))
    conn.commit()
    st.sidebar.success("Logged successfully!")

# --- FETCH DATA ---
df = pd.read_sql("SELECT * FROM neurograph ORDER BY timestamp", conn)

# --- PLOTS ---
st.subheader("Neurograph Metrics Over Time")
metrics = ["heart_race", "shakiness", "chest_tight", "stomach"]
fig, ax = plt.subplots(figsize=(10, 6))
for metric in metrics:
    ax.plot(df["timestamp"], df[metric], marker="o", label=metric)
ax.set_xticklabels(df["timestamp"], rotation=45, ha="right")
ax.set_ylabel("Metric value")
ax.set_xlabel("Timestamp")
ax.legend()
st.pyplot(fig)

# --- VIEW LOG ---
st.subheader("All Logged Sitreps")
st.dataframe(df)