import streamlit as st
import pandas as pd
import sqlite3
import pickle
import numpy as np

# =============================
# CONFIG
# =============================
DB_PATH = "tonga_sqf_enriched.db"
st.set_page_config("Tonga SQF Enricher & Search", layout="wide")

# =============================
# SQF Canonical Generator
# =============================
SQF_AXES = ["Boson","Fermion","Gauge","Scalar","Anchor","Operator","Boundary"]

SQF_PARTICLE_VECTORS = {
    "Boson":[1,0,0,0,0,0,0],
    "Fermion":[0,1,0,0,0,0,0],
    "Scalar":[0,0,0,1,0,0,0],
    "Gauge":[0,0,1,0,0,0,0],
    "Operator":[0,0,0,0,0,1,0],
    "Anchor":[0,0,0,0,1,0,0],
    "Photon":[0,0,0,1,0,0,0],
    "Gluon":[0,0,1,0,0,0,0],
    "Unknown":[0,0,0,0,0,0,0]
}

POS_TO_PARTICLE = {
    "Noun":"Boson","Proper Noun":"Boson","Pronoun":"Boson","Demonstrative Pronoun":"Boson",
    "Verb":"Fermion","Auxiliary Verb":"Fermion","Copula":"Fermion",
    "Adjective":"Scalar","Adverb":"Scalar","Degree Marker":"Scalar",
    "Preposition":"Gauge","Postposition":"Gauge","Possessive Marker":"Gauge",
    "Demonstrative Determiner":"Anchor",
    "Conjunction":"Operator","Subordinator":"Boundary","Complementizer":"Boundary",
    "Negation":"Operator",
    "Determiner":"Anchor","Article":"Anchor","Topic Marker":"Anchor","Focus Marker":"Scalar",
    "Particle":"Gauge","Interjection":"Scalar","Ideophone":"Scalar"
}

SQF_PARTICLE_CLASSES = {
    "Boson":[{"class":"BoC1","subparticle":"Primary actor"}],
    "Fermion":[{"class":"FeC1","subparticle":"Primary action"}],
    "Scalar":[{"class":"ScC1","subparticle":"Modifier"}],
    "Gauge":[{"class":"GaC1","subparticle":"Spatial"}],
    "Operator":[{"class":"OpC1","subparticle":"Operator"}],
    "Anchor":[{"class":"AnC1","subparticle":"Reference"}],
    "Photon":[{"class":"PhC1","subparticle":"Abstract"}],
    "Gluon":[{"class":"GlC1","subparticle":"Link"}],
    "Unknown":[{"class":"Unknown","subparticle":""}]
}

def canonical_sqf_dict(tonga_word, pos, comment=""):
    particle_type = POS_TO_PARTICLE.get(pos,"Unknown")
    particle_classes = SQF_PARTICLE_CLASSES.get(particle_type,[{"class":"Unknown","subparticle":""}])
    particle_class = particle_classes[0]["class"]
    subparticle = particle_classes[0]["subparticle"]
    vector = SQF_PARTICLE_VECTORS.get(particle_type,SQF_PARTICLE_VECTORS["Unknown"])
    return {
        "tonga_word": tonga_word,
        "pos": pos,
        "sqf_particle": particle_type,
        "particle_class": particle_class,
        "subparticle": subparticle,
        "features": vector,
        "comment": comment
    }

# =============================
# DATABASE
# =============================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lexicon (
            tonga_word TEXT PRIMARY KEY,
            pos TEXT,
            sqf_particle TEXT,
            particle_class TEXT,
            subparticle TEXT,
            features BLOB,
            comment TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_or_update(row):
    conn = get_conn()
    cur = conn.cursor()
    features_blob = pickle.dumps(row["features"])
    cur.execute("""
        INSERT OR REPLACE INTO lexicon
        (tonga_word,pos,sqf_particle,particle_class,subparticle,features,comment)
        VALUES (?,?,?,?,?,?,?)
    """, (
        row["tonga_word"], row["pos"], row["sqf_particle"],
        row["particle_class"], row["subparticle"], features_blob, row["comment"]
    ))
    conn.commit()
    conn.close()

def fetch_all():
    try:
        conn = get_conn()
        df = pd.read_sql("SELECT * FROM lexicon ORDER BY tonga_word", conn)
        conn.close()
        df["features"] = df["features"].apply(pickle.loads)
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "tonga_word","pos","sqf_particle",
            "particle_class","subparticle",
            "features","comment"
        ])

# =============================
# STREAMLIT UI
# =============================
tab1, tab2, tab3 = st.tabs(["📥 Upload & Enrich", "🔍 Search / Vector", "📦 Export Enriched Pickle"])

# -----------------------------
# TAB 1 - PICKLE UPLOAD
# -----------------------------
with tab1:
    st.subheader("Upload Pickle (List of dicts with tonga_word, pos, comment)")

    uploaded = st.file_uploader("Upload Pickle (.pkl)", type=["pkl"])
    if uploaded:
        data = pickle.load(uploaded)
        st.success(f"Loaded {len(data)} entries")
        enriched = []
        for entry in data:
            enriched.append(canonical_sqf_dict(
                entry.get("tonga_word",""),
                entry.get("pos",""),
                entry.get("comment","")
            ))
        st.write("Enriched Preview", enriched[:10])
        if st.button("Save Enriched to SQLite"):
            init_db()
            for row in enriched:
                insert_or_update(row)
            st.success(f"Saved {len(enriched)} entries to SQLite")

# -----------------------------
# TAB 2 - SEARCH / VECTOR
# -----------------------------
with tab2:
    st.subheader("Search by Word or English Comment")
    query = st.text_input("Enter Tonga word or English comment")
    df_all = fetch_all()
    if query:
        filtered = df_all[
            df_all["tonga_word"].str.contains(query,case=False) |
            df_all["comment"].str.contains(query,case=False)
        ]
        st.dataframe(filtered)

    st.divider()
    st.subheader("Vector Search (Dot Product)")
    vector_input = st.text_area(
        "Enter vector (comma-separated 7 dims)",
        placeholder="e.g. 1,0,0,0,0,0,0"
    )
    top_n = st.number_input("Top N results", min_value=1, max_value=50, value=5)

    if st.button("Run Vector Search") and vector_input:
        try:
            v = np.array([float(x) for x in vector_input.split(",")])
            if v.shape[0] != 7:
                st.error("Vector must have exactly 7 dimensions")
            else:
                df_all["dot"] = df_all["features"].apply(lambda f: np.dot(f,v))
                results = df_all.sort_values("dot",ascending=False).head(top_n)
                st.dataframe(results[["tonga_word","pos","sqf_particle","particle_class","subparticle","dot","comment"]])
        except Exception as e:
            st.error(f"Vector parse error: {e}")

# -----------------------------
# TAB 3 - EXPORT ENRICHED PICKLE
# -----------------------------
with tab3:
    st.subheader("Export Enriched SQF Lexicon as Pickle")

    try:
        df_all = fetch_all()
        if df_all.empty:
            st.warning("No data found in SQLite database.")
        else:
            enriched_list = []
            for _, row in df_all.iterrows():
                enriched_list.append({
                    "tonga_word": row["tonga_word"],
                    "pos": row["pos"],
                    "sqf_particle": row["sqf_particle"],
                    "particle_class": row["particle_class"],
                    "subparticle": row["subparticle"],
                    "features": row["features"],
                    "comment": row["comment"]
                })

            pickle_bytes = pickle.dumps(enriched_list)

            st.success(f"Prepared {len(enriched_list)} enriched entries")

            st.download_button(
                label="⬇️ Download Enriched Pickle",
                data=pickle_bytes,
                file_name="tonga_sqf_enriched.pkl",
                mime="application/octet-stream"
            )
    except Exception as e:
        st.error(f"Export failed: {e}")