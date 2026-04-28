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
st.set_page_config(layout="wide", page_title="Se-Chat v18.5", page_icon="📡")

st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { width: 100%; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat التنسيق الدولي للطيف v18.5"
PROJECT_SLOGAN = " Spectrum Intelligence & Governance"

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
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig', 'assigs'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون', 'without', 'excluding'],
    'GE06_KEY': ['ge06', 'geneva06', 'geneva 06', 'geneva o 6', 'جنيف 06', 'جي إي 06', 'ge06d'],
    'GE84_KEY': ['ge84', 'geneva84', 'geneva 84', 'جنيف 84', 'جي إي 84', 'اربعة وثمانين', '84']
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
        
        # محاولة التعرف على الإنجليزية أولاً بدقة عالية
        try:
            english_text = r.recognize_google(audio, language="en-US")
            # لو النص يبدو إنجليزي فعلاً (أكثر من كلمة أو كلمات مفتاحية هندسية) نرجعه
            if any(word in english_text.lower() for word in ['how', 'many', 'egypt', 'assignment', 'allotment', 'ge06']):
                return english_text
        except: pass
        
        raw_text = r.recognize_google(audio, language="ar-EG")
        return apply_phonetic_correction(raw_text)
    except Exception as e:
        return None

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
        if data:
            st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    main_df = pd.DataFrame()
    
    target_main = "Data.xlsx"
    if os.path.exists(target_main):
        df1 = pd.read_excel(target_main)
        df1.columns = df1.columns.str.strip()
        df1['Source_Plan'] = 'GE06'
        main_df = df1

    target_fm = "FM.xlsx"
    if os.path.exists(target_fm):
        df2 = pd.read_excel(target_fm)
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
            def clean_freq(f):
                try:
                    num = re.findall(r"[-+]?\d*\.\d+|\d+", str(f))
                    return float(num[0]) if num else 0.0
                except: return 0.0
            main_df['freq_val'] = main_df['Assigned Frequency'].apply(clean_freq)

        return main_df
    return None

def engine_v18_5(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    # تحديد الدول
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))[:4]
    
    if not selected_adms: return None, [], "Please specify a country / برجاء تحديد الدولة", 0, False

    # 1. منطق تحديد الاتفاقية (Force Filter)
    filter_plan = None
    if any(x in q_low for x in SYNONYMS['GE06_KEY']): filter_plan = 'GE06'
    elif any(x in q_low for x in SYNONYMS['GE84_KEY']): filter_plan = 'GE84'

    # 2. منطق التفرقة بين Assignments و Allotments
    is_allot_only = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    is_assig_only = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    
    comp_type = "Total"
    if is_allot_only and not is_assig_only: comp_type = "Allotments"
    elif is_assig_only and not is_allot_only: comp_type = "Assignments"

    # 3. تحديد نوع الخدمة بناءً على الخطة
    wanted_codes = []
    if filter_plan == 'GE06':
        wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV']
    elif filter_plan == 'GE84':
        wanted_codes = CAT_MAP['FM']
    else:
        # لو ما حددش خطة، نشغل الفلتر العام بناءً على الكلمات المفتاحية
        if any(x in q_low for x in SYNONYMS['DAB_KEY']): wanted_codes.extend(CAT_MAP['DAB'])
        if any(x in q_low for x in SYNONYMS['TV_KEY']): wanted_codes.extend(CAT_MAP['TV'])
        if any(x in q_low for x in SYNONYMS['FM_KEY']): wanted_codes.extend(CAT_MAP['FM'])
        if not wanted_codes: wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV'] + CAT_MAP['FM'] + ['G01']

    # استثناءات
    excluded_codes = []
    if any(x in q_low for x in SYNONYMS['EXCEPT_KEY']):
        if any(x in q_low for x in SYNONYMS['DAB_KEY']): excluded_codes.extend(CAT_MAP['DAB'])
        if any(x in q_low for x in SYNONYMS['TV_KEY']): excluded_codes.extend(CAT_MAP['TV'])

    final_codes = [c for c in wanted_codes if c not in excluded_codes]
    
    reports = []; final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_full = data[data['Adm'] == adm].copy()
        
        # تطبيق فلتر الاتفاقية
        if filter_plan:
            adm_full = adm_full[adm_full['Source_Plan'] == filter_plan]
            
        adm_filtered = adm_full[adm_full['Notice Type'].isin(final_codes)]
        
        a_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ALLOT)])
        
        stats = {
            'DAB': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['DAB'])]),
            'TV': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['TV'])]),
            'FM': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['FM'])])
        }
        
        # تحديد القيمة الراجعة بناءً على طلب المستخدم (Total, Assig, or Allot)
        res_val = a_count + l_count
        if comp_type == "Assignments": res_val = a_count
        elif comp_type == "Allotments": res_val = l_count

        reports.append({
            "Adm": adm, "Total": a_count + l_count, "Assignments": a_count, "Allotments": l_count,
            "ResultValue": res_val, "Stats": stats, 
            "DisplayName": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        })
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)

    # بناء رسالة الرد
    msg = ""
    for r in reports:
        unit = "سجل" if is_ar else "records"
        label = comp_type if not is_ar else ("تخصيصات" if comp_type=="Assignments" else ("توزيعات" if comp_type=="Allotments" else "إجمالي"))
        msg += f"{r['DisplayName']}: {r['ResultValue']} {label} {unit}. "

    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

with st.container(border=True):
    col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤 Speak", stop_prompt="🛑 Stop", key="v185_mic")
    
    input_val = speech_to_text_robust(voice_raw) if voice_raw else ""
    
    with col_v2:
        query = st.text_input("Spectrum Inquiry / استفسار الترددات:", value=input_val)
    
    with col_v3:
        if st.button("👂 Listen"):
            speak_text(query)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_5(query, db)
    
    if success:
        st.success(msg)
        if st.button("🔊 Play Results Summary"):
            speak_text(msg)
        
        m_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with m_cols[i]:
                st.markdown(f'<div class="flag-container"><img src="{FLAGS.get(r["Adm"])}" class="flag-img"></div>', unsafe_allow_html=True)
                st.metric(r['DisplayName'], f"Total: {r['Total']}", f"A:{r['Assignments']} | L:{r['Allotments']}")

        st.divider()
        st.subheader("📡 Geospatial Spectrum Distribution")
        if not res_df.empty and 'lat_dec' in res_df.columns:
            map_df = res_df.dropna(subset=['lat_dec', 'lon_dec'])
            fig_map = px.scatter_mapbox(map_df, lat="lat_dec", lon="lon_dec", color="Adm", 
                                       hover_name="Notice Type", zoom=3, height=600,
                                       mapbox_style="carto-positron")
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

        st.divider()
        st.subheader("📊 Service Analytics")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            chart_data = pd.DataFrame(reports)
            fig_bar = px.bar(chart_data, x="DisplayName", y=["Assignments", "Allotments"], 
                            barmode="group", title="Assignments vs Allotments",
                            color_discrete_sequence=['#1E3A8A', '#3B82F6'])
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            if len(reports) == 1:
                s = reports[0]['Stats']
                fig_pie = px.pie(values=list(s.values()), names=list(s.keys()), hole=0.4, title=f"Services in {reports[0]['DisplayName']}")
            else:
                total_stats = {'DAB': sum(r['Stats']['DAB'] for r in reports), 
                               'TV': sum(r['Stats']['TV'] for r in reports), 
                               'FM': sum(r['Stats']['FM'] for r in reports)}
                fig_pie = px.pie(values=list(total_stats.values()), names=list(total_stats.keys()), hole=0.4, title="Combined Service Breakdown")
            st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("Detailed Technical Records"): 
            st.dataframe(res_df, use_container_width=True)
