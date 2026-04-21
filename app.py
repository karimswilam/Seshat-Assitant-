import streamlit as st
import pandas as pd
import os
import re
import tempfile
import asyncio
from difflib import get_close_matches
import edge_tts

# --- Flags ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

# --- Knowledge ---
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'ARS': ['saudi', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'تركيا'],
    'CYP': ['cyprus', 'قبرص'],
    'GRC': ['greece', 'اليونان'],
    'ISR': ['israel', 'اسرائيل'],
    'ALLOT_KEY': ['allotment', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون']
}

st.set_page_config(page_title="Seshat AI - Human Voice", layout="wide")

st.markdown("""
<style>
.main { background: #f8f9fa; }
.flag-container { text-align: center; padding: 20px; }
.flag-img { width: 120px; border-radius: 8px; }
.answer-box { background: #fff; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# --- Load DB ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

# --- Voice ---
async def generate_voice(text, lang):
    voice = "ar-EG-SalmaNeural" if lang == "ar" else "en-US-GuyNeural"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        path = fp.name

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(path)

    return path

# --- Engine ---
def elite_engine(q, data):
    q_lower = q.lower()
    is_arabic = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)

    words = re.findall(r'\w+', q_lower)
    adms = []
    det_svc = None
    filter_type = None

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]

    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS and code not in adms:
                        adms.append(code)
                    elif code == 'ALLOT_KEY':
                        filter_type = 'allot'
                    elif code == 'ASSIG_KEY':
                        filter_type = 'assig'
                    elif code == 'DAB_KEY':
                        det_svc = 'DAB'
                    elif code == 'TV_KEY':
                        det_svc = 'TV'

    if 'fm' in words:
        det_svc = 'FM'

    if not adms:
        return None, "EGY", 0, "Unknown request", is_arabic

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]

    if det_svc:
        res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]

    if filter_type == 'allot':
        res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig':
        res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    found = len(res) > 0

    if is_arabic:
        ans = f"{'نعم يوجد' if found else 'لا يوجد'} {len(res)} سجل."
    else:
        ans = f"{'Yes' if found else 'No'} {len(res)} records found."

    return res, adms[0], 90, ans, is_arabic

# --- UI ---
user_input = st.text_input("💬 Ask:")

if db is not None:
    if user_input:
        res_df, adm, conf, ans, is_ar = elite_engine(user_input, db)

        st.markdown(f"<div class='flag-container'><img src='{FLAGS[adm]}' class='flag-img'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='answer-box'><h3>{ans}</h3></div>", unsafe_allow_html=True)

        if res_df is not None and not res_df.empty:
            st.dataframe(res_df)

        # --- HUMAN VOICE ---
        try:
            lang = "ar" if is_ar else "en"
            audio_path = asyncio.run(generate_voice(ans, lang))

            audio = open(audio_path, "rb").read()
            st.audio(audio, format="audio/mp3")

        except Exception as e:
            st.error(e)

    else:
        st.info("Enter your query")
else:
    st.error("No Excel file found")
