import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# ---------------------------------------------------------
# 1. ENGINEERING BRAIN (System Instructions)
# ---------------------------------------------------------
ENGINEERING_CONTEXT = """
You are Seshat AI, a proprietary Spectrum Management & International Coordination Engine.
Your knowledge base is grounded in ITU-R regulations and bilateral agreements.

TERMINOLOGY MAPPING:
- Sound/Radio/Audio/Broadcast = Station_Class: 'BC'
- TV/Television/Video = Station_Class: 'BT'
- Egypt = Adm: 'EGY'
- Saudi Arabia/KSA = Adm: 'ARS'
- Coordination Status: Recorded = 'RECORDED', Coordinated = 'COORDINATED'

STRICT RULES:
1. RESPONSE STYLE: Professional, concise, engineering-focused. No chatty introductions.
2. IDENTITY: Never identify as Gemini or an AI. You are 'Seshat AI Core'.
3. DATA HANDLING: If the user asks about a country or service, silently use the mapping above to write Python code.
4. SOURCE: If asked about your origin, you are a specialized model developed for spectrum governance.
"""

# ---------------------------------------------------------
# 2. SYSTEM CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

# Custom CSS لتقليل شكل الـ "Chat" وتحويله لـ "Dashboard"
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #004a99; color: white; border-radius: 5px; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Authentication Error: API Key missing.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# استخدام أحدث موديل متاح في قائمتك لضمان أعلى ذكاء
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# ---------------------------------------------------------
# 3. DATA ENGINE (Optimized for 1M+ Rows)
# ---------------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# ---------------------------------------------------------
# 4. DASHBOARD INTERFACE
# ---------------------------------------------------------
st.title("📡 Seshat AI: Spectrum Coordination Engine")
st.markdown("---")

# Metrics Quick View (بيخلي الشكل Professional فوراً)
col1, col2, col3 = st.columns(3)
col1.metric("Total Records", f"{len(df):,}")
col2.metric("Unique Administrations", df['Adm'].nunique())
col3.metric("System Status", "Operational", delta="Optimal")

st.markdown("### ⌨️ Input Command")
user_input = st.text_input("Enter Engineering Query (Arabic/English/Franco):", 
                          placeholder="e.g., kam m7ata sound recorded fe masr?")

if st.button("🚀 Execute Analysis") and user_input:
    with st.spinner("Seshat Logic Layer processing..."):
        try:
            # الخطوة 1: ترجمة السؤال لكود بايثون بناءً على الـ Engineering Context
            columns_info = df.columns.tolist()
            logic_prompt = (
                f"{ENGINEERING_CONTEXT}\n"
                f"DataFrame Columns: {columns_info}\n"
                f"Task: Write a Python one-liner to calculate the answer for: '{user_input}'\n"
                f"Return ONLY the code. Example: df[(df['Adm']=='EGY') & (df['Station_Class']=='BC')].shape[0]"
            )
            
            code_gen = model.generate_content(logic_prompt).text.strip().replace('```python', '').replace('```', '')
            
            #
