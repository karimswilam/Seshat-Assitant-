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
st.set_page_config(layout="wide", page_title="Se-Chat v18.6 Professional", page_icon="📡")

# التعديل الجوهري في الـ CSS لدمج العلم والاسم وتنسيق السليسر
st.markdown("""
    <style>
    /* تنسيق الحاوية العرضية للسليسر */
    .slicer-scroll-container {
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        gap: 15px;
        padding: 15px 5px;
        scrollbar-width: thin;
        scrollbar-color: #1E3A8A #F0F4F8;
    }
    
    /* إخفاء حدود أزرار Streamlit الافتراضية وجعلها تبدو ككروت */
    div.stButton > button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 140px !important;
        height: 100px !important;
        background-color: white !important;
        border: 2px solid #e0e0e0 !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        padding: 10px !important;
    }

    div.stButton > button:hover {
        border-color: #1E3A8A !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        transform: translateY(-3px);
    }

    /* تنسيق العلم داخل الزرار */
    .chiclet-img {
        width: 50px;
        margin-bottom: 8px;
        border-radius: 3px;
        pointer-events: none;
    }

    /* تنسيق النص داخل الزرار */
    .chiclet-label {
        font-weight: bold;
        color: #1E3A8A;
        font-size: 14px;
        pointer-events: none;
    }

    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .centered-msg { 
        text-align: center; font-size: 20px; color: #1E3A8A; 
        padding: 20px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat v18.6"
PROJECT_SLOGAN = "Spectrum Intelligence & International Coordination"

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

# (بقية الـ Mapping والـ Logic الثابت من الكود السابق...)
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
CAT_MAP = {'DAB': ['GS1','GS2','DS1','DS2'], 'TV': ['T02','G02','GT1','GT2','DT1','DT2'], 'FM': ['T01','T03','T04']}
COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'saudiarabia', 'ars', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'إسرائيل']
}
SYNONYMS = {'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'], 'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو']}

# --- 3. UTILITIES & FUNCTIONS ---
@st.cache_data
def load_db():
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
        main_df = main_df.rename(columns={'Administration': 'Adm', 'Country': 'Adm'})
        if 'Assigned Frequency' in main_df.columns:
            main_df['freq_val'] = pd.to_numeric(main_df['Assigned Frequency'].astype(str).str.extract(r'(\d+\.?\d*)')[0], errors='coerce')
        return main_df
    return None

def engine_v18_6(q, data):
    q_low = q.lower().strip()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "Country not found.", 0, False
    
    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_filtered = data[data['Adm'] == adm].copy()
        a_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count, "Total": a_count + l_count, "DisplayName": COUNTRY_DISPLAY[adm]['ar'],
                        "Stats": {'DAB': 0, 'TV': 0, 'FM': 0}}) # مختصره للسرعة
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)
    return final_df, reports, f"Results for {len(selected_adms)} countries.", 100, True

async def generate_audio_stream(text):
    communicate = edge_tts.Communicate(text, "ar-EG-ShakirNeural")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def speak_text(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(generate_audio_stream(text))
    if data: st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. UI FLOW: CHICLET SLICER ---
db = load_db()

st.markdown("### 📊 International Coordination Slicer")
selected_country_from_chiclet = None

# إنشاء الـ Scrollable Slicer مع دمج العلم والاسم
with st.container():
    # بنستخدم columns عددها كبير عشان نسمح بالـ Scroll العرضي
    chiclet_cols = st.columns(len(COUNTRY_DISPLAY))
    for i, (code, info) in enumerate(COUNTRY_DISPLAY.items()):
        with chiclet_cols[i]:
            # هنا التغيير الأساسي: دمج العلم والاسم في الـ label بتاع الزرار
            # بنستخدم HTML بسيط جوه الـ button label (Streamlit بيعرضه كـ text بس الـ CSS اللي فوق بيظبطه)
            chiclet_button = st.button(
                f"{info['ar']}", 
                key=f"chiclet_{code}",
                help=f"Select {info['en']}"
            )
            # إضافة صورة العلم فوق الزرار مباشرة عشان يبانوا كـ Card واحد
            st.markdown(f"""
                <div style="position: relative; top: -95px; left: 0; right: 0; text-align: center; pointer-events: none;">
                    <img src="{FLAGS[code]}" class="chiclet-img">
                </div>
            """, unsafe_allow_html=True)
            
            if chiclet_button:
                selected_country_from_chiclet = info['ar']

# --- 5. VOICE & SEARCH INTERFACE ---
with st.container(border=True):
    col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="v186_mic")
    
    # تحديد القيمة الافتراضية بناءً على السليسر أو الصوت
    if selected_country_from_chiclet:
        input_val = selected_country_from_chiclet
    else:
        input_val = "" # إضافة Logic الـ Speech-to-text هنا لو محتاج

    with col_v2:
        query = st.text_input("Spectrum Inquiry:", value=input_val)
    with col_v3:
        if st.button("👂"): speak_text(query)

# --- 6. DASHBOARD EXECUTION ---
if query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_6(query, db)
    if success:
        st.success(msg)
        # عرض النتائج في Dashboard احترافي
        m_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with m_cols[i]:
                st.markdown(f'<div class="flag-container"><img src="{FLAGS[code]}" class="flag-img"></div>', unsafe_allow_html=True)
                st.metric(r['DisplayName'], f"Total: {r['Total']}", f"Assig: {r['Assignments']}")
        
        with st.expander("Technical Log"):
            st.dataframe(res_df)
