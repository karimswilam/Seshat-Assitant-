import streamlit as st
import pandas as pd
import os
import io
import re
import base64
from gtts import gTTS
from difflib import get_close_matches

# --- 1. Flags System (Base64 Vectors for speed & offline reliability) ---
# ملاحظة: دي عينات SVG صغيرة جداً وسريعة التحميل
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
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab', 'digital sound'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station', 'digital tv']
}

st.set_page_config(page_title="Seshat AI v12.0.4 - Elite Edition", layout="wide")

# CSS لإخراج مظهر الـ Dashboard الاحترافي
st.markdown("""
    <style>
    .main { background: #f8f9fa; }
    .flag-container { text-align: center; padding: 20px; }
    .flag-img { width: 120px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .answer-box { background: #ffffff; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; }
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
    is_boolean = any(x in q_lower for x in ['does', 'is ', 'هل', 'موجود'])
    is_arabic = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
    
    words = re.findall(r'\w+', q_lower)
    adms = []; det_svc = None; filter_type = None; exclude_codes = []
    
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
    
    if 'fm' in words or 'راديو' in q_lower: det_svc = 'FM'

    if not adms: return None, "EGY", 0, "Unknown Request", is_arabic

    # Core Filtering
    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]
    
    # Building the Humanized Answer
    found = len(res) > 0
    if is_arabic:
        ans_prefix = "نعم، يوجد" if found else "عذراً، لا يوجد"
        ans_text = f"{ans_prefix} {len(res)} سجلات مطابقة لطلبك في {adms[0]}."
    else:
        ans_prefix = "Yes, there are" if found else "No, there are no"
        ans_text = f"{ans_prefix} {len(res)} records found for your request in {adms[0]}."
    
    conf = 100 if (det_svc and filter_type) else 85
    return res, adms[0], conf, ans_text, is_arabic

# --- UI Layout ---
user_input = st.text_input("💬 Ask Seshat (Arabic or English):", placeholder="Does Israel have FM assignments?")

if db is not None:
    current_adm = "EGY"
    if user_input:
        res_df, current_adm, confidence, human_ans, is_ar = elite_engine(user_input, db)
        
        # Display Flag
        flag_url = FLAGS.get(current_adm)
        st.markdown(f"<div class='flag-container'><img src='{flag_url}' class='flag-img'></div>", unsafe_allow_html=True)
        
        # Display Answer
        st.markdown(f"<div class='answer-box'><h3>{human_ans}</h3><p>Engine Confidence: {confidence}%</p></div>", unsafe_allow_html=True)
        
        if not res_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1: st.metric("Count", len(res_df))
            with c2: st.bar_chart(res_df['Notice Type'].value_counts())
            st.dataframe(res_df, use_container_width=True)
            
            # Professional Voice Output
            try:
                lang_code = 'ar' if is_ar else 'en'
                tts = gTTS(text=human_ans, lang=lang_code, slow=False)
                b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
            except: pass
    else:
        # Default View
        st.markdown(f"<div class='flag-container'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
        st.info("Welcome, Engineer. Please enter your query above.")
