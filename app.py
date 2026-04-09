import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Mission Critical", layout="wide")

# --- 1. الذاكرة الفولاذية (تأمين الـ Session State) ---
if 'voice_response' not in st.session_state: st.session_state.voice_response = None
if 'text_msg' not in st.session_state: st.session_state.text_msg = ""
if 'map_data' not in st.session_state: st.session_state.map_data = pd.DataFrame()

# --- 2. تحميل البيانات (حل السطر 38 للأبد) ---
@st.cache_data
def load_data_rock_solid():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # استخدام .apply لضمان عدم حدوث AttributeError
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].fillna('UNKNOWN').apply(lambda x: str(x).upper().strip())
        return df
    except: return pd.DataFrame()

df = load_data_rock_solid()

# --- 3. محرك الـ AI (مهمته الصوت فقط) ---
def build_engineer_response(results_dict, user_query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = f"Engineer! Local Data: {results_dict}. User: {user_query}. Respond in natural Egyptian Ammiya. Be concise and professional."
        response = model.generate_content(prompt).text
        
        # توليد الصوت
        tts = gTTS(text=response, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        return response, audio_io.getvalue()
    except: return "الداتا جاهزة يا هندسة بس فيه ضغط على السيرفر.", None

# --- 4. واجهة التشغيل ---
st.title("📡 Seshat AI: Spectrum Intelligence")
query = st.text_input("Engineering Command:", placeholder="مثلاً: مصر فيها كام محطة صوت؟")

if st.button("🚀 Run System Analysis") and query:
    q = query.lower()
    
    # فلترة محلية صارمة (Local Filtering)
    adm_target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    filtered = df[df['adm'] == adm_target] if adm_target != "GLOBAL" else df
    
    # منطق البحث المتعدد
    stats = {}
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        stats["Television"] = len(filtered[filtered['station_class'] == 'BT'])
    if any(x in q for x in ["sound", "صوت", "إذاعة", "bc"]):
        stats["Sound"] = len(filtered[filtered['station_class'] == 'BC'])
    
    if not stats: stats["Total Stations"] = len(filtered)

    # تشغيل الـ AI للصوت فقط
    with st.spinner("Synchronizing with Gemini..."):
        msg, audio = build_engineer_response(stats, query)
        st.session_state.text_msg = msg
        st.session_state.voice_response = audio
        st.session_state.map_data = filtered.head(100) # عينة للخريطة

# --- 5. مرحلة العرض (مستقلة تماماً عن الـ Loop) ---
if st.session_state.text_msg:
    if st.session_state.voice_response:
        st.audio(st.session_state.voice_response, format='audio/mp3')
    
    st.info(st.session_state.text_msg)
    
    # عرض الأرقام
    c1, c2 = st.columns(2)
    c1.metric("Selected Admin", adm_target if 'adm_target' in locals() else "Global")
    c2.write(stats if 'stats' in locals() else "")

    # الخريطة (لو فيه إحداثيات)
    if not st.session_state.map_data.empty and 'lat' in st.session_state.map_data.columns:
        m = folium.Map(location=[26, 30], zoom_start=5)
        # كود إضافة الـ Markers هنا
        st_folium(m, width=800, height=400, key="stable_map")
