import streamlit as st
import pandas as pd
import numpy as np
import os, io, time, asyncio
import speech_recognition as sr
import edge_tts
from streamlit_mic_recorder import mic_recorder
from rapidfuzz import fuzz
import plotly.graph_objects as go

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Seshat AI v30 – Voice Core")

FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'],
    'TOTAL_KEY': ['total', 'اجمالي']
}

# ---------------- DB ----------------
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else None
    if not target: return None
    df = pd.read_excel(target)
    df.columns = df.columns.str.strip()
    return df

# ---------------- AUDIO ANALYSIS ----------------
def analyze_audio(audio_bytes):
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
    db = 20 * np.log10(rms + 1e-6)
    return rms, db

def signal_meter(db):
    fig = go.Figure(go.Bar(
        x=[db],
        y=["Signal Level"],
        orientation='h'
    ))
    fig.update_layout(
        xaxis=dict(range=[-60, 0], title="dB"),
        height=120,
        margin=dict(l=50, r=20, t=20, b=20)
    )
    return fig

# ---------------- SPEECH TO TEXT ----------------
def speech_to_text(audio_bytes):
    r = sr.Recognizer()
    audio = sr.AudioFile(io.BytesIO(audio_bytes))
    with audio as source:
        audio_data = r.record(source)

    try:
        return r.recognize_google(audio_data, language="ar-EG")
    except:
        try:
            return r.recognize_google(audio_data, language="en-US")
        except:
            return None

# ---------------- TEXT TO SPEECH ----------------
async def tts(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    comm = edge_tts.Communicate(text, voice)
    data = io.BytesIO()
    async for c in comm.stream():
        if c["type"] == "audio":
            data.write(c["data"])
    data.seek(0)
    return data

# ---------------- UI ----------------
st.title("🎙️ Seshat AI – Voice Assistant Core")

db = load_db()

rec_col, flow_col = st.columns([1, 4])

with rec_col:
    audio = mic_recorder(
        start_prompt="🎤 Start Asking",
        stop_prompt="🛑 Stop",
        key="rec"
    )

if audio:
    st.subheader("🔎 Signal Validation")

    rms, db_level = analyze_audio(audio['bytes'])
    st.plotly_chart(signal_meter(db_level), use_container_width=True)

    if db_level < -45:
        st.error("❌ الصوت ضعيف – مفيش Voice Input واضح")
        st.stop()

    st.success("✅ Voice Detected – Processing Started")

    with st.status("🧠 Processing...", expanded=True) as status:

        time.sleep(0.5)
        st.write("🎧 Reading audio...")
        
        text = speech_to_text(audio['bytes'])
        if not text:
            st.warning("⚠️ مش فاهم أي كلام واضح في التسجيل")
            status.update(label="Failed", state="error")
            st.stop()

        time.sleep(0.5)
        first_word = text.split()[0]

        st.write(f"✅ First word detected: **{first_word}**")
        time.sleep(0.5)

        st.write("✅ Full question extracted")
        st.info(text)

        st.session_state.query = text
        status.update(label="Processing Done", state="complete")

# ---------------- CONFIRM / ENGINE ----------------
query = st.text_input(
    "✍️ Confirm or Edit Question:",
    value=st.session_state.get("query", "")
)

if query and db is not None:
    from engine import engine_v17_0   # محركك كما هو

    res_df, reports, msg, conf, success = engine_v17_0(query, db)

    if success:
        st.subheader("🔊 Assistant Answer")
        st.success(msg)

        voice = asyncio.run(tts(msg))
        st.audio(voice, format="audio/mp3")

        st.subheader("📊 Data Output")
        st.dataframe(res_df)
    else:
        st.error("❌ Inquiry not understood fully – some parts skipped")
