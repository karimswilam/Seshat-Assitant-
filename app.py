import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
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

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees', 'assig'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'sound'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'tlfzyon'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'GENERIC_BR_KEY': ['إذاعية', 'إذاعة', 'اذاعة', 'اذاعية', 'broadcasting']
}

# --- 3. GEOSPATIAL UTILITIES ---
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

# --- 4. VOICE ENGINE ---
async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
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
        async iose.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3")
    except: pass

# --- 5. ENGINE CORE v16.9 ---
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
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Standard/Allotment Area'],
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

def engine_v16_9(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "ADM identification error.", 0, False

    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    svc_codes = []
    is_dab = any(x in q_low for x in SYNONYMS['DAB_KEY'])
    is_tv = any(x in q_low for x in SYNONYMS['TV_KEY'])
    is_fm = any(x in q_low for x in SYNONYMS['FM_KEY'])
    is_gen = any(x in q_low for x in SYNONYMS['GENERIC_BR_KEY'])

    if is_dab: svc_codes = ['GS1','GS2','DS1','DS2']
    elif is_tv: svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif is_fm: svc_codes = ['T01','T03','T04']
    elif is_gen: svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        # تصنيف السجل هندسياً
        adm_df['Record Type'] = adm_df['Notice Type'].apply(
            lambda x: 'Assignment' if x in STRICT_ASSIG else ('Allotment' if x in STRICT_ALLOT else 'Unknown')
        )
        
        a_count = len(adm_df[adm_df['Record Type'] == 'Assignment'])
        l_count = len(adm_df[adm_df['Record Type'] == 'Allotment'])
        
        res = {"Adm": adm}
        if mentions_assig and not mentions_allot:
            res["Assignments"] = a_count
            temp = adm_df[adm_df['Record Type'] == 'Assignment']
        elif mentions_allot and not mentions_assig:
            res["Allotments"] = l_count
            temp = adm_df[adm_df['Record Type'] == 'Allotment']
        else:
            res["Assignments"] = a_count
            res["Allotments"] = l_count
            temp = adm_df
            
        reports.append(res)
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: " + (f"{r['Assignments']} Assig " if "Assignments" in r else "") + (f"{r['Allotments']} Allot" if "Allotments" in r else "") for r in reports])
    return final_df, reports, msg, 100, True

# --- 6. UI FLOW ---
db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry:", key="main_q")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    st.divider()

    res_df, reports, msg, conf, success = engine_v16_9(query, db)
    
    if success and reports:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p style="text-align:center; font-weight:bold;">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300)
                st.markdown(f'<p style="text-align:center; color:grey;">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()

        # --- Geospatial Logic v16.9 (Colored Shapes) ---
        if PLOTLY_AVAILABLE and not res_df.empty:
            map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
            if not map_data.empty:
                st.markdown("### 🌍 Geospatial Spectrum Distribution")
                fig_map = px.scatter_mapbox(
                    map_data, 
                    lat="lat_dec", lon="lon_dec", 
                    hover_name="Site/Allotment Name", 
                    color="Record Type",
                    symbol="Record Type",
                    color_discrete_map={"Assignment": "#1E3A8A", "Allotment": "#EF4444"},
                    zoom=3, mapbox_style="carto-positron", height=600
                )
                fig_map.update_traces(marker={'size': 12}) # تكبير النقاط للوضوح
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("⚠️ No valid coordinates for mapping.")

        m1, m2 = st.columns([1, 2])
        chart_df = pd.DataFrame(reports).set_index('Adm')
        with m1:
            st.metric("Confidence", f"{conf}%")
            if PLOTLY_AVAILABLE and "Assignments" in chart_df.columns:
                fig = px.pie(values=[reports[0].get('Assignments', 0), reports[0].get('Allotments', 0)], 
                             names=['Assignments', 'Allotments'], hole=.4, color_discrete_sequence=['#1E3A8A', '#EF4444'])
                st.plotly_chart(fig, use_container_width=True)
        with m2: st.bar_chart(chart_df)
        
        st.table(chart_df)
        st.markdown("### 🔊 Assistant Response")
        st.success(msg)
        play_audio(msg)
        with st.expander("Technical Records"): st.dataframe(res_df)
