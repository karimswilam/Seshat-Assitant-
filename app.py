import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium

# 1. نظام التعريفات السريع
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪', 'KWT': '🇰🇼'}

st.set_page_config(page_title="Seshat Core", page_icon="📡", layout="wide")

@st.cache_data
def load_clean_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    # توحيد مسميات الأعمدة عشان الخريطة متهنجش
    # استبدل 'lat_col' و 'long_col' بالأسماء الحقيقية في ملفك لو عارفها
    df.columns = [c.lower().strip() for c in df.columns]
    df['service'] = df['station_class'].map({'bc': 'Sound', 'bt': 'TV'}).fillna('Other')
    return df

df = load_clean_data()

# --- Dashboard Layout ---
st.title("📡 Seshat AI: Precision Spectrum Engine")
query = st.text_input("Engineering Query:", placeholder="e.g., TV stations in Egypt")

if st.button("🚀 Execute Analysis") and query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

    # Logic: اكتشاف الدولة والخدمة
    adm = None
    if "egy" in query.lower() or "مصر" in query.lower(): adm = "EGY"
    elif "isr" in query.lower() or "israel" in query.lower(): adm = "ISR"
    
    f_df = df[df['adm'] == adm] if adm else df
    if "tv" in query.lower(): f_df = f_df[f_df['service'] == 'TV']
    elif "sound" in query.lower(): f_df = f_df[f_df['service'] == 'Sound']

    # الإجابة المختصرة (No hallucination)
    res_count = len(f_df)
    ans = f"Admin: {adm if adm else 'Global'} | Service: {query} | Total Records: {res_count} units."
    
    # --- العرض المرئي (بدون رغي) ---
    st.markdown(f"### {FLAGS.get(adm, '🌐')} {ans}")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        # Pie Chart مختصر
        fig = px.pie(f_df, names='intent', hole=0.6, title="Coordination Status")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📍 Real-time Geospatial Trace")
        # Preprocessing: التأكد من وجود أعمدة الإحداثيات
        # لو الأعمدة عندك أساميها مختلفة (مثلاً Latitude)، غيرها هنا:
        lat_col = 'lat' if 'lat' in f_df.columns else None
        lon_col = 'long' if 'long' in f_df.columns else None

        if lat_col and lon_col:
            m_df = f_df.dropna(subset=[lat_col, lon_col])
            if not m_df.empty:
                m = folium.Map(location=[m_df[lat_col].mean(), m_df[lon_col].mean()], 
                               zoom_start=6, tiles="CartoDB dark_matter")
                for _, row in m_df.head(100).iterrows(): # أول 100 لضمان السرعة
                    folium.CircleMarker([row[lat_col], row[lon_col]], radius=4, color="#00d4ff").add_to(m)
                st_folium(m, width=700, height=450)
            else:
                st.warning("Coordinates found but empty for this selection.")
        else:
            st.error(f"Geospatial Error: Columns 'lat'/'long' not found in CSV. Existing columns: {list(df.columns)}")
