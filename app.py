import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Final Spectrum Core", layout="wide")

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
    # حل الـ AttributeError: استخدام .str قبل .upper
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# --- محرك الـ AI للرد العامي ---
def get_ai_voice_response(count, country, service, n_type, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash') 
        prompt = f"""
        Answer as an Egyptian Telecommunications Engineer.
        Data: {count} {service} stations for {country}. Filter: {n_type if n_type else 'None'}.
        User Question: "{query}"
        Rules: Respond only in natural Egyptian Arabic (Ammiya). 
        Be professional but friendly. No rigid templates like "Ya handsa" unless it fits.
        """
        return model.generate_content(prompt).text
    except:
        return f"يا بطل، لقيت {count} محطة {service} في {country}."

# --- UI ---
st.title("📡 Seshat AI: Precision Spectrum Dashboard")
query = st.text_input("Engineering Command:", placeholder="e.g., hya masr 3ndha kam m7ta sound notice type TB2")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # فلترة البيانات
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target] if target != "GLOBAL" else df
    
    n_type = re.search(r'tb\d+', q).group(0).upper() if re.search(r'tb\d+', q) else None
    if n_type: f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q for x in ["tv", "bt", "تلفزيون"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    s_label = "Television" if is_tv else "Sound Broadcasting"
    
    res_count = len(f_df)

    with st.spinner("Processing Logic Layer..."):
        ai_msg = get_ai_voice_response(res_count, target, s_label, n_type, query)
        
        # تحويل الصوت بأمان
        try:
            tts = gTTS(text=ai_msg, lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
        except:
            audio_data = None
        
        # تخزين النتائج بأمان لتفادي الـ KeyError
        st.session_state.results = {
            'msg': ai_msg, 
            'audio': audio_data, 
            'df': f_df, 
            'count': res_count, 
            'adm': target,
            'n_type': n_type
        }

# --- عرض النتائج (Check if exists) ---
if 'results' in st.session_state:
    res = st.session_state.results
    
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    
    st.info(res['msg'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(label=f"Total {res['adm']} Records", value=res['count'])
        if res['n_type']:
            st.warning(f"Filtered by: {res['n_type']}")
        
    with col2:
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, 
                           tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr="CartoDB")
            for _, row in m_df.head(100).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00FBFF", fill=True).add_to(m)
            st_folium(m, key="final_map", width=700, height=400)
        else:
            st.error("No valid coordinates found for mapping.")
