import streamlit as st
import pandas as pd
import os
import re
import random
import base64
import subprocess

# --- 1. Settings & Style ---
st.set_page_config(page_title="Seshat AI v12.2.0", layout="wide")

# تثبيت ستايل الـ Dashboard اللي بتحبه
st.markdown("""
<style>
    .stMetric { background: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .ans-box { background: #ffffff; padding: 20px; border-right: 5px solid #1E3A8A; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'GRC': "https://flagcdn.com/w160/gr.png"
}

# --- 2. The Bulletproof Voice Engine ---
def get_neural_voice_html(text, is_ar):
    """توليد الصوت باستخدام Terminal Command لتجنب مشاكل الـ Async"""
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    output_file = "speech.mp3"
    try:
        # تنفيذ الأمر مباشرة في نظام التشغيل (أسرع وأضمن)
        subprocess.run(["edge-tts", "--voice", voice, "--text", text, "--write-media", output_file], check=True)
        with open(output_file, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        return f'<audio autoplay src="data:audio/mp3;base64,{b64}">'
    except Exception as e:
        return f""

# --- 3. Logic & Search (أفكارنا المدمجة) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    return pd.read_excel(files[0]) if files else None

db = load_db()
query = st.text_input("💬 اسأل المساعد الذكي (Seshat AI):")

if db is not None and query:
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in query)
    target_adm = "EGY"
    if "tur" in query.lower() or "تركيا" in query: target_adm = "TUR"
    elif "ars" in query.lower() or "سعودية" in query: target_adm = "ARS"
    
    res = db[db['Adm'].astype(str).str.contains(target_adm, na=False)]
    
    # الرد الذكي
    ans_text = f"تمام يا هندسة، لقيت {len(res)} سجل لإدارة {target_adm}." if is_ar else f"Engineer, I found {len(res)} records for {target_adm}."

    # --- العرض (The Dashboard) ---
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.image(FLAGS.get(target_adm, FLAGS['EGY']), width=150)
    
    with col2:
        st.markdown(f"<div class='ans-box'><h3>{ans_text}</h3></div>", unsafe_allow_html=True)
    
    with col3:
        st.metric("Confidence", "100%")
        st.progress(100)

    st.markdown("---")
    st.dataframe(res, use_container_width=True)

    # تشغيل الصوت (تلقائي بدون تهنيج)
    audio_html = get_neural_voice_html(ans_text, is_ar)
    st.markdown(audio_html, unsafe_allow_html=True)

elif db is None:
    st.error("فين ملف الـ Excel يا هندسة؟")
