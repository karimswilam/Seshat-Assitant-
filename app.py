import streamlit as st
import pandas as pd
import os
import re
import asyncio
import base64
import random
import nest_asyncio
from edge_tts import Communicate
from difflib import get_close_matches

# تفعيل الـ Async جوه Streamlit
nest_asyncio.apply()

# --- 1. Settings & UI Style ---
st.set_page_config(page_title="Seshat AI - Professional Edition", layout="wide")
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .answer-card { background: white; padding: 20px; border-left: 5px solid #1E3A8A; border-radius: 8px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ksa', 'السعودية', 'ars'],
    'TUR': ['turkey', 'تركيا'],
    'ALLOT_KEY': ['allotment', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون']
}

# --- 2. Neural Voice Engine ---
async def generate_voice(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def play_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
    st.markdown(md, unsafe_allow_html=True)

# --- 3. Core Engine (دمج منطق بحثك) ---
def smart_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    adms = []; det_svc = None; filter_type = None
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]

    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
    
    target_adm = adms[0] if adms else "EGY"
    res = data[data['Adm'].astype(str).str.contains(target_adm, na=False)]
    
    ans = f"تمام يا هندسة، لقيت {len(res)} سجل لإدارة {target_adm}." if is_ar else f"Found {len(res)} records for {target_adm}."
    return res, target_adm, ans, is_ar

# --- 4. Main UI ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    return pd.read_excel(files[0]) if files else None

db = load_db()
st.title("🛰️ Seshat AI v12.1.5")
query = st.text_input("💬 اسأل المساعد الذكي:")

if db is not None and query:
    res_df, adm, ans, is_ar = smart_engine(query, db)
    
    # Dashboard
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.image(FLAGS.get(adm), width=120)
    with col2:
        st.markdown(f"<div class='answer-card'><h3>{ans}</h3></div>", unsafe_allow_html=True)
    with col3:
        st.metric("Confidence", "100%")
        st.progress(100)

    st.dataframe(res_df, use_container_width=True)

    # Voice Execution
    with st.spinner("🔊 Generating Voice..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_voice(ans, is_ar))
        play_audio(audio)
