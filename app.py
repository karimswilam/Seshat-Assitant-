import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI: Intelligent Core", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    # (هنا بنحط كود تحويل الإحداثيات اللي عملناه قبل كدة)
    # ...
    return df

df = load_data()

# --- الـ Logic الحقيقي للـ LLM ---
def generate_ai_voice_text(count, country, service, n_type, original_query):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    # الـ Prompt ده هو اللي بيخلي الـ LLM يرد بذكاء مش بجمل ثابتة
    prompt = f"""
    You are an expert Telecommunications Engineer. 
    The user asked: "{original_query}"
    The data found: {count} {service} stations in {country}. 
    Additional filter used: {n_type if n_type else 'None'}.
    
    Task: Respond to the user's question directly and professionally in Egyptian Arabic (Ammiya). 
    Rules:
    1. Do NOT use fixed phrases like "Ya handsa" or "L2et" unless it feels natural.
    2. Be concise and precise with numbers.
    3. If multiple types exist, mention them.
    4. Sound like an Egyptian colleague, not a robot.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- Interface ---
st.title("📡 Seshat AI: Dynamic Response Core")

query = st.text_input("Engineering Query:", placeholder="How many sound stations in Egypt?")

if st.button("🚀 Run Intelligent Analysis") and query:
    # 1. تحليل الداتا (الـ Python Logic اللي عملناه)
    q = query.lower()
    target = "EGY" if "egy" in q or "مصر" in q else "ISR" if "isr" in q else None
    
    # (تكملة فلترة الـ df حسب النوع والـ notice type كما في الكود السابق)
    # ... لنفرض إننا طلعنا الـ res_count والـ s_label ...
    res_count = 356 # مثال
    s_label = "Sound"
    n_type = "TB2" # مثال
    
    # 2. نطلب من الـ LLM يولد الرد بناءً على النتيجة
    with st.spinner("Seshat is thinking..."):
        ai_voice_text = generate_ai_voice_text(res_count, target, s_label, n_type, query)
    
    # 3. تحويل رد الـ AI لصوت
    tts = gTTS(text=ai_voice_text, lang='ar')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    
    # --- العرض ---
    st.audio(audio_fp.getvalue(), format='audio/mp3')
    st.write(f"🤖 **Seshat says:** {ai_voice_text}")
    
    # (هنا بنعرض الخريطة والمقاييس كما في النسخ السابقة)
    # ...
