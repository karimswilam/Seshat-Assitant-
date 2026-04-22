import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & UI ---
st.set_page_config(layout="wide", page_title="Seshat AI v16.1")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v16.1"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# الهيدر مع اللوجو (العودة للتصميم المتكامل)
header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom:0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)
st.divider()

# --- 2. THE LOGIC & FLAGS (الثوابت اللي مستحيل تطير) ---
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

# --- 3. SMART MAPPER & LOADER ---
def smart_column_mapper(df):
    mapping = {
        'Adm': ['Administration', 'Adm', 'Admin', 'Country'],
        'Notice Type': ['Notice Type', 'NT', 'Type', 'NoticeType'],
        'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Allotment Name', 'Location'],
        'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'Lat/Long']
    }
    new_cols = {}
    for standard, synonyms in mapping.items():
        for col in df.columns:
            if col.strip() in synonyms:
                new_cols[col] = standard
                break
    return df.rename(columns=new_cols)

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return smart_column_mapper(df)
    return None

# --- 4. ENGINE v16.1 (Logic Intact) ---
async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3")
    except: pass

def engine_v16_1(q, data):
    q_low = q.lower()
    COUNTRY_MAP = {
        'EGY': ['egypt', 'egy', 'مصر', 'المصرية'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
        'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'],
        'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']
    }
    SYNONYMS = {
        'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
        'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
        'DAB_KEY': ['dab', 'داب', 'صوتية'], 'TV_KEY': ['tv', 'television', 'تلفزيون'],
        'FM_KEY': ['fm', 'radio'], 'GENERIC_BR_KEY': ['إذاعية', 'إذاعة', 'broadcasting']
    }
    STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
    STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM Error", 0, False

    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['GENERIC_BR_KEY']): svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {"Adm": adm, "Assignments": a_count, "Allotments": l_count}
        reports.append(res)
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Assignments']} Assig {r['Allotments']} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW (Restoring the Dashboard) ---
db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry:", key="main_q")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    st.divider()

    res_df, reports, msg, conf, success = engine_v16_1(query, db)
    
    if success and reports:
        # 1. استعادة الأعلام
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p style="text-align:center; font-weight:bold;">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300)
                st.markdown(f'<p style="text-align:center; color:grey;">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()
        
        # 2. استعادة الـ Charts والـ Metrics
        m1, m2 = st.columns([1, 2])
        chart_df = pd.DataFrame(reports).set_index('Adm')
        
        with m1:
            st.metric("Confidence Score", f"{conf}%")
            if PLOTLY_AVAILABLE:
                total_assig = sum(r['Assignments'] for r in reports)
                total_allot = sum(r['Allotments'] for r in reports)
                fig = px.pie(values=[total_assig, total_allot], names=['Assignments', 'Allotments'], hole=.4, color_discrete_sequence=['#1E3A8A', '#94A3B8'])
                st.plotly_chart(fig, use_container_width=True)
        
        with m2:
            st.bar_chart(chart_df[['Assignments', 'Allotments']])
        
        # 3. الرد الصوتي والجدول
        st.markdown("### 🔊 Assistant Response")
        st.success(msg)
        play_audio(msg)
        
        with st.expander("Technical Records"):
            st.dataframe(res_df)
