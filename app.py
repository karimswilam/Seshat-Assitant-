import streamlit as st
import pandas as pd
import os
import io
import re
import subprocess
from difflib import get_close_matches

# --- 1. Flags System ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

# --- 2. Master Knowledge Base ---
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

st.set_page_config(page_title="Seshat AI v12.05 - Elite Neural", layout="wide")

# --- 3. Neural Voice Engine (Natural Human Voice - NO LOOP ERROR) ---
def get_neural_voice_sync(text, is_ar):
    # استخدام أمر خارجي لضمان عدم حدوث Loop Error
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    output_file = "speech.mp3"
    # تنفيذ الأمر عبر Terminal بشكل مخفي
    cmd = f'edge-tts --voice {voice} --text "{text}" --write-media {output_file}'
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        with open(output_file, "rb") as f:
            data = f.read()
        return data
    except:
        return None

# UI Styling
st.markdown("""
    <style>
    .flag-container { text-align: center; padding: 20px; }
    .flag-img { width: 120px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .answer-box { background: #ffffff; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def elite_engine(q, data):
    q_lower = q.lower()
    is_ar = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
    words = re.findall(r'\w+', q_lower)
    adms = []; det_svc = None; filter_type = None
    
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words or 'راديو' in q_lower: det_svc = 'FM'
    if not adms: return None, "EGY", "يرجى تحديد الإدارة المطلوبة.", is_ar

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]
    
    found = len(res) > 0
    if is_ar:
        ans = f"نعم يا بشمهندس، يوجد {len(res)} سجلات في {adms[0]}." if found else f"عذراً يا بشمهندس، لا توجد نتائج لـ {adms[0]}."
    else:
        ans = f"Yes Engineer, I found {len(res)} records in {adms[0]}." if found else f"No records found for {adms[0]}."
    
    return res, adms[0], ans, is_ar

# --- UI ---
user_input = st.text_input("💬 Ask Seshat Professional:")

if db is not None:
    if user_input:
        res_df, current_adm, human_ans, is_ar = elite_engine(user_input, db)
        
        st.markdown(f"<div class='flag-container'><img src='{FLAGS[current_adm]}' class='flag-img'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='answer-box'><h3>{human_ans}</h3></div>", unsafe_allow_html=True)
        
        if res_df is not None:
            st.dataframe(res_df, use_container_width=True)
            
            # تشغيل الصوت البشري (Neural) بدون تعليق
            audio_data = get_neural_voice_sync(human_ans, is_ar)
            if audio_data:
                st.audio(audio_data, format="audio/mp3")
    else:
        st.markdown(f"<div class='flag-container'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
else:
    st.error("Missing Data.xlsx!")
