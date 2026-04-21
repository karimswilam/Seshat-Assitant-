import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
from difflib import get_close_matches

# محاولة معالجة المكتبات
try:
    import edge_tts
    import nest_asyncio
    nest_asyncio.apply()
    VOICE_READY = True
except ImportError:
    VOICE_READY = False

# --- 1. Database & Flags ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.0.5", layout="wide")

# --- 2. Guaranteed Voice Engine (Fixing the Loop) ---
async def generate_neural_audio(text, is_ar):
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 3. UI Styling ---
st.markdown("""
    <style>
    .ans-card { background: white; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .flag-img { width: 120px; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_db():
    for f in os.listdir('.'):
        if f.endswith('.xlsx'):
            df = pd.read_excel(f)
            df.columns = df.columns.str.strip()
            return df
    return None

db = load_db()

def engine_v12(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    adms = []; det_svc = None; filter_type = None

    for code, keys in SYNONYMS.items():
        if any(k in q_low for k in keys):
            if code in FLAGS.keys(): adms.append(code)
            elif code == 'ALLOT_KEY': filter_type = 'allot'
            elif code == 'ASSIG_KEY': filter_type = 'assig'
            elif code == 'DAB_KEY': det_svc = 'DAB'
            elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words: det_svc = 'FM'
    if not adms: return None, "EGY", 0, "برجاء تحديد الدولة يا بشمهندس.", is_ar

    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    ans = f"نعم يا بشمهندس، تم العثور على {len(res)} سجلات لـ {adms[0]}." if is_ar else f"Yes Engineer, I found {len(res)} records for {adms[0]}."
    return res, adms[0], 100, ans, is_ar

# --- UI Layout ---
query = st.text_input("💬 اسأل Seshat (Neural Voice Mode):")

if db is not None:
    if query:
        res_df, adm, conf, human_ans, is_arabic = engine_v12(query, db)
        
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS.get(adm, FLAGS['EGY'])}' class='flag-img'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2></div>", unsafe_allow_html=True)
        
        if res_df is not None:
            st.dataframe(res_df, use_container_width=True)
            
            # محرك الصوت المطور
            if VOICE_READY:
                try:
                    # الطريقة الأضمن لتشغيل Async جوه Streamlit بدون تضارب
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    audio_bytes = new_loop.run_until_complete(generate_neural_audio(human_ans, is_arabic))
                    st.audio(audio_bytes, format="audio/mp3")
                except Exception as e:
                    st.error(f"خطأ في محرك الصوت: {e}")
            else:
                st.warning("المكتبات ناقصة. شغل السطر ده في الـ Terminal: pip install edge-tts nest_asyncio")
    else:
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
else:
    st.error("Data.xlsx not found!")
