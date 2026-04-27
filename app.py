import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# =================================================
# 1. CONFIG & INTERFACE
# =================================================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(
        f"""
        <div style="text-align:center">
            <h1 style="color:#1E3A8A;margin-bottom:0">{PROJECT_NAME}</h1>
            <p style="color:#475569;font-size:18px">{PROJECT_SLOGAN}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# =================================================
# 2. CONSTANTS & MAPS
# =================================================
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': 'جمهورية مصر العربية',
    'ARS': 'المملكة العربية السعودية',
    'TUR': 'الجمهورية التركية',
    'CYP': 'جمهورية قبرص',
    'GRC': 'الجمهورية اليونانية',
    'ISR': 'إسرائيل'
}

COUNTRY_MAP = {
    'EGY': ['egypt','egy','مصر','المصرية'],
    'ARS': ['saudi','ars','ksa','السعودية','المملكة'],
    'TUR': ['turkey','tur','تركيا'],
    'CYP': ['cyprus','cyp','قبرص'],
    'GRC': ['greece','grc','اليونان'],
    'ISR': ['israel','isr','اسرائيل']
}

STRICT_ASSIG = ['T01','T03','T04','GS1','DS1','GT1','DT1','G01']
STRICT_ALLOT = ['T02','G02','GT2','DT2','GS2','DS2']

SYNONYMS = {
    'ASSIG': ['assignment','assignments','تخصيص','تخصيصات'],
    'ALLOT': ['allotment','allotments','توزيع','توزيعات'],
    'DAB': ['dab','داب','صوتية','صوتيه','sound'],
    'TV': ['tv','television','تلفزيون','مرئية'],
    'FM': ['fm','radio','راديو'],
}


# =================================================
# 3. GEOSPATIAL PARSING (ROBUST)
# =================================================
def dms_to_decimal(text):
    try:
        text = str(text).strip().upper()

        # Decimal format: 30.123 , 31.456
        if re.match(r'^-?\d+(\.\d+)?$', text):
            return float(text)

        # DMS format
        nums = list(map(float, re.findall(r'\d+(?:\.\d+)?', text)))
        dirs = re.findall(r'[NSEW]', text)

        if len(nums) >= 3 and dirs:
            deg, minu, sec = nums[:3]
            val = deg + minu/60 + sec/3600
            if dirs[0] in ['S','W']:
                val *= -1
