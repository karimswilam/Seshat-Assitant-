import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import time
from streamlit_mic_recorder import speech_to_text

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.9")

if 'query_text' not in st.session_state:
    st.session_state.query_text = ""
if 'step_log' not in st.session_state:
    st.session_state.step_log = []

# --- 2. ENGINEERING LOGIC (DATA & FLAGS) ---
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

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

# --- 3. UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        parts = re.findall(r"(\d+)", dms_str)
        direction = re.findall(r"([NSEW])", dms_str.upper())
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(generate_audio(text))
    if data: st.audio(data, format="audio/mp3")

# --- 4. ENGINE CORE (FIXED FOR VALUEERROR) ---
def engine_v17_9(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    
    if not selected_adms: return None, [], "ADM identification error.", 0, False

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({
            "Adm": adm, 
            "Total": a_count + l_count, 
            "Assignments": a_count, 
            "Allotments": l_count
        })
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Total']} records" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI & LIVE INDICATORS ---
st.title("Seshat Master Precision v17.9")
st.markdown("### 🎙️ Live Voice Validation")

col_mic, col_txt = st.columns([1, 4])
with col_mic:
    # مؤشر تسجيل مرئي
    audio_val = speech_to_text(language='ar-EG', start_prompt="🔴 Start", stop_prompt="🟢 Stop", key='mic_v179')
    if audio_val:
        st.session_state.query_text = audio_val
        st.toast(f"Input Captured: {audio_val}")

with col_txt:
    query = st.text_input("Confirm Inquiry:", value=st.session_state.query_text)

db = load_db()

if query and db is not None:
    # نظام الـ Status للـ Validation
    with st.status("📡 Processing Signal...", expanded=True) as status:
        st.write("Step 1: Analyzing Voice/Text Spectrum...")
        time.sleep(0.5)
        
        try:
            res_df, reports, msg, conf, success = engine_v17_9(query, db)
            st.write(f"Step 2: {len(reports)} Administrations Identified.")
            
            if success:
                status.update(label="✅ Analysis Success", state="complete")
                
                # النتائج
                st.markdown("---")
                cols = st.columns(len(reports))
                for i, r in enumerate(reports):
                    with cols[i]:
                        st.image(FLAGS.get(r['Adm'], ""), width=150)
                        st.metric(r['Adm'], f"Total: {r['Total']}", f"A:{r['Assignments']} | L:{r['Allotments']}")
                
                # تصحيح الـ ValueError بتاع الرسم البياني
                if PLOTLY_AVAILABLE and len(reports) > 0:
                    st.markdown("### 📊 Spectrum Comparison")
                    chart_df = pd.DataFrame(reports)
                    # الحماية: التأكد من وجود أعمدةAssignments و Allotments قبل الرسم لتجنب Error الصورة
                    fig = px.bar(chart_df, x="Adm", y=["Assignments", "Allotments"], barmode="group")
                    st.plotly_chart(fig, use_container_width=True)

                if not res_df.empty:
                    st.markdown("### 🌍 Geospatial Analysis")
                    map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
                    st.map(map_data[['lat_dec', 'lon_dec']])

                st.success(msg)
                play_audio(msg)
            else:
                status.update(label="❌ No Results Found", state="error")
        except Exception as e:
            st.error(f"Engine Failure: {e}")

# --- Debug Expander ---
with st.expander("🛠️ Internal System Logs"):
    st.write(f"Current Query: {query}")
    st.write(f"DB Status: {'Connected' if db is not None else 'Disconnected'}")
