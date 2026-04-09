import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Spectrum Core", layout="wide")

# --- معالجة البيانات ---
def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", str(dms_str))
        if not parts: return None, None
        res = {}
        for deg, mins, sec, direction in parts:
            decimal = float(deg) + float(mins)/60 + float(sec)/3600
            if direction in ['S', 'W']: decimal *= -1
            res[direction] = decimal
        return res.get('N') or res.get('S'), res.get('E') or res.get('W')
    except: return None, None

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    # الحل النهائي لـ AttributeError: استخدام .str
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# --- محرك الـ AI للرد العامي ---
def get_ai_voice_response(count, country, service, n_type, query):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash') 
    
    prompt = f"""
    Context: Telecom Data Analysis.
    Data: Found {count} {service} stations for {country}. Filter: {n_type}.
    User Query: "{query}"
    Task: Respond directly in natural Egyptian Arabic (Ammiya). 
    Do not use generic "ya handsa" or fixed templates. 
    Just answer the question based on the numbers provided in a helpful, colleague-like way.
    """
    try:
        return model.generate_content(prompt).text
    except:
        return f"فيه {count} محطة {service} في {country}."

# --- UI ---
st.title("📡 Seshat AI: Intelligent Spectrum Dashboard")
query = st.text_input("اسأل عن محطات الترددات (مثلاً: مصر فيها كام محطة TB2؟):")

if st.button("🚀 تحليل") and query:
    q = query.lower()
    
    # فلترة سريعة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    n_type = re.search(r'tb\d+', q).group(0).upper() if re.search(r'tb\d+', q) else None
    if n_type: f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q for x in ["tv", "bt", "تلفزيون"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    s_label = "تلفزيون" if is_tv else "إذاعة صوتية"
    
    res_count = len(f_df)

    with st.spinner("جاري صياغة الرد..."):
        ai_msg = get_ai_voice_response(res_count, target, s_label, n_type, query)
        tts = gTTS(text=ai_msg, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        
        st.session_state.last_res = {
            'msg': ai_msg, 'audio': audio_fp.getvalue(), 
            'df': f_df, 'count': res_count, 'adm': target
        }

if 'last_res' in st.session_state:
    res = st.session_state.last_res
    st.audio(res['audio'], format='audio/mp3')
    st.info(res['msg'])
    
    # عرض الخريطة
    m_df = res['df'].dropna(subset=['lat', 'lon'])
    if not m_df.empty:
        m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, 
                       tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr="CartoDB")
        for _, row in m_df.head(100).iterrows():
            folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00FBFF", fill=True).add_to(m)
        st_folium(m, key="spectrum_map", width=900, height=500)
