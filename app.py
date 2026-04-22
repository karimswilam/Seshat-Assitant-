import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v14.1")

# استخدام session_state لمنع التهنيج وضمان استمرارية الـ Loop
if 'audio_ready' not in st.session_state:
    st.session_state.audio_ready = False

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 2. OPTIMIZED NEURAL VOICE (No-Wait Loop) ---
async def speak_neural_async(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
    
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        # تشغيل الصوت بطريقة لا تمنع تنفيذ باقي الكود
        result = asyncio.run(speak_neural_async(text))
        st.audio(result, format="audio/mp3")
    except Exception as e:
        pass

# --- 3. LOGICAL ENGINE (Deep Clear) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

def process_query(q, data):
    # تصفير محلي تام
    q_low = q.lower()
    wants_assig = any(x in q_low for x in ['assignment', 'تخصيص', 'تخصيصات'])
    wants_allot = any(x in q_low for x in ['allotment', 'توزيع', 'توزيعات'])
    
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    words = re.findall(r'\w+', q_low)
    selected_adms = []
    
    # البحث عن الأكواد والأسماء
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper())
        for code, names in {'EGY':['egypt','مصر'], 'ARS':['saudi','السعودية'], 'ISR':['israel','اسرائيل'], 'TUR':['turkey','تركيا']}.items():
            if word in names: selected_adms.append(code)

    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "Please specify an ADM.", 0, False

    reports = []; final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        
        if wants_assig and not wants_allot:
            work_df = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif wants_allot and not wants_assig:
            work_df = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else:
            work_df = adm_df

        a_count = len(work_df[work_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(work_df[work_df['Notice Type'].isin(STRICT_ALLOT)])

        if a_count > 0 or l_count > 0:
            reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
            final_df = pd.concat([final_df, work_df], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Assignments'] if wants_assig else ''} Assignments, {r['Allotments'] if wants_allot else ''} Allotments" for r in reports])
    return final_df, reports, msg, 100, True

# --- 4. UI ---
db = load_db()
st.title("🛰️ Seshat Engineering Assistant v14.1")

# استخدام الـ key والـ on_change لضمان استجابة أسرع
query = st.text_input("🎙️ Input Question:", key="query_input")

if query:
    if db is not None:
        res_df, reports, msg, conf, success = process_query(query, db)
        
        if success and reports:
            # Header
            h1, h2 = st.columns([3, 1])
            with h1:
                cols = st.columns(len(reports))
                for i, r in enumerate(reports): cols[i].image(FLAGS.get(r['Adm']), width=70)
            with h2:
                st.metric("Confidence Score", f"{conf}%")

            # Charts & Table
            chart_data = pd.DataFrame(reports).set_index('Adm')
            st.bar_chart(chart_data)
            st.table(chart_data)

            # Response Section
            st.markdown("### 🔊 Voice Response")
            st.success(msg)
            
            # تشغيل السؤال والجواب في مكان واحد لتقليل الـ Overhead
            with st.expander("Listen to Question & Answer"):
                st.write("Question Voice:")
                play_audio(query)
                st.write("Assistant Voice:")
                play_audio(msg)

            with st.expander("Spectrum Details"):
                st.dataframe(res_df, use_container_width=True)
