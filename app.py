import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
from gtts import gTTS
import io

# 1. نظام الأعلام المتطور
FLAGS = {
    'EGY': '🇪🇬', 'ARS': '🇸🇦', 'ISR': '🇮🇱', 
    'UAE': '🇦🇪', 'KWT': '🇰🇼', 'JOR': '🇯🇴'
}

st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

# CSS لتنسيق العلم والتقرير
st.markdown("""
    <style>
    .report-card { background-color: #1a1c23; border-radius: 15px; padding: 25px; border-left: 8px solid #00d4ff; }
    .flag-header { font-size: 50px; margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound/Radio', 'BT': 'Television'}).fillna('Other')
    return df

df = load_data()

# --- Header ---
st.title("📡 Seshat AI: Geospatial Coordination Core")
st.write("---")

# --- Logic Processing ---
query = st.text_input("Engineering Query (with Location Intelligence):", placeholder="e.g., show me TV stations in Israel")
if st.button("🚀 Analyze & Map") and query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    # محرك البحث (Israel/Egypt/Saudi)
    adm_map = {'israel': 'ISR', 'isr': 'ISR', 'egypt': 'EGY', 'egy': 'EGY', 'saudi': 'ARS', 'ars': 'ARS'}
    target_adm = next((code for word, code in adm_map.items() if word in query.lower()), None)
    
    # الفلترة
    filtered_df = df[df['Adm'] == target_adm] if target_adm else df
    if "tv" in query.lower(): filtered_df = filtered_df[filtered_df['Service_Type'] == 'Television']
    elif "sound" in query.lower(): filtered_df = filtered_df[filtered_df['Service_Type'] == 'Sound/Radio']

    # الرد الصوتي والنصي
    report = model.generate_content(f"Report: {len(filtered_df)} records found for {target_adm}. One formal sentence.").text
    
    # --- Display Results ---
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.markdown(f"<div class='flag-header'>{FLAGS.get(target_adm, '🌐')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='report-card'><h4>{target_adm} Analysis</h4><p>{report}</p></div>", unsafe_allow_html=True)
        
        # Pie Chart (Fixed Colors)
        fig = px.pie(filtered_df, names='Intent', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📍 Geospatial Distribution")
        # تنظيف الداتا من الـ NaN في الـ Lat/Long قبل الرسم
        map_data = filtered_df.dropna(subset=['lat', 'long']).head(100) # عرض أول 100 لتجنب الثقل
        
        if not map_data.empty:
            m = folium.Map(location=[map_data['lat'].mean(), map_data['long'].mean()], zoom_start=6, tiles="CartoDB dark_matter")
            for _, row in map_data.iterrows():
                folium.CircleMarker(
                    location=[row['lat'], row['long']],
                    radius=5,
                    color="#00d4ff",
                    fill=True,
                    popup=f"Station: {row.get('location', 'Unknown')}"
                ).add_to(m)
            st_folium(m, width=700, height=500)
        else:
            st.warning("No GPS coordinates found for this selection.")
