import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import nest_asyncio
from difflib import get_close_matches

# ضروري جداً لحل مشكلة الـ RuntimeError
nest_asyncio.apply()

# --- 1. Flags & Dictionary ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.0.8", layout="wide")

# --- 2. Voice Function (Synchronous Wrapper) ---
def get_voice(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    # تنفيذ الـ async جوه وظيفة عادية لمنع الـ Loop Error
    async def _generate():
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    
    return asyncio.run(_generate())

# --- 3. UI Styling ---
st.markdown("""
    <style>
    .ans-card { background: white; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .flag-img { width: 120px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_db():
    for f in os.listdir('.'):
        if f.endswith('.xlsx'):
            df = pd.read_excel(f)
            df.columns = df.columns.str.strip()
            return df
    return None

db = load_db()

def engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    adms = []
    det_svc = None
    
    # Simple Matching
    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            if code in FLAGS.keys(): adms.append(code)
            elif code == 'DAB_KEY': det_svc = 'DAB'
            elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words: det_svc = 'FM'
    if not adms: return None, "EGY", 0, "Specify a country.", is_ar

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]

    found = len(res) > 0
    if is_ar:
        ans = f"تمام يا هندسة، لقيت {len(res)} سجلات في {adms[0]}." if found else f"لا يوجد سجلات لـ {adms[0]}."
    else:
        ans = f"Done. I found {len(res)} records for {adms[0]}." if found else f"No records found for {adms[0]}."
    
    return res, adms[0], 100, ans, is_ar

# --- UI Logic ---
query = st.text_input("💬 Ask Seshat (Fixed Version):")

if db is not None:
    if query:
        res_df, adm, conf, human_ans, is_arabic = engine(query, db)
        
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS.get(adm, FLAGS['EGY'])}' class='flag-img'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2></div>", unsafe_allow_html=True)
        
        if res_df is not None and not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            
            # 🔥 الحل النهائي لاستدعاء الصوت
            try:
                audio_bytes = get_voice(human_ans, is_arabic)
                st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.warning(f"Voice ready, but audio playback had a glitch: {e}")
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
else:
    st.error("Data.xlsx missing!")
