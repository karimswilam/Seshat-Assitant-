import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
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

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station']
}

st.set_page_config(page_title="Seshat AI v12.0.5 - Human Voice", layout="wide")

# --- 2. Advanced Human Voice Engine ---
async def generate_human_voice(text, is_arabic):
    # نختار الصوت بناءً على اللغة
    voice = "ar-EG-SalmaNeural" if is_arabic else "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    # تحويل الصوت لـ Buffer عشان يشتغل في Streamlit
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 3. UI & Logic ---
st.markdown("""
    <style>
    .flag-container { text-align: center; padding: 10px; }
    .flag-img { width: 150px; border-radius: 10px; border: 2px solid #ddd; }
    .answer-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
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

def engine_v12_5(q, data):
    q_lower = q.lower()
    is_arabic = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
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
    if not adms: return None, "EGY", 0, "Unknown Request", is_arabic

    # Filter Logic
    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    
    # Humanized Text Response
    found = len(res) > 0
    if is_arabic:
        ans_text = f"نعم يا هندسة، لقيت {len(res)} سجلات في {adms[0]}." if found else f"للاسف يا هندسة، مفيش سجلات لـ {adms[0]} في الطلب ده."
    else:
        ans_text = f"Yes, I found {len(res)} records for {adms[0]}." if found else f"No records found for {adms[0]}."

    return res, adms[0], 100, ans_text, is_arabic

# --- Main App ---
user_input = st.text_input("💬 Ask Seshat (Now with Human Voice):")

if db is not None:
    current_adm = "EGY"
    if user_input:
        res_df, current_adm, confidence, human_ans, is_ar = engine_v12_5(user_input, db)
        
        # Display Flag
        st.markdown(f"<div class='flag-container'><img src='{FLAGS[current_adm]}' class='flag-img'></div>", unsafe_allow_html=True)
        
        st.markdown(f"<div class='answer-card'><h2>{human_ans}</h2></div>", unsafe_allow_html=True)
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            st.bar_chart(res_df['Notice Type'].value_counts())
            
            # 🔥 الرهان هنا: توليد الصوت البشري
            audio_bytes = asyncio.run(generate_human_voice(human_ans, is_ar))
            st.audio(audio_bytes, format="audio/mp3")
    else:
        st.markdown(f"<div class='flag-container'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
