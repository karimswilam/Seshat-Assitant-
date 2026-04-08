import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_folium import st_folium
import folium
from gtts import gTTS
import io

# 1. المابينج الهندسي والأعلام (The Identity Core)
FLAGS = {
    'ISR': '🇮🇱',
    'EGY': '🇪🇬',
    'ARS': '🇸🇦',
    'UAE': '🇦🇪',
    'KWT': '🇰🇼'
}

st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

# CSS لتنسيق العلم والتقرير
st.markdown("""
    <style>
    .report-card { background-color: #1a1c23; border-radius: 15px; padding: 25px; border-left: 8px solid #00d4ff; margin-bottom: 20px; }
    .flag-style { font-size: 80px; text-align: center; margin-bottom: -20px; }
    .stApp { background-color: #0e1117; color: white; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    # تنظيف مسميات الخدمة
    df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound/Radio', 'BT': 'Television'}).fillna('Other')
    return df

df = load_data()

# --- Header ---
st.title("📡 Seshat AI: Geospatial Spectrum Core")
st.write("---")

# --- Control Center ---
col_in, col_empty = st.columns([2, 1])
with col_in:
    query = st.text_input("Engineering Query (Location-Aware):", placeholder="e.g., How many TV stations in Israel?")
    analyze_btn = st.button("🚀 Analyze & Map Intelligence")

if analyze_btn and query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

    with st.spinner("Processing Geospatial Data..."):
        try:
            # اكتشاف الدولة أوتوماتيكياً
            target_adm = None
            if any(x in query.lower() for x in ["israel", "isr", "إسرائيل"]): target_adm = "ISR"
            elif any(x in query.lower() for x in ["egypt", "egy", "مصر"]): target_adm = "EGY"
            elif any(x in query.lower() for x in ["saudi", "ars", "السعودية"]): target_adm = "ARS"

            # فلترة البيانات
            f_df = df[df['Adm'] == target_adm] if target_adm else df
            
            # فلترة نوع الخدمة
            service_label = "General Spectrum"
            if "tv" in query.lower() or "television" in query.lower():
                f_df = f_df[f_df['Service_Type'] == 'Television']
                service_label = "TV"
            elif "sound" in query.lower() or "radio" in query.lower():
                f_df = f_df[f_df['Service_Type'] == 'Sound/Radio']
                service_label = "Sound/Radio"

            # توليد التقرير
            report_prompt = f"System Report: {len(f_df)} {service_label} records for Adm:{target_adm}. Formal tone."
            ai_report = model.generate_content(report_prompt).text

            # --- النتائج (Layout) ---
            row1_col1, row1_col2 = st.columns([1, 1.5])
            
            with row1_col1:
                # عرض العلم
                st.markdown(f"<div class='flag-style'>{FLAGS.get(target_adm, '🌐')}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='report-card'><h3>{target_adm if target_adm else 'Global'} Report</h3><p>{ai_report}</p></div>", unsafe_allow_html=True)
                
                # Pie Chart
                fig = px.pie(f_df, names='Intent', hole=0.5, title=f"{service_label} Status", 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)

            with row1_col2:
                st.subheader("📍 Geospatial Mapping")
                # عرض الخريطة لو فيه إحداثيات (أول 50 نقطة للسرعة)
                map_df = f_df.dropna(subset=['lat', 'long']).head(50)
                
                if not map_df.empty:
                    m = folium.Map(location=[map_df['lat'].mean(), map_df['long'].mean()], 
                                   zoom_start=7, tiles="CartoDB dark_matter")
                    for _, row in map_df.iterrows():
                        folium.Marker(
                            [row['lat'], row['long']],
                            popup=f"Station: {row.get('location', 'N/A')}",
                            icon=folium.Icon(color="blue", icon="broadcast-tower", prefix="fa")
                        ).add_to(m)
                    st_folium(m, width=700, height=500)
                else:
                    st.info("No GPS coordinates available for this view.")

            # الصوت
            tts = gTTS(text=ai_report, lang='en')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"System Error: {e}")

# Trace Log
with st.expander("🛠️ Seshat Trace Log"):
    st.code(f"[SYS] V4.1 Online\n[GEO] Map Layer: Folium\n[ADM] Current Target: {target_adm if 'target_adm' in locals() else 'None'}")
