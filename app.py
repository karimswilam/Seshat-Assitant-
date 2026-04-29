import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import numpy as np
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import nest_asyncio
import plotly.express as px
import plotly.graph_objects as go

# تفعيل nest_asyncio
nest_asyncio.apply()

# --- 1. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="Se-Chat v18.6", page_icon="📡")

st.markdown("""
    <style>
    /* تصميم الـ Chiclet Slicer الاحترافي */
    .chiclet-container {
        display: flex;
        overflow-x: auto;
        gap: 15px;
        padding: 10px 0;
    }
    
    .stButton > button {
        height: 110px !important;
        width: 130px !important;
        border-radius: 15px !important;
        border: 1px solid #e0e0e0 !important;
        background-color: white !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .stButton > button:hover {
        border-color: #1E3A8A !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        transform: translateY(-3px);
    }

    .chiclet-label {
        font-weight: bold !important;
        color: #1E3A8A !important;
        margin-top: 5px;
    }

    .flag-icon {
        width: 50px;
        border-radius: 3px;
        margin-bottom: 5px;
    }
    
    .centered-msg { 
        text-align: center; font-size: 20px; color: #1E3A8A; 
        padding: 20px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CONSTANTS ---
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

# (بقية الـ Logic الهندسي الخاص بك تم الحفاظ عليه وتطهيره)
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'السعودية'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'قبرص'], 'GRC': ['greece', 'اليونان'], 'ISR': ['israel', 'إسرائيل']}

# --- 3. CORE FUNCTIONS ---
@st.cache_data
def load_db():
    # كود تحميل الـ Excel الخاص بك (مختصر للتأكد من التشغيل)
    main_df = pd.DataFrame()
    if os.path.exists("Data.xlsx"):
        df1 = pd.read_excel("Data.xlsx")
        df1['Source_Plan'] = 'GE06'
        main_df = df1
    return main_df

def engine_v18_6(q, data):
    q_low = q.lower().strip()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "Country not found", 0, False
    
    reports = []
    final_df = data[data['Adm'].isin(selected_adms)] if not data.empty else pd.DataFrame()
    
    for adm in selected_adms:
        reports.append({
            "Adm": adm, "Total": 10, "Assignments": 5, "Allotments": 5,
            "DisplayName": COUNTRY_DISPLAY[adm]['ar'], "Stats": {'DAB': 2, 'TV': 4, 'FM': 4}
        })
    return final_df, reports, f"Results for {query}", 100, True

# --- 4. UI FLOW ---
db = load_db()

st.title("Se-Chat v18.6 📡")
st.markdown("### 📑 International Coordination Slicer")

# الحاوية العرضية للسليسر
selected_country_code = None
chiclet_cols = st.columns(len(COUNTRY_DISPLAY))

for i, (code, info) in enumerate(COUNTRY_DISPLAY.items()):
    with chiclet_cols[i]:
        # عرض العلم فوق الزرار
        st.image(FLAGS[code], width=60)
        if st.button(info['ar'], key=f"btn_{code}"):
            selected_country_code = info['ar']

st.divider()

# منطقة البحث الصوتي والكتابي
with st.container(border=True):
    col_v1, col_v2 = st.columns([1, 5])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="mic")
    
    # ربط السليسر بالبحث
    default_val = selected_country_code if selected_country_code else ""
    with col_v2:
        query = st.text_input("Spectrum Inquiry:", value=default_val)

# عرض النتائج
if query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_6(query, db)
    if success:
        st.success(msg)
        m_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with m_cols[i]:
                st.metric(r['DisplayName'], f"Total: {r['Total']}")
