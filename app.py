import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. CONFIG & STRICT CLASSIFICATION ---
st.set_page_config(layout="wide", page_title="Seshat AI v13.2.2")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STOP_WORDS = ['does', 'is', 'how', 'many', 'have', 'has', 'show', 'give', 'me', 'the', 'between', 'compared', 'to']

# التصنيف القاطع - لا رجعة فيه
# الـ GT1 و الـ GS1 تخصيصات (Assignments) دايماً
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01'] 
# الـ GT2 و الـ GS2 توزيعات (Allotments) دايماً
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل'],
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

def final_strict_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    clean_q = re.sub(r'\b(' + '|'.join(STOP_WORDS) + r')\b', '', q_low)
    words = re.findall(r'\w+', clean_q)
    
    selected_adms = []; services = []
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            if word.upper() not in selected_adms: selected_adms.append(word.upper())
            continue
        match = get_close_matches(word, all_keys, n=1, cutoff=0.7)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS and code not in selected_adms: selected_adms.append(code)
                    elif code == 'DAB_KEY': services.append('DAB')
                    elif code == 'TV_KEY': services.append('TV')
                    elif code == 'FM_KEY': services.append('FM')

    if not selected_adms: return None, [], 0, "No ADM identified", is_ar, False

    reports = []; final_df = pd.DataFrame()
    services = list(set(services)) if services else ['SOUND', 'TV']

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]
        for svc in services:
            svc_codes = MASTER_KNOWLEDGE.get(svc, [])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            
            row = {"Administration": f"{adm} ({svc})"}
            # الحساب بناءً على الـ Strict Lists المعدلة
            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            if wants_assig: row["Assignments"] = a_count
            if wants_allot: row["Allotments"] = l_count
            
            if (wants_assig and a_count >= 0) or (wants_allot and l_count >= 0):
                reports.append(row)
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments',0)} Assig, {r.get('Allotments',0)} Allot" for r in reports])
    return final_df, reports, 100, msg, is_ar, True

# --- 3. UI ---
query = st.text_input("💬 Ask Seshat (Strict Classification Mode):")

if db is not None and query:
    res_df, reports, conf, msg, is_ar, logical = final_strict_engine(query, db)
    
    if logical:
        c1, c2 = st.columns([3, 1])
        with c1:
            adms = list(set([r['Administration'].split()[0] for r in reports]))
            f_cols = st.columns(len(adms) if adms else 1)
            for i, a in enumerate(adms): f_cols[i].image(FLAGS.get(a), width=70, caption=a)
        with c2: st.metric("Confidence", f"{conf}%")

        st.info(f"📋 {msg}")
        chart_df = pd.DataFrame(reports).set_index('Administration')
        st.bar_chart(chart_df)
        st.table(chart_df) # الأرقام هنا هتظهر الـ GT1 في الـ Assignments صح

        with st.expander("Show Details"):
            st.dataframe(res_df, use_container_width=True)

        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en'); b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
