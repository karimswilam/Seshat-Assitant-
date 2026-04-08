import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
import re

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI Dashboard", layout="wide")

# دالة تحويل الإحداثيات (DMS to Decimal)
def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", str(dms_str))
        if not parts: return None, None
        res = {}
        for deg, mins, sec, direction in parts:
            decimal = int(deg) + int(mins)/60 + int(sec)/3600
            if direction in ['S', 'W']: decimal *= -1
            res[direction] = decimal
        return res.get('N') or res.get('S'), res.get('E') or res.get('W')
    except: return None, None

@st.cache_data
def load_and_fix_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    # الربط البرمجي بين الكود ونوع الخدمة
    df['service_label'] = df['station_class'].map({'bc': 'Sound', 'bt': 'TV'}).fillna('Other')
    return df

df = load_and_fix_data()

# --- واجهة المستخدم ---
st.title("📡 Seshat AI: Spectrum Intelligence Dashboard")

query = st.text_input("Enter Engineering Command:", placeholder="e.g., hya masr 3ndha kam m7ta sound")
run_btn = st.button("🚀 Analyze Data")

if run_btn and query:
    # 2. منطق الفلترة (Filtering Logic)
    target_adm = "EGY" if any(x in query.lower() for x in ["egy", "egypt", "مصر"]) else \
                 "ISR" if any(x in query.lower() for x in ["isr", "israel", "إسرائيل"]) else None
    
    f_df = df[df['adm'] == target_adm] if target_adm else df
    
    # تحديد نوع الخدمة المطلوبة
    if "tv" in query.lower():
        f_df = f_df[f_df['service_label'] == 'TV']
        service_title = "TV Broadcasting"
    else:
        f_df = f_df[f_df['service_label'] == 'Sound']
        service_title = "Sound Broadcasting"

    final_count = len(f_df)

    # --- العرض (Results Display) ---
    col_flag, col_metric = st.columns([1, 3])
    with col_flag:
        st.markdown(f"<h1 style='font-size: 100px; margin:0;'>{FLAGS.get(target_adm, '🌐')}</h1>", unsafe_allow_html=True)
    with col_metric:
        st.metric(label=f"Total {service_title} in {target_adm or 'Global'}", value=f"{final_count:,}")

    st.write("---")
    
    # 3. الخريطة (The Map) - تم إصلاح القوس هنا
    st.subheader("📍 Geospatial Distribution")
    map_df = f_df.dropna(subset=['lat', 'lon'])
    
    if not map_df.empty:
        m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], 
                       zoom_start=6, tiles="CartoDB dark_matter")
        
        for _, row in map_df.head(200).iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=5,
                color="#00d4ff",
                fill=True,
                popup=f"Site: {row.get('location', 'Unknown')}"
            ).add_to(m)
        
        # تصليح الـ Syntax: تأكد إن القوس مقفول صح
        st_folium(m, width=1200, height=500, key="stable_map")
    else:
        st.warning("No valid coordinates found for mapping in this selection.")
