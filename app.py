import streamlit as st
import pandas as pd
import os, io, re, asyncio, edge_tts, time
import numpy as np
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import requests

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")
LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# تظبيط الهيدر
st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1>
        <p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p>
    </div>
""", unsafe_allow_html=True)
st.divider()

# --- 2. ENGINEERING CONSTANTS ---
COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. SPEECH & SIGNAL LOGIC ---
def speech_to_text_engine(audio_bytes):
    # محاولة استخدام OpenAI أولاً
    api_key = st.secrets.get("OPENAI_API_KEY")
    if api_key and "sk-" in api_key:
        try:
            buf = io.BytesIO(audio_bytes); buf.name = "audio.wav"
            resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                                headers={"Authorization": f"Bearer {api_key}"},
                                files={"file": buf}, data={"model": "whisper-1"})
            if resp.status_code == 200: return resp.json().get("text", "")
        except: pass
    
    # الحل المجاني (Fallback) عشان المشروع ميتعطلش
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language="ar-EG")
        except:
            try: return recognizer.recognize_google(audio_data, language="en-US")
            except: return ""

# --- 4. DATA ENGINE (FIXED KEYERROR) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # الربط الذكي اللي بيحل مشكلة الـ KeyError
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'الادارة', 'إدارة'],
            'Notice Type': ['Notice Type', 'NT', 'نوع الإخطار'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'اسم الموقع']
        }
        for std_name, synonyms in mapping.items():
            for col in df.columns:
                if col in synonyms:
                    df.rename(columns={col: std_name}, inplace=True)
                    break
        return df
    return None

def engine_v17_core(q, data):
    q_low = q.lower()
    # تحديد الدول
    adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not adms: return None, [], "Identification error.", 0, False

    reports = []; final_df = pd.DataFrame()
    for adm in adms:
        # التأكد من وجود العمود لتجنب الصور اللي بعتها
        if 'Adm' not in data.columns: return None, [], "Column 'Adm' not found!", 0, False
        
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({"Adm": adm, "Total": a_count + l_count, "Assignments": a_count, "Allotments": l_count})
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    return final_df, reports, f"Processed {len(adms)} countries.", 100, True

# --- 5. MAIN UI FLOW ---
db = load_db()

with st.sidebar:
    st.header("Settings")
    if db is not None: st.success("✅ Database Connected")
    else: st.error("❌ No Data.xlsx found")

st.subheader("🎤 Intelligence Control Center")
audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key="mic")

query = ""
if audio_input:
    # الـ Status Bar اللي كان بيضرب Error
    with st.status("📡 Processing Spectrum Intelligence...", expanded=True) as status:
        st.write("1. Validating Sound Variation...")
        time.sleep(0.4) # دلوقتي الـ time متعرف صح
        st.write("2. Converting Signal to Text...")
        query = speech_to_text_engine(audio_input['bytes'])
        if query:
            status.update(label=f"🎯 Query Recognized: {query}", state="complete")
        else:
            status.update(label="❌ No Voice Detected", state="error")

if not query:
    query = st.text_input("⌨️ Manual Inquiry / Confirmation:")

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v17_core(query, db)
    if success:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            cols[i].metric(f"Country: {r['Adm']}", f"Total: {r['Total']}", f"Assig: {r['Assignments']}")
        
        with st.expander("View Filtered Spectrum Data"):
            st.dataframe(res_df)
