import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
import re

# 1. إعدادات الهوية والأعلام
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪', 'JOR': '🇯🇴'}

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
    # التحويل لمرة واحدة وتخزينه في الكاش
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    df['service'] = df['station_class'].map({'bc': 'Sound', 'bt': 'TV'}).fillna('Other')
    return df

df = load_and_fix_data()

# --- Dashboard Header ---
st.title("📡 Seshat AI: Spectrum Intelligence Dashboard")
st.write("---")

# Input Section
col_query, col_btn = st.columns([4, 1])
with col_query:
    query = st.text_input("Enter Engineering Command:", placeholder="e.g., How many sound stations in Egypt?")
with col_btn:
    st.write(" ") # alignment
    run_btn = st.button("🚀 Analyze Data")

if run_btn and query:
    # المنطق الرقمي (Logic Only)
    target_adm = "EGY" if any(x in query.lower() for x in ["egy", "egypt", "مصر"]) else \
                 "ISR" if any(x in query.lower() for x in ["isr", "israel", "إسرائيل"]) else None
    
    f_df = df[df['adm'] == target_adm] if target_adm else df
    
    if "tv" in query.lower():
        f_df = f_df[f_df['service'] == 'TV']
        lbl = "TV Stations"
    else:
        f_df = f_df[f_df['service'] == 'Sound']
        lbl = "Sound Stations"

    final_count = len(f_df)
    
    # --- عرض النتائج (Power BI Style) ---
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1:
        # كارت الرقم (Metric Card)
        st.metric(label=f"{lbl} Count", value=f"{final_count:,}")
        st.markdown(f"### {FLAGS.get(target_adm, '🌐')} {target_adm or 'Global'}")

    with c2:
        # Pie Chart صغير للحالة
        fig = px.pie(f_df, names='intent', hole=0.7, height=200)
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    st.write("---")
    
    # الخريطة الكبيرة (Fixed Map)
    st.subheader("📍 Geospatial Distribution")
    map_df = f_df.dropna(subset=['lat', 'lon'])
    
    if not map_df.empty:
        # سنتر الخريطة على متوسط النقاط
        m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], 
                       zoom_start=6, tiles="CartoDB dark_matter")
        
        # إضافة النقاط
        for _, row in map_df.head(200).iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=4,
                color="#00d4ff",
                fill=True,
                popup=f"Site: {row.get('site name', 'Unknown')}"
            ).add_to(m)
        
        # عرض الخريطة مع منع الـ Rerun المفاجئ
        st_folium(m, width="100%", height=500, key
