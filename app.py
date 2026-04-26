import streamlit as st
import pandas as pd
import os, io, time
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import requests

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v29.0")

# --- 2. DATA ENGINE (Silent Mapping) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # Mapping إجباري عشان مشكلة الـ KeyError: 'Adm'
        m = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT']}
        for std, syns in m.items():
            for col in df.columns:
                if col in syns:
                    df.rename(columns={col: std}, inplace=True)
        return df
    return None

# --- 3. SPEECH ENGINE (The Fixed Part) ---
def speech_to_text_engine(audio_bytes):
    if not audio_bytes:
        return None
    
    # محاولة Whisper أولاً (أدق بكتير)
    api_key = st.secrets.get("OPENAI_API_KEY")
    if api_key:
        try:
            buf = io.BytesIO(audio_bytes)
            buf.name = "audio.wav"
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": buf},
                data={"model": "whisper-1", "language": "ar"}
            )
            if resp.status_code == 200:
                return resp.json().get("text")
        except:
            pass

    # الحل البديل (Fixed Google Engine)
    r = sr.Recognizer()
    try:
        # تحويل لـ AudioData مباشرة لتجنب ValueError بتاع الـ PCM Header
        audio_stream = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_stream) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language="ar-EG")
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. MAIN INTERFACE ---
st.title("Seshat Master Precision v29.0")
db = load_db()

# مسح الـ Cache يدوياً لو العمود لسه مش باين
if st.sidebar.button("🔄 Force Refresh Database"):
    st.cache_data.clear()
    st.rerun()

st.subheader("🎤 Voice Control & Signal Monitor")
audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Process Inquiry", key="v29_mic")

if audio_input:
    # الـ Status bar اللي كان بيعمل الـ NameError اتصلح بـ import time
    with st.status("📡 Analyzing Spectrum Command...", expanded=True) as status:
        st.write("1. Synchronizing Audio Buffer...")
        time.sleep(0.3) 
        query = speech_to_text_engine(audio_input['bytes'])
        
        if query and "Error" not in query:
            status.update(label=f"✅ Command Recognized: {query}", state="complete")
            st.session_state.last_query = query
        else:
            status.update(label="❌ Capture Error - Please use manual input", state="error")

# Confirm / Edit Area
final_q = st.text_input("📝 Confirm Spectrum Inquiry:", value=st.session_state.get('last_query', ""))

if final_q and db is not None:
    st.divider()
    # هنا تحط الـ engine_v17_core بتاعك لعرض النتائج
    st.success(f"Processing query for: {final_q}")
    if 'Adm' in db.columns:
        # عرض سريع للتأكد إن الـ KeyError اختفى
        match = db[db['Adm'].astype(str).str.contains(final_q, case=False, na=False)]
        st.dataframe(match)
    else:
        st.error("Column 'Adm' is still missing. Please check your Excel file headers.")
