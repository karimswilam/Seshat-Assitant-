import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS 
from difflib import get_close_matches

# --- 1. Flags & Master Knowledge (The Brain) ---
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

# تقسيم صارم للأنواع حسب طلبك
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب', 'assign'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab', 'digital sound'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station', 'digital tv']
}

st.set_page_config(page_title="Seshat AI v12.1.0 - Final Elite", layout="wide")

# --- 2. Voice Engine (Safe Synchronous) ---
def get_voice_safe(text, is_ar):
    # استخدام gTTS لضمان الاستقرار وعدم حدوث Runtime Errors
    lang = 'ar' if is_ar else 'en'
    tts = gTTS(text=text, lang=lang)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

# --- 3. UI Styling ---
st.markdown("""
    <style>
    .main { background: #f8f9fa; }
    .ans-card { 
        background: white; 
        padding: 25px; 
        border-radius: 20px; 
        border-left: 10px solid #1e3a8a; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.05); 
        margin-bottom: 20px;
    }
    .flag-img { width: 150px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 15px; }
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

def engine_v12_final(q, data):
    q_low = q.lower()
    # كشف لغة السؤال
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    # كشف لو السؤال بصيغة "Does / Is / هل"
    is_boolean = any(x in q_low for x in ['does', 'is ', 'هل', 'موجود', 'فيه'])
    
    words = re.findall(r'\w+', q_low)
    adms = []; det_svc = None; filter_type = None

    # Matching logic using Synonyms
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
    if not adms: return None, "EGY", 0, "عذراً يا هندسة، حدد الدولة.", is_ar

    # Core Logic
    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    # Humanized Intelligence Response
    found = len(res) > 0
    if is_ar:
        prefix = "نعم يا هندسة،" if found else "للاسف يا هندسة، لا يوجد"
        if not is_boolean: prefix = "تمام يا هندسة،"
        ans = f"{prefix} لقيت {len(res)} سجلات لـ {adms[0]} في قاعدة البيانات."
    else:
        prefix = "Yes, sir." if found else "I'm sorry, sir. No"
        if not is_boolean: prefix = "Done."
        ans = f"{prefix} I found {len(res)} records for {adms[0]}."

    return res, adms[0], 100, ans, is_ar

# --- UI Layout ---
st.title("📡 Seshat AI v12.1.0 - Stable Elite")
query = st.text_input("💬 Ask Seshat (e.g., هل يوجد FM في إسرائيل؟):")

if db is not None:
    if query:
        res_df, top_adm, conf, human_ans, is_arabic = engine_v12_final(query, db)
        
        # Display Header & Flag
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS[top_adm]}' class='flag-img'><h3>{top_adm} Intelligence Report</h3></div>", unsafe_allow_html=True)
        
        # Result Card
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2><p>Confidence: {conf}%</p></div>", unsafe_allow_html=True)
        
        if res_df is not None:
            if not res_df.empty:
                st.dataframe(res_df, use_container_width=True)
                st.bar_chart(res_df['Notice Type'].value_counts())
            
            # Voice Output (The Fixed Way)
            audio_bytes = get_voice_safe(human_ans, is_arabic)
            st.audio(audio_bytes, format="audio/mp3")
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
        st.info("System is operational. Enter your frequency coordination query.")
else:
    st.error("Error: Please make sure Data.xlsx is present in the directory.")
