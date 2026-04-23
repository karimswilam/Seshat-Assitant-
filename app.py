import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import numpy as np
import sounddevice as sd
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# =========================
# 🎙️ LIVE AUDIO METER (FIXED)
# =========================
def get_audio_level(duration=0.1, fs=44100): # قللت الـ duration عشان الـ UI ميبقاش بطيء
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        sd.wait()
        amplitude = np.linalg.norm(recording) / len(recording)
        db = 20 * np.log10(amplitude + 1e-6)
        return max(min((db + 60) / 60, 1), 0)
    except:
        return 0

def render_audio_meter(level):
    color = "#22c55e" if level < 0.7 else "#ef4444"
    bar_html = f"""
    <div style="width:100%; background:#222; border-radius:10px; padding:5px;">
        <div style="width:{int(level*100)}%; height:15px; 
                    background:{color};
                    border-radius:10px; transition: width 0.1s ease-in-out;">
        </div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)

# =========================
# 🎙️ SPEECH TO TEXT (WHISPER API)
# =========================
def speech_to_text(audio_bytes):
    import requests
    try:
        # التصحيح: الموديل الرسمي هو whisper-1
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper-1"} 
        )
        return response.json().get("text", "")
    except Exception as e:
        st.error(f"STT Error: {e}")
        return ""

# =========================
# 🔊 TEXT TO SPEECH (EDGE-TTS)
# =========================
async def generate_speech(text):
    communicate = edge_tts.Communicate(text, "ar-EG-SalmaNeural")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return base64.b64encode(audio_data).decode()

def play_audio(b64_string):
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64_string}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(layout="wide", page_title="Seshat AI v21.0")

st.title("🎙️ Seshat Master Precision v21.0")

# Setup Database logic
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if files:
        df = pd.read_excel(files[0])
        df.columns = df.columns.astype(str).str.strip()
        return df
    return None

db = load_db()

# UI Layout
col_mic, col_status = st.columns([1, 1])

with col_mic:
    audio_data = mic_recorder(
        start_prompt="🎤 ابدأ التحدث",
        stop_prompt="⏹ توقف",
        key="recorder"
    )

with col_status:
    st.markdown("### 🔊 Mic Signal Level")
    level = get_audio_level()
    render_audio_meter(level)
    if level < 0.02:
        st.caption("🔇 المايك هادئ...")

# =========================
# ⚙️ ENGINE WITH FUZZY MATCHING
# =========================
COUNTRY_MAP = {
    'EGY': ['مصر', 'المصرية', 'egypt'],
    'ARS': ['السعودية', 'المملكة', 'saudi'],
    'TUR': ['تركيا', 'التركية', 'turkey'],
    'ISR': ['اسرائيل', 'israel']
}

def enhanced_engine(q, df):
    q = q.lower()
    selected = []
    
    # استخدام RapidFuzz للبحث عن اسم الدولة
    for code, keywords in COUNTRY_MAP.items():
        for kw in keywords:
            if fuzz.partial_ratio(kw, q) > 85: # دقة التطابق
                selected.append(code)
                break
                
    if not selected:
        return None, "لم أستطع تحديد الدولة في استفسارك."

    # تأمين عمود الـ Adm (Fix لـ KeyError)
    adm_col = 'Adm' if 'Adm' in df.columns else df.columns[0]
    res_df = df[df[adm_col].isin(selected)]
    
    msg = f"تم العثور على {len(res_df)} سجل لـ {', '.join(selected)}."
    return res_df, msg

# PROCESS
if audio_data:
    with st.spinner("⏳ جاري تحليل الصوت..."):
        recognized_text = speech_to_text(audio_data['bytes'])
        
        if recognized_text:
            st.info(f"📝 النص المستخرج: {recognized_text}")
            
            if db is not None:
                final_df, response_text = enhanced_engine(recognized_text, db)
                
                st.success(response_text)
                
                # تشغيل الرد الصوتي
                b64_audio = asyncio.run(generate_speech(response_text))
                play_audio(b64_audio)
                
                if final_df is not None:
                    st.dataframe(final_df)
            else:
                st.error("❌ قاعدة البيانات غير موجودة!")
        else:
            st.warning("⚠️ لم يتم التعرف على كلمات واضحة.")

# Keep your text input as fallback
st.divider()
manual_query = st.text_input("⌨️ أو اكتب استفسارك هنا:")
if manual_query and db is not None:
    res, msg = enhanced_engine(manual_query, db)
    st.write(msg)
    if res is not None: st.dataframe(res)
