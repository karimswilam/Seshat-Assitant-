import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Core", layout="wide")

# --- معالجة البيانات ---
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # حل مشكلة الـ AttributeError (استخدام .str)
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            
    # تحويل الإحداثيات (بافتراض وجود عمود location)
    if 'location' in df.columns:
        # كود الـ dms_to_decimal هنا
        pass 
    return df

df = load_data()

# --- محرك الـ AI (للرد العامي الصرف) ---
def get_ai_response(count, country, service, n_type, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = f"""
        Context: Spectrum Management Analysis.
        Found {count} {service} stations for {country}. Filter: {n_type}.
        Question: "{query}"
        Task: Respond naturally in Egyptian Arabic (Ammiya) as a colleague. 
        Focus on the data. No fixed templates.
        """
        return model.generate_content(prompt).text
    except:
        return f"فيه {count} محطة {service} في {country}."

# --- واجهة البرنامج ---
st.title("📡 Seshat AI: Precision Dashboard")
query = st.text_input("Engineering Query:", placeholder="مثلاً: مصر فيها كام محطة TB2؟")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # منطق الفلترة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target] if target != "GLOBAL" else df
    
    n_type = re.search(r'tb\d+', q).group(0).upper() if re.search(r'tb\d+', q) else None
    if n_type: f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q for x in ["tv", "bt", "تلفزيون"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    
    res_count = len(f_df)

    with st.spinner("AI is thinking..."):
        msg = get_ai_response(res_count, target, "TV" if is_tv else "Sound", n_type, query)
        
        # توليد الصوت بأمان
        audio_data = None
        try:
            tts = gTTS(text=msg, lang='ar')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            audio_data = fp.getvalue()
        except: pass

        # أهم خطوة: تخزين كل شيء لتفادي الـ KeyError
        st.session_state.results = {
            'msg': msg, 'audio': audio_data, 'count': res_count,
            'adm': target, 'n_type': n_type, 'df': f_df
        }

# --- العرض الآمن للنتائج ---
if 'results' in st.session_state:
    res = st.session_state.results
    
    # 1. الصوت والرسالة
    if res.get('audio'):
        st.audio(res['audio'], format='audio/mp3')
    st.success(res['msg'])
    
    # 2. البيانات والجداول
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric(f"Total Stations ({res['adm']})", res['count'])
        if res['n_type']:
            st.info(f"Filtered by Notice: {res['n_type']}")
            
    with c2:
        # عرض الخريطة فقط لو فيه إحداثيات
        if 'lat' in res['df'].columns and not res['df']['lat'].dropna().empty:
            m = folium.Map(location=[res['df']['lat'].mean(), res['df']['lon'].mean()], zoom_start=6)
            # إضافة الماركرز هنا...
            st_folium(m, key="map_v14", width=700, height=400)
        else:
            st.warning("No geospatial data available for this view.")
