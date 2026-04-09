import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from gtts import gTTS
import io

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI: Spectrum Intelligence", layout="wide")

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
    # تنظيف الأعمدة
    cols_to_fix = ['adm', 'station_class', 'notice type']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# الذاكرة المؤقتة (Session State)
if 'results' not in st.session_state:
    st.session_state.results = None

st.title("📡 Seshat AI: Precision Spectrum Dashboard")

query = st.text_input("Engineering Query:", placeholder="e.g., masr 3ndha kam m7ta sound notice type TB2")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # 1. منطق الفلترة المتقدم
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel", "إسرائيل"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    # فلترة Notice Type (مثل TB2)
    n_type = None
    notice_match = re.search(r'tb\d+', q) # يبحث عن TB متبوعة برقم
    if notice_match:
        n_type = notice_match.group(0).upper()
        f_df = f_df[f_df['notice type'] == n_type]
    
    # فلترة النوع
    if any(x in q for x in ["tv", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        s_label = "TV Broadcasting"
    else:
        f_df = f_df[f_df['station_class'] == 'BC']
        s_label = "Sound Broadcasting"

    res_count = len(f_df)
    
    # 2. تحويل الرد لصوت (Humanized English)
    response_text = f"Engineer, for {target or 'Global'}, I found {res_count} {s_label} units."
    if n_type: response_text += f" specifically under notice type {n_type}."
    
    tts = gTTS(text=response_text, lang='en')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    
    st.session_state.results = {
        'df': f_df,
        'count': res_count,
        'adm': target,
        'label': s_label,
        'audio': audio_fp.getvalue(),
        'n_type': n_type
    }

# --- العرض (UI) ---
if st.session_state.results:
    res = st.session_state.results
    
    # التأكد من وجود مفتاح الصوت قبل التشغيل (حل الـ KeyError)
    if 'audio' in res:
        st.audio(res['audio'], format='audio/mp3')
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"## {FLAGS.get(res['adm'], '🌐')} {res['adm']}")
        st.metric(label=f"Total {res['label']}", value=res['count'])
        if res['n_type']:
            st.info(f"Filtered by Notice Type: {res['n_type']}")
        
    with c2:
        st.subheader("📍 Geospatial Trace")
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], 
                           zoom_start=6, tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB')
            for _, row in m_df.head(200).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=4, color="#00FBFF", fill=True).add_to(m)
            st_folium(m, key="v9_map", width=700, height=450, returned_objects=[])
