import streamlit as st
import pandas as pd
import os, io, re, asyncio, edge_tts, base64, requests
import numpy as np
import speech_recognition as sr  # للمجاني
from streamlit_mic_recorder import mic_recorder

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE (Original v17.0 Style) ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")
LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. FIXED ENGINEERING LOGIC (V17.0) ---
# [Keep all your FLAGS, COUNTRY_MAP, and SYNONYMS here exactly as they are]
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png", 'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر', 'المصرية'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
SYNONYMS = {'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'], 'DAB_KEY': ['dab', 'داب', 'صوتية'], 'TV_KEY': ['tv', 'television', 'تلفزيون'], 'FM_KEY': ['fm', 'radio', 'راديو'], 'TOTAL_KEY': ['total', 'إجمالي'], 'EXCEPT_KEY': ['except', 'ma3ada']}

# --- 3. THE NEW DIAGNOSTIC ENGINE (Your Request) ---
def analyze_signal(audio_bytes):
    """بيشوف لو الصوت حقيقي بناء على الـ Intensity"""
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_array.astype(float)**2))
    db = 20 * np.log10(rms) if rms > 0 else 0
    # الـ Human voice غالبا بيبقى فيه Variation عالي في الـ dB
    variation = np.std(audio_array)
    return (db > 35 and variation > 100), db

def speech_to_text_engine(audio_bytes):
    """محرك مزدوج: OpenAI (بفلوس) أو Google (مجاني)"""
    # 1. Trial with OpenAI Whisper if Key exists
    api_key = st.secrets.get("OPENAI_API_KEY")
    if api_key and "sk-" in api_key:
        try:
            buf = io.BytesIO(audio_bytes); buf.name = "audio.wav"
            resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                                headers={"Authorization": f"Bearer {api_key}"},
                                files={"file": buf}, data={"model": "whisper-1"})
            if resp.status_code == 200: return resp.json().get("text", "")
        except: pass
    
    # 2. Fallback to Google Free API (Zero Cost)
    st.info("📡 Using Free Signal Processing (No API Key required)...")
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language="ar-EG")
        except:
            try: return recognizer.recognize_google(audio_data, language="en-US")
            except: return ""

# --- 4. ENGINE CORE v17.0 (Mapping Logic Included) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # ده الـ Mapping اللي إنت عامله في 17.0 وهو ممتاز
        mapping = {'Adm': ['Administration', 'Adm', 'Country', 'الادارة'], 'Notice Type': ['Notice Type', 'NT'], 'Site/Allotment Name': ['Site/Allotment Name', 'Site Name'], 'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates']}
        for std, syns in mapping.items():
            for col in df.columns:
                if col in syns: df.rename(columns={col: std}, inplace=True); break
        return df
    return None

# [Keep your engine_v17_0 function here exactly as it is]

# --- 5. UI WITH INDICATORS ---
db = load_db()

st.subheader("🎤 Voice Control & Signal Monitor")
diag_col1, diag_col2 = st.columns([1, 2])

with diag_col1:
    audio = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key="v17_mic")

query = ""
if audio:
    with diag_col2:
        is_human, db_level = analyze_signal(audio['bytes'])
        if is_human:
            st.success(f"✅ Signal Detected! (Intensity: {db_level:.1f} dB)")
            # شريط المعالجة اللي طلبته
            with st.status("🛠️ Processing Audio...", expanded=True) as status:
                st.write("1. Validating Sound Variation...")
                time.sleep(0.3)
                st.write("2. Converting Signal to Text...")
                query = speech_to_text_engine(audio['bytes'])
                if query:
                    status.update(label=f"🎯 Recognized: {query}", state="complete")
                else:
                    status.update(label="❌ Failed to understand text.", state="error")
        else:
            st.error(f"🚫 No Human Voice Detected (Low Intensity: {db_level:.1f} dB)")

# Fallback Input
if not query:
    query = st.text_input("📝 Manual Inquiry:", key="manual")

# [Rest of your UI/Dashboard code from v17.0]
