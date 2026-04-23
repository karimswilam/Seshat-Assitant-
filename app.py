import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests
import numpy as np
import edge_tts
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v22.0", page_icon="🛰️")

# --- 2. FIXED DATA LOADER (Universal Mapping) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if not target: return None
    
    df = pd.read_excel(target)
    # تنظيف شامل للأسماء
    df.columns = df.columns.astype(str).str.strip()
    
    # الـ Mapping اللي أنت مثبته بس بشكل أكتر صرامة لمنع KeyError
    mapping = {
        'Adm': ['Administration', 'Adm', 'Country', 'الإدارة', 'الدولة'],
        'Notice Type': ['Notice Type', 'NT', 'نوع الإخطار'],
        'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'الموقع'],
        'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'الإحداثيات']
    }
    
    for std_name, synonyms in mapping.items():
        for col in df.columns:
            if col in synonyms or col.lower() in [s.lower() for s in synonyms]:
                df = df.rename(columns={col: std_name})
                break

    # 🔥 حل مشكلة الـ ArrowTypeError (التواريخ اللي بتوقف الأبلكيشن)
    for col in df.columns:
        if any(key in col.lower() for key in ['date', 'receipt', 'time']):
            df[col] = df[col].astype(str).replace(['nan', 'NaT'], '')
            
    return df

# --- 3. VOICE UTILITIES (Whisper & TTS) ---
def stt_whisper(audio_bytes):
    """تحويل الصوت لنص باستخدام OpenAI Whisper"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper-1"}
        )
        return response.json().get("text", "")
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. UI FLOW & VOICE INDICATOR ---
db = load_db()

st.markdown(f"## 🎙️ Voice & Signal Command Center")

# إضافة الـ Recorder مع Indication مرئي
c1, c2 = st.columns([1, 3])
with c1:
    audio_output = mic_recorder(
        start_prompt="🎤 ابدأ التحدث", 
        stop_prompt="⏹ توقف للتحليل", 
        key="spectrum_mic"
    )

voice_query = ""
if audio_output:
    # Indication 1: حجم الإشارة
    st.info(f"🛰️ Signal Capture: {len(audio_output['bytes'])/1024:.1f} KB received.")
    
    # Indication 2: رسم توضيحي للإشارة (Oscilloscope)
    audio_array = np.frombuffer(audio_output['bytes'], dtype=np.int16)
    st.line_chart(audio_array[:2000], height=80) 
    
    with st.spinner("🔄 Decoding signal via Whisper..."):
        voice_query = stt_whisper(audio_output['bytes'])
        if voice_query:
            st.success(f"Recognized: {voice_query}")

# خانة السؤال (تأخذ النص من الصوت تلقائياً)
query = st.text_input("⌨️ Confirm/Edit Inquiry:", value=voice_query)

if query and db is not None:
    # استدعاء الـ Engine (v17 Logic)
    # ملاحظة: تأكد من وجود دالة engine_v17_0 كاملة في الكود عندك
    from engine import engine_v17_0 # مثال لو كانت في ملف خارجي
    
    res_df, reports, msg, conf, success = engine_v17_0(query, db)
    
    if success:
        st.success(msg)
        # عرض الجدول (لن يضرب الآن بفضل تحويل التواريخ لنصوص)
        st.dataframe(res_df, use_container_width=True)
    else:
        st.error(f"Engine Error: {msg}")
