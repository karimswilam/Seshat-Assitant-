import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from difflib import get_close_matches

# --- 1. Flags & Knowledge Mapping ---
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
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab', 'digital sound'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station', 'digital tv']
}

st.set_page_config(page_title="Seshat AI v12.0.6 - Final Pro", layout="wide")

# --- 2. Ultra-Realistic Voice Engine ---
async def speak_human(text, is_ar):
    # اختيار أصوات Neural احترافية
    v = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    comm = edge_tts.Communicate(text, v)
    data = b""
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            data += chunk["data"]
    return data

# --- 3. Style & UI ---
st.markdown("""
    <style>
    .main { background: #f0f2f5; }
    .stTextInput > div > div > input { border-radius: 10px; border: 2px solid #1e3a8a; }
    .ans-card { background: white; padding: 25px; border-radius: 20px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .flag-img { width: 140px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 10px; }
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

def process_query(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    adms = []; det_svc = None; filter_type = None
    
    # Matching
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
    
    if 'fm' in words or 'راديو' in q_low: det_svc = 'FM'
    if not adms: return None, "EGY", 0, "Wait...", is_ar

    # Core Logic
    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    # Humanized Response Logic
    found = len(res) > 0
    if is_ar:
        prefix = "نعم يا هندسة،" if found else "للاسف يا هندسة، لا يوجد"
        ans = f"{prefix} تم العثور على {len(res)} سجلات لـ {adms[0]}."
    else:
        prefix = "Yes, sir." if found else "I'm sorry, no"
        ans = f"{prefix} {len(res)} records found for {adms[0]} based on your query."
    
    return res, adms[0], 100, ans, is_ar

# --- App Layout ---
user_input = st.text_input("📡 Ask Seshat (Professional Voice & Logic):")

if db is not None:
    current_adm = "EGY"
    if user_input:
        res_df, top_adm, conf, human_ans, is_arabic = process_query(user_input, db)
        
        # Header with Flag
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS[top_adm]}' class='flag-img'><br><h3>{top_adm} Analysis</h3></div>", unsafe_allow_html=True)
        
        # Result Card
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2><p>Confidence: {conf}%</p></div>", unsafe_allow_html=True)
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            st.bar_chart(res_df['Notice Type'].value_counts())
        
        # 🎙️ Professional Human Voice
        try:
            audio_data = asyncio.run(speak_human(human_ans, is_arabic))
            st.audio(audio_data, format="audio/mp3")
        except: pass
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
