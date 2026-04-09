import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import re
from gtts import gTTS
import io

# إعدادات الصفحة
st.set_page_config(page_title="Seshat AI: Core", layout="wide")

# --- 1. معالجة البيانات بأمان (حل الـ AttributeError) ---
@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # حل السطر 38: استخدام .str قبل .upper() لتجنب الـ AttributeError
        string_cols = ['adm', 'station_class', 'notice type']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        # هندسة الإحداثيات (بافتراض وجود عمود location بصيغة DMS)
        if 'location' in df.columns:
            def quick_convert(val):
                try:
                    parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", str(val))
                    if not parts: return None, None
                    res = {}
                    for d, m, s, dir in parts:
                        dec = float(d) + float(m)/60 + float(s)/3600
                        if dir in ['S', 'W']: dec *= -1
                        res[dir] = dec
                    return res.get('N') or res.get('S'), res.get('E') or res.get('W')
                except: return None, None
            
            coords = df['location'].apply(quick_convert)
            df['lat'] = coords.apply(lambda x: x[0])
            df['lon'] = coords.apply(lambda x: x[1])
            
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

df = load_and_clean_data()

# --- 2. محرك الـ AI (بدون Fixed Templates) ---
def get_ai_speech(count, country, service, query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = f"Answer as an Egyptian Engineer. Context: {count} {service} stations found for {country}. User asked: {query}. Respond in natural Egyptian Ammiya, focus on facts."
        response = model.generate_content(prompt).text
        
        # تحويل الصوت
        tts = gTTS(text=response, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return response, fp.getvalue()
    except:
        return f"يا هندسة فيه {count} محطة {service} لـ {country}.", None

# --- 3. واجهة التحكم (Command Center) ---
st.title("📡 Seshat AI: Geospatial Spectrum Intelligence")
query = st.text_input("Enter Engineering Command:", placeholder="مثلاً: مصر فيها كام محطة صوتية TB2؟")

if st.button("🚀 Execute Analysis") and query:
    q_low = query.lower()
    
    # منطق الفلترة (Deterministic Logic)
    target = "EGY" if any(x in q_low for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q_low for x in ["isr", "israel"]) else "GLOBAL"
    f_df = df[df['adm'] == target] if target != "GLOBAL" else df
    
    n_type = re.search(r'tb\d+', q_low).group(0).upper() if re.search(r'tb\d+', q_low) else None
    if n_type: f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q_low for x in ["tv", "bt", "تلفزيون"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    
    # توليد الرد
    msg, audio = get_ai_speech(len(f_df), target, "TV" if is_tv else "Sound", query)
    
    # تخزين آمن في الـ Session لتفادي الـ KeyError (حل سطر 98 و 104)
    st.session_state['core_results'] = {
        'msg': msg, 'audio': audio, 'df': f_df, 
        'count': len(f_df), 'adm': target, 'n_type': n_type
    }

# --- 4. مرحلة العرض الآمن (Safe Rendering) ---
if 'core_results' in st.session_state:
    res = st.session_state['core_results']
    
    # تشغيل الصوت والرد
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    st.info(res['msg'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Total Records", res['count'])
        st.write(f"**Administration:** {res['adm']}")
        if res['n_type']: st.warning(f"Notice: {res['n_type']}")
        
    with col2:
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, tiles="CartoDB dark_matter")
            for _, r in m_df.head(50).iterrows():
                folium.CircleMarker([r['lat'], r['lon']], radius=4, color="#00FBFF", fill=True).add_to(m)
            st_folium(m, key="main_map", width=700, height=400)
        else:
            st.error("No valid coordinates found for this query.")
