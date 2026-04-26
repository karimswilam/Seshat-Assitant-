import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
from streamlit_mic_recorder import mic_recorder

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v29.0", page_icon="🛰️")

# تهيئة الـ Session State لحفظ النصوص
if 'transcript' not in st.session_state: st.session_state.transcript = ""

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v29.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=120)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

# --- 2. FIXED ENGINEERING LOGIC (V17 Core) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'}, 'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'}, 'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'], 'TUR': ['turkey', 'tur', 'تركيا'], 'ISR': ['israel', 'isr', 'اسرائيل']}
SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو'],
    'TOTAL_KEY': ['total', 'إجمالي'], 'EXCEPT_KEY': ['except', 'ماعدا']
}

# --- 3. UTILITIES (STT, TTS, DMS) ---
def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)", str(dms_str))
        if len(parts) >= 3:
            res = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
            return -res if any(x in str(dms_str).upper() for x in ['S', 'W']) else res
    except: return None

async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    return audio_data

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

def whisper_stt(audio_bytes):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ Missing OpenAI API Key in Secrets!")
        return ""
    try:
        buf = io.BytesIO(audio_bytes); buf.name = "audio.wav"
        resp = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                             headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                             files={"file": buf}, data={"model": "whisper-1"})
        return resp.json().get("text", "")
    except Exception as e: return f"Error: {e}"

# --- 4. ENGINE CORE (V17 Integration) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if not target: return None
    df = pd.read_excel(target)
    df.columns = df.columns.str.strip()
    # Fix Column Headers
    mapping = {'Adm': ['Country', 'Administration', 'Adm'], 'Notice Type': ['NT', 'Notice Type'], 'Site/Allotment Name': ['Site/Allotment Name', 'Site Name']}
    for std, syns in mapping.items():
        for col in df.columns:
            if col.lower() in [s.lower() for s in syns]: df.rename(columns={col: std}, inplace=True); break
    if 'Geographic Coordinates' in df.columns:
        coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
        if coords.shape[1] >= 2:
            df['lon_dec'] = coords[0].apply(dms_to_decimal)
            df['lat_dec'] = coords[1].apply(dms_to_decimal)
    return df

def engine_v29(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM identification error.", 0, False
    
    is_total = any(x in q_low for x in SYNONYMS['TOTAL_KEY'])
    is_except = any(x in q_low for x in SYNONYMS['EXCEPT_KEY'])
    
    def get_svcs(text):
        s = []
        if any(x in text for x in SYNONYMS['DAB_KEY']): s.extend(['GS1','GS2','DS1','DS2'])
        if any(x in text for x in SYNONYMS['TV_KEY']): s.extend(['T02','G02','GT1','GT2','DT1','DT2'])
        if any(x in text for x in SYNONYMS['FM_KEY']): s.extend(['T01','T03','T04'])
        return s

    svc_codes = get_svcs(q_low)
    if is_total and not svc_codes: svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']

    reports = []; final_df = pd.DataFrame()
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Total": a_count+l_count, "Assignments": a_count, "Allotments": l_count})
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    msg = f"Analysis complete for {', '.join(selected_adms)}."
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

c1, c2 = st.columns([1, 2])
with c1:
    st.info("🎤 Voice Control & Signal Monitor")
    audio = mic_recorder(start_prompt="Start Recording", stop_prompt="Stop & Process", key="v29_mic")

if audio:
    with c2:
        waveform = np.frombuffer(audio['bytes'], dtype=np.int16)
        intensity = np.abs(waveform).mean()
        if intensity > 40:
            st.success("✅ Signal Detected & Validated")
            st.line_chart(waveform[:1500], height=80)
            with st.spinner("📡 Processing Voice Signal via OpenAI..."):
                st.session_state.transcript = whisper_stt(audio['bytes'])
        else:
            st.warning("⚠️ No valid voice signal detected. Try again.")

query = st.text_input("📝 Confirm Spectrum Inquiry:", value=st.session_state.transcript)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v29(query, db)
    if success:
        st.divider()
        # Flags & Metrics
        mcols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with mcols[i]:
                st.image(FLAGS.get(r['Adm']), width=100)
                st.metric(f"{r['Adm']} Stats", f"Σ {r['Total']}", f"A:{r['Assignments']} | L:{r['Allotments']}")

        # Map Section
        if PLOTLY_AVAILABLE and 'lat_dec' in res_df.columns:
            st.markdown("### 🌍 Geospatial Distribution")
            fig = px.scatter_mapbox(res_df.dropna(subset=['lat_dec']), lat="lat_dec", lon="lon_dec", hover_name="Site/Allotment Name", color="Adm", zoom=3, mapbox_style="carto-positron", height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Assistant Response
        st.success(f"🤖 Assistant: {msg}")
        play_audio(msg)
        
        with st.expander("🔍 View Technical Records"):
            st.dataframe(res_df)
