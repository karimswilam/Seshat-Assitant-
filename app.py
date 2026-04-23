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
# 🎙️ LIVE AUDIO METER
# =========================
def get_audio_level(duration=0.3, fs=44100):
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        sd.wait()
        amplitude = np.linalg.norm(recording) / len(recording)
        db = 20 * np.log10(amplitude + 1e-6)
        return max(min((db + 60) / 60, 1), 0)  # normalize 0 → 1
    except:
        return 0


def render_audio_meter(level):
    bar_html = f"""
    <div style="width:100%; background:#222; border-radius:10px; padding:5px;">
        <div style="width:{int(level*100)}%; height:20px; 
                    background:linear-gradient(90deg, #22c55e, #eab308, #ef4444);
                    border-radius:10px; transition: width 0.2s;">
        </div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)


# =========================
# 🎙️ SPEECH TO TEXT (WEB API)
# =========================
def speech_to_text(audio_bytes):
    import requests
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "gpt-4o-mini-transcribe"}
        )
        return response.json().get("text", "")
    except:
        return ""


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

st.title("🎙️ Voice Assistant Mode")

# ===== MIC RECORDER =====
audio = mic_recorder(
    start_prompt="🎤 Start Recording",
    stop_prompt="⏹ Stop",
    key="recorder"
)

# ===== LIVE METER =====
st.markdown("### 🔊 Mic Signal Level")
level = get_audio_level()
render_audio_meter(level)

if level < 0.05:
    st.warning("⚠️ No voice detected from microphone")

# ===== PROCESS AUDIO =====
if audio:
    st.success("✅ Voice captured, processing...")

    text = speech_to_text(audio['bytes'])

    if not text.strip():
        st.error("❌ No speech detected (empty audio)")
    else:
        st.success(f"📝 Recognized Text: {text}")

        query = text

        # =========================
        # YOUR ORIGINAL ENGINE
        # =========================

        FLAGS = {
            'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
            'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
            'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
        }

        COUNTRY_DISPLAY = {
            'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
            'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
            'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
            'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
            'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
            'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
        }

        STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
        STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

        COUNTRY_MAP = {
            'EGY': ['egypt', 'egy', 'مصر'],
            'ARS': ['saudi', 'ksa', 'السعودية'],
            'TUR': ['turkey', 'تركيا'],
            'CYP': ['cyprus', 'قبرص'],
            'GRC': ['greece', 'اليونان'],
            'ISR': ['israel', 'اسرائيل']
        }

        SYNONYMS = {
            'TOTAL_KEY': ['total', 'اجمالي'],
            'FM_KEY': ['fm', 'radio'],
        }

        @st.cache_data
        def load_db():
            files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
            if files:
                return pd.read_excel(files[0])
            return None

        db = load_db()

        def simple_engine(q, df):
            q = q.lower()
            selected = [k for k, v in COUNTRY_MAP.items() if any(x in q for x in v)]
            if not selected:
                return None, "❌ Could not detect country"

            df = df[df['Adm'].isin(selected)]
            return df, f"✅ Found {len(df)} records"

        if db is not None:
            res_df, msg = simple_engine(query, db)

            st.markdown("### 🔊 Assistant Response")
            st.success(msg)

            if res_df is not None:
                st.dataframe(res_df)

        else:
            st.error("❌ No database found")

# ===== TEXT FALLBACK =====
st.divider()
query_text = st.text_input("⌨️ Or type your question")

if query_text:
    st.info(f"Typed: {query_text}")
