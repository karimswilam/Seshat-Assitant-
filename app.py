import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import re
import time
import plotly.express as px
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# --- 1. CONFIGURATION (Strict Restoration) ---
st.set_page_config(layout="wide", page_title="Seshat Precision v31.0")

# --- 2. THE INFRASTRUCTURE (The Fixed Logic You Trust) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ISR': "https://flagcdn.com/w640/il.png", 'TUR': "https://flagcdn.com/w640/tr.png"}
COUNTRY_MAP = {'EGY': ['مصر', 'egypt', 'egy'], 'ISR': ['اسرائيل', 'israel', 'isr'], 'TUR': ['تركيا', 'turkey', 'tur']}

# دقة الـ ITU في التصنيف (v17.0 Logic)
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. CORE FUNCTIONS ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or str(dms_str).strip().lower() == 'empty': return None
        parts = re.findall(r"(\d+)", str(dms_str))
        direction = re.findall(r"([NSEW])", str(dms_str).upper())
        if len(parts) >= 3 and direction:
            dd = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
            if direction[0] in ['S', 'W']: dd *= -1
            return dd
    except: return None

@st.cache_data
def load_spectrum_data():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    df = pd.read_excel(files[0])
    df.columns = df.columns.str.strip()
    # توحيد أسماء الأعمدة (Mapping)
    df.rename(columns={'Administration': 'Adm', 'Adm': 'Adm', 'Notice Type': 'Notice Type'}, inplace=True)
    if 'Geographic Coordinates' in df.columns:
        coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
        if coords.shape[1] >= 2:
            df['lon_dec'] = coords[0].apply(dms_to_decimal)
            df['lat_dec'] = coords[1].apply(dms_to_decimal)
    return df

# --- 4. THE VOICE ENGINE (Fixed for Mobile & Laptop) ---
def speech_to_text(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        # التعديل التقني: قراءة الـ Raw Bytes مباشرة كملف WAV
        audio_stream = io.BytesIO(audio_data['bytes'])
        with sr.AudioFile(audio_stream) as source:
            audio = r.record(source)
            # محاولة التعرف (عربي أولاً)
            return r.recognize_google(audio, language="ar-EG")
    except Exception as e:
        # لو فشل، جرب باللغة الإنجليزية كخيار بديل
        try:
            audio_stream.seek(0)
            with sr.AudioFile(audio_stream) as source:
                audio = r.record(source)
                return r.recognize_google(audio, language="en-US")
        except: return None

# --- 5. UI & ENGINE EXECUTION ---
st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>Seshat Master Precision v31.0</h1>", unsafe_allow_html=True)
db = load_spectrum_data()

# Intelligence Control Area
with st.expander("🎙️ Intelligence Control Center", expanded=True):
    c1, c2 = st.columns([1, 4])
    with c1:
        voice_raw = mic_recorder(start_prompt="Click to Speak", stop_prompt="Process Signal", key="v31_mic")
    
    detected_text = ""
    if voice_raw:
        with st.status("Analyzing Frequency Signal...") as s:
            detected_text = speech_to_text(voice_raw)
            if detected_text:
                s.update(label=f"Signal Captured: {detected_text}", state="complete")
            else:
                s.update(label="Signal weak or corrupted. Please try again.", state="error")

    query = st.text_input("Manual Inquiry / Confirmation:", value=detected_text)

# --- 6. SPECTRUM ENGINE (The Comparison Brain) ---
if query and db is not None:
    q_low = query.lower()
    # تحديد الدول في السؤال (Compare Logic)
    target_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    
    if target_adms:
        st.subheader("📊 Comparative Intelligence Dashboard")
        metrics_cols = st.columns(len(target_adms))
        summary_data = []

        for idx, adm in enumerate(target_adms):
            adm_df = db[db['Adm'] == adm].copy()
            
            # Strict Filtering based on Notice Type
            asg_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
            alt_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
            total = asg_count + alt_count
            
            summary_data.append({'Adm': adm, 'Assignments': asg_count, 'Allotments': alt_count})
            
            with metrics_cols[idx]:
                st.image(FLAGS.get(adm, ""), width=150)
                st.metric(f"{adm} Records", total, f"A:{asg_count} | L:{alt_count}")

        # Charts (Back from v17.0)
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.write("📈 Service Distribution")
            fig = px.bar(pd.DataFrame(summary_data), x='Adm', y=['Assignments', 'Allotments'], barmode='group')
            st.plotly_chart(fig, use_container_width=True)
            
        with chart_col2:
            filtered_full = db[db['Adm'].isin(target_adms)]
            if 'lat_dec' in filtered_full.columns:
                st.write("🗺️ Geospatial Deployment")
                fig_map = px.scatter_mapbox(filtered_full, lat="lat_dec", lon="lon_dec", hover_name="Adm", zoom=3, height=300)
                fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)
        
        st.dataframe(filtered_full, use_container_width=True)
    else:
        st.warning("Please mention a valid Administration (e.g., Egypt or Israel) in your query.")
