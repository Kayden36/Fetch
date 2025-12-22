import streamlit as st
import nltk
import pandas as pd

# --- Ensure tokenizer ---
nltk.download("punkt", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)

# --- POS → Feature Map ---
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

# --- NLTK tag → coarse class ---
def map_pos(tag):
    if tag.startswith("NN"):
        return "NOUN"
    if tag.startswith("VB"):
        return "VERB"
    if tag.startswith("JJ"):
        return "ADJ"
    if tag.startswith("RB"):
        return "ADV"
    if tag in ("IN",):
        return "ADP"
    if tag in ("PRP", "PRP$"):
        return "PRON"
    if tag == "CD":
        return "NUM"
    return "OTHER"

# --- Streamlit UI ---
st.title("🧠 Token Semantic Classifier")

text = st.text_input("Enter a sentence")

if text:
    tokens = nltk.word_tokenize(text)
    tagged = nltk.pos_tag(tokens)

    rows = []
    for word, tag in tagged:
        cls = map_pos(tag)
        features = WORD_CLASS_MAP[cls]
        rows.append([word, tag, cls] + features)

    df = pd.DataFrame(
        rows,
        columns=["Token", "NLTK_POS", "Class"] + FEATURES
    )

    st.subheader("Token Classification")
    st.dataframe(df)