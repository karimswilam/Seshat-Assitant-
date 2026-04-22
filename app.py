import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- 1. CONFIG & RECOVERY ---
st.set_page_config(layout="wide", page_title="Seshat AI v15.0")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# قاموس المفاتيح المحسن (عربي وإنجليزي)
COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'التركية'],
    'CYP': ['cyprus', 'cyp', 'قبرص', 'القبرصية'],
    'GRC': ['greece', 'grc', 'اليونان', 'اليونانية'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. THE NEURAL VOICE ENGINE ---
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = text.replace("|", " . ").replace(":", " , ")
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        data = asyncio.run(generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 3. THE CORE LOGICAL ENGINE (Enhanced Comparison) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def advanced_engine_v15(q, data):
    q_low = q.lower()
    
    # Identify Administrations - تحسين الكشف عن أكتر من دولة
    selected_adms = []
    # 1. Check for 3-letter codes
    words = re.findall(r'\w+', q_low)
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper())
    
    # 2. Check for Full Names (Arabic/English)
    for code, keywords in COUNTRY_MAP.items():
        if any(k in q_low for k in keywords):
            selected_adms.append(code)
    
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "No country identified.", 0, False

    # Identify Intent
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    # Identify Service
    service_filter = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): service_filter = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): service_filter = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): service_filter = ['T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if service_filter:
            adm_df = adm_df[adm_df['Notice Type'].isin(service_filter)]
        
        a_df = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        l_df = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        
        res = {"Adm": adm, "Assignments": len(a_df), "Allotments": len(l_df)}
        reports.append(res)
        
        # Build Table Data
        if wants_assig and not wants_allot: final_df = pd.concat([final_df, a_df])
        elif wants_allot and not wants_assig: final_df = pd.concat([final_df, l_df])
        else: final_df = pd.concat([final_df, adm_df])

    msg_list = []
    for r in reports:
        parts = f"{r['Adm']}: "
        if wants_assig: parts += f"{r['Assignments']} Assignments "
        if wants_allot: parts += f"{r['Allotments']} Allotments"
        msg_list.append(parts)
    
    return final_df, reports, " | ".join(msg_list), 100, True

# --- 4. UI ---
db = load_db()
st.title("🎙️ Seshat Master AI v15.0")

query = st.text_input("🎙️ Input Question (Compare countries, services, etc.):", key="main_q")

if query:
    st.markdown("### 🔈 Question Audio")
    play_audio(query)

    if db is not None:
        res_df, reports, msg, conf, success = advanced_engine_v15(query, db)
        
        if success and reports:
            # Flags & Confidence
            c1, c2 = st.columns([3, 1])
            with c1:
                f_cols = st.columns(len(reports))
                for i, r in enumerate(reports): f_cols[i].image(FLAGS.get(r['Adm']), width=70, caption=r['Adm'])
            with c2: st.metric("Confidence Score", f"{conf}%")

            # Chart & Table
            chart_df = pd.DataFrame(reports).set_index('Adm')
            # تصفية الأعمدة في الشارت بناءً على الطلب
            visible_cols = []
            if any(x in query.lower() for x in SYNONYMS['ASSIG_KEY']): visible_cols.append("Assignments")
            if any(x in query.lower() for x in SYNONYMS['ALLOT_KEY']): visible_cols.append("Allotments")
            if not visible_cols: visible_cols = ["Assignments", "Allotments"]
            
            st.bar_chart(chart_df[visible_cols])
            st.table(chart_df[visible_cols])

            # Assistant Voice
            st.markdown("### 🔊 Assistant Response")
            st.success(msg)
            play_audio(msg)

            with st.expander("Show Detailed Technical Data"):
                st.dataframe(res_df, use_container_width=True)
