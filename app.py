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
st.set_page_config(layout="wide", page_title="Se-Chat v18.8", page_icon="📡")

# تنسيق CSS مخصص للأعلام والسلايسر
st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
    .flag-img { width: 80px; border-radius: 5px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .slicer-box { padding: 10px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #1E3A8A; }
    [data-testid="stMetricValue"] { font-size: 22px !important; color: #1E3A8A; }
    .stButton button { width: 100%; border-radius: 15px; background-color: #1E3A8A; color: white; }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat v18.8 - Spectrum Intelligence"

# Header
h_col1, h_col2, h_col3 = st.columns([1, 2, 1])
with h_col2:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=100)
    st.markdown(f'<h2 style="text-align: center; color: #1E3A8A;">{PROJECT_NAME}</h2>', unsafe_allow_html=True)

# --- 2. DATA & LOGIC ---
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

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'إسرائيل']
}

CAT_MAP = {'DAB': ['GS1','GS2','DS1','DS2'], 'TV': ['T02','G02','GT1','GT2','DT1','DT2'], 'FM': ['T01','T03','T04']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. CORE FUNCTIONS ---
@st.cache_data
def load_db():
    # محاكاة تحميل البيانات (نفس منطق الكود الأصلي بتاعك)
    # تأكد من وجود ملفات Data.xlsx و FM.xlsx في نفس المجلد
    try:
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
            # توحيد أسماء الأعمدة
            main_df = main_df.rename(columns={'Administration': 'Adm', 'Country': 'Adm', 'NT': 'Notice Type'})
            # تنظيف الترددات والإحداثيات (منطقك الأصلي)
            return main_df
    except: pass
    return None

def engine_v18_8(q, data, selected_from_slicer=None):
    q_low = q.lower().strip()
    # إذا كان هناك اختيار من السلايسر، نعطيه الأولوية
    selected_adms = selected_from_slicer if selected_from_slicer else []
    
    # البحث عن دول إضافية في النص
    for code, keys in COUNTRY_MAP.items():
        if any(k in q_low for k in keys) and code not in selected_adms:
            selected_adms.append(code)

    if not selected_adms:
        return None, [], "Please select a country / برجاء اختيار دولة", 0, False

    reports = []
    final_df = pd.DataFrame()
    
    for adm in selected_adms:
        adm_data = data[data['Adm'] == adm]
        a_count = len(adm_data[adm_data['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_data[adm_data['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({
            "Adm": adm, "Assignments": a_count, "Allotments": l_count, "Total": a_count + l_count,
            "DisplayName": COUNTRY_DISPLAY[adm]['en'],
            "Stats": {'DAB': len(adm_data[adm_data['Notice Type'].isin(CAT_MAP['DAB'])]),
                      'TV': len(adm_data[adm_data['Notice Type'].isin(CAT_MAP['TV'])]),
                      'FM': len(adm_data[adm_data['Notice Type'].isin(CAT_MAP['FM'])])}
        })
        final_df = pd.concat([final_df, adm_data], ignore_index=True)

    return final_df, reports, f"Found records for {len(selected_adms)} countries.", 100, True

# --- 4. SIDEBAR & SLICER ---
st.sidebar.header("📊 Global Slicer")
with st.sidebar.container():
    st.markdown('<div class="slicer-box">', unsafe_allow_html=True)
    options = {f"{v['en']} {v['ar']}": k for k, v in COUNTRY_DISPLAY.items()}
    selected_names = st.multiselect("Select Target Countries:", options=list(options.keys()))
    selected_codes = [options[name] for name in selected_names]
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN UI FLOW ---
db = load_db()

# عرض الأعلام المختارة فوراً كـ "Visual Feedback"
if selected_codes:
    cols = st.columns(len(selected_codes) + 2)
    with cols[0]: st.write("🎯 Selected:")
    for i, code in enumerate(selected_codes):
        with cols[i+1]:
            st.image(FLAGS[code], width=50)

# Voice & Text Input
with st.container(border=True):
    c1, c2 = st.columns([1, 5])
    with c1:
        voice = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="mic_8")
    with c2:
        query = st.text_input("Ask about Spectrum (e.g., 'How many assignments in Egypt?')", key="query_input")

# Logic Execution
if (query or selected_codes) and db is not None:
    res_df, reports, msg, conf, success = engine_v18_8(query, db, selected_codes)
    
    if success:
        st.success(msg)
        
        # Dashboard
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'''
                    <div style="text-align:center; border:1px solid #ddd; padding:10px; border-radius:10px;">
                        <img src="{FLAGS[r['Adm']]}" style="width:60px; margin-bottom:5px;">
                        <br><b>{r['DisplayName']}</b>
                    </div>
                ''', unsafe_allow_html=True)
                st.metric("Total", r['Total'])
                st.caption(f"Assig: {r['Assignments']} | Allot: {r['Allotments']}")

        # Charts
        tab1, tab2 = st.tabs(["📊 Comparison", "📋 Data Table"])
        with tab1:
            if PLOTLY_AVAILABLE:
                fig = px.bar(pd.DataFrame(reports), x="DisplayName", y=["Assignments", "Allotments"], barmode="group", color_discrete_sequence=['#1E3A8A', '#BC7AF9'])
                st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.dataframe(res_df)
    else:
        st.info("Waiting for input or country selection...")
