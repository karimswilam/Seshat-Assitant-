import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (ثابت لا مساس به)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

# أكواد التخصيص والتعيين الصارمة (Strict Mapping)
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2'] # Allotments (توزيع)
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1'] # Assignments (تخصيص)

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب']
}

st.set_page_config(page_title="Seshat AI v12.0.S_Final", layout="wide")

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

def final_solid_engine(q, data):
    q_clean = re.sub(r'[?؟.!]', '', q.lower()).strip()
    words = q_clean.split()
    
    conf = 0
    det_adm = None; det_svc = None; filter_type = None; exclude_code = None
    
    # 1. لقط العناصر بـ Cutoff عالي للدقة
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']: 
                        det_adm = code; conf += 50
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    break

    # 2. لقط الخدمة (TV, FM, DAB)
    for svc in MASTER_KNOWLEDGE.keys():
        if svc.lower().replace("_", " ") in q_clean or (svc == 'FM' and 'راديو' in q_clean) or (svc == 'DAB' and 'داب' in q_clean):
            det_svc = svc; conf += 25; break

    if not det_adm: return None, "Please specify a country.", 0

    # 3. الفلترة الصارمة
    res = data[data['Adm'].astype(str).str.contains(det_adm, na=False)]
    
    # فلترة الخدمة أولاً
    if det_svc:
        res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    
    # فلترة التخصيص/التعيين بناءً على الأكواد الصارمة (تمنع دخول DS2 في TV)
    if filter_type == 'allot':
        res = res[res['Notice Type'].isin(STRICT_ALLOT)]
        conf = min(conf + 25, 100)
    elif filter_type == 'assig':
        res = res[res['Notice Type'].isin(STRICT_ASSIG)]
        conf = min(conf + 25, 100)

    # 4. رسالة ذكية وتلميحات (Context-Aware Hints)
    msg = f"Confirmed results for {det_adm}"
    hint = None
    if not det_svc:
        hint = "💡 Hint: Specify a service (FM, TV, DAB) for more precise charts."
    if not filter_type:
        hint = "💡 Hint: Ask for 'Assignment' or 'Allotment' to filter results."

    return res, msg, conf, hint

st.title("📡 Seshat AI – Solid Reference v12.0.S_Final")
user_input = st.text_input("Ask Seshat:")

if db is not None and user_input:
    res_df, message, confidence, smart_hint = final_solid_engine(user_input, db)
    
    st.progress(confidence / 100)
    st.write(f"**Confidence Indicator:** {confidence}%")
    
    if res_df is not None:
        st.info(message)
        if smart_hint: st.warning(smart_hint)
            
        c1, c2 = st.columns([1, 2])
        with c1: st.metric("Records Found", len(res_df))
        with c2: 
            if not res_df.empty: st.bar_chart(res_df['Notice Type'].value_counts())
        
        st.dataframe(res_df)
    else:
        st.error(message)
