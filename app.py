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

st.set_page_config(page_title="Seshat AI: Core", layout="wide")

# --- تحسين معالجة البيانات ---
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
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).upper().strip()
    return df

df = load_data()

# --- دالة الـ AI (The Brain) ---
def get_ai_response(count, country, service, n_type, query):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash') # استخدام Flash أسرع من Pro
    
    prompt = f"""
    Context: Telecommunications Spectrum Data.
    Data: {count} {service} stations found for {country}. Filter: {n_type}.
    Query: {query}
    Task: Respond as an Egyptian Engineer in concise Egyptian Arabic (Ammiya). 
    Focus on the numbers and technical facts directly. No generic intros.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return f"موجود {count} محطة {service} في {country}."

# --- UI Layout ---
st.title("📡 Seshat AI: Precision Engine")
query = st.text_input("Engineering Query:", key="user_query")

if st.button("🚀 Analyze") and query:
    q = query.lower()
    
    # 1. Python Fast Filtering
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    n_type = re.search(r'tb\d+', q).group(0).upper() if re.search(r'tb\d+', q) else None
    if n_type: f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q for x in ["tv", "bt"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    s_label = "تلفزيون" if is_tv else "إذاعة"
    
    res_count = len(f_df)

    # 2. AI Humanized Response & Voice
    with st.spinner("Seshat is processing..."):
        ai_text = get_ai_response(res_count, target, s_label, n_type, query)
        
        # تحويل الصوت
        tts = gTTS(text=ai_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        
        # حفظ في الـ Session
        st.session_state.current_results = {
            'text': ai_text,
            'audio': audio_fp.getvalue(),
            'df': f_df,
            'count': res_count,
            'adm': target
        }

# --- Display Section ---
if 'current_results' in st.session_state:
    res = st.session_state.current_results
    
    st.audio(res['audio'], format='audio/mp3')
    st.success(res['text'])
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric(label="Results Count", value=res['count'])
        st.markdown(f"**Target:** {FLAGS.get(res['adm'], '🌐')} {res['adm']}")
        
    with c2:
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, 
                           tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr="CartoDB")
            for _, row in m_df.head(100).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00FBFF", fill=True).add_to(m)
            st_folium(m, key="stable_map", width=700, height=400, returned_objects=[])
