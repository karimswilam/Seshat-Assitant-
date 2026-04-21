import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
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
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'سعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 't-dab'],
    'TV_KEY': ['tv', 'تلفزيون', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.0.5 - Analytical Edition", layout="wide")

# CSS (نفس الستايل بتاعك مع تحسين عرض المقارنة)
st.markdown("""
    <style>
    .flag-img { width: 100px; border-radius: 8px; margin: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .answer-box { background: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #1e3a8a; margin-bottom: 20px; }
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

def analytical_engine(q, data):
    q_lower = q.lower()
    is_arabic = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
    words = re.findall(r'\w+', q_lower)
    
    adms = []; det_svc = None; filter_type = None; exclude_code = None
    
    # 1. Detection Logic
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for i, word in enumerate(words):
        # الاستثناء (Except/ما عدا)
        if word in ['except', 'ماعدا', 'بدون', 'without'] and i+1 < len(words):
            exclude_code = words[i+1].upper()
            
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
    if not adms: return None, ["EGY"], 0, "Unknown", is_arabic

    # 2. Advanced Filtering
    res = data[data['Adm'].isin(adms)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]
    if exclude_code: res = res[res['Notice Type'] != exclude_code]

    # 3. Calculation & Comparison Text
    stats = res.groupby('Adm').size().to_dict()
    ans_parts = []
    for adm in adms:
        count = stats.get(adm, 0)
        if is_arabic: ans_parts.append(f"{count} سجل لـ {adm}")
        else: ans_parts.append(f"{count} records for {adm}")
    
    summary = " | ".join(ans_parts)
    human_ans = f"التحليل: {summary}" if is_arabic else f"Analysis: {summary}"
    
    return res, adms, 100, human_ans, is_arabic

# --- UI ---
user_input = st.text_input("💬 Ask Analytical Seshat:", placeholder="Compare EGY and ARS DAB assignments")

if db is not None and user_input:
    res_df, current_adms, confidence, human_ans, is_ar = analytical_engine(user_input, db)
    
    # Display Flags for all detected countries
    cols = st.columns(len(current_adms))
    for idx, adm in enumerate(current_adms):
        cols[idx].image(FLAGS.get(adm), width=100, caption=adm)
    
    st.markdown(f"<div class='answer-box'><h3>{human_ans}</h3><p>Confidence: {confidence}%</p></div>", unsafe_allow_html=True)
    
    if not res_df.empty:
        c1, c2 = st.columns([1, 2])
        c1.metric("Total Match", len(res_df))
        c2.bar_chart(res_df.groupby('Adm').size())
        
        st.dataframe(res_df, use_container_width=True)
        
        # Voice Assistant
        try:
            tts = gTTS(text=human_ans, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
