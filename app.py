import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. CONFIG & FULL ADM LIST ---
st.set_page_config(layout="wide", page_title="Seshat AI v13.2.0 - Full Spectrum")

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

# تحديث الـ Synonyms لضمان قبول الاختصارات الـ 3 حروف
SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو']
}

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

# --- 2. THE ULTIMATE ENGINE ---
def final_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    selected_adms = []
    services = []
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    # التحقق من الكلمات (تقليل الـ cutoff لضمان الـ ARS و GRC)
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        # لو الكلمة 3 حروف وموجودة في المفاتيح، خدها مباشرة
        if len(word) == 3 and word.upper() in FLAGS:
            if word.upper() not in selected_adms: selected_adms.append(word.upper())
            continue
            
        match = get_close_matches(word, all_keys, n=1, cutoff=0.7) # خفضنا الـ cutoff لـ 0.7
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS and code not in selected_adms: selected_adms.append(code)
                    elif code == 'DAB_KEY' and 'DAB' not in services: services.append('DAB')
                    elif code == 'TV_KEY' and 'TV' not in services: services.append('TV')
                    elif code == 'FM_KEY' and 'FM' not in services: services.append('FM')

    if not selected_adms: return None, [], 0, "Adm not found", is_ar, False
    
    reports = []
    filtered_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]
        active_services = services if services else ['SOUND', 'TV']
        
        for svc in active_services:
            svc_codes = MASTER_KNOWLEDGE.get(svc, [])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            
            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig:
                count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
                row["Assignments"] = count
                filtered_df = pd.concat([filtered_df, svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)]])
            if wants_allot:
                count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
                row["Allotments"] = count
                filtered_df = pd.concat([filtered_df, svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)]])
            
            if row.get("Assignments", 0) > 0 or row.get("Allotments", 0) > 0:
                reports.append(row)

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments', 0)} Assig, {r.get('Allotments', 0)} Allot" for r in reports])
    return filtered_df, reports, 100, msg, is_ar, True

# --- 3. UI LAYOUT ---
st.title("🛰️ Seshat v13.2.0 - Final Edition")
query = st.text_input("🎙️ Complex Comparison (e.g., ARS vs EGY vs GRC):")

if db is not None and query:
    res_df, reports, conf, msg, is_ar, logical = final_engine(query, db)
    
    # Flags & Confidence Row
    c1, c2 = st.columns([3, 1])
    with c1:
        adms_present = list(set([r['Administration'].split()[0] for r in reports]))
        f_cols = st.columns(len(adms_present) if adms_present else 1)
        for i, a in enumerate(adms_present):
            f_cols[i].image(FLAGS.get(a), width=60, caption=a)
    with c2:
        st.metric("Confidence", f"{conf}%")
        st.progress(conf)

    if logical:
        st.info(f"📢 {msg}")
        chart_df = pd.DataFrame(reports).set_index('Administration')
        st.bar_chart(chart_df)
        
        st.markdown("### 🔢 Data Analysis Table")
        st.table(chart_df) # الأرقام واضحة ومباشرة
        
        with st.expander("Show Details"):
            st.dataframe(res_df, use_container_width=True)

        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
