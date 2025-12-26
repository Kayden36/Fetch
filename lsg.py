import streamlit as st
import pandas as pd
import sqlite3
import pickle
from pathlib import Path
import numpy as np

# =============================
# CONFIG
# =============================
DB_PATH = "tonga_sqf_vectors.db"
st.set_page_config("Tonga SQF Semantic Search", layout="wide")

# =============================
# POS → Particle Map
# =============================
POS_TO_PARTICLE = {
    "Noun":"Boson",
    "Proper Noun":"Boson",
    "Pronoun":"Boson",
    "Demonstrative":"Boson",
    "Verb":"Fermion",
    "Adjective":"Scalar",
    "Adverb":"Scalar",
    "Preposition":"Gauge",
    "Conjunction":"Operator",
    "Interjection":"Scalar",
    "Number":"Scalar",
    "Demonstrative Pronoun":"Anchor",
    "Question":"Operator"
}

# =============================
# SQF Classes / KV semantic features
# =============================
SubclassSemanticMatrix = {
    "BoC1":{"features":{"life":1,"agency":1,"volition":1,"physicality":1}},
    "BoC2":{"features":{"life":1,"agency":1,"plurality":1,"physicality":1}},
    "FeC1":{"features":{"agency_required":1,"volition":1,"causation":1}},
    "FeC2":{"features":{"modifies":1,"temporal":1}},
    "ScC1":{"features":{"modifies":1,"attribute":1}},
    "GaC1":{"features":{"relational":1,"spatial":1}},
    "OpC1":{"features":{"logical":1}},
    "AnC1":{"features":{"pointing":1}},
    "Unknown":{"features":{}}
}

SQF_PARTICLE_CLASSES = {
    "Boson":["BoC1","BoC2"],
    "Fermion":["FeC1","FeC2"],
    "Scalar":["ScC1","ScC2"],
    "Gauge":["GaC1"],
    "Operator":["OpC1","OpC2"],
    "Anchor":["AnC1"],
    "Unknown":["Unknown"]
}

PARTICLE_IDX = {k:i for i,k in enumerate(SQF_PARTICLE_CLASSES.keys())}

# =============================
# VECTOR GENERATOR
# =============================
def sqf_vector(particle_type, particle_class):
    vector = np.zeros(10)
    vector[0] = PARTICLE_IDX.get(particle_type, PARTICLE_IDX["Unknown"])
    class_list = SQF_PARTICLE_CLASSES.get(particle_type, ["Unknown"])
    vector[1] = class_list.index(particle_class) if particle_class in class_list else 0
    features = SubclassSemanticMatrix.get(particle_class,{}).get("features",{})
    vector[2] = features.get("life",0)
    vector[3] = features.get("agency",0) + features.get("agency_required",0)
    vector[4] = features.get("physicality",0)
    vector[5] = features.get("plurality",0)
    vector[6] = features.get("instrumental",0) + features.get("modifies",0) + features.get("causation",0) + features.get("volition",0)
    vector[7] = features.get("spatial",0)
    vector[8] = features.get("abstract",0) + features.get("logical",0) + features.get("pointing",0) + features.get("temporal",0)
    vector[9] = 0
    return vector.tolist()

# =============================
# DATABASE HELPERS
# =============================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocab (
            tonga_word TEXT,
            comment TEXT,
            pos TEXT,
            sqf_particle TEXT,
            particle_class TEXT,
            vector TEXT,
            PRIMARY KEY(tonga_word)
        )
    """)
    conn.commit()
    conn.close()

def insert_row(row):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO vocab
        (tonga_word, comment, pos, sqf_particle, particle_class, vector)
        VALUES (?,?,?,?,?,?)
    """,(row["tonga_word"], row["comment"], row["pos"], row["sqf_particle"], row["particle_class"], str(row["vector"])))
    conn.commit()
    conn.close()

def fetch_all():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM vocab ORDER BY tonga_word",conn)
    conn.close()
    return df

init_db()

# =============================
# UI
# =============================
st.title("🌐 Tonga SQF Semantic Search")

tab1, tab2, tab3 = st.tabs(["📦 Enrich & Save", "🔍 Search", "📤 Export Pickle"])

# -----------------------------
# TAB 1 — Enrich & Save
# -----------------------------
with tab1:
    st.subheader("Upload Pickle")
    uploaded = st.file_uploader("Pickle file (.pkl) containing Tonga lexicon", type=["pkl"])
    if uploaded:
        data = pickle.load(uploaded)
        st.write(f"Loaded {len(data)} entries.")
        enriched = []
        for row in data:
            particle_type = row.get("sqf_particle","Unknown")
            particle_class = row.get("particle_class","Unknown")
            row["vector"] = sqf_vector(particle_type, particle_class)
            enriched.append(row)
            insert_row(row)
        st.success(f"Enriched and saved {len(enriched)} entries to SQLite.")
        st.dataframe(pd.DataFrame(enriched).head(20))

# -----------------------------
# TAB 2 — Search
# -----------------------------
with tab2:
    st.subheader("Search Tonga or English comment")
    query = st.text_input("Search by word or comment substring")
    if st.button("Search Text"):
        df = fetch_all()
        mask = df.apply(lambda r: query.lower() in str(r["tonga_word"]).lower() or query.lower() in str(r["comment"]).lower(), axis=1)
        st.dataframe(df[mask])

    st.subheader("Vector Search")
    vector_input = st.text_area("Enter 10-dim vector (comma-separated)")
    if st.button("Search Vector"):
        try:
            qvec = np.array([float(x) for x in vector_input.strip().split(",")])
            df = fetch_all()
            vectors = df["vector"].apply(lambda s: np.array(eval(s)))
            dot_scores = vectors.apply(lambda v: np.dot(qvec,v))
            df["score"] = dot_scores
            st.dataframe(df.sort_values("score",ascending=False).head(20))
        except:
            st.error("Invalid vector input. Enter 10 numbers separated by commas.")

# -----------------------------
# TAB 3 — Export Pickle
# -----------------------------
with tab3:
    st.subheader("Generate & Download Enriched Pickle")
    if st.button("Generate Pickle"):
        df = fetch_all()
        enriched_list = df.to_dict(orient="records")
        pickle_bytes = pickle.dumps(enriched_list)
        st.download_button(
            "Download Enriched Pickle",
            data=pickle_bytes,
            file_name="tonga_sqf_enriched.pkl",
            mime="application/octet-stream"
        )
        st.success("Pickle ready for download.")