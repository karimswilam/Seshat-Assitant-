import streamlit as st
import pandas as pd
import re
import subprocess
import tempfile
import os
from rapidfuzz import process, fuzz

# --- 1. CONFIG (حافظت على مساراتك) ---
# ملحوظة: تأكد من وجود ملفات الـ .onnx في فولدر voices بجانب الكود
AR_VOICE = "voices/ar_JO-kareem-medium.onnx"
EN_VOICE = "voices/en_US-amy-medium.onnx"

FLAGS = {
    "EGY": "https://flagcdn.com/w160/eg.png",
    "ISR": "https://flagcdn.com/w160/il.png",
    "KSA": "https://flagcdn.com/w160/sa.png",
}

SYNONYMS = {
    "EGY": ["egypt", "egy", "مصر", "المصرية"],
    "ISR": ["israel", "isr", "اسرائيل", "إسرائيل"],
    "KSA": ["ksa", "saudi", "السعودية", "المملكة"],
    "FM": ["fm", "radio", "راديو", "اف ام"],
    "TV": ["tv", "television", "تلفزيون", "مرئي"],
    "ALLOT": ["allotment", "توزيع"],
    "ASSIG": ["assignment", "تخصيص"],
}

# --- 2. LOAD DATA ---
@st.cache_data
def load_db():
    # تأكد من وجود ملف Data.xlsx
    return pd.read_excel("Data.xlsx")

db = load_db()

# --- 3. THE ENGINE (تطوير منطق الـ Fuzzy الخاص بك) ---
def detect_language(text):
    return "ar" if re.search(r"[أ-ي]", text) else "en"

def match_keyword(word):
    keys = [k for v in SYNONYMS.values() for k in v]
    match = process.extractOne(word, keys, scorer=fuzz.partial_ratio, score_cutoff=85)
    return match[0] if match else None

def engine(question):
    lang = detect_language(question)
    words = re.findall(r"\w+", question.lower())
    adm = svc = mode = None

    for w in words:
        m = match_keyword(w)
        if not m: continue
        for k, v in SYNONYMS.items():
            if m in v:
                if k in FLAGS: adm = k
                elif k in ["FM", "TV"]: svc = k
                elif k in ["ALLOT", "ASSIG"]: mode = k

    if not adm:
        return None, "EGY", lang, "❌ السؤال خارج نطاق المعرفة الحالية.", 0

    df = db[db["Adm"] == adm]
    if svc: df = df[df.get("Service", "") == svc]
    if mode: df = df[df.get("Type", "") == mode]

    if df.empty:
        msg = "عذراً، لا توجد نتائج مطابقة." if lang == "ar" else "Sorry, no matching records found."
        return df, adm, lang, msg, 50

    msg = f"نعم يا هندسة، يوجد {len(df)} سجل لـ {adm}." if lang == "ar" else f"Yes, I found {len(res)} records for {adm}."
    return df, adm, lang, msg, 100

# --- 4. TTS (نظام Piper الـ Offline) ---
def speak(text, lang):
    voice = AR_VOICE if lang == "ar" else EN_VOICE
    # التأكد من وجود ملف الموديل قبل التشغيل
    if not os.path.exists(voice):
        return None
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        try:
            # تشغيل Piper كـ Process خارجي (أسرع طريقة)
            subprocess.run(
                ["piper", "--model", voice, "--output_file", f.name],
                input=text.encode(),
                check=True
            )
            return f.name
        except:
            return None

# --- 5. UI (إعادة الـ Dashboard المفقود على أساس كودك) ---
st.set_page_config(layout="wide", page_title="Seshat AI v12.5.0")

st.title("🛰️ Seshat Intelligence Assistant")
q = st.text_input("🎙 اسأل (عربي أو English):")

if q:
    res, adm, lang, answer, conf = engine(q)

    # Dashboard Row
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.image(FLAGS.get(adm, FLAGS["EGY"]), width=150)
    with col2:
        st.markdown(f"### {answer}")
    with col3:
        st.metric("Confidence", f"{conf}%")
        st.progress(conf)

    st.divider()

    if res is not None and not res.empty:
        st.dataframe(res, use_container_width=True)

        # Voice Trigger
        with st.spinner("🔊 Generating Offline Voice..."):
            audio_path = speak(answer, lang)
            if audio_path:
                st.audio(audio_path)
            else:
                st.warning("Model files (.onnx) not found in /voices folder.")
