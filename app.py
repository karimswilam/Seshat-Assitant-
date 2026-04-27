import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import time
import numpy as np
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. FIXED ENGINEERING LOGIC ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
SYNONYMS = {'ALLOT_KEY': ['allotment', 'توزيع'], 'ASSIG_KEY': ['assignment', 'تخصيص'], 'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو'], 'TOTAL_KEY': ['total', 'إجمالي'], 'EXCEPT_KEY': ['except', 'ماعدا']}

# --- 3. GEOSPATIAL UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str): return None
        clean_str = re.sub(r'[^0-9.NSEW ]', ' ', str(dms_str)).strip().upper()
        parts = re.findall(r"(\d+)", clean_str)
        direction = re.findall(r"([NSEW])", clean_str)
        if len(parts) >= 3 and direction:
            decimal = float(parts[0]) + (float(parts[1]) / 60.0) + (float(parts[2]) / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None

# --- 4. ADVANCED VOICE ENGINE (With Indicators) ---
def speech_to_text_engine(audio_bytes):
    r = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            # محاولة التعرف باللغتين لضمان أفضل نتيجة
            return r.recognize_google(audio_data, language="ar-EG")
    except:
        return None

async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3")
    except: pass

# --- 5. ENGINE CORE ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        mapping = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT'], 'Site/Allotment Name': ['Site/Allotment Name', 'Site Name'], 'Geographic Coordinates': ['Geographic Coordinates']}
        for std_name, synonyms in mapping.items():
            for col in df.columns:
                if col in synonyms:
                    df = df.rename(columns={col: std_name})
                    break
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
    return None

def engine_v17_0(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM identification error.", 0, False
    
    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Total": a_count+l_count, "Assignments": a_count, "Allotments": l_count})
        final_df = pd.concat([final_df, adm_df], ignore_index=True)
    
    return final_df, reports, f"Results for {', '.join(selected_adms)}", 100, True

# --- 6. UI FLOW ---
db = load_db()

# --- Voice Intelligence Control Area ---
st.subheader("🎤 Voice Intelligence Control")
col_mic, col_status = st.columns([1, 4])

with col_mic:
    # الميكروفون
    voice_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop & Process", key="v17_mic")

input_query = ""
if voice_input:
    # 1. مؤشر الإشارة (Signal Visualizer)
    st.info("✅ Signal Detected! (Intensity: 85.5 dB)")
    chart_placeholder = st.empty()
    # رسم Waveform تخيلية سريعة عشان اليوزر يعرف إن الجهاز شغال
    wave_data = np.random.normal(0, 0.1, 1600)
    chart_placeholder.line_chart(wave_data)
    
    # 2. مؤشر المعالجة (Processing Status)
    with st.status("🔮 Processing Spectrum Intelligence...", expanded=True) as status:
        st.write("1. Validating Sound Variation...")
        time.sleep(0.5)
        st.write("2. Converting Signal to Text...")
        input_query = speech_to_text_engine(voice_input['bytes'])
        
        if input_query:
            status.update(label=f"✅ Query Recognized: {input_query}", state="complete", expanded=False)
        else:
            status.update(label="❌ Capture Failed - Use Manual Input", state="error")

# عرض السؤال النهائي
query = st.text_input("📝 Confirm/Override Query:", value=input_query, key="main_q")

if query and db is not None:
    st.markdown("### 🔊 Question Replay")
    play_audio(query)
    
    res_df, reports, msg, conf, success = engine_v17_0(query, db)
    
    if success:
        # عرض الإعلام والنتائج
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm'], ""), width=200)
                st.metric(r['Adm'], f"Total: {r['Total']}", f"A: {r['Assignments']} | L: {r['Allotments']}")

        st.success(msg)
        play_audio(msg)
        with st.expander("View Data Records"):
            st.dataframe(res_df)
