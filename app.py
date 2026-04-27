import streamlit as st
import pandas as pd
import os
import io
import re
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIGURATION (Back to v17.0 Logic) ---
st.set_page_config(layout="wide", page_title="Seshat Precision v32.1")

FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ISR': "https://flagcdn.com/w640/il.png"}
# الـ Mapping اللي بيحل مشكلة الـ Headers اللي قولت عليها
ADM_HEADERS = ['Administration', 'Adm', 'ADMINISTRATION', 'adm']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 2. DATA ENGINE (Robust Header Matching) ---
@st.cache_data
def load_and_fix_data():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    df = pd.read_excel(files[0])
    
    # Matching Logic من v17.0
    for header in ADM_HEADERS:
        if header in df.columns:
            df.rename(columns={header: 'Adm'}, inplace=True)
            break
            
    if 'Notice Type' not in df.columns:
        # لو الاسم مختلف شوية (زي NoticeType)
        df.columns = [c.replace('NoticeType', 'Notice Type') for c in df.columns]
        
    return df

db = load_and_fix_data()

# --- 3. VOICE ENGINE (PCM WAV FIX) ---
def process_audio_v17(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        # قراءة الـ Bytes مباشرة وتحويلها لـ AudioData
        audio_file = io.BytesIO(audio_data['bytes'])
        with sr.AudioFile(audio_file) as source:
            recorded_audio = r.record(source)
            return r.recognize_google(recorded_audio, language="ar-EG")
    except Exception as e:
        return None

# --- 4. UI ---
st.title("📡 Seshat Master Precision v32.1")
st.caption("Restored Engineering Logic | Project BASIRA")

with st.container(border=True):
    st.write("🎙️ Voice Input Control")
    # رجعنا للمكون المستقر في v17
    audio_output = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop", key="v32_mic")
    
    recognized_text = ""
    if audio_output:
        with st.spinner("Decoding Signal..."):
            recognized_text = process_audio_v17(audio_output)
            if recognized_text: st.success(f"Recognized: {recognized_text}")
            else: st.error("Signal weak. Please use manual input.")

query = st.text_input("Confirm Spectrum Inquiry:", value=recognized_text)

# --- 5. COMPARISON LOGIC ---
if query and db is not None:
    q_low = query.lower()
    target_adms = []
    if any(k in q_low for k in ['مصر', 'egypt', 'egy']): target_adms.append('EGY')
    if any(k in q_low for k in ['اسرائيل', 'israel', 'isr']): target_adms.append('ISR')

    if target_adms:
        cols = st.columns(len(target_adms))
        for idx, adm in enumerate(target_adms):
            adm_df = db[db['Adm'] == adm]
            asg = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
            alt = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
            
            with cols[idx]:
                st.image(FLAGS.get(adm, ""), width=120)
                st.metric(f"{adm} Total", asg + alt, f"A:{asg} | L:{alt}")
        
        st.dataframe(db[db['Adm'].isin(target_adms)], use_container_width=True)
    else:
        st.warning("Please specify Egypt or Israel.")
