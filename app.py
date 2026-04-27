import os
import re
 # -----------------------------import time
    # OUTPUT
    # -----------------------------
    st.subheader("✅ Answer")
    st.write(
        f"**{country} has {count} {qtype} {service} records.**"
    )

    st.info(f"Confidence: {confidence}%")

    st.subheader("📊 Distribution")
    chart_data = result_df["Notice Type"].value_counts()

    if not chart_data.empty:
        fig, ax = plt.subplots()
        chart_data.plot(kind="bar", ax=ax)
        ax.set_ylabel("Count")
        ax.set_xlabel("Notice Type")
        st.pyplot(fig)
    else:
        st.write("No data to display.")
``
import tempfile

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import speech_recognition as sr

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Voice Assistant Prototype",
    layout="centered"
)

st.title("🎙️ Voice Assistant – Prototype (Stage 1)")
st.write("Arabic OR English only • Audio upload (wav / mp3)")

# -----------------------------
# CHECK DATA FILE
# -----------------------------
DATA_FILE = "data.xlsx"

if not os.path.exists(DATA_FILE):
    st.error(
        "❌ data.xlsx file not found.\n\n"
        "Please make sure `data.xlsx` is in the same folder as `app.py`."
    )
    st.stop()

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data(path):
    return pd.read_excel(path)

df = load_data(DATA_FILE)

# -----------------------------
# NOTICE TYPE MAP
# -----------------------------
NOTICE_MAP = {
    "GS1": ("DAB", "Assignment"),
    "GS2": ("DAB", "Allotment"),
    "DS1": ("DAB", "Assignment"),
    "DS2": ("DAB", "Allotment"),
    "GT1": ("TV",  "Assignment"),
    "GT2": ("TV",  "Allotment"),
    "DT1": ("TV",  "Assignment"),
    "DT2": ("TV",  "Allotment"),
}

# -----------------------------
# COUNTRY SYNONYMS
# -----------------------------
COUNTRIES = {
    "TUR": ["turkey", "turkiye", "türkiye", "تركيا"],
    "EGY": ["egypt", "masr", "misr", "مصر"],
    "ISR": ["israel", "إسرائيل"],
    "SAU": ["saudi", "ksa", "السعودية"]
}

# -----------------------------
# SIMPLE NLP (ZERO INTELLIGENCE)
# -----------------------------
def detect_language(text):
    ar = re.search(r"[ء-ي]", text)
    en = re.search(r"[a-zA-Z]", text)
    if ar and not en:
        return "ar"
    if en and not ar:
        return "en"
    return "mix"

def extract_country(text):
    t = text.lower()
    for code, names in COUNTRIES.items():
        for n in names:
            if n in t:
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

# -----------------------------
# UI – AUDIO UPLOAD
# -----------------------------
audio_file = st.file_uploader(
    "Upload your voice question (wav / mp3)",
    type=["wav", "mp3"]
)

progress = st.progress(0)
status = st.empty()

# -----------------------------
# PROCESS AUDIO
# -----------------------------
if audio_file:
    progress.progress(10)
    status.text("Processing audio...")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(audio_file.read())
        audio_path = tmp.name

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
    except Exception as e:
        st.error("❌ Could not recognize the audio.")
        st.stop()

    progress.progress(40)

    st.subheader("📝 Transcribed Text")
    st.write(text)

    lang = detect_language(text)
    if lang == "mix":
        st.error("Please speak Arabic OR English only (no mix).")
        st.stop()

    progress.progress(60)
    status.text("Analyzing question...")

    country = extract_country(text)
    service = extract_service(text)
    qtype = extract_type(text)

    confidence = int(
        (sum([
            country is not None,
            service is not None,
            qtype is not None
        ]) / 3) * 100
    )

    # -----------------------------
    # FILTER DATA
    # -----------------------------
    result_df = df.copy()

    if country:
        result_df = result_df[result_df["Administration"] == country]

    valid_notice_types = [
        k for k, v in NOTICE_MAP.items()
        if v[0] == service and v[1] == qtype
    ]

    if valid_notice_types:
        result_df = result_df[result_df["Notice Type"].isin(valid_notice_types)]

    count = len(result_df)

    progress.progress(100)
    status.text("✅ Done")

