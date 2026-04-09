import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI Core", layout="wide")

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
    # التحويل وتخزينه في الكاش فوراً
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    # توحيد حالة الحروف في الأعمدة الأساسية
    for col in ['adm', 'station_class']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# --- الذاكرة المؤقتة (Session State) لمنع الطيران ---
if 'results' not in st.session_state:
    st.session_state.results = None

st.title("📡 Seshat AI: Precision Spectrum Dashboard")

# Input Section
query = st.text_input("Engineering Query:", placeholder="e.g., hya masr 3ndha kam m7tet sound")
if st.button("🚀 Analyze Data"):
    # منطق الفلترة المرن
    q = query.lower()
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel", "إسرائيل"]) else None
    
    f_df = df[df['adm'] == target] if target else df
    
    # فلترة النوع (Sound/BC or TV/BT)
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        s_type = "TV Stations"
    else:
        f_df = f_df[f_df['station_class'] == 'BC']
        s_type = "Sound Stations"
    
    # حفظ النتائج في الـ Session
    st.session_state.results = {
        'df': f_df,
        'count': len(f_df),
        'adm': target,
        'label': s_type
    }

# --- العرض الثابت ---
if st.session_state.results:
    res = st.session_state.results
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown(f"## {FLAGS.get(res['adm'], '🌐')} {res['adm']}")
        st.metric(label=f"Total {res['label']}", value=res['count'])
    
    with c2:
        st.subheader("📍 Geospatial Trace")
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            # استخدام zoom_start ثابت وسنتر محسوب
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], 
                           zoom_start=7, tiles="CartoDB dark_matter")
            for _, row in m_df.head(150).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=4, color="#00d4ff", fill=True).add_to(m)
            
            # أهم سطر: key ثابت و use_container_width
            st_folium(m, key="fixed_map_v7", width=700, height=450, returned_objects=[])
        else:
            st.error("Data filtered but no valid coordinates found for mapping.")
