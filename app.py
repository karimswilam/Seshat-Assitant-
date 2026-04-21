import streamlit as st
import pandas as pd
import re
from gtts import gTTS
import io
from rapidfuzz import process, fuzz

# --- 1. CONFIG & UI ---
st.set_page_config(layout="wide", page_title="Seshat AI - Stable")

FLAGS = {
    "EGY": "https://flagcdn.com/w160/eg.png",
    "ISR": "https://flagcdn.com/w160/il.png",
    "KSA": "https://flagcdn.com/w160/sa.png",
}

SYNONYMS = {
    "EGY": ["egypt", "egy", "مصر", "المصرية"],
    "ISR": ["israel", "isr", "اسرائيل", "إسرائيل"],
    "KSA": ["ksa", "saudi", "السعودية", "المملكة", "ars"],
    "FM": ["fm", "radio", "راديو"],
    "TV": ["tv", "television", "تلفزيون"],
}

# --- 2. ENGINE (Fuzzy Logic) ---
@st.cache_data
def load_db():
    return pd.read_excel("Data.xlsx")

def engine(question, db):
    is_ar = bool(re.search(r"[أ-ي]", question))
    words = re.findall(r"\w+", question.lower())
    adm = None
    
    # استخدام منطق الـ Fuzzy اللي إنت عملته
    keys = [k for v in SYNONYMS.values() for k in v]
    for w in words:
        match = process.extractOne(w, keys, scorer=fuzz.partial_ratio, score_cutoff=85)
        if match:
            for k, v in SYNONYMS.items():
                if match[0] in v and k in FLAGS: adm = k

    if not adm:
        return None, "EGY", "السؤال خارج النطاق حالياً" if is_ar else "Out of scope", 0

    res = db[db["Adm"] == adm]
    msg = f"لقيت {len(res)} سجل لـ {adm}" if is_ar else f"Found {len(res)} records for {adm}"
    return res, adm, msg, 100

# --- 3. UI EXECUTION ---
db = load_db()
q = st.text_input("🎙 Ask Seshat:")

if q:
    res, adm, answer, conf = engine(q, db)
    
    # Dashboard (البرستيج اللي بنبني فيه)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1: st.image(FLAGS[adm], width=120)
    with c2: st.subheader(answer)
    with c3: 
        st.metric("Confidence", f"{conf}%")
        st.progress(conf)

    if res is not None:
        st.dataframe(res, use_container_width=True)
        
        # الصوت (Stable & Cloud Friendly)
        tts = gTTS(text=answer, lang='ar' if bool(re.search(r"[أ-ي]", answer)) else 'en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp)
