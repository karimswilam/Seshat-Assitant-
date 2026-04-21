import streamlit as st
import pandas as pd
import os
import re
import random
import subprocess
import base64

# --- 1. Master Settings ---
st.set_page_config(page_title="Seshat Elite v12.1.0", layout="wide")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

SYNONYMS = {
    'EGY': ['egypt', 'مصر'], 'ARS': ['saudi', 'السعودية', 'ars'],
    'TUR': ['turkey', 'تركيا'], 'GRC': ['greece', 'اليونان'],
    'ISR': ['israel', 'إسرائيل', 'isr']
}

# --- 2. Robust Voice Engine (No Async Errors) ---
def speak_neural(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    # إنشاء ملف صوتي مؤقت باستخدام Terminal command
    try:
        cmd = f'edge-tts --voice {voice} --text "{text}" --write-media voice.mp3'
        subprocess.run(cmd, shell=True, check=True)
        with open("voice.mp3", "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        return f'<audio autoplay src="data:audio/mp3;base64,{b64}">'
    except:
        return ""

# --- 3. Logic & UI ---
@st.cache_data
def load_data():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    return pd.read_excel(files[0]) if files else None

df = load_data()
query = st.text_input("💬 Ask Seshat (Neural Assistant):")

if df is not None and query:
    q_low = query.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in query)
    
    # تحديد الإدارة
    target_adm = "EGY"
    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            target_adm = code
            break
            
    res = df[df['Adm'].astype(str).str.contains(target_adm, na=False)]
    
    # --- العرض (The Dashboard) ---
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.image(FLAGS.get(target_adm), width=150)
    with c2:
        # الرد الذكي
        ans = f"لقد حللت بيانات {target_adm} ووجدت {len(res)} سجلات مطابقة." if is_ar else f"I analyzed {target_adm} data and found {len(res)} matching records."
        st.subheader(ans)
    with c3:
        st.metric("Confidence", "100%")
    
    st.markdown("---")
    st.dataframe(res, use_container_width=True)
    
    # تشغيل الصوت في الخلفية (The Hidden Trigger)
    audio_html = speak_neural(ans, is_ar)
    st.markdown(audio_html, unsafe_allow_html=True)

elif df is None:
    st.error("Missing Data.xlsx!")
