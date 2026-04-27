import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import speech_recognition as sr
import time
import re
import tempfile

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Voice Data Assistant", layout="centered")
DATA_PATH = "data.xlsx"

# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_data(path):
    return pd.read_excel(path)

df = load_data(DATA_PATH)

# ----------------------------
# NOTICE TYPE LOGIC
# ----------------------------
NOTICE_MAP = {
    "GS1": {"service": "DAB", "type": "Assignment"},
    "GS2": {"service": "DAB", "type": "Allotment"},
    "DS1": {"service": "DAB", "type": "Assignment"},
    "DS2": {"service": "DAB", "type": "Allotment"},
    "GT1": {"service": "TV", "type": "Assignment"},
    "GT2": {"service": "TV", "type": "Allotment"},
    "DT1": {"service": "TV", "type": "Assignment"},
    "DT2": {"service": "TV", "type": "Allotment"},
}

# ----------------------------
# SYNONYMS
# ----------------------------
COUNTRIES = {
    "TUR": ["turkey", "turkiye", "türkiye", "تركيا"],
    "EGY": ["egypt", "masr", "misr", "مصر"],
    "ISR": ["israel", "إسرائيل"],
    "SAU": ["saudi", "ksa", "السعودية"]
}

# ----------------------------
# NLP (Zero Intelligence)
# ----------------------------
def detect_language(text):
    ar = re.search(r'[ء-ي]', text)
    en = re.search(r'[a-zA-Z]', text)
    if ar and not en:
        return "ar"
    if en and not ar:
        return "en"
    return "mix"

def extract_country(text):
    t = text.lower()
    for code, aliases in COUNTRIES.items():
        for a in aliases:
            if a in t:
                return code
    return None

def extract_service(text):
    t = text.lower()
    if "dab" in t or "إذاع" in t:
        return "DAB"
    if "tv" in t or "television" in t or "تلفزيون" in t:
        return "TV"
    return None

def extract_type(text):
    t = text.lower()
    if "assignment" in t or "تخصيص" in t:
        return "Assignment"
    if "allotment" in t or "توزيع" in t:
        return "Allotment"
    return None

# ----------------------------
# UI
# ----------------------------
st.title("🎙️ Voice Assistant (Upload Audio)")
st.write("✅ Arabic OR English only")

uploaded_audio = st.file_uploader(
    "Upload voice file (wav / mp3)", type=["wav", "mp3"]
)

progress = st.progress(0)
status = st.empty()

if uploaded_audio:
    status.text("Processing audio...")
    progress.progress(20)

    # Save temp audio
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_audio.read())
        audio_path = tmp.name

    recognizer = sr.Recognizer()

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    progress.progress(50)

    try:
        text = recognizer.recognize_google(audio)
    except:
        st.error("❌ Could not recognize speech")
        st.stop()

    st.subheader("📝 Transcribed Text")
    st.write(text)

    lang = detect_language(text)
    if lang == "mix":
        st.error("Please input voice in Arabic OR English (no mix)")
        st.stop()

    progress.progress(70)
    status.text("Analyzing query...")

    country = extract_country(text)
    service = extract_service(text)
    qtype = extract_type(text)

    score = sum([country is not None, service is not None, qtype is not None])
    confidence = int((score / 3) * 100)

    valid_notices = [
        k for k, v in NOTICE_MAP.items()
        if v["service"] == service and v["type"] == qtype
    ]

    result_df = df.copy()

    if country:
        result_df = result_df[result_df["Administration"] == country]

    if valid_notices:
        result_df = result_df[result_df["Notice Type"].isin(valid_notices)]

    count = len(result_df)

    progress.progress(100)
    status.text("✅ Done")

    st.subheader("✅ Answer")
    st.write(f"{country} has **{count} {qtype} {service} records**")
    st.info(f"Confidence: {confidence}%")

    st.subheader("📊 Distribution")
    chart_data = result_df["Notice Type"].value_counts()

    fig, ax = plt.subplots()
    chart_data.plot(kind="bar", ax=ax)
    ax.set_ylabel("Count")
    ax.set_xlabel("Notice Type")

    st.pyplot(fig)
