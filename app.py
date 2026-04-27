import streamlit as st
import pandas as pd
import os
import io
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Seshat Precision v32.0")

# الـ Logic الأصلي (v17.0)
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ISR': "https://flagcdn.com/w640/il.png"}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 2. DATA ENGINE (FIXED KEYERROR) ---
@st.cache_data
def load_clean_data():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    df = pd.read_excel(files[0])
    # تنظيف الأعمدة لضمان عدم حدوث KeyError
    df.columns = [str(c).strip() for c in df.columns]
    mapping = {'Administration': 'Adm', 'Adm': 'Adm', 'Notice Type': 'Notice Type'}
    for k, v in mapping.items():
        if k in df.columns: df.rename(columns={k: v}, inplace=True)
    return df

db = load_clean_data()

# --- 3. VOICE HANDLER (NEW COMPATIBILITY LAYER) ---
def process_voice(audio_bytes):
    r = sr.Recognizer()
    try:
        # تحويل الصوت لـ AudioData مباشرة
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language="ar-EG")
    except: return None

# --- 4. INTERFACE ---
st.title("📡 Seshat Core v32.0")

# ميكروفون جديد متوافق مع الموبايل واللاب (بيظهر بشكل أيقونة مايك بسيطة)
st.write("🎙️ Record Inquiry:")
audio_bytes = audio_recorder(text="", icon_size="2x", neutral_color="#1E3A8A")

query = ""
if audio_bytes:
    with st.spinner("Decoding Signal..."):
        query = process_voice(audio_bytes)
        if query: st.success(f"Recognized: {query}")
        else: st.error("Signal weak or corrupted. Using manual input.")

# الـ Input Field هو الأساس
final_query = st.text_input("Confirm/Type Inquiry:", value=query)

# --- 5. SPECTRUM INTELLIGENCE LOGIC ---
if final_query and db is not None:
    # البحث عن "مصر" أو "اسرائيل" في السؤال
    target_adms = []
    if any(k in final_query for k in ['مصر', 'egypt', 'egy']): target_adms.append('EGY')
    if any(k in final_query for k in ['اسرائيل', 'israel', 'isr']): target_adms.append('ISR')

    if target_adms:
        cols = st.columns(len(target_adms))
        for idx, adm in enumerate(target_adms):
            adm_df = db[db['Adm'] == adm]
            asg = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
            alt = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
            
            with cols[idx]:
                st.image(FLAGS.get(adm, ""), width=100)
                st.metric(f"{adm} Spectrum Sum", asg + alt, f"A:{asg} | L:{alt}")
        
        # عرض البيانات المفلترة
        with st.expander("Show Detailed Records"):
            st.dataframe(db[db['Adm'].isin(target_adms)])
    else:
        st.warning("Please mention a country (Egypt/Israel) in your query.")
