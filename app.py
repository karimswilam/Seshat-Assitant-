import streamlit as st
import numpy as np
from streamlit_mic_recorder import mic_recorder
import plotly.graph_objects as go

st.set_page_config(page_title="Mic Truth Test", layout="centered")

st.title("🎙️ Microphone Reality Check")

audio = mic_recorder(
    start_prompt="▶️ Start recording",
    stop_prompt="⏹️ Stop recording",
    format="wav",
    just_once=True
)

def analyze_audio(audio_bytes):
    if audio_bytes is None:
        return {"status": "NO_DATA", "level": 0}

    if len(audio_bytes) < 1000:
        return {"status": "EMPTY", "level": 0}

    data = np.frombuffer(audio_bytes, dtype=np.int16)

    if data.size == 0:
        return {"status": "ZERO_ARRAY", "level": 0}

    rms = np.sqrt(np.mean(data.astype(float) ** 2))
    level = int(min((rms / 32768) * 120, 100))

    if level < 5:
        return {"status": "SILENCE", "level": level}

    return {"status": "VOICE_OK", "level": level}

result = None
if audio and "bytes" in audio:
    result = analyze_audio(audio["bytes"])

st.divider()

if result is None:
    st.info("🟡 Microphone idle – press Start")
else:
    level = result["level"]

    fig = go.Figure(go.Bar(
        x=[level],
        y=["Signal"],
        orientation="h",
        marker_color="lime" if level >= 5 else "crimson",
        text=[f"{level}%"],
        textposition="inside"
    ))

    fig.update_layout(
        xaxis=dict(range=[0, 100], visible=False),
        yaxis=dict(visible=False),
        height=100,
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    status = result["status"]

    if status == "VOICE_OK":
        st.success("✅ REAL AUDIO ENTERED FROM MICROPHONE")
    elif status == "SILENCE":
        st.error("❌ Microphone opened BUT NO VOICE (silence)")
    elif status == "EMPTY":
        st.error("❌ Browser returned EMPTY audio buffer")
    elif status == "NO_DATA":
        st.error("❌ No audio data received")
    else:
        st.error("❌ Unknown mic failure")

    st.code({
        "raw_bytes_length": len(audio["bytes"]),
        "detected_level": level,
        "status": status
    })
