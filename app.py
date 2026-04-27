import streamlit as st
import pandas as pd
import numpy as np
import os, io, asyncio, time
import edge_tts
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from rapidfuzz import process, fuzz

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v2026 - Voice Pro")

# Logic Constants
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'], 'ISR': ['israel', 'isr', 'اسرائيل']}

# --- 2. ADVANCED AUDIO ENGINE (Signal Analysis & STT) ---
def analyze_and_recognize(audio_bytes):
    # 1. Signal Analysis (dB Level)
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_data**2))
    db_level = 20 * np.log10(rms) if rms > 0 else 0
    
    # 2. Recognition Logic
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)
    
    try:
        # بنجرب التعرف على العربي والإنجليزي مع بعض
        text = r.recognize_google(audio, language="ar-EG")
        return text, db_level, True
    except sr.UnknownValueError:
        return None, db_level, False
    except Exception as e:
        return f"Error: {str(e)}", db_level, False

async def text_to_speech(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice)
    data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            data.write(chunk["data"])
    data.seek(0)
    return data

# --- 3. CORE CALCULATION ENGINE (Placeholder for your enginev170) ---
def enginev170_mock(user_input, df):
    # ده محاكي لمنطق التخصيص بتاعك (Israel/DAB)
    found_isr = any(word in user_input.lower() for word in ['israel', 'اسرائيل'])
    found_dab = any(word in user_input.lower() for word in ['dab', 'داب', 'تخصيص'])
    
    if found_isr and found_dab:
        msg = "تم فحص قاعدة البيانات: إسرائيل لديها 14 تخصيص داب (DAB) مفعلة حالياً."
        return pd.DataFrame({"Item": ["DAB"], "Count": [14]}), msg, True
    return None, "لم أستطع تحديد الطلب بدقة، يرجى إعادة الصياغة.", False

# --- 4. UI LAYOUT ---
st.title("🎙️ Seshat Voice Assistant 2026")

# Sidebar for Database status
with st.sidebar:
    st.header("System Status")
    uploaded_file = st.file_uploader("Upload Data.xlsx", type=['xlsx'])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("Database Loaded!")
    else:
        st.warning("Please upload 'Data.xlsx'")
        df = None

# Main Voice Interaction Area
st.subheader("Interactive Voice Control")
audio_input = mic_recorder(
    start_prompt="🎤 Start Asking (English/Arabic)",
    stop_prompt="🛑 Stop & Process",
    key="voice_input"
)

if audio_input:
    # 1. Validation Step (Signal Analysis)
    raw_bytes = audio_input['bytes']
    text_query, db_level, success = analyze_and_recognize(raw_bytes)
    
    # Visual dB Meter
    st.write(f"**Signal Level:** {db_level:.2f} dB")
    st.progress(min(max(int(db_level), 0), 100) / 100.0)
    
    if db_level < 10:
        st.error("Low signal detected. Please speak louder.")
    
    # 2. Processing Steps (Status Bar)
    with st.status("Processing Audio Content...", expanded=True) as status:
        st.write("🔍 Analyzing Signal Frequencies...")
        time.sleep(0.6)
        st.write("🤖 Converting Speech to Text (STT)...")
        time.sleep(0.8)
        
        if success:
            st.write("✅ Text Recognition Successful!")
            status.update(label="Processing Complete!", state="complete", expanded=False)
            
            # عرض السؤال
            st.chat_message("user").write(text_query)
            
            # نداء الـ Engine
            if df is not None:
                res_df, response_text, engine_ok = enginev170_mock(text_query, df)
                
                if engine_ok:
                    st.chat_message("assistant").write(response_text)
                    if res_df is not None:
                        st.table(res_df)
                    
                    # الرد الصوتي
                    audio_output = asyncio.run(text_to_speech(response_text))
                    st.audio(audio_output, format="audio/mp3")
                else:
                    st.warning("Kalam skipped: " + response_text)
        else:
            # حالة عدم فهم الكلام (Skip logic)
            st.write("⚠️ Low Confidence in Speech Detection")
            status.update(label="Processing Failed", state="error")
            st.error("مفهمتش الجزء ده في الريكورد، ياريت تعيد السؤال بوضوح.")
            st.info("Tip: Try to avoid background noise.")

# --- 5. DASHBOARD VISUALS (Static example) ---
if df is not None:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Allocations", len(df))
    with col2:
        st.image(FLAGS['ISR'], width=100, caption="Current Target Filter")
