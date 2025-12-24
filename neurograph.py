import streamlit as st
import pandas as pd
import pickle

st.title("Local Language Vocabulary → Pickle Generator (Raw POS)")

# Upload Excel file
uploaded_file = st.file_uploader("Upload your Tonga vocab Excel file", type=["xlsx", "xls"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("Preview of Excel data:")
    st.dataframe(df.head())

    # Convert to dictionary
    tonga_vocab = df.to_dict(orient='index')

    # Button to save pickle
    if st.button("Generate Pickle"):
        pickle_file_name = "tonga_vocab.pickle"
        with open(pickle_file_name, "wb") as f:
            pickle.dump(tonga_vocab, f)
        st.success(f"Pickle file saved as {pickle_file_name}")
        st.download_button(
            "Download Pickle",
            data=open(pickle_file_name, "rb").read(),
            file_name=pickle_file_name
        )