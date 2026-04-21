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

# 1. تفعيل nest_asyncio لمنع الـ Runtime Errors في Streamlit
nest_asyncio.apply()

# --- 2. Flags & Knowledge Mapping ---
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

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'السعودية', 'ksa', 'ars'],
    'TUR': ['turkey', 'تركيا'],
    'GRC': ['greece', 'اليونان'],
    'ISR': ['israel', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'],
    'TV_KEY': ['tv', 'تلفزيون']
}

st.set_page_config(page_title="Seshat AI v12.0.9", layout="wide")

# --- 3. Neural Voice Engine (Salma & Guy) ---
async def generate_neural_audio(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
    st.markdown(md, unsafe_allow_html=True)

# --- 4. Intelligent Response Generator ---
def get_dynamic_response(count, adm, is_ar):
    if is_ar:
        options = [
            f"تحليلي لبيانات {adm} أظهر وجود {count} سجلات مطابقة.",
            f"بالنسبة لطلبك، قاعدة بيانات {adm} تحتوي حالياً على {count} مدخلات.",
            f"تم رصد {count} نتيجة تخص {adm} بناءً على المعايير المحددة."
        ]
    else:
        options = [
            f"My analysis shows {count} matching records for {adm}.",
            f"For your request, the {adm} database currently contains {count} entries.",
            f"I have identified {count} results for {adm} based on the specified criteria."
        ]
    return random.choice(options)

# --- 5. Data Processing ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    if files:
        df = pd.read_excel(files[0])
        df.columns = df.columns.str.strip()
        return df
    return None

def main_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    adms = []; det_svc = None; filter_type = None

    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            if code in FLAGS.keys(): adms.append(code)
            elif code == 'ALLOT_KEY': filter_type = 'allot'
            elif code == 'ASSIG_KEY': filter_type = 'assig'
            elif code == 'DAB_KEY': det_svc = 'DAB'
            elif code == 'TV_KEY': det_svc = 'TV'
    
    if not adms: return None, "EGY", "Please specify a country.", is_ar, 0

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    ans = get_dynamic_response(len(res), adms[0], is_ar)
    return res, adms[0], ans, is_ar, 100

# --- 6. UI Rendering ---
db = load_db()
query = st.text_input("💬 Ask Seshat (Neural Dynamic Voice Mode):")

if db is not None:
    if query:
        res_df, adm_code, response_text, is_arabic, confidence = main_engine(query, db)
        
        # Dashboard Style (v12.04 Heritage)
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(FLAGS.get(adm_code, FLAGS['EGY']), width=120)
            st.metric("Confidence", f"{confidence}%")
        with col2:
            st.markdown(f"### {response_text}")

        if res_df is not None:
            st.dataframe(res_df, use_container_width=True)
            
            # Voice Execution (The Fix)
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                audio_content = new_loop.run_until_complete(generate_neural_audio(response_text, is_arabic))
                autoplay_audio(audio_content)
            except Exception as e:
                st.error(f"Voice engine error: {e}")
    else:
        st.info("Waiting for your professional inquiry...")
else:
    st.error("Data file not found. Please ensure your Excel file is in the root directory.")
