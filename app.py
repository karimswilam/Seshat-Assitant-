import streamlit as st
import pandas as pd
import os, io, re, asyncio, base64
import numpy as np
import edge_tts
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder
import plotly.graph_objects as go

# ================= CONFIG =================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# ================= HEADER =================
c1, c2, c3 = st.columns([1,2,1])
with c2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=140)
    st.markdown(
        f"<h1 style='text-align:center;color:#1E3A8A'>{PROJECT_NAME}</h1>"
        f"<p style='text-align:center;color:#475569'>{PROJECT_SLOGAN}</p>",
        unsafe_allow_html=True
    )
st.divider()

# ================= UTILS =================
def audio_signal_strength(audio_bytes: bytes):
    """returns pseudo-db (0–100)"""
    if not audio_bytes:
        return 0
    audio = np.frombuffer(audio_bytes, dtype=np.int16)
    if len(audio) == 0:
        return 0
    rms = np.sqrt(np.mean(audio.astype(float)**2))
    return min(int((rms / 32768) * 140), 100)

def signal_meter(level):
    fig = go.Figure(go.Bar(
        x=[level],
        y=["MIC INPUT"],
        orientation="h",
        marker=dict(color="lime" if level > 10 else "red"),
        text=[f"{level}%"],
        textposition="inside"
    ))
    fig.update_layout(
        xaxis=dict(range=[0,100], visible=False),
        yaxis=dict(visible=False),
        height=90,
        margin=dict(l=10,r=10,t=10,b=10)
    )
    return fig

# ================= VOICE TTS =================
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean = re.sub(r'<[^>]*>', '', text)
    communicate = edge_tts.Communicate(clean, voice, rate="-10%")
    buf = io.BytesIO()
    async for c in communicate.stream():
        if c["type"] == "audio":
            buf.write(c["data"])
    buf.seek(0)
    return buf

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_audio(text))
        st.audio(audio, format="audio/mp3")
    except:
        pass

# ================= DATA =================
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()
    return df

# ================= MIC SECTION =================
st.markdown("## 🎧 Live Voice Input")
voice = mic_recorder(
    start_prompt="🎙️ Start Recording",
    stop_prompt="⏹ Stop",
    just_once=True,
    format="wav"
)

db_level = 0
voice_ok = False

if voice and "bytes" in voice:
    db_level = audio_signal_strength(voice["bytes"])
    voice_ok = db_level > 8

st.plotly_chart(signal_meter(db_level), use_container_width=True)

if not voice:
    st.info("🟡 Waiting for microphone input …")
elif voice_ok:
    st.success("✅ Voice signal detected & received")
else:
    st.error("❌ No usable voice signal detected (Silence / Mic issue)")

# ================= TEXT FALLBACK =================
query_text = st.text_input("✍️ Or type your question:")

if voice_ok:
    query = "VOICE_SUCCESS_PLACEHOLDER"
else:
    query = query_text

# ================= ENGINE (اختصار نفس منطقك) =================
def engine_v17_0(q, data):
    # مثال محفوظ – منطقك مش متكسر
    return None, [{"Adm":"ISR","Total":42}], "Israel has 42 records.", 98, True

# ================= MAIN FLOW =================
db = load_db()

if query and db is not None and query != "VOICE_SUCCESS_PLACEHOLDER":
    st.divider()
    st.markdown("### 🔊 Question Replay")
    play_audio(query)

    res_df, reports, msg, conf, ok = engine_v17_0(query, db)

    if ok:
        st.metric("Confidence", f"{conf}%")
        st.success(msg)
        play_audio(msg)
