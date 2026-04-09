import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from gtts import gTTS
import io

# 1. إعدادات الهوية والأعلام
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI Core", layout="wide")

# دالة تحويل الإحداثيات (DMS to Decimal)
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
    # تنظيف البيانات الأساسية
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# الذاكرة المؤقتة
if 'results' not in st.session_state:
    st.session_state.results = None

st.title("📡 Seshat AI: Precision Spectrum Dashboard")

# --- Logic Engine (Advanced Query Parsing) ---
query = st.text_input("Engineering Query:", placeholder="e.g., masr 3ndha kam m7ta sound notice type TB2")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # 1. تحديد الدولة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel", "إسرائيل"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    # 2. فلترة الـ Notice Type (مثلاً TB2)
    notice_match = re.search(r'notice type\s+(\w+)', q)
    if notice_match:
        n_type = notice_match.group(1).upper()
        f_df = f_df[f_df['notice type'] == n_type]
    
    # 3. فلترة نوع الخدمة (Sound/TV)
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        s_label = "TV Broadcasting"
    else:
        f_df = f_df[f_df['station_class'] == 'BC']
        s_label = "Sound Broadcasting"

    res_count = len(f_df)
    
    # 4. توليد الرد الصوتي (Humanized)
    country_name = "Egypt" if target == "EGY" else "the selected region"
    voice_text = f"Engineer, for {country_name}, I found {res_count} {s_label} units."
    if notice_match:
        voice_text += f" specifically for notice type {n_type}."
    
    tts = gTTS(text=voice_text, lang='en', slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    
    st.session_state.results = {
        'df': f_df,
        'count': res_count,
        'adm': target,
        'label': s_label,
        'audio': fp.getvalue()
    }

# --- UI Visualization ---
if st.session_state.results:
    res = st.session_state.results
    
    # تشغيل الصوت تلقائياً
    st.audio(res['audio'], format='audio/mp3')
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"## {FLAGS.get(res['adm'], '🌐')} {res['adm']}")
        st.metric(label=f"Total {res['label']}", value=res['count'])
        
    with col2:
        st.subheader("📍 Mapbox Professional Visualization")
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            # هنا استخدمنا Mapbox style عن طريق Folium
            m = folium.Map(
                location=[m_df['lat'].mean(), m_df['lon'].mean()], 
                zoom_start=6,
                tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attr='&copy; CartoDB'
            )
            for _, row in m_df.head(200).iterrows():
                folium.CircleMarker(
                    [row['lat'], row['lon']], 
                    radius=5, color="#00FBFF", fill=True, fill_opacity=0.7,
                    popup=f"Notice: {row.get('notice type', 'N/A')}"
                ).add_to(m)
            st_folium(m, key="professional_map", width=800, height=500, returned_objects=[])
