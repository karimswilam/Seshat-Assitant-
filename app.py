import streamlit as st
import pandas as pd
import os, io, re, asyncio, time
import edge_tts
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from rapidfuzz import process, fuzz

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.1.A")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.1.A"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# Header Display
header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. ENGINEERING LOGIC ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png", 'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_DISPLAY = {'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'}, 'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'}, 'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'}, 'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'}, 'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'}, 'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر', 'المصرية'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']}
SYNONYMS = {'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3'], 'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees'], 'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'sound'], 'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'tlfzyon'], 'FM_KEY': ['fm', 'radio', 'راديو'], 'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all records'], 'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'من غير', 'without']}

# --- 3. SPEECH & AUDIO ENGINES ---
def speech_to_text_engine(audio_bytes):
    r = sr.Recognizer()
    try:
        audio_stream = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_stream) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language="ar-EG")
    except:
        return ""

async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
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

# --- 4. ENGINE CORE v17.1.A (Fixed Indentation) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'الادارة'],
            'Notice Type': ['Notice Type', 'NT', 'نوع الإخطار'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name']
        }
        for std, syns in mapping.items():
            for col in df.columns:
                if col in syns:
                    df.rename(columns={col: std}, inplace=True)
                    break
        return df
    return None

def engine_v17_0(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    if not selected_adms: return None, [], "ADM identification error.", 0, False

    reports = []; final_df = pd.DataFrame()
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {"Adm": adm, "Total": a_count + l_count, "Assignments": a_count, "Allotments": l_count}
        reports.append(res)
        
        temp = adm_df
        if mentions_assig and not mentions_allot: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif mentions_allot and not mentions_assig: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        final_df = pd.concat([final_df, temp], ignore_index=True)

    return final_df, reports, f"Results for {', '.join(selected_adms)}", 100, True

# --- 5. UI MAIN FLOW ---
db = load_db()

# Voice Input Section
st.subheader("🎙️ Spectrum Voice Command")
audio_input = mic_recorder(start_prompt="Click to Speak", stop_prompt="Process Command", key="mic_v17")

query = ""
if audio_input:
    with st.status("📡 Analyzing Audio Signal...", expanded=True) as status:
        query = speech_to_text_engine(audio_input['bytes'])
        if query:
            status.update(label=f"🎯 Recognized: {query}", state="complete")
            st.session_state.voice_q = query
        else:
            status.update(label="❌ Speech not recognized", state="error")

manual_q = st.text_input("Enter/Edit Query:", value=st.session_state.get('voice_q', ""))

if manual_q and db is not None:
    res_df, reports, msg, conf, success = engine_v17_0(manual_q, db)
    if success:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=200)
                st.metric(r['Adm'], f"Total: {r['Total']}", f"A:{r['Assignments']} | L:{r['Allotments']}")
        
        st.success(msg)
        play_audio(msg)
        with st.expander("Technical Records"):
            st.dataframe(res_df)
