import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v31.0 Precision")

if 'transcript' not in st.session_state: st.session_state.transcript = ""

# --- 2. THE TRACE LOGIC (أداة التتبع) ---
def logger(stage, message, type="info"):
    with st.sidebar:
        if type == "info": st.info(f"🧬 **{stage}**: {message}")
        elif type == "success": st.success(f"✅ **{stage}**: {message}")
        elif type == "error": st.error(f"🚨 **{stage}**: {message}")
        elif type == "warning": st.warning(f"⚠️ **{stage}**: {message}")

# --- 3. DATA & ENGINEERING LOGIC (V17 Core) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png"}
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)", str(dms_str))
        if len(parts) >= 3:
            res = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
            return -res if any(x in str(dms_str).upper() for x in ['S', 'W']) else res
    except: return None

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    logger("Database", "Scanning directory for Excel files...")
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files:
        logger("Database", "No data file found!", "error")
        return None
    df = pd.read_excel(files[0])
    logger("Database", f"Loaded {len(df)} records from {files[0]}", "success")
    return df

def engine_v17_core(q, data):
    logger("Logic", f"Analyzing query: '{q}'")
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    
    if not selected_adms:
        logger("Logic", "Could not identify Country (ADM) in your speech.", "error")
        return None, [], "ADM identification error.", 0, False

    logger("Logic", f"Target ADMs identified: {selected_adms}", "success")
    reports = []
    for adm in selected_adms:
        adm_df = data[data['Country'] == adm].copy() # تأكد من اسم العمود في ملفك
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Total": a_count+l_count, "Assignments": a_count, "Allotments": l_count})
    
    return data[data['Country'].isin(selected_adms)], reports, f"Found records for {selected_adms}", 100, True

# --- 5. SPEECH PROCESSOR (The Traceable Part) ---
def whisper_stt_traceable(audio_bytes):
    if "OPENAI_API_KEY" not in st.secrets:
        logger("API", "API Key missing in Streamlit Secrets!", "error")
        return ""
    
    logger("API", "Sending audio packets to OpenAI Whisper...")
    try:
        buf = io.BytesIO(audio_bytes); buf.name = "audio.wav"
        resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                             headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                             files={"file": buf}, data={"model": "whisper-1"})
        
        if resp.status_code != 200:
            logger("API", f"OpenAI Error: {resp.json().get('error', {}).get('message')}", "error")
            return ""
            
        text = resp.json().get("text", "")
        logger("API", f"Transcription Received: '{text}'", "success")
        return text
    except Exception as e:
        logger("API", f"Request Failed: {e}", "error")
        return ""

# --- 6. UI LAYOUT ---
st.sidebar.title("🛠️ System Trace Log")
db = load_db()

c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("🎤 Voice Input")
    audio = mic_recorder(start_prompt="Record Inquiry", stop_prompt="Process Audio", key="mic_v31")

if audio:
    with c2:
        st.subheader("📈 Signal Analysis")
        waveform = np.frombuffer(audio['bytes'], dtype=np.int16)
        st.line_chart(waveform[:2000])
        
        # المرحلة الأولى: STT
        transcript = whisper_stt_traceable(audio['bytes'])
        if transcript:
            st.session_state.transcript = transcript
            # المرحلة الثانية: Processing
            res_df, reports, msg, conf, success = engine_v17_core(transcript, db)
            
            if success:
                st.write(f"📝 **Recognized:** {transcript}")
                # عرض النتائج (v17 style)
                mcols = st.columns(len(reports))
                for i, r in enumerate(reports):
                    with mcols[i]:
                        st.metric(r['Adm'], f"Total: {r['Total']}", f"Assig: {r['Assignments']}")
                
                st.dataframe(res_df)
            else:
                st.warning("Logic Engine couldn't parse the data. Check the Trace Log.")
