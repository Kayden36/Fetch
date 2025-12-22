import streamlit as st
import spacy
import numpy as np
import pandas as pd

# --- NLP setup (NO external models) ---
nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

# --- Semantic feature rules (cheap "embeddings") ---
WORD_CLASS_MAP = {
    "NOUN":  [0.85, 0.10, 0.40, 0.30, 0.15, 0.0, 0.0],
    "VERB":  [0.10, 0.85, 0.30, 0.20, 0.10, 0.0, 0.2],
    "ADJ":   [0.30, 0.20, 0.10, 0.70, 0.10, 0.0, 0.0],
    "ADV":   [0.10, 0.20, 0.10, 0.60, 0.20, 0.0, 0.0],
    "ADP":   [0.05, 0.05, 0.80, 0.05, 0.05, 0.0, 0.0],
    "PRON":  [0.05, 0.10, 0.05, 0.10, 0.70, 0.0, 0.0],
    "NUM":   [0.20, 0.05, 0.05, 0.60, 0.10, 0.2, 0.0],
    "OTHER": [0.10, 0.10, 0.10, 0.10, 0.10, 0.0, 0.0],
}

FEATURES = [
    "Bosonness", "Fermionness", "Gluonness",
    "Photonness", "Leptonness", "Charge", "Operator"
]

def token_to_vec(token):
    pos = token.pos_ if token.pos_ else "OTHER"
    return np.array(WORD_CLASS_MAP.get(pos, WORD_CLASS_MAP["OTHER"]))

def sentence_gist(sentence):
    vectors = [token_to_vec(t) for t in sentence if t.is_alpha]
    if not vectors:
        return np.zeros(len(FEATURES))
    return np.mean(vectors, axis=0)

def paragraph_gist(sent_gists):
    if not sent_gists:
        return np.zeros(len(FEATURES))
    weights = np.array([np.linalg.norm(g) for g in sent_gists])
    weights = weights / weights.sum()
    return np.sum([w * g for w, g in zip(weights, sent_gists)], axis=0)

# --- Streamlit UI ---
st.title("🧠 Quantum Disambiguation Engine")
text = st.text_area("Input text", height=150)

if text:
    doc = nlp(text)

    sentence_rows = []
    sentence_gists = []

    for sent in doc.sents:
        gist = sentence_gist(sent)
        sentence_gists.append(gist)
        sentence_rows.append([sent.text] + list(gist))

    para_gist = paragraph_gist(sentence_gists)

    st.subheader("Sentence Gist Vectors")
    df_sent = pd.DataFrame(sentence_rows, columns=["Sentence"] + FEATURES)
    st.dataframe(df_sent)

    st.subheader("Paragraph Gist Vector")
    df_para = pd.DataFrame([para_gist], columns=FEATURES)
    st.dataframe(df_para)