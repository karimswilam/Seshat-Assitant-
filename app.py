import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
import plotly.express as px
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v27.0", page_icon="🛰️")

# --- 2. SESSION STATE INITIALIZATION ---
# دي أهم خطوة عشان البيانات متضيعش مع الـ Refresh
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False

# --- 3. ROBUST DATA LOADER ---
@st.cache_data
def load_db_v27():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        # توحيد أسماء الأعمدة لمنع الـ KeyError
        mapping = {'Adm': ['Country', 'ADMS', 'Administration'], 'Notice Type': ['NT', 'TYPE']}
        for std, syns in mapping.items():
            for col in df.columns:
                if col.upper() in [s.upper() for s in syns]:
                    df = df.rename(columns={col: std})
        return df
    return None

# --- 4. ENGINE LOGIC (Directly Integrated) ---
def run_spectrum_engine(q, data):
    # تحويل السؤال لنص يبحث عن مصر (EGY) والتخصيص الإذاعي
    q_low = q.lower()
    if any(k in q_low for k in ['مصر', 'egypt', 'egy']):
        target_adm = 'EGY'
    else:
        return None, "لم يتم تحديد الدولة بوضوح في السؤال."

    # فلترة البيانات (إذاعي/تلفزيون/DAB)
    # نستخدم أكواد ITU المعروفة (T01, T02, GS1, etc.)
    filtered = data[data['Adm'] == target_adm].copy()
    
    # حساب الإحصائيات
    total = len(filtered)
    assig = len(filtered[filtered['Notice Type'].isin(['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01'])])
    allot = total - assig
    
    msg = f"تم العثور على {total} سجل لجمهورية مصر العربية ({assig} تخصيص و {allot} توزيع)."
    return filtered, msg

# --- 5. UI & VOICE PROCESSING ---
db = load_db_v27()
st.markdown(f"## 🛰️ {st.session_state.get('transcript', 'Waiting for Signal...')}")

c1, c2 = st.columns([1, 2])
with c1:
    audio_data = mic_recorder(start_prompt="🎤 إبدأ السؤال", stop_prompt="⏹ معالجة الإشارة", key="mic_v27")

if audio_data and not st.session_state.processing_done:
    with c2:
        waveform = np.frombuffer(audio_data['bytes'], dtype=np.int16)
        intensity = np.abs(waveform).mean()
        
        if intensity > 40:
            st.success("✅ Signal Detected & Validated")
            st.line_chart(waveform[:1500], height=80)
            
            # محاولة تحويل الصوت لنص
            with st.spinner("📡 جارٍ تحويل الإشارة الصوتية إلى نص..."):
                try:
                    buffer = io.BytesIO(audio_data['bytes'])
                    buffer.name = "audio.wav"
                    resp = requests.post(
                        "https://api.openai.com/v1/audio/transcriptions", 
                        headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                        files={"file": buffer}, data={"model": "whisper-1"}
                    )
                    st.session_state.transcript = resp.json().get("text", "")
                    st.session_state.processing_done = True
                    st.rerun() # إجبار التطبيق على التحديث فوراً لعرض النتيجة
                except Exception as e:
                    st.error(f"Transcription Error: {e}")
        else:
            st.warning("⚠️ إشارة ضعيفة جداً، حاول مرة أخرى.")

# --- 6. OUTPUT RENDERER ---
# دي المرحلة اللي بتعرض النتيجة بعد الـ Rerun
if st.session_state.transcript:
    st.info(f"🔍 السؤال المكتشف: {st.session_state.transcript}")
    
    if db is not None:
        with st.spinner("⚙️ جاري تحليل قاعدة البيانات..."):
            res_df, final_msg = run_spectrum_engine(st.session_state.transcript, db)
            
            if res_df is not None:
                st.divider()
                st.balloons()
                
                # عرض النتيجة زي v17.0
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("إجمالي السجلات (مصر)", len(res_df))
                    st.success(final_msg)
                with col_b:
                    # لو فيه إحداثيات ارسم خريطة
                    if 'lat_dec' in res_df.columns:
                        st.map(res_df)
                
                st.dataframe(res_df.head(10))
                
                # زرار لإعادة البدء
                if st.button("🔄 سؤال جديد"):
                    st.session_state.transcript = ""
                    st.session_state.processing_done = False
                    st.rerun()
