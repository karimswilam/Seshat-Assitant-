import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Stage 0 - Sanity Check", layout="centered")

st.title("✅ Stage 0: Streamlit Sanity Check")

st.subheader("📁 Files in current directory")
st.write(os.listdir("."))

DATA_FILE = "data.xlsx"

st.subheader("📄 Checking data.xlsx")

if not os.path.exists(DATA_FILE):
    st.error("❌ data.xlsx NOT FOUND")
    st.write("Make sure the file is uploaded next to app.py")
    st.stop()

st.success("✅ data.xlsx found")

st.subheader("📥 Loading Excel file")

try:
    df = pd.read_excel(DATA_FILE)
except Exception as e:
    st.error("❌ Failed to read data.xlsx")
    st.exception(e)
    st.stop()

st.success("✅ Excel loaded successfully")

st.subheader("🔍 Data preview (first 5 rows)")
st.dataframe(df.head())
