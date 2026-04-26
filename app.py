import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
import plotly.express as px
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & DASHBOARD UI (Restored from v17) ---
st.set_page_config(layout="wide", page_title="Seshat Master Precision v28.0", page_icon="🛰️")

if 'transcript' not in st.session_state: st.session_state.transcript = ""

# --- 2. ROBUST DATA ENGINE (The Core v17 Logic) ---
@st.cache_data
def load_and_fix_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if not target: return None
    
    df = pd.read_excel(target)
    df.columns = df.columns.str.strip()
    # Fix Column Headers to prevent KeyError
    mapping = {'Adm': ['Country', 'Administration', 'ADMS'], 'Notice Type': ['NT', 'TYPE', 'Notice']}
    for std, syns in mapping.items():
        for col in df.columns:
            if col.lower() in [s.lower() for s in syns]:
                df.rename(columns={col: std}, inplace=True)
    
    # Coordinates Processing for Map (v17 Logic)
    if 'Geographic Coordinates' in df.columns:
        def dms_to_dec(s):
            try:
                parts = re.findall(r"(\d+)", str(s))
                if len(parts) >= 3:
                    res = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
                    return -res if any(x in str(s).upper() for x in ['S', 'W']) else res
            except: return None
        coords = df['Geographic Coordinates'].astype(str).str.split(expand=True)
        if coords.shape[1] >= 2:
            df['lon_dec'] = coords[0].apply(dms_to_dec)
            df['lat_dec'] = coords[1].apply(dms_to_dec)
    return df

# --- 3. SPECTRUM ANALYSIS ENGINE ---
def run_analysis(query, data):
    q = query.lower()
    # Country Detection
    adm = 'EGY' if any(x in q for x in ['مصر', 'egypt']) else ('ISR' if 'اسرائيل' in q else None)
    if not adm: return None, "لم يتم التعرف على الدولة."
    
    filtered = data[data['Adm'] == adm].copy()
    is_dab = any(x in q for x in ['dab', 'داب', 'إذاعي'])
    if is_dab: filtered = filtered[filtered['Notice Type'].str.contains('GS|DS', na=False)]
    
    total = len(filtered)
    assig = len(filtered[filtered['Notice Type'].str.startswith(('T01', 'T03', 'GS1', 'GT1'), na=False)])
    msg = f"Analysis for {adm}: Total {total} records found ({assig} Assignments)."
    return filtered, msg

# --- 4. MAIN INTERFACE ---
db = load_and_fix_db()

st.title("🛰️ Seshat Master Precision v28.0")
st.markdown("### Signal Capture & Dashboard Engine")

col1, col2 = st.columns([1, 2])
with col1:
    audio = mic_recorder(start_prompt="🎤 Start Voice Command", stop_prompt="⏹ Process", key="v28_mic")

# Processing Logic
if audio:
    with col2:
        waveform = np.frombuffer(audio['bytes'], dtype=np.int16)
        st.line_chart(waveform[:2000], height=100)
        
        # Check for OpenAI Key before calling API
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("❌ Missing OpenAI API Key in Streamlit Secrets!")
        else:
            with st.spinner("📡 Decoding Spectrum Inquiry..."):
                try:
                    buf = io.BytesIO(audio['bytes']); buf.name = "audio.wav"
                    r = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                                     headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                                     files={"file": buf}, data={"model": "whisper-1"})
                    st.session_state.transcript = r.json().get("text", "")
                except Exception as e: st.error(f"STT Error: {e}")

# Display Results & Dashboards (v17 style)
query = st.text_input("Confirm Inquiry:", value=st.session_state.transcript)

if query and db is not None:
    res_df, report_msg = run_analysis(query, db)
    
    if res_df is not None:
        st.divider()
        st.success(f"✅ {report_msg}")
        
        # Dashboard Grid
        m1, m2 = st.columns(2)
        m1.metric("Total Records", len(res_df))
        m2.metric("Filtered Scope", query)
        
        # Map & Visuals (Restored)
        c_a, c_b = st.columns([2, 1])
        with c_a:
            if 'lat_dec' in res_df.columns:
                st.map(res_df[['lat_dec', 'lon_dec']].dropna())
        with c_b:
            st.bar_chart(res_df['Notice Type'].value_counts())
        
        st.dataframe(res_df)
