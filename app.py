import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import time
import asyncio

import speech_recognition as sr
import edge_tts
from streamlit_mic_recorder import mic_recorder
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Seshat AI – Voice Assistant Core",
    layout="wide"
)

# =====================================================
# DATABASE
# =====================================================
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()
    return df

db = load_db()

# =====================================================
# AUDIO ANALYSIS (dB)
# =====================================================
def analyze_audio(audio_bytes):
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    if len(samples) == 0:
        return -100
    rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
    db = 20 * np.log10(rms + 1e-6)
    return db

def draw_signal(db):
    fig = go.Figure(go.Bar(
        x=[db],
        y=["Signal Level"],
        orientation="h"
    ))
    fig.update_layout(
        xaxis=dict(range=[-60, 0], title="dB"),
        height=120,
        margin=dict(l=60, r=20, t=20, b=20)
    )
    return fig

# =====================================================
# SPEECH TO TEXT (NO WAV / NO FFMPEG)
# =====================================================
def speech_to_text(audio_bytes):
    r = sr.Recognizer()
    try:
        audio = sr.AudioData(
            audio_bytes,
            sample_rate=44100,
            sample_width=2
        )
        try:
            return r.recognize_google(audio, language="ar-EG")
        except:
            return r.recognize_google(audio, language="en-US")
    except:
        return None

# =====================================================
# TEXT TO SPEECH
# =====================================================
async def text_to_speech(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"

    comm = edge_tts.Communicate(text, voice)
    audio_out = io.BytesIO()

    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_out.write(chunk["data"])

    audio_out.seek(0)
    return audio_out

# =====================================================
# UI
# =====================================================
st.title("🎙️ Seshat AI – Voice Assistant Core")

left, right = st.columns([1, 4])

with left:
    audio = mic_recorder(
        start_prompt="🎤 Start Asking",
        stop_prompt="🛑 Stop",
        key="voice_input"
    )

# =====================================================
# VOICE FLOW
# =====================================================
if audio:
    st.subheader("🔊 Signal Validation")

    db_level = analyze_audio(audio["bytes"])
    st.plotly_chart(draw_signal(db_level), use_container_width=True)

    if db_level < -45:
        st.error("❌ الصوت ضعيف – مفيش Voice Input واضح")
    else:
        st.success("✅ Voice Detected – Processing Started")

        with st.status("🧠 Processing...", expanded=True) as status:
            st.write("🎧 Reading audio...")
            time.sleep(0.4)

            text = speech_to_text(audio["bytes"])

            if not text:
                status.update(state="error")
                st.error("❌ مش قادر أفهم التسجيل")
            else:
                st.write(f"✅ First word: **{text.split()[0]}**")
                time.sleep(0.3)
                st.write("✅ Full question extracted")
                st.info(text)

                st.session_state["query"] = text
                status.update(state="complete")

# =====================================================
# MANUAL / CONFIRM INPUT (ORIGINAL DASHBOARD BEHAVIOR)
# =====================================================
query = st.text_input(
    "✍️ Confirm / Edit Question:",
    value=st.session_state.get("query", "")
)

# =====================================================
# ENGINE CALL (UNCHANGED)
# =====================================================
if query and db is not None:
    try:
        from engine import engine_v17_0
    except:
        st.error("❌ engine_v17_0 مش موجود – تأكد من ملف engine.py")
        st.stop()

    res_df, reports, msg, conf, success = engine_v17_0(query, db)

    if success:
        st.subheader("🔊 Assistant Response")
        st.success(msg)

        audio_reply = asyncio.run(text_to_speech(msg))
        st.audio(audio_reply, format="audio/mp3")

        st.subheader("📊 Results")
        st.dataframe(res_df)
    else:
        st.warning("⚠️ السؤال غير واضح بالكامل – تم تخطي أجزاء")
