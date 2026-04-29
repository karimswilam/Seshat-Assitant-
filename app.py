import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import nest_asyncio

# تفعيل nest_asyncio
nest_asyncio.apply()

# --- 1. CONFIG & STYLING ---
st.set_page_config(layout="wide", page_title="Se-Chat v18.6", page_icon="📡")

st.markdown("""
    <style>
    .stButton > button {
        height: 100px !important;
        width: 130px !important;
        border-radius: 15px !important;
        border: 1px solid #d1d5db !important;
        background-color: white !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        border-color: #1E3A8A !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .centered-msg { 
        text-align: center; font-size: 18px; color: #1E3A8A; 
        padding: 15px; border: 1px solid #1E3A8A; border-radius: 10px; 
        background-color: #F8FAFC;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- 3. UI: CHICLET SLICER ---
st.title("Se-Chat v18.6 | Spectrum Intelligence 📡")
st.write("### 📑 International Coordination Slicer")

selected_code = None
# إنشاء الـ Slicer بشكل عرضي
chiclet_cols = st.columns(len(COUNTRY_DISPLAY))

for i, (code, info) in enumerate(COUNTRY_DISPLAY.items()):
    with chiclet_cols[i]:
        st.image(FLAGS[code], width=50)
        if st.button(info['ar'], key=f"chic_{code}"):
            selected_code = info['ar']

st.divider()

# --- 4. SEARCH & VOICE ---
with st.container(border=True):
    v_col1, v_col2 = st.columns([1, 5])
    with v_col1:
        voice_input = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="main_mic")
    
    with v_col2:
        # الربط بين السليسر والبحث
        default_q = selected_code if selected_code else ""
        query = st.text_input("Spectrum Inquiry / استفسار الترددات:", value=default_q)

# --- 5. RESULTS ---
if query:
    st.info(f"Analyzing Spectrum Data for: {query}")
    # هنا تحط الـ engine_v18_6 بتاعك
