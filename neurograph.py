import streamlit as st
import pandas as pd
import sqlite3
import pickle
from pathlib import Path

# -----------------------------
# Config
# -----------------------------
DB_PATH = "tonga_sqf.db"
PICKLE_PATH = "tonga_sqf.pkl"

st.set_page_config(page_title="Tonga SQF Tagger", layout="wide")

# -----------------------------
# Database
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocab (
            tonga_word TEXT PRIMARY KEY,
            pos TEXT,
            sqf_token TEXT,
            comment TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Helpers
# -----------------------------
def insert_or_update(row):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO vocab
        (tonga_word, pos, sqf_token, comment)
        VALUES (?, ?, ?, ?)
    """, (row["tonga_word"], row["pos"], row["sqf_token"], row["comment"]))
    conn.commit()
    conn.close()

def fetch_all():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM vocab ORDER BY tonga_word", conn)
    conn.close()
    return df

def fetch_word(word):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM vocab WHERE tonga_word LIKE ?",
        conn,
        params=(f"%{word}%",)
    )
    conn.close()
    return df

def export_pickle():
    df = fetch_all()
    records = df.to_dict(orient="records")
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(records, f)

# -----------------------------
# UI
# -----------------------------
st.title("Tonga → SQF POS Tagger")

tab1, tab2 = st.tabs(["📥 Ingest / Edit", "🔍 Search"])

# =============================
# TAB 1 — INGEST
# =============================
with tab1:
    st.subheader("Manual Entry")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tonga_word = st.text_input("Tonga Word")

    with col2:
        pos = st.text_input("POS")

    with col3:
        sqf_token = st.text_input("SQF Token")

    with col4:
        comment = st.text_input("Comment")

    if st.button("Save Entry"):
        if tonga_word and pos:
            insert_or_update({
                "tonga_word": tonga_word.strip(),
                "pos": pos.strip(),
                "sqf_token": sqf_token.strip(),
                "comment": comment.strip()
            })
            st.success("Saved.")
        else:
            st.error("Tonga word and POS are required.")

    st.divider()

    st.subheader("Upload Excel")

    uploaded = st.file_uploader(
        "Upload Excel (2 columns: Tonga word, POS)",
        type=["xlsx"]
    )

    if uploaded:
        df = pd.read_excel(uploaded, header=None)
        df.columns = ["tonga_word", "pos"]
        df["sqf_token"] = ""
        df["comment"] = ""

        st.dataframe(df, use_container_width=True)

        if st.button("Save Uploaded Data"):
            for _, row in df.iterrows():
                insert_or_update({
                    "tonga_word": str(row["tonga_word"]).strip(),
                    "pos": str(row["pos"]).strip(),
                    "sqf_token": "",
                    "comment": ""
                })
            st.success("Excel data saved.")

    st.divider()

    st.subheader("Database Contents")
    st.dataframe(fetch_all(), use_container_width=True)

    if st.button("Export Pickle"):
        export_pickle()
        st.success(f"Pickle exported → {PICKLE_PATH}")

# =============================
# TAB 2 — SEARCH
# =============================
with tab2:
    st.subheader("Search Tonga Word")

    query = st.text_input("Enter Tonga word")

    if query:
        results = fetch_word(query)
        st.dataframe(
            results[["pos", "sqf_token", "comment"]],
            use_container_width=True
        )