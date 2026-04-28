import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import numpy as np
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import nest_asyncio

# تفعيل nest_asyncio للتعامل مع edge-tts
nest_asyncio.apply()

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Se-Chat v18.7", page_icon="📡")

st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 5px; }
    .flag-img { width: 80px; border-radius: 5px; cursor: pointer; transition: 0.3s; }
    .flag-img:hover { transform: scale(1.1); filter: brightness(1.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { border-radius: 10px; }
    .centered-msg { 
        text-align: center; font-size: 20px; color: #1E3A8A; 
        padding: 20px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat التنسيق الدولي للطيف v18.7"
PROJECT_SLOGAN = "Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=100)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

# --- 2. FIXED ENGINEERING LOGIC ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'مصر', 'en': 'Egypt'},
    'ARS': {'ar': 'السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'تركيا', 'en': 'Turkey'},
    'CYP': {'ar': 'قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'اليونان', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

CAT_MAP = {
    'DAB': ['GS1','GS2','DS1','DS2'],
    'TV': ['T02','G02','GT1','GT2','DT1','DT2'],
    'FM': ['T01','T03','T04']
}

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'المصريه', 'مصرية', 'مصريه'],
    'ARS': ['saudi', 'saudiarabia', 'ars', 'ksa', 'السعودية', 'سعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'إسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تردد'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'مرئية'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'GE06_KEY': ['ge06', 'geneva06', 'جنيف 06'],
    'GE84_KEY': ['ge84', 'geneva84', 'جنيف 84']
}

# --- 3. UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        clean_str = re.sub(r'[^0-9.NSEW ]', ' ', dms_str).strip().upper()
        parts = re.findall(r"(\d+)", clean_str)
        direction = re.findall(r"([NSEW])", clean_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None

def speech_to_text_robust(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        webm_audio = io.BytesIO(audio_data['bytes'])
        audio_segment = AudioSegment.from_file(webm_audio, format="webm")
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.record(source)
        try:
            return r.recognize_google(audio, language="ar-EG")
        except:
            return r.recognize_google(audio, language="en-US")
    except Exception: return None

async def generate_audio_stream(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        communicate = edge_tts.Communicate(text, voice, rate="-5%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def speak_text(text):
    if text:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio_stream(text))
        if data: st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. DATA LOADER ---
@st.cache_data
def load_db():
    main_df = pd.DataFrame()
    if os.path.exists("Data.xlsx"):
        df1 = pd.read_excel("Data.xlsx")
        df1['Source_Plan'] = 'GE06'
        main_df = df1
    if os.path.exists("FM.xlsx"):
        df2 = pd.read_excel("FM.xlsx")
        df2['Source_Plan'] = 'GE84'
        main_df = pd.concat([main_df, df2], ignore_index=True)
    
    if not main_df.empty:
        main_df.columns = main_df.columns.str.strip()
        main_df = main_df.rename(columns={'Administration': 'Adm', 'Country': 'Adm', 'NT': 'Notice Type'})
        if 'Geographic Coordinates' in main_df.columns:
            coords = main_df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords.shape[1] >= 2:
                main_df['lon_dec'] = coords[0].apply(dms_to_decimal)
                main_df['lat_dec'] = coords[1].apply(dms_to_decimal)
        if 'Assigned Frequency' in main_df.columns:
            main_df['freq_val'] = main_df['Assigned Frequency'].apply(lambda x: float(re.findall(r"\d+\.?\d*", str(x))[0]) if re.findall(r"\d+\.?\d*", str(x)) else 0.0)
    return main_df

# --- 5. SEARCH ENGINE ---
def engine_v18_7(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM not found", 0, False

    f_range = re.findall(r"(\d+\.?\d*)", q_low)
    f_start, f_stop = (float(f_range[0]), float(f_range[1])) if len(f_range) >= 2 else (None, None)

    filter_plan = 'GE06' if any(x in q_low for x in SYNONYMS['GE06_KEY']) else ('GE84' if any(x in q_low for x in SYNONYMS['GE84_KEY']) else None)
    
    wanted_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): wanted_codes.extend(CAT_MAP['DAB'])
    if any(x in q_low for x in SYNONYMS['TV_KEY']): wanted_codes.extend(CAT_MAP['TV'])
    if any(x in q_low for x in SYNONYMS['FM_KEY']): wanted_codes.extend(CAT_MAP['FM'])
    if not wanted_codes: wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV'] + CAT_MAP['FM'] + ['G01']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if filter_plan: adm_df = adm_df[adm_df['Source_Plan'] == filter_plan]
        if f_start and f_stop: adm_df = adm_df[(adm_df['freq_val'] >= f_start) & (adm_df['freq_val'] <= f_stop)]
        
        adm_filtered = adm_df[adm_df['Notice Type'].isin(wanted_codes)]
        a_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({
            "Adm": adm, "Assignments": a_count, "Allotments": l_count, "Total": a_count + l_count,
            "Stats": {'DAB': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['DAB'])]),
                      'TV': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['TV'])]),
                      'FM': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['FM'])])},
            "DisplayName": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        })
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)

    msg = ". ".join([f"{r['DisplayName']}: {r['Total']} items" for r in reports])
    return final_df, reports, msg, 100, True

# --- 6. UI FLOW ---
db = load_db()

# Flags Matrix - Scrolling Horizontal
if 'voice_active' not in st.session_state: st.session_state.voice_active = False

# Show flags only if no voice command is active
if not st.session_state.voice_active:
    st.write("### 🌍 Select Country (ADM)")
    flag_cols = st.columns(len(FLAGS))
    for i, (code, url) in enumerate(FLAGS.items()):
        with flag_cols[i]:
            st.markdown(f'<div class="flag-container"><img src="{url}" class="flag-img"></div>', unsafe_allow_html=True)
            if st.button(f"Analyze {code}", key=f"btn_{code}"):
                st.session_state.query_input = code

# Input Section
with st.container(border=True):
    c_v1, c_v2, c_v3 = st.columns([1, 4, 1])
    with c_v1:
        voice_raw = mic_recorder(start_prompt="🎤 Voice", stop_prompt="🛑 Stop", key="mic_v187")
    
    if voice_raw:
        st.session_state.voice_active = True
        st.session_state.query_input = speech_to_text_robust(voice_raw)

    with c_v2:
        final_query = st.text_input("Search ADM or Frequency:", value=st.session_state.get('query_input', ''))

    with c_v3:
        if st.button("Reset 🔄"):
            st.session_state.voice_active = False
            st.session_state.query_input = ""
            st.rerun()

# Execution
if final_query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_7(final_query, db)
    
    if success:
        st.success(msg)
        if st.session_state.voice_active: speak_text(msg)
        
        if len(reports) == 1:
            r = reports[0]
            st.markdown(f'<div class="flag-container"><img src="{FLAGS.get(r["Adm"])}" style="width:120px; border-radius:10px;"></div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("FM Radio", r['Stats']['FM'])
            m2.metric("DAB Digital", r['Stats']['DAB'])
            m3.metric("TV Broadcasting", r['Stats']['TV'])
            
            st.divider()
            col_left, col_right = st.columns(2)
            with col_left:
                if PLOTLY_AVAILABLE:
                    map_df = res_df.dropna(subset=['lat_dec', 'lon_dec'])
                    if not map_df.empty:
                        fig = px.scatter_mapbox(map_df, lat="lat_dec", lon="lon_dec", color="Notice Type", zoom=5, height=400, mapbox_style="carto-positron", title="Site Distribution")
                        st.plotly_chart(fig, use_container_width=True)
            with col_right:
                pie_df = pd.DataFrame({'Service': ['FM', 'DAB', 'TV'], 'Count': [r['Stats']['FM'], r['Stats']['DAB'], r['Stats']['TV']]})
                st.plotly_chart(px.pie(pie_df, values='Count', names='Service', hole=0.5, title="Service Share"), use_container_width=True)
        
        with st.expander("Technical Data Sheet"):
            st.dataframe(res_df, use_container_width=True)
