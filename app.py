import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests
import numpy as np
import edge_tts
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v21.0", page_icon="🛰️")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v21.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# Header
header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. CONSTANTS & DICTIONARIES (Your Core Logic) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'TUR': "https://flagcdn.com/w640/tr.png"}
COUNTRY_MAP = {'EGY': ['egypt', 'مصر'], 'TUR': ['turkey', 'تركيا']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. CORE UTILITIES ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        # 🔥 إصلاح مشكلة ArrowTypeError المذكورة في الـ Log
        # تحويل أي عمود يحتوي على تاريخ أو Receipt إلى نص لمنع تعارض الأنواع
        for col in df.columns:
            if any(key in col.lower() for key in ['date', 'receipt', 'time']):
                df[col] = df[col].astype(str).replace(['nan', 'NaT'], '')
        
        df.columns = df.columns.astype(str).str.strip()
        return df
    return None

def compute_signal_level(audio_bytes):
    """مؤشر هندسي للتأكد من التقاط المايك للصوت"""
    if not audio_bytes: return 0
    arr = np.frombuffer(audio_bytes, dtype=np.int16)
    if arr.size == 0: return 0
    rms = np.sqrt(np.mean(arr.astype(float)**2))
    return min(int((rms / 32768) * 150), 100)

def stt_whisper(audio_bytes):
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper-1"}
        )
        return response.json().get("text", "")
    except: return ""

async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-SalmaNeural" if is_ar else "en-US-AndrewNeural"
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

# --- 4. THE ENGINE ---
def engine_v21(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "❌ لم يتم تحديد الدولة.", 0, False

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count, "Total": a_count+l_count})
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    msg = f"تم تحليل بيانات {len(selected_adms)} دول."
    return final_df, reports, msg, 100, True

# --- 5. UI MAIN FLOW ---
db = load_db()

st.markdown("### 🎙️ Signal Capture & Validation")
c_mic, c_feed = st.columns([1, 3])

with c_mic:
    audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop & Analyze", key="v21_mic")

voice_query = ""
if audio_data:
    signal = compute_signal_level(audio_data['bytes'])
    with c_feed:
        # Oscilloscope Feedback
        st.write(f"**Signal Detected:** {len(audio_data['bytes'])/1024:.2f} KB received.")
        waveform = np.frombuffer(audio_data['bytes'], dtype=np.int16)
        st.line_chart(waveform[:2000], height=80) # رؤية الموجة الصوتية فوراً
        
    if signal > 5:
        with st.spinner("🔄 Decoding signal via Whisper..."):
            voice_query = stt_whisper(audio_data['bytes'])
            if voice_query: st.success(f"Recognized: {voice_query}")
    else:
        st.error("⚠️ Signal too weak. Please check your mic.")

# Input Field (Voice or Text)
query = st.text_input("⌨️ Confirm/Override Query:", value=voice_query)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v21(query, db)
    
    if success:
        st.toast("✅ Analysis Complete", icon="✔")
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=150)
                st.metric(r['Adm'], f"Total: {r['Total']}", f"Assig: {r['Assignments']}")

        # Data Table with Fix for ArrowTypeError
        with st.expander("Detailed Engineering Records"):
            st.dataframe(res_df, use_container_width=True)
            
        # Map with updated Plotly call (scatter_map instead of scatter_mapbox)
        if 'lat_dec' in res_df.columns:
            import plotly.express as px
            st.divider()
            fig = px.scatter_map(res_df.dropna(subset=['lat_dec']), lat="lat_dec", lon="lon_dec", color="Adm", zoom=3)
            st.plotly_chart(fig, use_container_width=True)
