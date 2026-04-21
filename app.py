import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import nest_asyncio
from difflib import get_close_matches

# حل مشكلة تضارب العمليات في Streamlit
nest_asyncio.apply()

# --- 1. Flags & Intelligence Mapping ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

MASTER_KNOWLEDGE = {
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.5.0 - Natural Voice", layout="wide")

# --- 2. Neural Voice Engine (The Natural Human Voice) ---
async def get_neural_voice(text, is_ar):
    # أصوات مايكروسوفت العصبية (أكثر الأصوات واقعية في 2026)
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 3. Style & UI ---
st.markdown("""
    <style>
    .main { background: #f0f2f5; }
    .ans-card { 
        background: white; padding: 25px; border-radius: 15px; 
        border-right: 10px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
    }
    .flag-img { width: 140px; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_db():
    for f in os.listdir('.'):
        if f.endswith('.xlsx'):
            df = pd.read_excel(f); df.columns = df.columns.str.strip()
            return df
    return None

db = load_db()

def engine_v12_5(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    is_bool = any(x in q_low for x in ['هل', 'موجود', 'فيه', 'does', 'is '])
    
    words = re.findall(r'\w+', q_low)
    adms = []; det_svc = None

    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            if code in FLAGS.keys(): adms.append(code)
            elif code == 'DAB_KEY': det_svc = 'DAB'
            elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words: det_svc = 'FM'
    if not adms: return None, "EGY", 0, "برجاء تحديد الدولة يا بشمهندس.", is_ar

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]

    found = len(res) > 0
    if is_ar:
        status = "نعم يا بشمهندس، يوجد" if found else "لا يوجد يا بشمهندس"
        ans = f"{status} {len(res)} سجلات تابعة لإدارة {adms[0]}."
    else:
        status = "Yes, Engineer." if found else "No, Engineer."
        ans = f"{status} I found {len(res)} records for {adms[0]}."

    return res, adms[0], 100, ans, is_ar

# --- UI Layout ---
st.title("📡 Seshat AI v12.5.0 - Natural Voice Era")
query = st.text_input("💬 اسأل المساعد الذكي (صوت بشري طبيعي):")

if db is not None:
    if query:
        res_df, top_adm, conf, human_ans, is_arabic = engine_v12_5(query, db)
        
        # Display
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS.get(top_adm, FLAGS['EGY'])}' class='flag-img'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2></div>", unsafe_allow_html=True)
        
        if res_df is not None:
            if not res_df.empty:
                st.dataframe(res_df, use_container_width=True)
            
            # 🔥 تشغيل الصوت البشري الطبيعي (Microsoft Neural)
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(get_neural_voice(human_ans, is_arabic))
                st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.warning(f"Voice ready, but audio playback had a minor issue: {e}")
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
else:
    st.error("Data.xlsx not found!")
