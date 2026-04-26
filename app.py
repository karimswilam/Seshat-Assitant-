import streamlit as st
import pandas as pd
import os, io, re, asyncio, time
import numpy as np
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import requests

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A;">{PROJECT_NAME}</h1><p>{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

# --- 2. DATA ENGINE (Fixed Mapping) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # الربط الذكي - تأكد من أسماء الأعمدة في ملفك
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'الادارة', 'إدارة'],
            'Notice Type': ['Notice Type', 'NT', 'نوع الإخطار'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name']
        }
        for std, syns in mapping.items():
            for col in df.columns:
                if col in syns:
                    df = df.rename(columns={col: std})
                    break
        return df
    return None

# --- 3. SPEECH ENGINE (Fixed ValueError) ---
def speech_to_text_engine(audio_bytes):
    # محاولة OpenAI لو متوفر
    api_key = st.secrets.get("OPENAI_API_KEY")
    if api_key:
        try:
            buf = io.BytesIO(audio_bytes)
            buf.name = "audio.wav"
            resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                                headers={"Authorization": f"Bearer {api_key}"},
                                files={"file": buf}, data={"model": "whisper-1"})
            if resp.status_code == 200: return resp.json().get("text", "")
        except: pass

    # الحل المجاني - تعديل مهم لتجنب ValueError
    recognizer = sr.Recognizer()
    try:
        # تحويل الـ bytes لملف صوتي يقبله المعالج
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="ar-EG")
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. MAIN UI ---
db = load_db()

with st.sidebar:
    if db is not None:
        st.success("✅ Database Connected")
        if 'Adm' not in db.columns:
            st.error("❌ Column 'Adm' not found! Check Excel headers.")
    else:
        st.error("❌ No Data.xlsx found")

st.subheader("🎤 Intelligence Control Center")
audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key="v17_mic")

if audio_input:
    with st.status("📡 Processing Signal...", expanded=True) as status:
        st.write("1. Validating Audio Stream...")
        query = speech_to_text_engine(audio_input['bytes'])
        if query and "Error" not in query:
            status.update(label=f"🎯 Recognized: {query}", state="complete")
            st.session_state.query = query
        else:
            status.update(label="❌ Capture Failed - Use Manual Input", state="error")

manual_query = st.text_input("📝 Confirm/Override Query:", value=st.session_state.get('query', ""))

if manual_query and db is not None:
    # هتاخد الـ Manual Query وتمررها لـ engine_v17_core اللي عندك
    st.info(f"Analyzing: {manual_query}")
