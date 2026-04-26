import streamlit as st
import pandas as pd
import os, io, re, asyncio, time
import edge_tts
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from rapidfuzz import process, fuzz

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v30.0")

# نداء الـ Core Logic بتاعك (بدون أي تعديل في الحسابات)
# [نفس الـ FLAGS والـ SYNONYMS والـ COUNTRY_MAP اللي بعتهم في رسالتك]
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png", 'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']}
SYNONYMS = {'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'], 'DAB_KEY': ['dab', 'داب'], 'TOTAL_KEY': ['total', 'اجمالي']}

# --- 2. THE VOX ENGINE (Fixed ValueError) ---
def speech_to_text(audio_bytes):
    r = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            # استخدام Google كحل مجاني ومستقر
            return r.recognize_google(audio_data, language="ar-EG")
    except Exception as e:
        return f"Error: {str(e)}"

async def text_to_speech(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice)
    data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": data.write(chunk["data"])
    data.seek(0)
    return data

# --- 3. DATABASE ENGINE (Fixed KeyError) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # تصليح الـ KeyError: 'Adm' نهائياً
        rename_map = {}
        for col in df.columns:
            if col.lower() in ['adm', 'administration', 'country', 'الادارة']: rename_map[col] = 'Adm'
            if col.lower() in ['notice type', 'nt', 'نوع الاخطار']: rename_map[col] = 'Notice Type'
        df.rename(columns=rename_map, inplace=True)
        return df
    return None

# --- 4. MAIN UI ---
st.title("Seshat Master Precision v30.0")
db = load_db()

# مساحة الـ Voice Assistant
col_v1, col_v2 = st.columns([1, 4])
with col_v1:
    audio_data = mic_recorder(start_prompt="🎤 Start Assistant", stop_prompt="🛑 Finish", key="assistant")

if audio_data:
    query = speech_to_text(audio_data['bytes'])
    if "Error" not in query:
        st.session_state.query = query
        st.success(f"Recognized: {query}")
    else:
        st.error("Audio conversion failed. Using manual input.")

# الـ Manual Input لضمان الشغل في كل الحالات
user_input = st.text_input("Confirm/Type Inquiry:", value=st.session_state.get('query', ""))

if user_input and db is not None:
    # نداء محركك الهندسي (engine_v17_0 من كودك الأصلي)
    # ملاحظة: أنا حطيت هنا مثال سريع عشان الكود يشتغل، استعمل الـ engine_v17_0 بتاعك بالظبط
    from engine import engine_v17_0 # لو المحرك في ملف خارجي أو انسخه هنا
    res_df, reports, msg, conf, success = engine_v17_0(user_input, db)
    
    if success:
        st.subheader("🔊 Assistant Response")
        st.info(msg)
        # تشغيل الرد الصوتي تلقائياً
        audio_response = asyncio.run(text_to_speech(msg))
        st.audio(audio_response, format="audio/mp3")
        
        # عرض الـ Dataframe والنتائج [نفس الـ UI Flow بتاعك]
        st.dataframe(res_df)
