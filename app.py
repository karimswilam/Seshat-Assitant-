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

# تفعيل nest_asyncio للسماح بتشغيل الـ Audio Engine بسلاسة
nest_asyncio.apply()

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.2", page_icon="📡")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.2"
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
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'المصريه'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة', 'المملكه', 'السعوديه'],
    'TUR': ['turkey', 'tur', 'تركيا', 'تركي', 'التركية', 'التركيه', 'turkish'],
    'CYP': ['cyprus', 'cyp', 'قبرص', 'قبرصية'],
    'GRC': ['greece', 'grc', 'اليونان', 'يوناني', 'اليونانية'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio', 'إذاعي', 'اذاعي'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون']
}

# --- 3. UTILITIES & VOICE ENGINE ---
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

def speech_to_text_robust(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        # تحويل الـ WebM القادم من المتصفح إلى WAV باستخدام Pydub (تتطلب FFmpeg)
        webm_audio = io.BytesIO(audio_data['bytes'])
        audio_segment = AudioSegment.from_file(webm_audio, format="webm")
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language="ar-EG")
    except Exception as e:
        st.error(f"Signal Processing Error: {e}")
        return None

async def generate_audio_stream(text):
    """دالة لتوليد ملف الصوت بصيغة MP3 من النص"""
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-5%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        return audio_data.getvalue()
    except Exception as e:
        return None

# --- 4. MAIN INTERFACE LOGIC ---
st.subheader("🎙️ Voice Intelligence Control")
audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key='recorder')

if audio_input:
    query_text = speech_to_text_robust(audio_input)
    if query_text:
        st.success(f"Recognized: {query_text}")
        # هنا يتم وضع منطق البحث في البيانات الخاص بك (Excel/Dataframe)
        # وسنقوم بتشغيل محرك الرد الصوتي (TTS)
        loop = asyncio.get_event_loop()
        reply_audio = loop.run_until_complete(generate_audio_stream(f"لقد استلمت استفسارك بخصوص {query_text}"))
        if reply_audio:
            st.audio(reply_audio, format="audio/mp3")
    else:
        st.warning("Signal weak or unrecognized. Please try again.")

# ملاحظة هندسية: تأكد من وجود ملف packages.txt وبه سطر ffmpeg لضمان عمل pydub.
