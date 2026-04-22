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
st.set_page_config(layout="wide", page_title="Seshat AI v16.3 | Project BASIRA")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v16.3"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Geospatial Intelligence"

# الأعلام والثوابت (كما هي تماماً)
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

# --- 2. THE GEOSPATIAL CONVERTER (المحرك الجديد) ---
def dms_to_decimal(dms_str):
    """تحويل الإحداثيات من 033°57'19"E لـ Decimal Degrees"""
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        # استخراج الأرقام والاتجاهات
        parts = re.findall(r"(\d+)", dms_str)
        direction = re.findall(r"([NSEW])", dms_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60) + (sec / 3600)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None
    return None

def process_coordinates(df):
    """معالجة عمود الإحداثيات بالكامل"""
    if 'Geographic Coordinates' in df.columns:
        # تقسيم العمود لـ Lat و Long بناءً على المسافة بينهما في النص
        coords = df['Geographic Coordinates'].str.split(expand=True)
        if coords.shape[1] >= 2:
            df['lon_dec'] = coords[0].apply(dms_to_decimal)
            df['lat_dec'] = coords[1].apply(dms_to_decimal)
    return df

# --- 3. SMART DATA LOADER ---
def smart_column_mapper(df):
    mapping = {
        'Adm': ['Administration', 'Adm', 'Admin', 'Country'],
        'Notice Type': ['Notice Type', 'NT', 'Type', 'NoticeType'],
        'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Allotment Name', 'Site/Allot. Name'],
        'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'Lat/Long', 'Geo Coords']
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
        df = smart_column_mapper(df)
        df = process_coordinates(df) # تحويل الإحداثيات فور التحميل
        return df
    return None

# --- 4. ENGINE CORE (Precision Logic v16.2) ---
def engine_v16_3(q, data):
    q_low = q.lower()
    COUNTRY_MAP = {
        'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa'],
        'TUR': ['turkey', 'tur', 'تركيا'], 'ISR': ['israel', 'isr']
    }
    SYNONYMS = {
        'ALLOT_KEY': ['allotment', 'allotments', 'توزيع'],
        'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص'],
        'DAB_KEY': ['dab', 'داب']
    }
    STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
    STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM Error", 0, False

    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']

    is_assig_requested = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    is_allot_requested = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not is_assig_requested and not is_allot_requested:
        is_assig_requested = is_allot_requested = True

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]) if is_assig_requested else 0
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]) if is_allot_requested else 0
        
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
        
        temp_filtered = pd.DataFrame()
        if is_assig_requested: temp_filtered = pd.concat([temp_filtered, adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]])
        if is_allot_requested: temp_filtered = pd.concat([temp_filtered, adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]])
        final_df = pd.concat([final_df, temp_filtered], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {f'{r['Assignments']} Assig' if is_assig_requested else ''} {f'{r['Allotments']} Allot' if is_allot_requested else ''}" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW & MAP VISUALIZATION ---
header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A;">{PROJECT_NAME}</h1></div>', unsafe_allow_html=True)

db = load_db()
query = st.text_input("🎙️ Spectrum Analysis Query:", key="main_q")

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v16_3(query, db)
    
    if success:
        # 1. الأعلام (تراكمي)
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p style="text-align:center; font-weight:bold;">{COUNTRY_DISPLAY.get(r["Adm"], {}).get("ar", r["Adm"])}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300)
        
        st.divider()

        # 2. الخريطة الفخمة (Visualization)
        if not res_df.empty and 'lat_dec' in res_df.columns:
            st.markdown("### 🌍 Geospatial Spectrum Distribution")
            fig_map = px.scatter_mapbox(res_df, lat="lat_dec", lon="lon_dec", 
                                        hover_name="Site/Allotment Name", 
                                        hover_data=["Notice Type", "Adm"],
                                        color="Adm", size_max=15, zoom=4,
                                        mapbox_style="carto-positron", height=600)
            st.plotly_chart(fig_map, use_container_width=True)

        # 3. الـ Charts والـ Metrics (تراكمي)
        m1, m2 = st.columns([1, 2])
        with m1:
            st.metric("Confidence Score", f"{conf}%")
            fig_pie = px.pie(values=[sum(r['Assignments'] for r in reports), sum(r['Allotments'] for r in reports)], 
                             names=['Assignments', 'Allotments'], hole=.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with m2:
            st.bar_chart(pd.DataFrame(reports).set_index('Adm')[['Assignments', 'Allotments']])
        
        st.success(msg)
        with st.expander("Technical Records"): st.dataframe(res_df)
