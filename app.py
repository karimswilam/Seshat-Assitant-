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
st.set_page_config(layout="wide", page_title="Seshat AI v18.5", page_icon="📡")

# CSS لتحسين المظهر وتنسيق الأزرار والأعلام
st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { width: 100%; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v18.5"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Voice Feedback"

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
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'المصريه', 'قصر', 'متر'],
    'ARS': ['saudi', 'saudiarabia', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'قبرص'],
    'GRC': ['greece', 'اليونان'],
    'ISR': ['israel', 'إسرائيل', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون', 'without']
}

# --- 3. UTILITIES & VOICE ENGINE ---
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
    corrections = {r'\bدياب\b': 'داب', r'\bدب\b': 'داب', r'\bباب\b': 'داب'}
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
            raw_text = r.recognize_google(audio, language="ar-EG")
        except:
            raw_text = r.recognize_google(audio, language="en-US")
        return apply_phonetic_correction(raw_text)
    except: return None

async def generate_audio_async(text):
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

def speak(text):
    if text:
        data = asyncio.run(generate_audio_async(text))
        if data: st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        mapping = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT']}
        for std_name, synonyms in mapping.items():
            for col in df.columns:
                if col in synonyms:
                    df = df.rename(columns={col: std_name})
                    break
        if 'Geographic Coordinates' in df.columns:
            coords_split = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords_split.shape[1] >= 2:
                df['lon_dec'] = coords_split[0].apply(dms_to_decimal)
                df['lat_dec'] = coords_split[1].apply(dms_to_decimal)
        return df
    return None

def engine_v18_5(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)][:4]
    if not selected_adms: return None, [], "Please specify a country (max 4) / برجاء تحديد الدولة", 0, False

    excluded_codes = []
    found_codes = re.findall(r'\b[a-z][0-9]{2}\b', q_low)
    explicit_codes = [c.upper() for c in found_codes]
    is_exclusion = any(x in q_low for x in SYNONYMS['EXCEPT_KEY'])
    
    if is_exclusion:
        if explicit_codes: excluded_codes.extend(explicit_codes)
        for k, codes in CAT_MAP.items():
            if any(x in q_low for x in SYNONYMS[k+'_KEY']): excluded_codes.extend(codes)

    wanted_codes = []
    for k, codes in CAT_MAP.items():
        if any(x in q_low for x in SYNONYMS[k+'_KEY']) and not is_exclusion: wanted_codes.extend(codes)
    
    if not wanted_codes: wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV'] + CAT_MAP['FM'] + ['G01']
    final_codes = [c for c in wanted_codes if c not in excluded_codes]

    reports = []; final_df = pd.DataFrame()
    comp_key = "Assignments" if any(x in q_low for x in SYNONYMS['ASSIG_KEY']) else ("Allotments" if any(x in q_low for x in SYNONYMS['ALLOT_KEY']) else "Total")

    for adm in selected_adms:
        adm_full = data[data['Adm'] == adm].copy()
        adm_filtered = adm_full[adm_full['Notice Type'].isin(final_codes)]
        stats = {k: len(adm_filtered[adm_filtered['Notice Type'].isin(v)]) for k, v in CAT_MAP.items()}
        a_c = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ASSIG)])
        l_c = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({
            "Adm": adm, "Total": a_c + l_c, "Assignments": a_c, "Allotments": l_c,
            "Stats": stats, "DisplayName": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        })
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)

    msg = " . ".join([f"{r['DisplayName']}: {r[comp_key]} records" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

with st.container(border=True):
    v_col, i_col = st.columns([1, 4])
    with v_col:
        voice_raw = mic_recorder(start_prompt="🎤 Record", stop_prompt="🛑 Stop", key="v185_mic")
    input_val = speech_to_text_robust(voice_raw) if voice_raw else ""

query = st.text_input("Enter Inquiry / أدخل استفسارك:", value=input_val)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_5(query, db)
    
    if success:
        # أزرار الصوت للتحقق والنتيجة
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("🔊 Hear Inquiry / اسمع السؤال"): speak(f"You asked: {query}" if not any(c in 'أ' for c in query) else f"سؤالك هو: {query}")
        with sc2:
            if st.button("📢 Hear Result / اسمع النتيجة"): speak(msg)

        st.success(msg)
        
        # عرض الأعلام
        m_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with m_cols[i]:
                st.markdown(f'<div class="flag-container"><img src="{FLAGS.get(r["Adm"])}" class="flag-img"></div>', unsafe_allow_html=True)
                st.metric(r['DisplayName'], f"T: {r['Total']}", f"A:{r['Assignments']} | L:{r['Allotments']}")

        st.divider()
        
        # الخريطة الكبيرة
        if not res_df.empty and 'lat_dec' in res_df.columns:
            st.subheader("📡 Geospatial Distribution")
            fig_map = px.scatter_mapbox(res_df.dropna(subset=['lat_dec']), lat="lat_dec", lon="lon_dec", color="Adm", zoom=3, height=600, mapbox_style="carto-positron")
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

        st.divider()

        # الإحصائيات
        st.subheader("📊 Service Analytics")
        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(px.bar(pd.DataFrame(reports), x="DisplayName", y=["Assignments", "Allotments"], barmode="group", title="Comparison"), use_container_width=True)
        with c_right:
            total_stats = {'DAB': sum(r['Stats']['DAB'] for r in reports), 'TV': sum(r['Stats']['TV'] for r in reports), 'FM': sum(r['Stats']['FM'] for r in reports)}
            st.plotly_chart(px.pie(values=list(total_stats.values()), names=list(total_stats.keys()), hole=0.4, title="Service Breakdown"), use_container_width=True)

        with st.expander("Detailed Technical Records"): 
            st.dataframe(res_df, use_container_width=True)
