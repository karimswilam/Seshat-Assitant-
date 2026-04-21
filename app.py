import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v13.1.0")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
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

# --- 2. PRECISION ENGINE ---
def precision_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    selected_adms = []
    services = []
    # البحث عن كلمات مفتاحية للأنواع بشكل صريح
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    # لو مسألش عن حاجة معينة، نفترض إنه عايز الاتنين
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS and code not in selected_adms: selected_adms.append(code)
                    elif code == 'DAB_KEY' and 'DAB' not in services: services.append('DAB')
                    elif code == 'TV_KEY' and 'TV' not in services: services.append('TV')
                    elif code == 'FM_KEY' and 'FM' not in services: services.append('FM')

    if not selected_adms: return None, [], 0, "No ADM detected", is_ar, False
    
    if 'FM' in services and wants_allot and not wants_assig:
        return None, selected_adms, 0, "Illogical: FM has no allotments.", is_ar, False

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
            
            reports.append(row)

    # بناء رسالة الـ Voice
    summary_parts = [f"{r['Administration']}: {r.get('Assignments', 0)} Assig, {r.get('Allotments', 0)} Allot" for r in reports]
    msg = " | ".join(summary_parts)
    
    return filtered_df, reports, 100, msg, is_ar, True

# --- 3. UI ---
st.title("🛰️ Seshat Precision Assistant v13.1")
query = st.text_input("🎙️ Ask for comparison or analysis:")

if db is not None and query:
    res_df, reports, conf, msg, is_ar, logical = precision_engine(query, db)
    
    # Flags & Confidence Row
    c1, c2 = st.columns([3, 1])
    with c1:
        adms_present = list(set([r['Administration'].split()[0] for r in reports]))
        f_cols = st.columns(len(adms_present) if adms_present else 1)
        for i, a in enumerate(adms_present):
            f_cols[i].image(FLAGS.get(a), width=70, caption=a)
    with c2:
        st.metric("Confidence", f"{conf}%")
        st.progress(conf)

    if not logical:
        st.error(msg)
    else:
        # Chart & Table Row
        chart_df = pd.DataFrame(reports).set_index('Administration')
        st.bar_chart(chart_df)
        
        # إظهار الأرقام بوضوح (طلبك الأساسي)
        st.markdown("### 🔢 Data Summary Table")
        st.table(chart_df) # الـ table بيظهر الأرقام ثابتة مش محتاجة حرك الماوس
        
        with st.expander("Show Details"):
            st.dataframe(res_df, use_container_width=True)

        # Voice Assistant
        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
