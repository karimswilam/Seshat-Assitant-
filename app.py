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

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v16.9")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v16.9"
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

# تصنيف الأنواع بناءً على تصحيحات v16.8
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'twze3'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'ta5sees'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'DAB_KEY': ['dab', 'داب']
}

# --- 3. GEOSPATIAL UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        parts = re.findall(r"(\d+)", dms_str)
        direction = re.findall(r"([NSEW])", dms_str.upper())
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None
    return None

# --- 4. VOICE ENGINE (FIXED) ---
async def _async_generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(_async_generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 5. ENGINE CORE v16.9 ---
@st.cache_data
def load_db():
    if os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
        # معالجة الإحداثيات (Fixing NaN Issues)
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
    return None

def engine_v16_9(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "Error.", 0, False

    svc_codes = []
    if any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']

    final_df = pd.DataFrame()
    reports = []
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        # إضافة تصنيف النوع هندسياً للرسم
        adm_df['Record Type'] = adm_df['Notice Type'].apply(
            lambda x: 'Assignment' if x in STRICT_ASSIG else 'Allotment'
        )
        
        reports.append({
            "Adm": adm, 
            "Assignments": len(adm_df[adm_df['Record Type'] == 'Assignment']),
            "Allotments": len(adm_df[adm_df['Record Type'] == 'Allotment'])
        })
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    return final_df, reports, "Success", 100, True

# --- 6. UI FLOW ---
db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry:", key="main_input")

if query and db is not None:
    play_audio(query)
    res_df, reports, msg, conf, success = engine_v16_9(query, db)
    
    if success:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=200)
                st.metric(r['Adm'], f"{r['Assignments']} Assig | {r['Allotments']} Allot")

        # --- الخريطة الاحترافية (تعديل v16.9 النهائي) ---
        if PLOTLY_AVAILABLE and not res_df.empty:
            map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
            st.markdown("### 🌍 Geospatial Spectrum Distribution")
            fig_map = px.scatter_mapbox(
                map_data, lat="lat_dec", lon="lon_dec", 
                color="Record Type", 
                symbol="Record Type",
                color_discrete_map={"Assignment": "#1E3A8A", "Allotment": "#EF4444"}, # أزرق وأحمر
                zoom=3, mapbox_style="carto-positron", height=600
            )
            fig_map.update_traces(marker={'size': 12})
            st.plotly_chart(fig_map, use_container_width=True)

        with st.expander("View Data"): st.dataframe(res_df)
