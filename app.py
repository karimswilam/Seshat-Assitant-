import streamlit as st
import pandas as pd
import os
import io
import re
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

# ================= ✅ FIXED STT =================
def speech_to_text_from_mic(mic_data):
    """
    mic_data comes directly from streamlit-mic-recorder
    """
    try:
        audio_bytes = mic_data["bytes"]
        sample_rate = mic_data.get("sample_rate", 16000)
        sample_width = 2  # 16-bit PCM

        audio = sr.AudioData(audio_bytes, sample_rate, sample_width)
        recognizer = sr.Recognizer()

        return recognizer.recognize_google(audio)
    except Exception as e:
        st.error(f"STT Error: {e}")
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
query = st.text_input("🔤 Ask by text")

status_box = st.empty()
progress_bar = st.progress(0)

st.markdown("### 🎤 Or ask by voice")
status_box.info("🎤 Ready to record")

voice = mic_recorder(
    start_prompt="▶ Start Recording",
    stop_prompt="⏹ Stop Recording",
    key="mic"
)

if voice and "bytes" in voice:
    status_box.warning("⏳ Processing audio...")
    progress_bar.progress(30)

    audio_size_kb = len(voice["bytes"]) / 1024
    st.caption(f"🔊 Audio captured: {audio_size_kb:.1f} KB")

    text = speech_to_text_from_mic(voice)
    progress_bar.progress(80)

    if text:
        status_box.success("✅ Voice recognized")
        st.success(f"You said: {text}")
        query = text
    else:
        status_box.error("❌ Could not recognize voice")

    progress_bar.progress(100)

if query and db is not None:
    status_box.info("📊 Processing query...")
    play_audio(query)

    result = engine(query, db)

    status_box.success("✅ Done")
    st.success(result)
    play_audio(result)
