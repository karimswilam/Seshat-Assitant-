import streamlit as st
import pandas as pd
import numpy as np
import os, io, time, asyncio
import speech_recognition as sr
import edge_tts
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
import plotly.graph_objects as go

# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Seshat AI – Voice Assistant Core")

# -------------------------------------------------
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()
    return df

# -------------------------------------------------
def convert_to_wav(audio_bytes):
    """
    🔑 ROOT FIX:
    Convert mic_recorder audio → WAV PCM
    """
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)
    return wav_io

# -------------------------------------------------
def analyze_audio(audio_bytes):
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
    db = 20 * np.log10(rms + 1e-6)
    return db

def draw_signal(db):
    fig = go.Figure(go.Bar(
        x=[db], y=["Signal Level"], orientation="h"
    ))
    fig.update_layout(
        xaxis=dict(range=[-60, 0], title="dB"),
        height=120, margin=dict(l=60, r=20, t=20, b=20)
    )
    return fig

# -------------------------------------------------
def speech_to_text(audio_bytes):
    r = sr.Recognizer()

    wav_audio = convert_to_wav(audio_bytes)

    with sr.AudioFile(wav_audio) as source:
        audio_data = r.record(source)

    try:
        return r.recognize_google(audio_data, language="ar-EG")
    except:
        try:
            return r.recognize_google(audio_data, language="en-US")
        except:
            return None

# -------------------------------------------------
async def tts(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    comm = edge_tts.Communicate(text, voice)

    out = io.BytesIO()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            out.write(chunk["data"])
    out.seek(0)
    return out

# -------------------------------------------------
st.title("🎙️ Seshat AI – Voice Assistant Core")

db = load_db()

col1, col2 = st.columns([1, 4])

with col1:
    audio = mic_recorder(
        start_prompt="🎤 Start Asking",
        stop_prompt="🛑 Stop",
        key="assistant"
    )

if audio:
    db_level = analyze_audio(audio["bytes"])
    st.subheader("🔊 Signal Validation")
    st.plotly_chart(draw_signal(db_level), use_container_width=True)

    if db_level < -44:
        st.error("❌ الصوت ضعيف – مفيش voice واضح")
        st.stop()

    with st.status("🧠 Processing voice...", expanded=True) as status:
        st.write("🎧 Reading audio...")
        time.sleep(0.5)

        text = speech_to_text(audio["bytes"])
        if not text:
            status.update(state="error")
            st.error("❌ مش فاهم الكلام المسجّل")
            st.stop()

        st.write(f"✅ First token: **{text.split()[0]}**")
        time.sleep(0.5)

        st.write("✅ Full query extracted")
        st.info(text)

        st.session_state.query = text
        status.update(state="complete")

# -------------------------------------------------
query = st.text_input(
    "✍️ Confirm / Edit Question",
    value=st.session_state.get("query", "")
)

if query and db is not None:
    from engine import engine_v17_0

    res_df, reports, msg, conf, success = engine_v17_0(query, db)

    if success:
        st.success(msg)
        audio_reply = asyncio.run(tts(msg))
        st.audio(audio_reply, format="audio/mp3")
        st.dataframe(res_df)
    else:
        st.warning("⚠️ بعض أجزاء السؤال غير مفهومة وتم تخطيها")
