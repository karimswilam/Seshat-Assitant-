import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v13.2.1")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

# كلمات السؤال اللي لازم نتجاهلها عشان ميعتبرهاش Error
STOP_WORDS = ['does', 'is', 'how', 'many', 'have', 'has', 'show', 'give', 'me', 'the', 'between', 'compared', 'to']

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

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

def smart_logical_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    # تنظيف السؤال من كلمات الحشو
    clean_q = re.sub(r'\b(' + '|'.join(STOP_WORDS) + r')\b', '', q_low)
    words = re.findall(r'\w+', clean_q)
    
    selected_adms = []
    services = []
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        # Check explicit 3-letter codes
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

    if not selected_adms: return None, [], 0, "Please specify an Administration (e.g. EGY, ARS, CYP)", is_ar, False
    
    # Filtering
    reports = []
    final_df = pd.DataFrame()
    services = list(set(services)) if services else ['SOUND', 'TV']

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]
        for svc in services:
            svc_codes = MASTER_KNOWLEDGE.get(svc, [])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            
            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig:
                row["Assignments"] = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            if wants_allot:
                row["Allotments"] = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            if row.get("Assignments", 0) > 0 or row.get("Allotments", 0) > 0:
                reports.append(row)
                # تجميع الداتا للجدول الكبير
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments',0)} Assig, {r.get('Allotments',0)} Allot" for r in reports])
    return final_df, reports, 100, msg, is_ar, True

# --- 3. UI ---
query = st.text_input("💬 Ask Seshat (e.g., Does EGY have more DAB than ARS?):")

if db is not None and query:
    res_df, reports, conf, msg, is_ar, logical = smart_logical_engine(query, db)
    
    if not logical:
        st.warning(msg)
    else:
        # Display Flags
        adms = list(set([r['Administration'].split()[0] for r in reports]))
        f_cols = st.columns(len(adms) if adms else 1)
        for i, a in enumerate(adms):
            f_cols[i].image(FLAGS.get(a), width=70, caption=a)
        
        # Dashboard
        st.metric("Engine Confidence", f"{conf}%")
        chart_df = pd.DataFrame(reports).set_index('Administration')
        st.bar_chart(chart_df)
        st.table(chart_df) # الأرقام الهنددية الدقيقة
        
        with st.expander("Show Details"):
            st.dataframe(res_df, use_container_width=True)

        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
