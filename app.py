import streamlit as st
import pandas as pd
import os
import re
import random
import subprocess
import base64
from difflib import get_close_matches

# --- 1. Flags & Core Data ---
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
    'ARS': ['saudi', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'تركيا'],
    'GRC': ['greece', 'اليونان'],
    'ISR': ['israel', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'],
    'TV_KEY': ['tv', 'تلفزيون']
}

st.set_page_config(page_title="Seshat AI v12.0.7", layout="wide")

# --- 2. Neural Voice Engine (The Smart Way) ---
def generate_neural_voice(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    output_file = "voice_temp.mp3"
    # تشغيل محرك Neural AI خارجي لضمان عدم حدوث Loop Error
    command = f'edge-tts --voice {voice} --text "{text}" --write-media {output_file}'
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True)
        with open(output_file, "rb") as f:
            data = f.read()
        return data
    except:
        return None

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
    st.markdown(md, unsafe_allow_html=True)

# --- 3. Professional Response Logic ---
def get_dynamic_response(count, adm, is_ar):
    if is_ar:
        phrases = [
            f"بناءً على طلبك، تم رصد {count} سجلات تابعة لإدارة {adm}.",
            f"إجمالي النتائج المطابقة لإدارة {adm} هو {count} سجل حالياً.",
            f"تحليلي للبيانات أظهر وجود {count} مدخلات تخص {adm}."
        ]
    else:
        phrases = [
            f"Based on your query, I found {count} matching records for {adm}.",
            f"The current count for {adm} administration is {count} records.",
            f"Data analysis reveals {count} entries matching your criteria for {adm}."
        ]
    return random.choice(phrases)

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    if files:
        df = pd.read_excel(files[0])
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def engine_v12_07(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    adms = []; det_svc = None; filter_type = None

    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            if code in FLAGS.keys(): adms.append(code)
            elif code == 'ALLOT_KEY': filter_type = 'allot'
            elif code == 'ASSIG_KEY': filter_type = 'assig'
            elif code == 'DAB_KEY': det_svc = 'DAB'
            elif code == 'TV_KEY': det_svc = 'TV'
    
    if not adms: return None, "EGY", "يرجى تحديد الإدارة المطلوبة بدقة.", is_ar, 0

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    
    ans = get_dynamic_response(len(res), adms[0], is_ar)
    return res, adms[0], ans, is_ar, 100

# --- 4. UI ---
query = st.text_input("💬 Ask Seshat (Neural Dynamic Voice):")

if db is not None:
    if query:
        res_df, adm, ans, is_ar, conf = engine_v12_07(query, db)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(FLAGS.get(adm), width=120)
            st.metric("Confidence", f"{conf}%")
        with col2:
            st.markdown(f"### {ans}")

        if res_df is not None:
            st.dataframe(res_df, use_container_width=True)
            # توليد الصوت البشري بدون أي مشاكل في الـ Loop
            audio_data = generate_neural_voice(ans, is_ar)
            if audio_data:
                autoplay_audio(audio_data)
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' style='width:120px;'></div>", unsafe_allow_html=True)
else:
    st.error("Missing Data.xlsx")
