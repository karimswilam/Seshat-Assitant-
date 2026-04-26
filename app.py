import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
import plotly.express as px
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v25.0", page_icon="🛰️")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v25.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# Header Layout
h_col1, h_col2, h_col3 = st.columns([1, 2, 1])
with h_col2:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=120)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

# --- 2. CORE ENGINEERING LOGIC (STABLE v17.0) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png", 'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_DISPLAY = {'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'}, 'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'}, 'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'}, 'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'}, 'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'}, 'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'israel', 'اسرائيل']}
SYNONYMS = {'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'], 'DAB_KEY': ['dab', 'داب', 'صوتية'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'radio', 'راديو'], 'TOTAL_KEY': ['total', 'إجمالي'], 'EXCEPT_KEY': ['except', 'ماعدا']}

# --- 3. POWERFUL UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        clean = re.sub(r'[^0-9.NSEW ]', ' ', dms_str).strip().upper()
        parts = re.findall(r"(\d+)", clean); dirs = re.findall(r"([NSEW])", clean)
        if len(parts) >= 3 and dirs:
            dec = float(parts[0]) + (float(parts[1])/60.0) + (float(parts[2])/3600.0)
            return dec * -1 if dirs[0] in ['S', 'W'] else dec
    except: return None

async def say_it(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        v = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        comm = edge_tts.Communicate(text, v)
        data = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio": data.write(chunk["data"])
        data.seek(0); return data
    except: return None

def play_audio_feedback(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio = loop.run_until_complete(say_it(text))
    if audio: st.audio(audio, format="audio/mp3")

def whisper_stt(audio_bytes):
    try:
        # Buffer fix for Cloud
        buffer = io.BytesIO(audio_bytes)
        buffer.name = "audio.wav"
        resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                             headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                             files={"file": buffer}, data={"model": "whisper-1"})
        return resp.json().get("text", "")
    except: return ""

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
    return None

# --- 4. ENGINE LOGIC ---
def engine_v17_core(q, data):
    q_low = q.lower()
    adms = list(dict.fromkeys([code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]))
    if not adms: return None, [], "Error: Country not identified.", 0, False
    
    svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04'] if any(x in q_low for x in SYNONYMS['TOTAL_KEY']) else []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    
    reports = []; final_df = pd.DataFrame()
    for adm in adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        a, l = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]), len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Total": a+l, "Assignments": a, "Allotments": l})
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Total']} records" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. HYBRID UI FLOW ---
db = load_db()

st.subheader("🎙️ Input Signal Control")
c1, c2 = st.columns([1, 2])

with c1:
    audio_input = mic_recorder(start_prompt="Speak Inquiry", stop_prompt="Process Signal", key="mic_v25")

captured_text = ""
if audio_input:
    with c2:
        # Visual Signal Feedback
        waveform = np.frombuffer(audio_input['bytes'], dtype=np.int16)
        st.line_chart(waveform[:3000], height=100)
        p_bar = st.progress(0)
        for i in range(100): time.sleep(0.005); p_bar.progress(i+1)
        captured_text = whisper_stt(audio_input['bytes'])

query = st.text_input("📝 Confirm/Override Query:", value=captured_text)

if query and db is not None:
    # 1. Play Question Replay (as in v17)
    st.markdown("### 🔈 Input Recognition")
    play_audio_feedback(query)
    
    # 2. Run Engine
    res_df, reports, msg, conf, success = engine_v17_core(query, db)
    
    if success:
        st.divider()
        # Flags & Metrics
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f"**{COUNTRY_DISPLAY[r['Adm']]['ar']}**")
                st.image(FLAGS.get(r['Adm']), width=150)
                st.metric(f"{r['Adm']} Stats", f"Total: {r['Total']}", f"Assig: {r['Assignments']}")

        # Map & Charts
        m_col1, m_col2 = st.columns([2, 1])
        with m_col1:
            if 'lat_dec' in res_df.columns:
                fig = px.scatter_mapbox(res_df.dropna(subset=['lat_dec']), lat="lat_dec", lon="lon_dec", color="Adm", zoom=3, mapbox_style="carto-positron", height=400)
                st.plotly_chart(fig, use_container_width=True)
        with m_col2:
            st.bar_chart(pd.DataFrame(reports).set_index('Adm')[['Assignments', 'Allotments']])

        # Final Voice Output
        st.success(f"Assistant: {msg}")
        play_audio_feedback(msg)
        
        with st.expander("Raw Data Explorer"):
            st.dataframe(res_df)
