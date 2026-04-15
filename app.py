import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (Master Knowledge)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل', 'israil'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'توزيع', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تنسيب', 'assign'],
    'DAB_KEY': ['dab', 'داب', 'ديجيتال'],
    'FM_KEY': ['fm', 'اف ام', 'راديو', 'radio']
}

st.set_page_config(page_title="Seshat AI v12.0.S", layout="wide")

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

# --- محرك البحث المطور مع الـ Confidence Indicator ---
def advanced_engine_v12_S(q, data):
    q_clean = re.sub(r'[?؟.!]', '', q.lower()).strip()
    words = q_clean.split()
    
    conf = 0
    det_adm = None; det_svc = None; filter_type = None; exclude_code = None
    
    # 1. تحليل الإدارة والفلتر (Fuzzy Match)
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.75)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']: 
                        det_adm = code; conf += 50
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'; conf += 25
                    elif code == 'FM_KEY': det_svc = 'FM'; conf += 25
                    break
            if det_adm and (det_svc or filter_type): break

    # 2. منطق الاستبعاد (Except)
    if 'ماعدا' in q_clean or 'except' in q_clean:
        potential_codes = [w.upper() for w in words if len(w) <= 4]
        for c in potential_codes:
            if any(c in codes for codes in MASTER_KNOWLEDGE.values()):
                exclude_code = c; conf = min(conf + 10, 100)

    # 3. لقط الخدمة لو لسه ملقنهاش
    if not det_svc:
        for svc in MASTER_KNOWLEDGE.keys():
            if svc.lower().replace("_", " ") in q_clean:
                det_svc = svc; conf += 25; break

    if not det_adm:
        return None, "Please specify a country.", 0

    # 4. تصفية البيانات (Logic Implementation)
    mask = (data['Adm'].astype(str).str.contains(det_adm, na=False))
    res = data[mask]
    
    if det_svc:
        res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    
    if filter_type == 'allot':
        res = res[res['Notice Type'].str.contains('2|G2|T2', na=False)]
        conf = min(conf + 25, 100)
    elif filter_type == 'assig':
        res = res[res['Notice Type'].str.contains('1|G1|T1|T01|T03|T04', na=False)]
        conf = min(conf + 25, 100)
    
    if exclude_code:
        res = res[res['Notice Type'] != exclude_code]

    msg = f"Results for {det_adm}"
    if det_svc: msg += f" - {det_svc}"
    if filter_type: msg += f" ({filter_type})"
    
    return res, msg, conf

st.title("📡 Seshat AI – Solid Reference v12.0.S")
user_input = st.text_input("Engineering Query (Interactive & Verified):")

if db is not None and user_input:
    res_df, message, confidence_level = advanced_engine_v12_S(user_input, db)
    
    # الـ Confidence Indicator (عاش يا هندسة، رجع مكانه)
    st.progress(confidence_level / 100)
    st.write(f"**Confidence Indicator:** {confidence_level}%")
    
    if res_df is not None:
        st.info(message)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Total Records", len(res_df))
        with c2:
            if not res_df.empty:
                st.subheader("Notice Type Distribution")
                st.bar_chart(res_df['Notice Type'].value_counts())
        
        st.dataframe(res_df)
        
        # Voice Output
        try:
            voice_txt = f"Found {len(res_df)} records with {confidence_level} percent confidence."
            tts = gTTS(text=voice_txt, lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
    else:
        st.error(message)
