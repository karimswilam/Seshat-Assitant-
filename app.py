import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from rapidfuzz import process, fuzz

# --- 1. CONFIG & RECOVERY (Fixed Lists) ---
st.set_page_config(layout="wide", page_title="Seshat Interactive Voice v13.6")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STOP_WORDS = ['does', 'is', 'how', 'many', 'have', 'has', 'show', 'give', 'me', 'the']

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

def speak(text, lang_auto=True):
    """وظيفة موحدة لإخراج الصوت"""
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    tts = gTTS(text=text, lang='ar' if is_ar else 'en', slow=False)
    b = io.BytesIO()
    tts.write_to_fp(b)
    return b

# --- 2. LOGICAL ENGINE ---
def engineering_engine(q, data):
    q_low = q.lower()
    clean_q = re.sub(r'\b(' + '|'.join(STOP_WORDS) + r')\b', '', q_low)
    words = re.findall(r'\w+', clean_q)
    
    selected_adms = []; services = []
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper()); continue
        best_match = process.extractOne(word, all_keys, scorer=fuzz.WRatio)
        if best_match and best_match[1] > 75:
            for code, keys in SYNONYMS.items():
                if best_match[0] in keys:
                    if code in FLAGS: selected_adms.append(code)
                    elif code == 'DAB_KEY': services.append('DAB')
                    elif code == 'TV_KEY': services.append('TV')
                    elif code == 'FM_KEY': services.append('FM')

    if not selected_adms: return None, [], "Adm not identified", False

    reports = []; final_df = pd.DataFrame()
    services = list(set(services)) if services else ['SOUND', 'TV']

    for adm in list(set(selected_adms)):
        adm_df = data[data['Adm'] == adm]
        for svc in services:
            svc_codes = ['GS1', 'GS2', 'DS1', 'DS2'] if svc == 'DAB' else (['T01', 'T03', 'T04'] if svc == 'FM' else ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig: row["Assignments"] = a_count
            if wants_allot: row["Allotments"] = l_count
            
            if (wants_assig and a_count > 0) or (wants_allot and l_count > 0):
                reports.append(row)
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments','')} {r.get('Allotments','')}" for r in reports])
    return final_df, reports, msg, True

# --- 3. UI LAYOUT ---
st.title("🎙️ Seshat Interactive Voice Dashboard")

# Input Section
query = st.text_input("✍️ Type your engineering question:", placeholder="e.g., How many DAB stations in Egypt and Saudi?")

col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔊 Play Question"):
        if query:
            st.audio(speak(query))
        else:
            st.warning("Write something first!")

# Processing & Results
if query and db is not None:
    res_df, reports, msg, success = engineering_engine(query, db)
    
    if success and reports:
        # Flags Row
        adms = list(set([r['Administration'].split()[0] for r in reports]))
        f_cols = st.columns(len(adms) if adms else 1)
        for i, a in enumerate(adms):
            f_cols[i].image(FLAGS.get(a), width=80, caption=a)

        # Charts & Tables
        chart_df = pd.DataFrame(reports).set_index('Administration')
        
        # Smart Filter for columns
        cols = []
        if any(x in query.lower() for x in SYNONYMS['ASSIG_KEY']): cols.append("Assignments")
        if any(x in query.lower() for x in SYNONYMS['ALLOT_KEY']): cols.append("Allotments")
        display_df = chart_df[cols] if cols else chart_df
        
        st.bar_chart(display_df)
        st.table(display_df)

        # Voice Output (The Answer)
        st.markdown("### 🔊 Assistant Answer")
        st.success(msg)
        st.audio(speak(msg)) # بيشغل الإجابة صوتياً فوراً

        with st.expander("Engineering Details (Raw Data)"):
            st.dataframe(res_df, use_container_width=True)
