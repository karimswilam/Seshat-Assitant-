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
from pydub import AudioSegment  # مكتبة معالجة الصوت
import nest_asyncio # حل مشكلة تداخل الـ loops في Streamlit

# تفعيل nest_asyncio للسماح بتشغيل الـ Audio Engine بسلاسة
nest_asyncio.apply()

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.2", page_icon="📡")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.2"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. FIXED ENGINEERING LOGIC ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'المصريه', 'مصرية', 'مصريه'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة', 'المملكه', 'سعودية', 'سعوديه', 'السعوديه', 'المملكه العربيه'],
    'TUR': ['turkey', 'tur', 'تركيا', 'تركي', 'التركية', 'التركيه', 'turkish', 'تركيه', 'التركيه'],
    'CYP': ['cyprus', 'cyp', 'قبرص', 'قبرصية', 'قبرصيه', 'القبرصية'],
    'GRC': ['greece', 'grc', 'اليونان', 'يوناني', 'اليونانية', 'اليونانيه', 'يونانيه'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot', 'ألوتمنت'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig', 'تخصيصي'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio', 'إذاعي', 'اذاعي', 'اذاعة', 'إذاعة'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه', 'قنوات'],
    'FM_KEY': ['fm', 'radio', 'راديو', 'اف ام'],
    'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all', 'عدد', 'كام'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون', 'غير']
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
            st.toast("🔊 Signal Normalized...", icon="✅")
            r.adjust_for_ambient_noise(source, duration=0.2)
            audio = r.record(source)
        return r.recognize_google(audio, language="ar-EG")
    except Exception as e:
        st.error(f"Signal Processing Error: {e}")
        return None

async def generate_audio(text):
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

def play_audio(text):
    try:
        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3")
    except: pass

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country'],
            'Notice Type': ['Notice Type', 'NT'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name'],
            'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates']
        }
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

def engine_v17_2(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    # 1. تحديد الدول بدقة أعلى
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    
    if not selected_adms: 
        return None, [], "برجاء تحديد الدولة (مصر، السعودية، اليونان، إلخ)" if is_ar else "Please specify a country.", 0, False

    # 2. تحديد الخدمات المطلوبة
    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes.extend(['GS1','GS2','DS1','DS2'])
    if any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes.extend(['T02','G02','GT1','GT2','DT1','DT2'])
    if any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes.extend(['T01','T03','T04'])
    
    # لو السؤال عام أو لم يتم تحديد خدمة، نأخذ الكل
    if not svc_codes or any(x in q_low for x in SYNONYMS['TOTAL_KEY']):
        svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04', 'G01']

    reports = []; final_df = pd.DataFrame()
    comp_type = "Assignments" if any(x in q_low for x in SYNONYMS['ASSIG_KEY']) else "Total"

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({
            "Adm": adm, "Total": a_count + l_count, 
            "Assignments": a_count, "Allotments": l_count,
            "DisplayName": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        })
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    # 3. صياغة الرد والمقارنة
    sorted_reports = sorted(reports, key=lambda x: x[comp_type], reverse=True)
    
    if len(reports) >= 2:
        if is_ar:
            msg = f"بناءً على طلبك، إليك المقارنة: {sorted_reports[0]['DisplayName']} تتصدر بـ {sorted_reports[0][comp_type]} سجل، "
            msg += "يتبعها " + " و ".join([f"{r['DisplayName']} ({r[comp_type]})" for r in sorted_reports[1:]])
        else:
            msg = f"Comparison results: {sorted_reports[0]['Adm']} leads with {sorted_reports[0][comp_type]} records. "
            msg += "Followed by " + ", ".join([f"{r['Adm']} ({r[comp_type]})" for r in sorted_reports[1:]])
    else:
        r = reports[0]
        if is_ar:
            msg = f"تم العثور على {r[comp_type]} سجل لـ {r['DisplayName']}."
        else:
            msg = f"Found {r[comp_type]} records for {r['Adm']}."

    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

with st.container(border=True):
    c1, c2 = st.columns([1, 4])
    with c1:
        voice_raw = mic_recorder(start_prompt="🎤 Speak", stop_prompt="🛑 Stop", key="v172_mic")
    
    input_val = ""
    if voice_raw:
        with st.spinner("Analyzing Audio Signal..."):
            input_val = speech_to_text_robust(voice_raw)

query = st.text_input("Enter Spectrum Inquiry:", value=input_val)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v17_2(query, db)
    
    if success:
        m_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with m_cols[i]:
                st.image(FLAGS.get(r['Adm']), use_container_width=True)
                st.metric(r['DisplayName'], f"Total: {r['Total']}", f"A: {r['Assignments']} | L: {r['Allotments']}")

        st.divider()
        st.success(msg)
        play_audio(msg)

        col_left, col_right = st.columns(2)
        chart_data = pd.DataFrame(reports)
        with col_left:
            if PLOTLY_AVAILABLE:
                fig = px.bar(chart_data, x="Adm", y=["Assignments", "Allotments"], barmode="group", 
                             title="Technical Spectrum Distribution")
                st.plotly_chart(fig, use_container_width=True)
        with col_right:
            if PLOTLY_AVAILABLE and not res_df.empty:
                map_df = res_df.dropna(subset=['lat_dec', 'lon_dec'])
                if not map_df.empty:
                    fig_map = px.scatter_mapbox(map_df, lat="lat_dec", lon="lon_dec", color="Adm", 
                                                zoom=3, mapbox_style="carto-positron", height=400)
                    st.plotly_chart(fig_map, use_container_width=True)

        with st.expander("Detailed Technical Records (Filtered)"): 
            st.dataframe(res_df, use_container_width=True)
