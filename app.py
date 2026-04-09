import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Ultra Core", layout="wide")

# --- 1. إصلاح معالجة البيانات (السطر 38 النهائي) ---
@st.cache_data
def load_data_final():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # الحل الجذري للـ AttributeError
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except: return pd.DataFrame()

df = load_data_final()

# --- 2. محرك الـ AI (دعم الرد المزدوج والعامية) ---
def get_combined_response(counts, country, services, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        details = ", ".join([f"{count} {svc}" for svc, count in counts.items()])
        prompt = f"""
        Respond as an Egyptian Telecom Engineer in Ammiya.
        Data: For {country}, we found: {details}.
        User Question: "{query}"
        Instruction: Provide a natural, friendly response in Egyptian Arabic including all found numbers. 
        Focus on technical accuracy.
        """
        response_text = model.generate_content(prompt).text
        
        # تحويل الصوت
        tts = gTTS(text=response_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return response_text, audio_fp.getvalue()
    except:
        return "حصل مشكلة في توليد الرد، بس الداتا قدامك اهي.", None

# --- 3. واجهة التحكم الذكية ---
st.title("📡 Seshat AI: Spectrum Intelligence Dashboard")
query = st.text_input("Engineering Query:", placeholder="مثلاً: مصر فيها كام محطة إذاعة وتلفزيون؟")

if st.button("🚀 Analyze & Speak") and query:
    q = query.lower()
    
    # تحديد الدولة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target] if target != "GLOBAL" else df
    
    # دعم البحث المزدوج (TV & Sound)
    counts = {}
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        counts["Television"] = len(f_df[f_df['station_class'] == 'BT'])
    if any(x in q for x in ["sound", "صوت", "إذاعة", "bc"]):
        counts["Sound Broadcasting"] = len(f_df[f_df['station_class'] == 'BC'])
    
    # لو مسألش عن حاجة محددة، نعرض كله
    if not counts:
        counts = {"Total Records": len(f_df)}

    with st.spinner("بيجهز الرد المصري..."):
        msg, audio = get_combined_response(counts, target, counts.keys(), query)
        
        st.session_state.ultra_res = {
            'msg': msg, 'audio': audio, 'counts': counts, 'adm': target
        }

# --- 4. العرض الصوتي والبصري المستقر ---
if 'ultra_res' in st.session_state:
    res = st.session_state.ultra_res
    
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    
    st.success(res['msg'])
    
    # عرض العدادات لكل نوع
    cols = st.columns(len(res['counts']))
    for i, (svc, count) in enumerate(res['counts'].items()):
        cols[i].metric(label=svc, value=count)
