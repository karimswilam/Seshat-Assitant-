import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder # الحل الأمثل للمتصفح
from rapidfuzz import process, fuzz

# --- 1. CONFIG & RULES (All features preserved) ---
st.set_page_config(layout="wide", page_title="Seshat Voice AI v13.5")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STOP_WORDS = ['does', 'is', 'how', 'many', 'have', 'has', 'show', 'give', 'me', 'the', 'between', 'compared', 'to']

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

# --- 2. ENGINE (Logical Processing) ---
def advanced_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    clean_q = re.sub(r'\b(' + '|'.join(STOP_WORDS) + r')\b', '', q_low)
    words = re.findall(r'\w+', clean_q)
    
    selected_adms = []; services = []
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            if word.upper() not in selected_adms: selected_adms.append(word.upper())
            continue
        best_match = process.extractOne(word, all_keys, scorer=fuzz.WRatio)
        if best_match and best_match[1] > 75:
            for code, keys in SYNONYMS.items():
                if best_match[0] in keys:
                    if code in FLAGS and code not in selected_adms: selected_adms.append(code)
                    elif code == 'DAB_KEY': services.append('DAB')
                    elif code == 'TV_KEY': services.append('TV')
                    elif code == 'FM_KEY': services.append('FM')

    if not selected_adms: return None, [], 0, "Adm not found", is_ar, False

    reports = []; final_df = pd.DataFrame()
    services = list(set(services)) if services else ['SOUND', 'TV']

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]
        for svc in services:
            svc_codes = ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'] if svc == 'SOUND' else \
                        (['GS1', 'GS2', 'DS1', 'DS2'] if svc == 'DAB' else \
                        (['T01', 'T03', 'T04'] if svc == 'FM' else ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2']))
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig: row["Assignments"] = a_count
            if wants_allot: row["Allotments"] = l_count
            
            if (wants_assig and a_count > 0) or (wants_allot and l_count > 0):
                reports.append(row)
                if wants_allot and not wants_assig: final_df = pd.concat([final_df, svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)]])
                elif wants_assig and not wants_allot: final_df = pd.concat([final_df, svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)]])
                else: final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments','')} {r.get('Allotments','')}" for r in reports])
    return final_df, reports, 100, msg, is_ar, True

# --- 3. UI: VOICE INTERFACE ---
st.title("🎙️ Seshat Voice AI Assistant")

# Voice Input Section
st.markdown("### 🗣️ Say Your Question")
audio = mic_recorder(start_prompt="🔴 Click to Record", stop_prompt="⏹️ Stop", key='recorder')

query = ""
if audio:
    # تحويل الصوت المسجل لنص باستخدام SpeechRecognition
    import speech_recognition as sr
    r = sr.Recognizer()
    audio_data = io.BytesIO(audio['bytes'])
    with sr.AudioFile(audio_data) as source:
        audio_recorded = r.record(source)
    try:
        query = r.recognize_google(audio_recorded)
        st.success(f"Captured: {query}")
    except:
        st.error("Could not process voice. Try speaking again.")

# Manual Text Input (Fallback)
text_query = st.text_input("Or type here:", value=query)
final_query = text_query if text_query else query

if final_query and db is not None:
    res_df, reports, conf, msg, is_ar, logical = advanced_engine(final_query, db)
    
    if logical and reports:
        # Header Info
        h1, h2 = st.columns([3, 1])
        with h1:
            adms = list(set([r['Administration'].split()[0] for r in reports]))
            f_cols = st.columns(len(adms))
            for i, a in enumerate(adms): f_cols[i].image(FLAGS.get(a), width=60)
        with h2: st.metric("Confidence", f"{conf}%")

        # Visuals
        chart_df = pd.DataFrame(reports).set_index('Administration')
        cols_to_keep = []
        if any(x in final_query.lower() for x in SYNONYMS['ASSIG_KEY']): cols_to_keep.append("Assignments")
        if any(x in final_query.lower() for x in SYNONYMS['ALLOT_KEY']): cols_to_keep.append("Allotments")
        display_df = chart_df[cols_to_keep] if cols_to_keep else chart_df
        
        st.bar_chart(display_df)
        st.table(display_df)

        # Voice Output Section
        st.markdown("### 🔊 Assistant Answer")
        st.info(msg)
        
        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        with st.expander("Detailed Engineering Records"):
            st.dataframe(res_df, use_container_width=True)
