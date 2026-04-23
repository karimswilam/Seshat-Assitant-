import streamlit as st
import pandas as pd
import os
import asyncio
import edge_tts
import base64
import requests
from rapidfuzz import fuzz
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="Seshat Master v21.5")

# --- 2. DATA LOADER (ANTI-KEYERROR) ---
@st.cache_data
def load_and_fix_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    if not files: return None
    try:
        df = pd.read_excel(files[0])
        # التخلص من أي مسافات في أسماء الأعمدة (حل KeyError)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error loading DB: {e}")
        return None

db = load_and_fix_db()

# --- 3. SPEECH ENGINES ---
async def text_to_speech_logic(text):
    communicate = edge_tts.Communicate(text, "ar-EG-SalmaNeural")
    data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": data += chunk["data"]
    return base64.b64encode(data).decode()

def speech_to_text_whisper(audio_bytes):
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
    except: return ""

# --- 4. ENGINE LOGIC (V17.0 REBORN) ---
COUNTRY_MAP = {
    'EGY': ['مصر', 'egypt', 'المصرية'],
    'TUR': ['تركيا', 'turkey', 'التركية'],
    'ARS': ['السعودية', 'saudi', 'المملكة']
}

def analyze_query(q, data):
    q = q.lower()
    selected_adm = None
    for code, terms in COUNTRY_MAP.items():
        if any(term in q for term in terms) or any(fuzz.partial_ratio(term, q) > 80 for term in terms):
            selected_adm = code
            break
    
    if not selected_adm: return None, "لم أستطع تحديد الدولة."

    # البحث عن العمود الصحيح بغض النظر عن الحالة (Adm / adm / ADM)
    col = next((c for c in data.columns if c.lower() == 'adm'), None)
    if not col: return None, "Error: 'Adm' column missing!"

    res_df = data[data[col].astype(str).str.contains(selected_adm, case=False)]
    msg = f"تحليل {selected_adm}: تم العثور على {len(res_df)} سجل."
    return res_df, msg

# --- 5. UI ---
st.title("🛰️ Seshat Master Precision v21.5")
st.caption("Project BASIRA | Digital Spectrum Governance")

if db is not None:
    st.success("✔️ Database Connected & Optimized")
    
    # الـ Mic Recorder هو الحل الوحيد للـ Cloud بدل sounddevice
    audio_input = mic_recorder(start_prompt="🎤 Start Voice Command", stop_prompt="⏹ Stop & Analyze", key="basira_mic")
    
    if audio_input:
        st.audio(audio_input['bytes']) # Feedback للمستخدم
        with st.spinner("Processing Signal..."):
            text = speech_to_text_whisper(audio_input['bytes'])
            if text:
                st.info(f"Recognized: {text}")
                res, msg = analyze_query(text, db)
                st.success(msg)
                
                # الرد الصوتي
                b64_audio = asyncio.run(text_to_speech_logic(msg))
                st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{b64_audio}">', unsafe_allow_html=True)
                
                if res is not None:
                    st.dataframe(res)
            else:
                st.error("Could not transcribe audio.")

else:
    st.error("❌ Please upload Data.xlsx to the root directory.")
