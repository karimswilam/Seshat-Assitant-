import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
import plotly.express as px
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v26.0", page_icon="🛰️")

# --- 2. ROBUST DATA LOADER (Fixes KeyError: 'Adm') ---
@st.cache_data
def load_db_v26():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # Mapping to prevent KeyError
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'ADMS', 'ADMINISTRATION'],
            'Notice Type': ['Notice Type', 'NT', 'TYPE'],
            'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'COORDS']
        }
        for std, syns in mapping.items():
            for col in df.columns:
                if col.upper() in [s.upper() for s in syns]:
                    df = df.rename(columns={col: std})
                    break
        return df
    return None

# --- 3. VOICE UTILITIES ---
def whisper_stt_v26(audio_bytes):
    if not audio_bytes or len(audio_bytes) < 1000: # التحقق من حجم الملف
        return None
    try:
        buffer = io.BytesIO(audio_bytes)
        buffer.name = "audio.wav"
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions", 
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": buffer}, 
            data={"model": "whisper-1"}
        )
        return resp.json().get("text", "")
    except: return None

# --- 4. UI COMPONENTS ---
db = load_db_v26()
st.title("🛰️ Seshat Master Precision v26.0")

# Logic to validate voice input
c1, c2 = st.columns([1, 2])
with c1:
    st.info("Step 1: Signal Capture")
    audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop & Process", key="mic_v26")

query = ""
if audio_data:
    with c2:
        waveform = np.frombuffer(audio_data['bytes'], dtype=np.int16)
        # التحقق من شدة الصوت (Validation)
        intensity = np.abs(waveform).mean()
        
        if intensity > 50: # Threshold للتحقق إن فيه صوت فعلاً مش شوشرة
            st.success("✅ Voice Signal Validated (Signal Detected)")
            st.line_chart(waveform[:2000], height=100)
            with st.spinner("🧠 AI is decoding your spectrum inquiry..."):
                query = whisper_stt_v26(audio_data['bytes'])
        else:
            st.warning("⚠️ Low Signal Level. Please speak closer to the mic.")

# Manual override if voice fails
user_input = st.text_input("📝 Confirm/Type Inquiry:", value=query if query else "")

# --- 5. EXECUTION ---
if user_input and db is not None:
    if 'Adm' not in db.columns:
        st.error("❌ Data Error: Column 'Adm' not found in Excel. Please check column headers.")
    else:
        # استدعاء الـ Engine v17 (المنطق الأصلي بتاعك)
        # ملاحظة: تأكد من تعريف engine_v17_core هنا أو استيراده
        from engine import engine_v17_core # افترضنا إنها في ملف خارجي أو عرفها هنا
        
        res_df, reports, msg, conf, success = engine_v17_core(user_input, db)
        
        if success:
            st.balloons()
            st.success(f"Assistant Response: {msg}")
            # عرض الداشبورد والخرائط (نفس منطق 17.0 السليم)
            st.dataframe(res_df)
