import streamlit as st
import pandas as pd
import os
import io
import asyncio
import edge_tts
import base64
import numpy as np
import requests
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder

# --- 1. SYSTEM CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat AI v21.5", page_icon="🛰️")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUDIO UTILITIES (Cloud-Safe) ---
def estimate_audio_level(audio_bytes):
    """تحليل شدة الصوت من البايتات المسجلة فعلياً لتجنب مشاكل الـ PortAudio"""
    try:
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        if len(audio_array) == 0: return 0
        amplitude = np.abs(audio_array).mean()
        # Scale for visualization
        return min(amplitude / 3000, 1.0) 
    except:
        return 0

def render_audio_meter(level):
    color = "#22c55e" # Green
    if level > 0.7: color = "#ef4444" # Red
    elif level > 0.4: color = "#eab308" # Yellow
    
    bar_html = f"""
    <div style="width:100%; background:#222; border-radius:10px; padding:5px; margin-bottom:10px;">
        <div style="width:{int(level*100)}%; height:15px; background:{color}; border-radius:10px; transition: width 0.3s;"></div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)

# --- 3. SPEECH ENGINES (STT & TTS) ---
def speech_to_text(audio_bytes):
    """Whisper API Correction"""
    try:
        # تأكد من وضع المفتاح في Streamlit Secrets
        api_key = st.secrets["OPENAI_API_KEY"]
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper-1"}
        )
        return response.json().get("text", "")
    except Exception as e:
        st.error(f"STT API Error: {e}")
        return ""

async def generate_audio_response(text):
    """Edge-TTS Logic"""
    try:
        # اختيار صوت احترافي لمشروع BASIRA
        communicate = edge_tts.Communicate(text, "ar-EG-SalmaNeural")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except:
        return None

def play_audio(text):
    """تسهيل تشغيل الصوت داخل Streamlit"""
    try:
        data = asyncio.run(generate_audio_response(text))
        if data:
            st.audio(data, format="audio/mp3")
    except:
        pass

# --- 4. DATA ENGINE (The Core) ---
@st.cache_data
def load_db():
    """تأمين قراءة البيانات من الـ Excel"""
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if files:
        df = pd.read_excel(files[0])
        # Fix KeyError: 'Adm' - تأمين أسماء الأعمدة من المسافات
        df.columns = [str(c).strip() for c in df.columns] 
        return df
    return None

def simple_engine(q, df):
    """محرك البحث باستخدام Fuzzy Matching لضمان دقة النتائج"""
    q_low = q.lower()
    # تأمين الوصول لعمود Adm بغض النظر عن الحالة
    adm_col = next((c for c in df.columns if c.lower() == 'adm'), None)
    
    if not adm_col:
        return None, "❌ Error: 'Adm' column not found in Database."

    # Mapping logic
    if any(x in q_low for x in ['مصر', 'egypt', 'egy']):
        target = 'EGY'
    elif any(x in q_low for x in ['اسرائيل', 'israel', 'isr']):
        target = 'ISR'
    elif any(x in q_low for x in ['تركيا', 'turkey', 'tur']):
        target = 'TUR'
    else:
        return None, "❌ لم يتم التعرف على الدولة المطلوبة."

    res_df = df[df[adm_col].astype(str).str.contains(target, case=False)]
    return res_df, f"✅ تم العثور على {len(res_df)} سجل لـ {target}."

# --- 5. UI LAYOUT ---
st.title("🎙️ Seshat Master Precision v21.5")
st.markdown("#### Project BASIRA | Digital Spectrum Governance")

db = load_db()

if db is not None:
    # Voice Section
    with st.expander("🎤 Voice Command Control", expanded=True):
        audio = mic_recorder(
            start_prompt="🎤 Start Recording", 
            stop_prompt="⏹ Stop & Analyze", 
            key="recorder",
            format="wav"
        )
        
        if audio:
            # Visualization logic based on your previous code
            level = estimate_audio_level(audio['bytes'])
            render_audio_meter(level)
            
            if level > 0.01: # عتبة بسيطة لمنع الضوضاء
                with st.spinner("Analyzing Signal..."):
                    text = speech_to_text(audio['bytes'])
                    if text:
                        st.info(f"📝 Recognized: {text}")
                        res_df, msg = simple_engine(text, db)
                        
                        st.success(msg)
                        play_audio(msg)
                        
                        if res_df is not None:
                            st.dataframe(res_df)
                    else:
                        st.error("Could not understand audio.")
            else:
                st.warning("⚠️ No clear audio detected. Please try again.")

    # Text Fallback
    st.divider()
    t_query = st.text_input("⌨️ Manual Query (Text Fallback):", placeholder="Ex: كم محطات مصر؟")
    if t_query:
        res_df, msg = simple_engine(t_query, db)
        st.write(msg)
        if res_df is not None: 
            st.dataframe(res_df)
else:
    st.error("❌ Data file missing! Please ensure Data.xlsx is in the root directory.")
