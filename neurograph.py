import streamlit as st
import spacy
import numpy as np

# --- Load English tokenizer ---
nlp = spacy.load("en_core_web_sm")

# --- Semantic table mapping ---
def token_to_particle(token_text, pos):
    feat = np.zeros(7)  # [boson, fermion, gluon, photon, lepton, charge, operator]
    if pos == "NOUN":
        feat[0] = 0.85  # bosonness
        feat[2] = 0.4   # gluonness
    elif pos == "VERB":
        feat[1] = 0.8   # fermionness
        feat[3] = 0.3   # photonness
    elif pos == "ADJ":
        feat[3] = 0.5
    elif pos == "ADV":
        feat[4] = 0.3
    return feat

# --- Disambiguation ---
def disambiguate(tokens_feats):
    feats = tokens_feats.copy()
    for i in range(len(feats)):
        if feats[i][1] > 0:  # fermionness
            if i > 0:
                feats[i-1][0] += 0.1
            if i < len(feats)-1:
                feats[i+1][0] += 0.1
    np.clip(feats, 0, 1, out=feats)
    return feats

# --- Coagulate token features into gist.vec ---
def coagulate(feats):
    return np.sum(feats, axis=0)

# --- Streamlit UI ---
st.title("Quantum-inspired Gist.vec Parser")

paragraph = st.text_area("Enter Paragraph:", 
                         "My client is selling this machine Min Pajero GD1 PRICE 55,000. CONTACT me on 0974833183.")

if st.button("Parse Gist.vec"):
    doc = nlp(paragraph)
    tokens = [t.text for t in doc]
    token_feats = np.array([token_to_particle(t.text, t.pos_) for t in doc])
    token_feats = disambiguate(token_feats)
    
    # Token-level particle features
    st.subheader("Token-level Particle Features")
    for t, f in zip(tokens, token_feats):
        st.write(f"{t}: {np.round(f,2)}")
    
    # Coagulate to paragraph gist.vec
    gist_vec = coagulate(token_feats)
    st.subheader("Paragraph Gist.vec")
    st.write(np.round(gist_vec,2))
    
    # Token contributions to gist.vec
    st.subheader("Token Contribution to Gist.vec Features")
    feature_names = ["Bosonness","Fermionness","Gluonness","Photonness","Leptonness","Charge","Operator"]
    contributions = token_feats / (gist_vec + 1e-6)  # avoid divide by zero
    for i, fname in enumerate(feature_names):
        token_vals = [(t, round(contributions[j][i],2)) for j,t in enumerate(tokens)]
        st.write(f"{fname}: {token_vals}")