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
st.set_page_config(layout="wide", page_title="Se-Chat v18.6 Professional", page_icon="📡")

# إضافة ستايل الـ Chiclet Slicer والـ UI
st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { width: 100%; border-radius: 20px; }
    .centered-msg { 
        text-align: center; font-size: 20px; color: #1E3A8A; 
        padding: 20px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 20px 0;
    }
    /* Chiclet Slicer Styling */
    .slicer-wrapper {
        display: flex;
        overflow-x: auto;
        gap: 12px;
        padding: 10px 0px;
        margin-bottom: 20px;
    }
    .chiclet-item {
        flex: 0 0 auto;
        width: 120px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat v18.6"
PROJECT_SLOGAN = "Spectrum Intelligence & International Coordination"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=120)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

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
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'المصريه', 'مصرية', 'مصريه', 'قصر', 'متر'],
    'ARS': ['saudi', 'saudiarabia', 'ars', 'ksa', 'السعودية', 'المملكة', 'المملكه', 'سعودية', 'سعوديه'],
    'TUR': ['turkey', 'tur', 'تركيا', 'تركي', 'التركية', 'التركيه'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'إسرائيل', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot', 'allots'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig', 'assigs', 'تردد', 'ترددات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه'],
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
    return None

def apply_phonetic_correction(text):
    if not text: return text
    corrections = {
        r'\bدياب\b': 'داب', r'\bدب\b': 'داب', r'\bباب\b': 'داب',
        r'\bناصيف\b': 'مصر', r'\bناصر\b': 'مصر', r'\bمتر\b': 'مصر',
        r'\bزومبايل\b': 'إسرائيل', r'\bعزرائيل\b': 'إسرائيل'
    }
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

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
            english_text = r.recognize_google(audio, language="en-US")
            if any(word in english_text.lower() for word in ['egypt', 'saudi', 'assignment']): return english_text
        except: pass
        raw_text = r.recognize_google(audio, language="ar-EG")
        return apply_phonetic_correction(raw_text)
    except: return None

async def generate_audio_stream(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-5%")
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

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    main_df = pd.DataFrame()
    if os.path.exists("Data.xlsx"):
        df1 = pd.read_excel("Data.xlsx")
        df1.columns = df1.columns.str.strip()
        df1['Source_Plan'] = 'GE06'
        main_df = df1
    if os.path.exists("FM.xlsx"):
        df2 = pd.read_excel("FM.xlsx")
        df2.columns = df2.columns.str.strip()
        df2['Source_Plan'] = 'GE84'
        main_df = pd.concat([main_df, df2], ignore_index=True)
    
    if not main_df.empty:
        mapping = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT']}
        for std_name, synonyms in mapping.items():
            for col in main_df.columns:
                if col in synonyms:
                    main_df = main_df.rename(columns={col: std_name})
                    break
        if 'Geographic Coordinates' in main_df.columns:
            coords_split = main_df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords_split.shape[1] >= 2:
                main_df['lon_dec'] = coords_split[0].apply(dms_to_decimal)
                main_df['lat_dec'] = coords_split[1].apply(dms_to_decimal)
        if 'Assigned Frequency' in main_df.columns:
            main_df['freq_val'] = pd.to_numeric(main_df['Assigned Frequency'].astype(str).str.extract(r'(\d+\.?\d*)')[0], errors='coerce')
        return main_df
    return None

def engine_v18_6(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    if not selected_adms: return None, [], "Country not found.", 0, False

    freq_numbers = re.findall(r"(\d+\.?\d*)", q_low)
    f_start, f_stop = (None, None)
    if len(freq_numbers) >= 2:
        nums = sorted([float(n) for n in freq_numbers])
        f_start, f_stop = nums[0], nums[1]

    filter_plan = 'GE06' if any(x in q_low for x in SYNONYMS['GE06_KEY']) else ('GE84' if any(x in q_low for x in SYNONYMS['GE84_KEY']) else None)
    is_allot_only = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    is_assig_only = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    comp_type = "Assignments" if is_assig_only else ("Allotments" if is_allot_only else "Total")

    wanted_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): wanted_codes.extend(CAT_MAP['DAB'])
    if any(x in q_low for x in SYNONYMS['TV_KEY']): wanted_codes.extend(CAT_MAP['TV'])
    if any(x in q_low for x in SYNONYMS['FM_KEY']): wanted_codes.extend(CAT_MAP['FM'])
    if not wanted_codes: wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV'] + CAT_MAP['FM'] + ['G01']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_full = data[data['Adm'] == adm].copy()
        if filter_plan: adm_full = adm_full[adm_full['Source_Plan'] == filter_plan]
        if f_start and f_stop: adm_full = adm_full[(adm_full['freq_val'] >= f_start) & (adm_full['freq_val'] <= f_stop)]
        adm_filtered = adm_full[adm_full['Notice Type'].isin(wanted_codes)]
        
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

    msg = ". ".join([f"{r['DisplayName']}: {r[comp_type] if comp_type in r else r['Total']} {comp_type}" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

# --- COUNTRY CHICLET SLICER ---
st.markdown("### 🌍 Select Country")
selected_from_slicer = ""

# التصميم العرضي للسليسر
with st.container():
    # استخدام div كـ wrapper للـ scroll
    st.markdown('<div class="slicer-wrapper">', unsafe_allow_html=True)
    cols = st.columns(len(COUNTRY_DISPLAY))
    for i, (code, info) in enumerate(COUNTRY_DISPLAY.items()):
        with cols[i]:
            st.image(FLAGS[code], width=70)
            if st.button(info['ar'], key=f"btn_{code}"):
                selected_from_slicer = info['ar']
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- VOICE & TEXT INPUT ---
with st.container(border=True):
    col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤 Speak", stop_prompt="🛑 Stop", key="v186_mic")
    
    input_val = speech_to_text_robust(voice_raw) if voice_raw else ""
    
    # دمج السليسر مع المدخلات
    final_query = selected_from_slicer if selected_from_slicer else input_val
    
    with col_v2:
        query = st.text_input("Spectrum Inquiry / استفسار الترددات:", value=final_query)
    with col_v3:
        if st.button("👂 Listen"): speak_text(query)

# --- EXECUTION & DASHBOARD ---
if query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_6(query, db)
    
    if not success:
        st.markdown(f'<div class="centered-msg">{msg}</div>', unsafe_allow_html=True)
    else:
        st.success(msg)
        if st.button("🔊 Play Results"): speak_text(msg)
        
        if len(reports) == 1:
            r = reports[0]
            st.markdown(f'<div class="flag-container"><img src="{FLAGS.get(r["Adm"])}" class="flag-img"></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("DAB", r['Stats']['DAB'])
            c2.metric("TV", r['Stats']['TV'])
            c3.metric("FM", r['Stats']['FM'])
            
            st.divider()
            d1, d2 = st.columns(2)
            with d1:
                map_data = res_df[res_df['Notice Type'].isin(STRICT_ASSIG)].dropna(subset=['lat_dec', 'lon_dec'])
                if not map_data.empty:
                    st.plotly_chart(px.scatter_mapbox(map_data, lat="lat_dec", lon="lon_dec", color="Notice Type", zoom=4, height=400, mapbox_style="carto-positron"), use_container_width=True)
            with d2:
                svc_df = pd.DataFrame({'Service': list(r['Stats'].keys()), 'Count': list(r['Stats'].values())})
                st.plotly_chart(px.pie(svc_df, values='Count', names='Service', hole=0.4, title="Distribution"), use_container_width=True)
        else:
            m_cols = st.columns(len(reports))
            for i, r in enumerate(reports):
                with m_cols[i]:
                    st.image(FLAGS.get(r["Adm"]), width=60)
                    st.metric(r['DisplayName'], r['Total'])

        with st.expander("Detailed Technical Records"):
            st.dataframe(res_df, use_container_width=True)
