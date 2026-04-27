import streamlit as st
import pandas as pd
import os
import io
import Ask by text")import re

st.markdown("### 🎤 Or ask by voice")
voice = mic_recorder(start_prompt="▶ Start", stop_prompt="⏹ Stop", key="mic")

if voice and "bytes" in voice:
    text = speech_to_text(voice["bytes"])
    if text:
        st.success(f"You said: {text}")
        query = text

if query and db is not None:
    play_audio(query)
    result = engine(query, db)
    st.success(result)
    play_audio(result)
``
import asyncio

import edge_tts
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# ================= CONFIG =================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

st.title("Seshat AI v17.0 – Voice Prototype")

# ================= CONSTANTS =================
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

# ================= DATA =================
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        st.error("❌ Data.xlsx not found")
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()
    return df

db = load_db()

# ================= TTS =================
async def generate_audio(text):
    voice = "ar-EG-ShakirNeural" if re.search(r"[ء-ي]", text) else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.write(chunk["data"])
    audio.seek(0)
    return audio

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_audio(text))
        st.audio(audio, format="audio/mp3")
    except:
        pass

# ================= STT =================
def speech_to_text(audio_bytes):
    try:
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = r.record(source)
        return r.recognize_google(audio)
    except:
        return None

# ================= ENGINE =================
def engine(query, data):
    q = query.lower()
    reports = []

    for adm, keys in COUNTRY_MAP.items():
        if any(k in q for k in keys):
            df_adm = data[data["Administration"] == adm]
            a = len(df_adm[df_adm["Notice Type"].isin(STRICT_ASSIG)])
            l = len(df_adm[df_adm["Notice Type"].isin(STRICT_ALLOT)])
            reports.append((adm, a, l))

    if not reports:
        return "No country identified."

    msg = " | ".join([f"{r[0]}: A={r[1]} L={r[2]}" for r in reports])
    return msg

# ================= UI =================
