import streamlit as st
import subprocess
import sys
import numpy as np

# ---------- Ensure spaCy + model ----------
def load_spacy():
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except:
        subprocess.run([sys.executable, "-m", "pip", "install", "spacy"])
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        import spacy
        return spacy.load("en_core_web_sm")

nlp = load_spacy()

# ---------- Quantum Semantic Mapping ----------
def semantic_features(token):
    """Map lexical class → particle features"""
    features = {
        "bosonness": 0.0,
        "fermionness": 0.0,
        "gluonness": 0.0,
        "photonness": 0.0,
        "leptonness": 0.0,
        "charge": 0.0,
        "operator": 0.0
    }

    if token.pos_ in ["NOUN", "PROPN"]:
        features["bosonness"] = 0.85
        features["gluonness"] = 0.40

    if token.pos_ == "VERB":
        features["fermionness"] = 0.75
        features["operator"] = 0.60

    if token.pos_ in ["ADJ", "ADV"]:
        features["photonness"] = 0.60

    if token.pos_ in ["ADP", "SCONJ", "CCONJ"]:
        features["gluonness"] = 0.80

    if token.pos_ in ["PRON", "DET"]:
        features["leptonness"] = 0.60

    if token.like_num:
        features["photonness"] = 0.70

    return np.array(list(features.values()))

FEATURE_NAMES = [
    "Bosonness",
    "Fermionness",
    "Gluonness",
    "Photonness",
    "Leptonness",
    "Charge",
    "Operator"
]

# ---------- Gist Vector Construction ----------
def gist_vector(text):
    doc = nlp(text)
    token_vectors = []
    tokens_used = []

    for token in doc:
        if token.is_alpha or token.like_num:
            vec = semantic_features(token)
            token_vectors.append(vec)
            tokens_used.append(token.text)

    if not token_vectors:
        return None, []

    # Quantum-style coagulation (sum + mild ReLU)
    mat = np.vstack(token_vectors)
    gist = np.maximum(0, mat.sum(axis=0))

    return gist, tokens_used

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Quantum Gist Engine", layout="wide")

st.title("🧠 Quantum Disambiguation Engine")
st.caption("Low-bloat semantic gist extraction · No embeddings · No attention")

text = st.text_area(
    "Enter text (scrambled or normal):",
    height=150,
    value="My client is selling this machine Min Pajero GD1 PRICE 55,000."
)

if st.button("Generate Gist.vec"):
    gist, tokens = gist_vector(text)

    if gist is None:
        st.warning("No valid tokens detected.")
    else:
        st.subheader("📌 Tokens Used")
        st.write(tokens)

        st.subheader("⚛️ Gist.vec (Low-Bloat Logits)")
        for name, value in zip(FEATURE_NAMES, gist):
            st.metric(name, round(float(value), 3))

        st.subheader("🧩 Interpretation")
        st.write("""
        • **Bosonness** → Core entities / anchors  
        • **Fermionness** → Actions & intent  
        • **Gluonness** → Structural coherence  
        • **Photonness** → Descriptors & modifiers  
        • **Leptonness** → Minor context  
        • **Charge** → Sentiment / polarity  
        • **Operator** → Command / instruction strength  
        """)

st.markdown("---")
st.caption("Prototype inspired by quantum-field semantics · 2023 model")