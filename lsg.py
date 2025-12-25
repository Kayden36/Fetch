import streamlit as st
import pandas as pd
import sqlite3
import pickle
from pathlib import Path

# =============================
# CONFIG
# =============================
DB_PATH = "tonga_sqf.db"
PICKLE_PATH = "tonga_sqf.pkl"

st.set_page_config(
    page_title="Tonga → SQF Tagger",
    layout="wide"
)

# =============================
# POS → SQF MAP
# =============================
POS_TO_SQF = {
    "Noun": "Boson",
    "Verb": "Fermion",
    "Pronoun": "Boson.Proxy",
    "Adjective": "Scalar.Boson",
    "Adverb": "Scalar.Fermion",
    "Preposition": "Gauge",
    "Conjunction": "Operator",
    "Interjection": "Scalar.Impulse",
    "Number": "Scalar.Quantizer",
    "Demonstrative": "Anchor.Gauge",
    "Question": "Operator.Probe"
}

def pos_to_sqf(pos):
    if not pos:
        return ""
    pos_clean = str(pos).strip().title()
    return POS_TO_SQF.get(pos_clean, "Unknown")

# =============================
# DATABASE
# =============================
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

# =============================
# DB HELPERS
# =============================
def insert_or_update(row):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO vocab
        (tonga_word, pos, sqf_token, comment)
        VALUES (?, ?, ?, ?)
    """, (
        row["tonga_word"],
        row["pos"],
        row["sqf_token"],
        row["comment"]
    ))
    conn.commit()
    conn.close()

def fetch_all():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM vocab ORDER BY tonga_word",
        conn
    )
    conn.close()
    return df

def fetch_word(query):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM vocab WHERE tonga_word LIKE ?",
        conn,
        params=(f"%{query}%",)
    )
    conn.close()
    return df

def export_pickle():
    df = fetch_all()
    records = df.to_dict(orient="records")
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(records, f)

# =============================
# UI
# =============================
st.title("🧠 Tonga → SQF POS Tagger")

tab1, tab2, tab3 = st.tabs([
    "📥 Ingest / Edit",
    "🔍 Search",
    "📦 Export"
])

# =============================
# TAB 1 — INGEST / EDIT
# =============================
with tab1:
    st.subheader("Manual Entry")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        tonga_word = st.text_input("Tonga Word")

    with c2:
        pos = st.text_input("POS (e.g. Noun, Verb)")

    with c3:
        sqf_token = st.text_input("SQF Token (optional)")

    with c4:
        comment = st.text_input("Comment / English gloss")

    if st.button("Save Entry"):
        if tonga_word and pos:
            final_sqf = sqf_token.strip() or pos_to_sqf(pos)
            insert_or_update({
                "tonga_word": tonga_word.strip(),
                "pos": pos.strip(),
                "sqf_token": final_sqf,
                "comment": comment.strip()
            })
            st.success("Saved.")
        else:
            st.error("Tonga word and POS are required.")

    st.divider()

    # =============================
    # EXCEL UPLOAD
    # =============================
    st.subheader("Upload Excel (4 columns, no headers)")
    st.caption("Columns: Tonga | POS | SQF(optional) | Comment")

    uploaded = st.file_uploader(
        "Upload .xlsx file",
        type=["xlsx"]
    )

    if uploaded:
        df = pd.read_excel(uploaded, header=None)

        # Ensure 4 columns
        while df.shape[1] < 4:
            df[df.shape[1]] = ""

        df = df.iloc[:, :4]
        df.columns = ["tonga_word", "pos", "sqf_token", "comment"]

        # Auto SQF assignment
        df["sqf_token"] = df.apply(
            lambda row:
                row["sqf_token"]
                if str(row["sqf_token"]).strip()
                else pos_to_sqf(row["pos"]),
            axis=1
        )

        st.dataframe(df, use_container_width=True)

        if st.button("Save Uploaded Data"):
            for _, row in df.iterrows():
                insert_or_update({
                    "tonga_word": str(row["tonga_word"]).strip(),
                    "pos": str(row["pos"]).strip(),
                    "sqf_token": str(row["sqf_token"]).strip(),
                    "comment": str(row["comment"]).strip()
                })
            st.success("Excel ingested successfully.")

    st.divider()
    st.subheader("Current Lexicon")
    st.dataframe(fetch_all(), use_container_width=True)

# =============================
# TAB 2 — SEARCH
# =============================
with tab2:
    st.subheader("Search Tonga Word")

    query = st.text_input("Search")

    if query:
        results = fetch_word(query)
        st.dataframe(
            results,
            use_container_width=True
        )

# =============================
# TAB 3 — EXPORT
# =============================
with tab3:
    st.subheader("Export")

    if st.button("Export Pickle"):
        export_pickle()
        st.success(f"Exported → {PICKLE_PATH}")

    st.caption(
        "Pickle contains list[dict]: "
        "tonga_word, pos, sqf_token, comment"
    )