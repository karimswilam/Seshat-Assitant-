import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
import re

# 1. دالة التحويل الهندسية (DMS to Decimal)
def dms_to_decimal(dms_str):
    try:
        # استخراج الأرقام والاتجاهات باستخدام Regex
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", str(dms_str))
        if not parts: return None, None
        
        results = {}
        for deg, mins, sec, direction in parts:
            decimal = int(deg) + int(mins)/60 + int(sec)/3600
            if direction in ['S', 'W']: decimal *= -1
            results[direction] = decimal
        
        # إرجاع الـ Lat (N/S) والـ Lon (E/W)
        lat = results.get('N') or results.get('S')
        lon = results.get('E') or results.get('W')
        return lat, lon
    except:
        return None, None

st.set_page_config(page_title="Seshat AI Core", layout="wide")

@st.cache_data
def load_and_preprocess():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # تحويل عمود الـ location لـ lat و lon لو موجود بالفورمات اللي بعته
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    
    df['service'] = df['station_class'].map({'bc': 'Sound', 'bt': 'TV'}).fillna('Other')
    return df

df = load_and_preprocess()

# --- واجهة الـ Dashboard ---
st.title("📡 Seshat AI: Location Intelligence")
query = st.text_input("Engineering Query:", placeholder="recorded TV in Egypt")

if st.button("🚀 Analyze & Map") and query:
    # (نفس منطق الفلترة السابق Adm و Service)
    target_adm = "EGY" if "egy" in query.lower() else ("ISR" if "isr" in query.lower() else None)
    f_df = df[df['adm'] == target_adm] if target_adm else df
    
    # عرض النتائج
    st.subheader(f"Analysis for {target_adm if target_adm else 'Global'}")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        # إجابة الـ AI المختصرة
        st.info(f"System found {len(f_df)} records matching your query.")
        fig = px.pie(f_df, names='intent', hole=0.6)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # الخريطة الثابتة والذكية
        st.subheader("📍 Interactive Geospatial View")
        m_df = f_df.dropna(subset=['lat', 'lon'])
        
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], 
                           zoom_start=6, tiles="CartoDB dark_matter")
            for _, row in m_df.head(100).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00d4ff", fill=True).add_to(m)
            st_folium(m, width=700, height=450)
        else:
            st.warning("Could not parse coordinates from the 'location' column.")
