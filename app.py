import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
import re

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI Core", layout="wide")

def dms_to_decimal(dms_str):
    try:
        # regex محسن للتعامل مع أي مسافات زيادة
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
def load_and_fix_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # تحويل الإحداثيات
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    
    # تنظيف عمود الـ ADM (تحويله لحروف كبيرة وإزالة المسافات)
    if 'adm' in df.columns:
        df['adm'] = df['adm'].astype(str).str.upper().str.strip()
        
    return df

df = load_and_fix_data()

# --- Dashboard ---
st.title("📡 Seshat AI: Precision Spectrum Dashboard")

query = st.text_input("Engineering Query:", placeholder="e.g., hya masr 3ndha kam m7ta sound")

if st.button("🚀 Analyze Data") and query:
    # منطق التعرف الذكي على الدولة
    target_adm = None
    q_lower = query.lower()
    if "masr" in q_lower or "مصر" in q_lower or "egy" in q_lower: target_adm = "EGY"
    elif "israel" in q_lower or "إسرائيل" in q_lower or "isr" in q_lower: target_adm = "ISR"
    
    # الفلترة الأساسية
    if target_adm:
        f_df = df[df['adm'] == target_adm]
    else:
        f_df = df.copy()

    # فلترة الخدمة (راديو BC أو تلفزيون BT)
    if "tv" in q_lower or "تلفزيون" in q_lower:
        f_df = f_df[f_df['station_class'].str.contains('BT', na=False, case=False)]
        service_label = "TV Stations"
    else:
        f_df = f_df[f_df['station_class'].str.contains('BC', na=False, case=False)]
        service_label = "Sound Stations"

    res_count = len(f_df)

    # --- العرض المرئي ---
    if res_count > 0:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"<h1 style='font-size: 80px;'>{FLAGS.get(target_adm, '🌐')}</h1>", unsafe_allow_html=True)
            st.metric(label=f"Total {service_label}", value=f"{res_count}")
        
        with c2:
            st.subheader("📍 Geospatial Trace")
            m_df = f_df.dropna(subset=['lat', 'lon'])
            if not m_df.empty:
                m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, tiles="CartoDB dark_matter")
                for _, row in m_df.head(100).iterrows():
                    folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00d4ff", fill=True).add_to(m)
                st_folium(m, width=800, height=400, key="fixed_map")
            else:
                st.warning("Coordinates found in data but format is non-standard.")
    else:
        st.error(f"No records found for ADM: {target_adm} and Service: {service_label}. Please check CSV values.")

# Debugger (للإطمئنان فقط)
with st.expander("🛠️ Internal Data Audit"):
    st.write("Unique Admins in File:", df['adm'].unique() if 'adm' in df.columns else "Column not found")
    st.write("Unique Station Classes:", df['station_class'].unique() if 'station_class' in df.columns else "Column not found")
