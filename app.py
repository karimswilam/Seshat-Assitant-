import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import speech_recognition as sr
import time
import re

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
# NOTICE TYPE DICTIONARY
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
# COUNTRY SYNONYMS
# ----------------------------
COUNTRIES = {
    "turkey": ["turkey", "türkiye", "turkiye", "تركيا"],
    "egypt": ["egypt", "masr", "misr", "مصر"],
    "israel": ["israel", "إسرائيل"],
    "saudi arabia": ["saudi", "ksa", "السعودية", "المملكة"]
}

# ----------------------------
# TEXT PARSING
# ----------------------------
def detect_language(text):
    if re.search(r'[a-zA-Z]', text) and not re.search(r'[ء-ي]', text):
        return "en"
    if re.search(r'[ء-ي]', text) and not re.search(r'[a-zA-Z]', text):
        return "ar"
    return "mix"

def extract_country(text):
    text = text.lower()
    for country, aliases in COUNTRIES.items():
        for a in aliases:
            if a in text:
                return country.upper()
    return None

def extract_service(text):
    text = text.lower()
    if "dab" in text or "إذاعي" in text or "اذاعة" in text:
        return "DAB"
    if "tv" in text or "television" in text or "تلفزيون" in text:
        return "TV"
    return None

def extract_type(text):
    text = text.lower()
    if "assignment" in text or "تخصيص" in text:
        return "Assignment"
    if "allotment" in text or "توزيع" in text:
        return "Allotment"
    return None

# ----------------------------
# VOICE INPUT
# ----------------------------
def record_voice():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)

    return audio

def speech_to_text(audio):
    r = sr.Recognizer()
    try:
        text = r.recognize_google(audio)
        return text
    except:
        return ""

# ----------------------------
# UI
# ----------------------------
st.title("🎙️ Voice Assistant for Broadcasting Data")

st.write("Ask in **Arabic or English only**. No mix.")

audio_level = st.progress(0)
process_bar = st.progress(0)
status = st.empty()

if st.button("🎤 Start Recording"):
    status.text("Listening...")
    audio_level.progress(30)

    audio = record_voice()
    audio_level.progress(80)

    process_bar.progress(20)
    status.text("Processing voice input...")

    time.sleep(0.5)

    text = speech_to_text(audio)
    process_bar.progress(40)

    st.subheader("📝 Transcribed Text")
    st.write(text if text else "❌ No speech detected")

    if not text:
        st.stop()

    lang = detect_language(text)
    if lang == "mix":
        st.error("Please input voice in Arabic OR English (no mix).")
        st.stop()

    country = extract_country(text)
    service = extract_service(text)
    qtype = extract_type(text)

    score = sum([country is not None, service is not None, qtype is not None])
    confidence = int((score / 3) * 100)

    process_bar.progress(60)
    status.text("Querying data...")

    time.sleep(0.5)

    # Filter Notice Types
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

    process_bar.progress(90)
    status.text("Generating output...")

    time.sleep(0.5)
    process_bar.progress(100)
    status.text("✅ Done")

    st.subheader("✅ Answer")
    st.write(
        f"{country} has **{count} {qtype} {service} records**."
    )

    st.info(f"Confidence: {confidence}%")

    # ----------------------------
    # BAR CHART
    # ----------------------------
    st.subheader("📊 Statistics")

    chart_df = result_df["Notice Type"].value_counts()

    fig, ax = plt.subplots()
    chart_df.plot(kind="bar", ax=ax)
    ax.set_ylabel("Count")
    ax.set_xlabel("Notice Type")
    ax.set_title("Distribution")

    st.pyplot(fig)
