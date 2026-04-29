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
st.set_page_config(layout="wide", page_title="Se-Chat v18.7", page_icon="📡")

# تنسيق الـ CSS لتحسين المظهر ودعم الاتجاهات
st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .centered-msg { 
        text-align: center; font-size: 18px; color: #1E3A8A; 
        padding: 15px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat v18.7 | نظام ذكاء الطيف"
PROJECT_SLOGAN = "Spectrum Intelligence & International Coordination"

# Header
h_col1, h_col2, h_col3 = st.columns([1, 2, 1])
with h_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=100)
    st.markdown(f'<div style="text-align: center;"><h2 style="color: #1E3A8A;">{PROJECT_NAME}</h2><p>{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

# --- 2. ENGINEERING LOGIC & MAPS ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'قصر', 'متر'],
    'ARS': ['saudi', 'saudiarabia', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'تركي'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'إسرائيل']
}

CAT_MAP = {'DAB': ['GS1','GS2','DS1','DS2'], 'TV': ['T02','G02','GT1','GT2','DT1','DT2'], 'FM': ['T01','T03','T04']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. SPEECH UTILITIES (ROBUST) ---
def speech_to_text_robust(audio_data):
    if not audio_data or 'bytes' not in audio_data: return ""
    r = sr.Recognizer()
    try:
        # تحويل الصوت بأمان
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data['bytes']), format="webm")
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio = r.record(source)
            # محاولة التعرف (عربي أولاً لدعم طبيعة الاستخدام)
            return r.recognize_google(audio, language="ar-EG")
    except Exception as e:
        return "" # إرجاع نص فارغ بدلاً من الـ Crash

async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def speak(text):
    if text:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. ENGINE CORE ---
@st.cache_data
def load_data():
    # دمج ملفات البيانات GE06 و GE84
    try:
        df_ge06 = pd.read_excel("Data.xlsx") if os.path.exists("Data.xlsx") else pd.DataFrame()
        df_ge84 = pd.read_excel("FM.xlsx") if os.path.exists("FM.xlsx") else pd.DataFrame()
        if not df_ge06.empty: df_ge06['Plan'] = 'GE06'
        if not df_ge84.empty: df_ge84['Plan'] = 'GE84'
        combined = pd.concat([df_ge06, df_ge84], ignore_index=True)
        # توحيد أسماء الأعمدة
        combined.rename(columns={'Administration': 'Adm', 'Notice Type': 'NT'}, inplace=True, errors='ignore')
        return combined
    except: return None

def engine_v18_7(q, data):
    q_low = q.lower()
    # تحديد الدولة
    selected = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected: return None, "الرجاء تحديد دولة صحيحة (مصر، السعودية، إلخ)"
    
    # فلاتر بسيطة وسريعة
    df_filtered = data[data['Adm'].isin(selected)]
    # (هنا نضع بقية منطق الفلترة الخاص بالخدمات والترددات كما في كودك)
    # ...
    count = len(df_filtered)
    msg = f"تم العثور على {count} سجل لـ {selected[0]}"
    return df_filtered, msg

# --- 5. MAIN UI ---
db = load_data()

with st.sidebar:
    st.info("System Status: Online 📡")
    if st.button("Clear App Cache"):
        st.cache_data.clear()
        st.rerun()

# منطقة الإدخال الصوتي والكتابي
input_container = st.container(border=True)
with input_container:
    c1, c2 = st.columns([1, 5])
    with c1:
        # وضع الميكروفون في Try لضمان عدم التهنيج
        try:
            audio_data = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="mic_v187")
        except:
            st.error("Mic Access Denied")
            audio_data = None
            
    with c2:
        voice_text = speech_to_text_robust(audio_data) if audio_data else ""
        query = st.text_input("اسأل Seshat AI (كتابة أو صوتاً):", value=voice_text)

if query and db is not None:
    res_df, result_msg = engine_v18_7(query, db)
    st.success(result_msg)
    
    if not res_df.empty:
        # عرض سريع للنتائج
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Total Records", len(res_df))
        with col_m2:
            if st.button("🔊 تشغيل الرد الصوتي"):
                speak(result_msg)
        
        st.dataframe(res_df.head(100), use_container_width=True)
