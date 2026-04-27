import streamlit as st
import pandas as pd
import os
import io
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder

st.set_page_config(layout="wide", page_title="Seshat Precision v32.2")

# --- 1. الـ Logic الهندسي الصارم ---
# رجعنا للأسماء اللي في الشيت بتاعك بالظبط
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

@st.cache_data
def load_data_engine():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    df = pd.read_excel(files[0])
    # تنظيف شامل للأعمدة
    df.columns = [str(c).strip() for c in df.columns]
    # التأكد من وجود Administration أو Adm
    if 'Administration' in df.columns:
        df.rename(columns={'Administration': 'Adm'}, inplace=True)
    return df

db = load_data_engine()

# --- 2. معالج الصوت (تم تحسينه ليتوافق مع الـ 85 dB اللي عندك) ---
def transcribe_spectrum(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    # تحسين الحساسية للتعامل مع الإشارة القوية
    r.energy_threshold = 300 
    try:
        audio_stream = io.BytesIO(audio_data['bytes'])
        with sr.AudioFile(audio_stream) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language="ar-EG")
    except: return None

# --- 3. الواجهة ---
st.title("📡 Seshat Master Precision v32.2")

with st.expander("🎙️ Voice Intelligence Control", expanded=True):
    # استخدام الـ Mic Recorder المستقر
    audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Process Signal", key="final_mic")
    
    voice_query = ""
    if audio_input:
        voice_query = transcribe_spectrum(audio_input)
        if voice_query: st.success(f"Recognized: {voice_query}")

query = st.text_input("Manual Confirmation / Inquiry:", value=voice_query)

# --- 4. محرك المقارنة (The Comparison Engine) ---
if query and db is not None:
    # Logic المقارنة بالكلمات المفتاحية
    search_map = {'EGY': ['مصر', 'egypt', 'egy'], 'ISR': ['اسرائيل', 'israel', 'isr']}
    selected_adms = [code for code, terms in search_map.items() if any(t in query.lower() for t in terms)]
    
    if selected_adms:
        st.subheader("📊 Comparative Results")
        cols = st.columns(len(selected_adms))
        
        for idx, adm in enumerate(selected_adms):
            # فلترة البيانات بناءً على الـ Adm والـ Notice Type
            adm_data = db[db['Adm'] == adm]
            asg = len(adm_data[adm_data['Notice Type'].isin(STRICT_ASSIG)])
            alt = len(adm_data[adm_data['Notice Type'].isin(STRICT_ALLOT)])
            
            with cols[idx]:
                st.metric(label=f"Total Records ({adm})", value=asg + alt, delta=f"Assig: {asg} | Allot: {alt}")
        
        # عرض الجدول المدمج
        st.dataframe(db[db['Adm'].isin(selected_adms)], use_container_width=True)
    else:
        st.warning("Please mention 'Egypt' or 'Israel' in your question.")
