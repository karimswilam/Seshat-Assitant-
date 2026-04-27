import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import re
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# --- 1. SETTINGS & APP CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat Precision v30.0", page_icon="📡")

# التنسيق الهندسي للواجهة
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINEERING LOGIC (The "Brain") ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ISR': "https://flagcdn.com/w640/il.png",
    'TUR': "https://flagcdn.com/w640/tr.png"
}

# الـ Mapping اللي بيضمن إن النتائج متخرفش
COUNTRY_MAP = {
    'EGY': ['مصر', 'egypt', 'egy'],
    'ISR': ['اسرائيل', 'israel', 'isr'],
    'TUR': ['تركيا', 'turkey', 'tur']
}

# تصنيفات الـ ITU الدقيقة
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or dms_str == 'empty': return None
        parts = re.findall(r"(\d+)", str(dms_str))
        direction = re.findall(r"([NSEW])", str(dms_str).upper())
        if len(parts) >= 3 and direction:
            dd = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
            if direction[0] in ['S', 'W']: dd *= -1
            return dd
    except: return None

@st.cache_data
def load_and_clean_data():
    # محاولة تحميل الملف المتاح
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    
    df = pd.read_excel(files[0])
    df.columns = df.columns.str.strip()
    
    # تأمين وجود الأعمدة الأساسية
    col_fix = {'Administration': 'Adm', 'Adm': 'Adm', 'Notice Type': 'Notice Type'}
    df.rename(columns=col_fix, inplace=True)
    
    if 'Geographic Coordinates' in df.columns:
        coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
        if coords.shape[1] >= 2:
            df['lon_dec'] = coords[0].apply(dms_to_decimal)
            df['lat_dec'] = coords[1].apply(dms_to_decimal)
    return df

# --- 4. THE VOICE ENGINE (FIXED) ---
def process_audio(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        # تحويل الـ bytes لملف WAV متوافق
        audio_file = io.BytesIO(audio_data['bytes'])
        with sr.AudioFile(audio_file) as source:
            recorded_audio = r.record(source)
            text = r.recognize_google(recorded_audio, language="ar-EG")
            return text
    except Exception as e:
        return None

# --- 5. MAIN INTERFACE ---
st.title("📡 Seshat Master Precision v30.0")
st.caption("Intelligence Control Center | International Coordination Framework")

data = load_and_clean_data()

# منطقة التحكم في الصوت والمدخلات
with st.container(border=True):
    col_a, col_b = st.columns([1, 3])
    with col_a:
        st.write("🎙️ Voice Input")
        audio_result = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key="v30_mic")
    
    input_text = ""
    if audio_result:
        with st.spinner("Analyzing Spectrum Signal..."):
            input_text = process_audio(audio_result)
            if input_text:
                st.success(f"Detected: {input_text}")
            else:
                st.error("Signal weak or unrecognized.")

    query = st.text_input("Confirm Spectrum Inquiry:", value=input_text)

# --- 6. EXECUTION & VISUALIZATION ---
if query and data is not None:
    q_low = query.lower()
    # تحديد الدول المطلوبة في الاستعلام
    target_adms = [code for code, keywords in COUNTRY_MAP.items() if any(k in q_low for k in keywords)]
    
    if target_adms:
        results = []
        filtered_df = data[data['Adm'].isin(target_adms)].copy()
        
        # 📊 Metrics & Comparison
        st.subheader("📊 Comparative Intelligence")
        m_cols = st.columns(len(target_adms))
        
        for idx, adm in enumerate(target_adms):
            adm_data = data[data['Adm'] == adm]
            asg = len(adm_data[adm_data['Notice Type'].isin(STRICT_ASSIG)])
            alt = len(adm_data[adm_data['Notice Type'].isin(STRICT_ALLOT)])
            total = asg + alt
            
            with m_cols[idx]:
                st.image(FLAGS.get(adm, ""), width=120)
                st.metric(label=f"Total Records ({adm})", value=total, delta=f"A:{asg} | L:{alt}")
                results.append({'Adm': adm, 'Assignments': asg, 'Allotments': alt})

        # 📈 Visual Dashboards (التي تم استعادتها)
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.write("📉 Distribution by Service Type")
            fig_bar = px.bar(pd.DataFrame(results), x='Adm', y=['Assignments', 'Allotments'], barmode='group', color_discrete_sequence=['#1E3A8A', '#3B82F6'])
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c2:
            if 'lat_dec' in filtered_df.columns and not filtered_df['lat_dec'].isna().all():
                st.write("🗺️ Geospatial Deployment")
                fig_map = px.scatter_mapbox(filtered_df, lat="lat_dec", lon="lon_dec", hover_name="Adm", zoom=4, height=300)
                fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)

        # 📋 Raw Data Table
        with st.expander("📑 View Detailed Spectrum Records"):
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("Please mention a valid Administration (e.g., Egypt, Israel) in your query.")
else:
    st.info("Waiting for input or Data.xlsx file to be present in the directory.")
