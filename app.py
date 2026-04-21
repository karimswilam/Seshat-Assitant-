import streamlit as st
import pandas as pd
import re
import subprocess
import tempfile
from rapidfuzz import process, fuzz

# ---------------- CONFIG ----------------
AR_VOICE = "voices/ar_JO-kareem-medium.onnx"
EN_VOICE = "voices/en_US-amy-medium.onnx"

FLAGS = {
    "EGY": "https://flagcdn.com/w160/eg.png",
    "ISR": "https://flagcdn.com/w160/il.png",
    "KSA": "https://flagcdn.com/w160/sa.png",
}

SYNONYMS = {
    "EGY": ["egypt", "egy", "مصر"],
    "ISR": ["israel", "isr", "اسرائيل", "إسرائيل"],
    "KSA": ["ksa", "saudi", "السعودية"],
    "FM": ["fm", "radio", "راديو"],
    "TV": ["tv", "television", "تلفزيون"],
    "ALLOT": ["allotment", "توزيع"],
    "ASSIG": ["assignment", "تخصيص"],
}

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_db():
    return pd.read_excel("Data.xlsx")

db = load_db()

# ---------------- ENGINE ----------------
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
        if not m:
            continue
        for k, v in SYNONYMS.items():
            if m in v:
                if k in FLAGS:
                    adm = k
                elif k in ["FM", "TV"]:
                    svc = k
                elif k in ["ALLOT", "ASSIG"]:
                    mode = k

    if not adm:
        return None, lang, "❌ السؤال خارج نطاق المعرفة الحالية."

    df = db[db["Adm"] == adm]

    if svc:
        df = df[df["Service"] == svc]

    if mode:
        df = df[df["Type"] == mode]

    if df.empty:
        msg = "عذراً، لا توجد نتائج مطابقة." if lang == "ar" else "Sorry, no matching records found."
        return df, lang, msg

    msg = (
        f"نعم، يوجد {len(df)} سجل مطابق لطلبك."
        if lang == "ar"
        else f"Yes, there are {len(df)} records matching your request."
    )

    return df, lang, msg

# ---------------- TTS ----------------
def speak(text, lang):
    voice = AR_VOICE if lang == "ar" else EN_VOICE
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        subprocess.run(
            ["piper", "--model", voice, "--output_file", f.name],
            input=text.encode(),
        )
        return f.name

# ---------------- UI ----------------
st.set_page_config(layout="wide", page_title="Offline Voice Assistant")

q = st.text_input("🎙 Ask (Arabic or English)")

if q:
    res, lang, answer = engine(q)

    st.markdown(f"### {answer}")

    if res is not None and not res.empty:
        st.dataframe(res, use_container_width=True)

    audio = speak(answer, lang)
    st.audio(audio)
