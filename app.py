import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Data-Driven Core", layout="wide")

# --- 1. تحميل الداتا (حل الـ AttributeError النهائي) ---
@st.cache_data
def load_spectrum_data():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # إصلاح السطر 38: استخدام .str قبل أي عملية نصوص
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

df = load_spectrum_data()

# --- 2. محرك الـ AI (مهمته تحويل الداتا لصوت فقط) ---
def generate_voice_from_local_data(data_results, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # إحنا هنا بنجبر الـ AI يلتزم بالأرقام اللي بعتناها له
        context = f"""
        Strict Instruction: Use ONLY these numbers from our database.
        Results: {data_results}
        User Query: "{query}"
        Task: Respond in natural Egyptian Arabic (Ammiya). 
        Mention the exact numbers and names. Be professional like a Telecom Engineer.
        """
        response_text = model.generate_content(context).text
        
        tts = gTTS(text=response_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return response_text, audio_fp.getvalue()
    except:
        return "الأرقام اهي قدامك يا هندسة بس فيه مشكلة في الصوت.", None

# --- 3. المنطق المحلي (Local Logic First) ---
st.title("📡 Seshat AI: Spectrum Intelligence Dashboard")
query = st.text_input("Engineering Command:", placeholder="e.g., مصر فيها كام محطة إذاعة؟")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # فلترة محلية من الـ DataFrame (مش من دماغ الـ AI)
    target_adm = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target_adm] if target_adm != "GLOBAL" else df
    
    # حصر الخدمات
    is_tv = any(x in q for x in ["tv", "تلفزيون", "bt"])
    is_sound = any(x in q for x in ["sound", "صوت", "إذاعة", "bc"])
    
    local_results = {}
    if is_tv:
        local_results["Television"] = len(f_df[f_df['station_class'] == 'BT'])
    if is_sound:
        local_results["Sound"] = len(f_df[f_df['station_class'] == 'BC'])
    if not is_tv and not is_sound:
        local_results["Total Stations"] = len(f_df)

    # إرسال الداتا المحلية للـ AI عشان "ينطقها" بس
    with st.spinner("Analyzing Local Database..."):
        ai_msg, ai_audio = generate_voice_from_local_data(local_results, query)
        
        st.session_state.final_build = {
            'msg': ai_msg, 'audio': ai_audio, 'data': local_results, 'adm': target_adm
        }

# --- 4. العرض ---
if 'final_build' in st.session_state:
    res = st.session_state.final_build
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    
    st.info(res['msg'])
    
    # عرض الأرقام في كروت واضحة (عشان تتأكد إنها من الـ Excel)
    cols = st.columns(len(res['data']))
    for i, (key, val) in enumerate(res['data'].items()):
        cols[i].metric(label=f"{key} ({res['adm']})", value=val)
