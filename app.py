import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import base64
import random
from edge_tts import Communicate
from difflib import get_close_matches

# --- 1. Flags & Master Data ---
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
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.0.6", layout="wide")

# --- 2. Intelligent Neural Voice Engine ---
async def get_neural_audio(text, is_ar):
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

# --- 3. Dynamic Response Generator (Anti-Fixed Sentences) ---
def generate_dynamic_answer(count, adm_name, is_ar):
    if is_ar:
        templates = [
            f"تم العثور على {count} سجلات في قاعدة بيانات {adm_name}.",
            f"بالنسبة لـ {adm_name}، فإجمالي السجلات المتاحة هو {count}.",
            f"موجود حالياً {count} بيان خاص بطلبك في ملفات {adm_name}.",
            f"النتيجة لـ {adm_name} هي {count} سجل مطابق."
        ]
    else:
        templates = [
            f"Found {count} records in {adm_name} database.",
            f"For {adm_name}, there are a total of {count} entries.",
            f"Currently, there are {count} records matching your query for {adm_name}.",
            f"The result for {adm_name} shows {count} matching files."
        ]
    return random.choice(templates)

# --- 4. Main Engine ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    if files:
        df = pd.read_excel(files[0])
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def intelligent_engine(q, data):
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
    
    if 'fm' in words: det_svc = 'FM'
    if not adms: return None, "EGY", "Please specify the administration.", is_ar, 0

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    dynamic_ans = generate_dynamic_answer(len(res), adms[0], is_ar)
    return res, adms[0], dynamic_ans, is_ar, 100

# --- UI Execution ---
st.title("🛰️ Seshat AI v12.0.6 - Neural Era")
query = st.text_input("Ask Seshat (Dynamic Voice Mode):")

if db is not None:
    if query:
        res_df, adm, ans, is_ar, conf = intelligent_engine(query, db)
        
        # Dashboard 12.04 Style
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(FLAGS.get(adm, FLAGS['EGY']), width=150)
            st.metric("Confidence", f"{conf}%")
        with col2:
            st.subheader(ans)
            st.write(f"**Records Found:** {len(res_df) if res_df is not None else 0}")

        if res_df is not None:
            st.dataframe(res_df, use_container_width=True)
            # Neural Voice Execution
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio = loop.run_until_complete(get_neural_audio(ans, is_ar))
            autoplay_audio(audio)
    else:
        st.info("Waiting for your professional inquiry...")
else:
    st.error("Data.xlsx not found.")
