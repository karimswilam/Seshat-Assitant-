import streamlit as st
import pandas as pd
import os, io, re, asyncio
import numpy as np
import edge_tts
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder
import plotly.graph_objects as go

# ================= PAGE =================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

# ================= HEADER =================
st.markdown("""
<h1 style="text-align:center;color:#1E3A8A">Seshat Master Precision v17.0</h1>
<p style="text-align:center;color:#475569">
Project BASIRA | Spectrum Intelligence & Governance
</p>
""", unsafe_allow_html=True)

st.divider()

# ================= VOICE DEBUG LAYER =================
st.markdown("## 🎙️ Microphone Signal Monitor (Debug Only)")

audio = mic_recorder(
    start_prompt="🎤 Start Mic",
    stop_prompt="⏹ Stop",
    just_once=True,
    format="wav"
)

def compute_level(audio_bytes):
    if not audio_bytes:
        return 0
    arr = np.frombuffer(audio_bytes, dtype=np.int16)
    if arr.size == 0:
        return 0
    rms = np.sqrt(np.mean(arr.astype(float)**2))
    level = min(int((rms / 32768) * 120), 100)
    return level

signal_level = compute_level(audio["bytes"]) if audio else 0

fig = go.Figure()
fig.add_bar(
    x=[signal_level],
    y=["MIC INPUT"],
    orientation="h",
    marker_color="lime" if signal_level > 8 else "crimson",
    text=[f"{signal_level}%"],
    textposition="inside"
)
fig.update_layout(
    xaxis=dict(range=[0,100], visible=False),
    yaxis=dict(visible=False),
    height=90,
    margin=dict(l=5,r=5,t=5,b=5)
)

st.plotly_chart(fig, use_container_width=True)

if not audio:
    st.info("🟡 Waiting for microphone input")
elif signal_level <= 8:
    st.error("❌ No usable voice detected (Silence / mic issue)")
else:
    st.success("✅ Voice signal detected and captured")

st.divider()

# ================= ORIGINAL TEXT INPUT (UNCHANGED) =================
query = st.text_input(
    "🎙️ Enter Spectrum Inquiry (Text or Voice-Assisted):",
    key="main_q"
)

# ================= TTS =================
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean = re.sub(r'<[^>]*>', '', text)
    com = edge_tts.Communicate(clean, voice, rate="-10%")
    buff = io.BytesIO()
    async for ch in com.stream():
        if ch["type"] == "audio":
            buff.write(ch["data"])
    buff.seek(0)
    return buff

def play_audio(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio = loop.run_until_complete(generate_audio(text))
    st.audio(audio, format="audio/mp3")

# ================= LOAD DATA =================
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()
    return df

# ================= ENGINE v17.0 (UNCHANGED) =================
def engine_v17_0(q, data):
    ql = q.lower()

    COUNTRY_MAP = {
        'ISR': ['israel', 'اسرائيل'],
        'EGY': ['egypt', 'مصر']
    }

    selected = [c for c,k in COUNTRY_MAP.items() if any(x in ql for x in k)]
    if not selected:
        return None, [], "Country not detected.", 0, False

    reports = []
    for c in selected:
        count = len(data[data["Adm"] == c])
        reports.append({"Adm": c, "Total": count})

    msg = " | ".join([f"{r['Adm']} has {r['Total']} records" for r in reports])
    return data, reports, msg, 100, True

# ================= MAIN FLOW =================
db = load_db()

if query and db is not None:
    st.markdown("### 🔁 Question Replay")
    play_audio(query)

    res_df, reports, msg, conf, ok = engine_v17_0(query, db)

    if ok:
        st.success(msg)
        st.metric("Confidence", f"{conf}%")
        play_audio(msg)
