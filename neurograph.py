import streamlit as st
import pandas as pd
import sqlite3
import pickle
import io

st.title("Tonga Vocabulary Ingest & Persist")

# --- SQLite Setup ---
conn = sqlite3.connect("tonga_vocab.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS vocab (
    tonga_word TEXT PRIMARY KEY,
    english_translation TEXT,
    POS TEXT,
    class INTEGER
)
""")
conn.commit()

# --- Manual Input ---
st.header("Manual Input")
manual_input = st.text_area(
    "Enter Tonga vocab manually (one per line, tab-separated: Tonga Word<TAB>English Translation<TAB>POS<TAB>Class)",
    height=150
)
if st.button("Add Manual Input"):
    if manual_input.strip():
        lines = manual_input.strip().split("\n")
        for line in lines:
            parts = line.split("\t")
            if len(parts) == 4:
                tonga_word, translation, pos, class_num = parts
                try:
                    c.execute("INSERT OR REPLACE INTO vocab VALUES (?, ?, ?, ?)",
                              (tonga_word.strip(), translation.strip(), pos.strip(), int(class_num.strip())))
                except Exception as e:
                    st.error(f"Error inserting {tonga_word}: {e}")
        conn.commit()
        st.success("Manual input added to database.")

# --- Excel Upload ---
st.header("Upload Excel File")
uploaded_file = st.file_uploader("Upload your Tonga vocab Excel file", type=["xlsx", "xls"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("Preview of Excel data:")
    st.dataframe(df.head())

    if st.button("Add Excel Data to DB"):
        for idx, row in df.iterrows():
            try:
                c.execute("INSERT OR REPLACE INTO vocab VALUES (?, ?, ?, ?)",
                          (row['Tonga Word'], row['English Translation'], row['POS'], int(row['Class'])))
            except Exception as e:
                st.error(f"Error inserting row {idx}: {e}")
        conn.commit()
        st.success("Excel data added to database.")

# --- View Database ---
st.header("Current Database Entries")
db_df = pd.read_sql("SELECT * FROM vocab", conn)
st.dataframe(db_df)

# --- Export Pickle ---
st.header("Export Database as Pickle")
if st.button("Generate Pickle"):
    vocab_dict = db_df.set_index('tonga_word').T.to_dict()
    pickle_file_name = "tonga_vocab.pickle"
    with open(pickle_file_name, "wb") as f:
        pickle.dump(vocab_dict, f)
    st.success(f"Pickle file saved as {pickle_file_name}")
    st.download_button(
        "Download Pickle",
        data=open(pickle_file_name, "rb").read(),
        file_name=pickle_file_name
    )

# --- Close connection on exit ---
# conn.close()  # Optional: keep it open for session persistence