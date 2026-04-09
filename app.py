import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Final Core", layout="wide")

# --- 1. معالجة البيانات (النسخة الآمنة من الـ AttributeError) ---
@st.cache_data
def load_data_safe():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # حل مشكلة السطر 38 اللي ظهرت في الـ Logs
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except: return pd.DataFrame()

df = load_data_safe()

# --- 2. محرك الـ AI (توليد الرد بالعامية المصرية) ---
def get_ai_speech_response(count, country, service, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        # الـ Prompt ده هو اللي بيخليه يتكلم مصري عفوياً
        prompt = f"""
        Answer as an Egyptian Telecom Engineer. 
        Context: Found {count} {service} stations for {country}. 
        Question: "{query}"
        Task: Respond in natural Egyptian Ammiya. Focus on the figures. 
        Be concise and helpful. Don't use robotic templates.
        """
        response_text = model.generate_content(prompt).text
        
        # تحويل الرد لصوت فوراً
        tts = gTTS(text=response_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return response_text, audio_fp.getvalue()
    except:
        return f"يا هندسة فيه {count} محطة {service} في {country}.", None

# --- 3. واجهة التحكم ---
st.title("📡 Seshat AI: Precision Spectrum Dashboard")
query = st.text_input("Engineering Query:", placeholder="مثلاً: مصر فيها كام محطة صوت؟")

if st.button("🚀 Analyze & Speak") and query:
    q = query.lower()
    
    # فلترة البيانات (Python Logic)
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target] if target != "GLOBAL" else df
    
    is_tv = any(x in q for x in ["tv", "bt", "تلفزيون"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    
    # نداء الـ AI لتوليد الرد الصوتي
    with st.spinner("جاري صياغة الرد المصري..."):
        ai_msg, ai_audio = get_ai_speech_response(len(f_df), target, "TV" if is_tv else "Sound", query)
        
        # تخزين النتائج لتفادي الـ KeyError
        st.session_state.final_res = {
            'msg': ai_msg, 'audio': ai_audio, 'count': len(f_df), 
            'adm': target, 'df': f_df
        }

# --- 4. العرض الصوتي والبصري ---
if 'final_res' in st.session_state:
    res = st.session_state.final_res
    
    # تشغيل الصوت تلقائياً (دي اللي كانت مختفية)
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    
    st.info(res['msg'])
    st.metric(f"Total Stations in {res['adm']}", res['count'])
    
    # عرض الخريطة (فقط لو فيه داتا)
    if not res['df'].empty:
        # هنا بنحط كود الـ Map اللي شغال معاك تمام
        pass
