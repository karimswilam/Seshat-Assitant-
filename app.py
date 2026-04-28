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
# المكتبة الجديدة للـ Chiclet Slicer
try:
    from streamlit_extras.chart_container import chart_container
    from streamlit_extras.stylable_container import stylable_container
except ImportError:
    st.error("Please add 'streamlit-extras' to your requirements.txt")

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
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { width: 100%; border-radius: 20px; }
    /* Style for Horizontal Slicer */
    div[data-testid="stHorizontalBlock"] {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 15px;
        overflow-x: auto;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat التنسيق الدولي للطيف v18.7"
PROJECT_SLOGAN = " Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=120)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. FIXED ENGINEERING LOGIC (No Changes Here) ---
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
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig', 'assigs', 'تردد', 'ترددات', 'مstation', 'مستقبل'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون', 'without', 'excluding'],
    'GE06_KEY': ['ge06', 'geneva06', 'geneva 06', 'geneva o 6', 'جنيف 06', 'جي إي 06', 'ge06d'],
    'GE84_KEY': ['ge84', 'geneva84', 'geneva 84', 'جنيف 84', 'جي إي 84', 'اربعة وثمانين', '84']
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
            if any(word in english_text.lower() for word in ['how', 'many', 'egypt', 'assignment', 'allotment', 'ge06']):
                return english_text
        except: pass
        raw_text = r.recognize_google(audio, language="ar-EG")
        return apply_phonetic_correction(raw_text)
    except Exception: return None

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
    # تأكد أن الملفات موجودة في المسار الصحيح
    for file, plan in [("Data.xlsx", "GE06"), ("FM.xlsx", "GE84")]:
        if os.path.exists(file):
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            df['Source_Plan'] = plan
            main_df = pd.concat([main_df, df], ignore_index=True)
    
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
            main_df['freq_val'] = main_df['Assigned Frequency'].apply(lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", str(x))[0]) if re.findall(r"[-+]?\d*\.\d+|\d+", str(x)) else 0.0)
        return main_df
    return None

def engine_v18_6(q, data, force_adm=None):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    # Priority to Chiclet Selection
    if force_adm:
        selected_adms = [force_adm]
    else:
        selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
        selected_adms = list(dict.fromkeys(selected_adms))

    if not selected_adms:
        return None, [], "Please select a country / برجاء اختيار دولة", 0, False

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
            "Stats": {
                'DAB': {'A': len(adm_filtered[adm_filtered['Notice Type'].isin(['GS1','DS1'])]), 'L': len(adm_filtered[adm_filtered['Notice Type'].isin(['GS2','DS2'])])},
                'TV': {'A': len(adm_filtered[adm_filtered['Notice Type'].isin(['GT1','DT1','T01'])]), 'L': len(adm_filtered[adm_filtered['Notice Type'].isin(['T02','G02','GT2','DT2'])])},
                'FM': {'A': len(adm_filtered[adm_filtered['Notice Type'].isin(['T01','T03','T04'])]), 'L': 0} # GE84 typical
            },
            "DisplayName": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        })
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)

    return final_df, reports, f"Analysis for {reports[0]['DisplayName']}", 100, True

# --- 5. UI FLOW ---
db = load_db()

# Chiclet Slicer Implementation
st.write("### 🌍 Select Country / اختر الدولة")
# تصميم الـ Chiclet Slicer يدوياً لضمان الشكل المطلوب
selected_country_code = None
cols = st.columns(len(FLAGS))
for i, (code, url) in enumerate(FLAGS.items()):
    with cols[i]:
        if st.button(f"{code}", key=f"btn_{code}"):
            st.session_state['selected_adm'] = code

# الحفاظ على الحالة
current_selection = st.session_state.get('selected_adm', 'EGY')

with st.container(border=True):
    col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤 Speak", stop_prompt="🛑 Stop", key="v187_mic")
    input_val = speech_to_text_robust(voice_raw) if voice_raw else ""
    with col_v2:
        query = st.text_input("Spectrum Inquiry / استفسار الترددات:", value=input_val, placeholder=f"Searching in {current_selection}...")
    with col_v3:
        if st.button("👂 Listen"): speak_text(query if query else f"Current country is {current_selection}")

if db is not None:
    # نقوم بتمرير الدولة المختارة من الـ Chiclet كأولوية
    res_df, reports, msg, conf, success = engine_v18_6(query if query else "", db, force_adm=current_selection)
    
    if success and reports:
        r = reports[0]
        st.markdown(f'### {r["DisplayName"]} Dashboard')
        
        # عرض العلم
        st.markdown(f'<div class="flag-container"><img src="{FLAGS.get(r["Adm"])}" class="flag-img"></div>', unsafe_allow_html=True)
        
        # توزيع الخدمات (DAB, FM, TV) مع تقسيم Assignments و Allotments لكل واحدة
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("DAB", f"{r['Stats']['DAB']['A'] + r['Stats']['DAB']['L']}")
            st.caption(f"Assig: {r['Stats']['DAB']['A']} | Allot: {r['Stats']['DAB']['L']}")
        with m2:
            st.metric("TV", f"{r['Stats']['TV']['A'] + r['Stats']['TV']['L']}")
            st.caption(f"Assig: {r['Stats']['TV']['A']} | Allot: {r['Stats']['TV']['L']}")
        with m3:
            st.metric("FM", f"{r['Stats']['FM']['A']}")
            st.caption(f"Assig: {r['Stats']['FM']['A']} (GE84)")

        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            # Map
            map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
            if not map_data.empty:
                fig_map = px.scatter_mapbox(map_data, lat="lat_dec", lon="lon_dec", color="Notice Type", hover_name="Assigned Frequency", zoom=5, height=400, mapbox_style="carto-positron")
                st.plotly_chart(fig_map, use_container_width=True)
        with c2:
            # Stats Chart
            svc_plot = pd.DataFrame([
                {'Service': 'DAB', 'Type': 'Assig', 'Count': r['Stats']['DAB']['A']},
                {'Service': 'DAB', 'Type': 'Allot', 'Count': r['Stats']['DAB']['L']},
                {'Service': 'TV', 'Type': 'Assig', 'Count': r['Stats']['TV']['A']},
                {'Service': 'TV', 'Type': 'Allot', 'Count': r['Stats']['TV']['L']},
                {'Service': 'FM', 'Type': 'Assig', 'Count': r['Stats']['FM']['A']},
            ])
            st.plotly_chart(px.bar(svc_plot, x='Service', y='Count', color='Type', barmode='group', title="Service Breakdown"), use_container_width=True)

        with st.expander("Detailed Technical Records"): 
            st.dataframe(res_df, use_container_width=True)
