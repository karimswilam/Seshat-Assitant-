# ==============================# ============================= PLOTLY_AVAILABLE = False

# ==============================
# 1. CONFIG & INTERFACE
# ==============================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(
        f"""
        <div style="text-align:center">
            <h1 style="color:#1E3A8A;margin-bottom:0">{PROJECT_NAME}</h1>
            <p style="color:#475569;font-size:18px">{PROJECT_SLOGAN}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ==============================
# 2. FIXED ENGINEERING LOGIC
# ==============================
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
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

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'sound'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية'],
    'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all records'],
    'EXCEPT_KEY': ['except', 'ماعدا', 'without']
}

# ==============================
# 3. VOICE OUTPUT (TTS)
# ==============================
async def generate_audio(text):
    is_ar = any(c in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = re.sub(r'<[^>]*>', '', text)
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_audio(text))
        if audio:
            st.audio(audio, format="audio/mp3")
    except:
        pass

# ==============================
# 4. VOICE INPUT (Speech → Text)
# ==============================
def speech_to_text_from_mic(audio_bytes):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except:
        return None

# ==============================
# 5. DATA LOADER
# ==============================
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if not target:
        return None
    df = pd.read_excel(target)
    df.columns = df.columns.str.strip()
    return df

# ==============================
# 6. ENGINE CORE v17.0
# ==============================
def engine_v17_0(q, data):
    q_low = q.lower()
    selected_adms = [c for c, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms:
        return None, [], "ADM identification error.", 0, False

    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    reports = []
    final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Administration'] == adm]
        a = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        l = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]

        reports.append({
            "Adm": adm,
            "Assignments": len(a),
            "Allotments": len(l),
            "Total": len(a) + len(l)
        })

        final_df = pd.concat([final_df, adm_df])

    msg = " | ".join(
        [f"{r['Adm']}: A={r['Assignments']} L={r['Allotments']}" for r in reports]
    )

    return final_df, reports, msg, 100, True

# ==============================
# 7. UI FLOW
# ==============================
db = load_db()

st.markdown("### 🎙️ Ask your Spectrum Question")

query = st.text_input(
    "Type your question (Arabic or English)",
    key="main_query"
)

st.markdown("### 🎤 Or ask by Voice")

voice_audio = mic_recorder(
    start_prompt="▶️ Start Recording",
    stop_prompt="⏹️ Stop Recording",
    key="voice_q"
)

if voice_audio and "bytes" in voice_audio:
    voice_text = speech_to_text_from_mic(voice_audio["bytes"])
    if voice_text:
        st.success(f"You said: {voice_text}")
        query = voice_text
    else:
        st.error("Could not understand voice input")

if query and db is not None:
    play_audio(query)
    st.divider()

    res_df, reports, msg, conf, success = engine_v17_0(query, db)

    if success:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.metric(r['Adm'], r['Total'], f"A={r['Assignments']} L={r['Allotments']}")
                st.image(FLAGS.get(r['Adm']), width=180)

        st.success(msg)
        play_audio(msg)

        if PLOTLY_AVAILABLE:
            chart_df = pd.DataFrame(reports).set_index('Adm')
            st.bar_chart(chart_df[['Assignments', 'Allotments']])
``
# IMPORTS
# ==============================
import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import base64
import tempfile

import edge_tts
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
