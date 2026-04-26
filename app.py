import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time
import numpy as np
import edge_tts
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Seshat AI v23.0", page_icon="🛰️")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v23.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

# Header
header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. THE ENGINEERING LOGIC (V17.0 FULL LOGIC) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png", 'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"}
COUNTRY_DISPLAY = {'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'}, 'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'}, 'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'}, 'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'}, 'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'}, 'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}}
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
COUNTRY_MAP = {'EGY': ['egypt', 'egy', 'مصر', 'المصرية'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'], 'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'], 'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل']}
SYNONYMS = {'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3'], 'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees'], 'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'sound'], 'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'tlfzyon'], 'FM_KEY': ['fm', 'radio', 'راديو'], 'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all records'], 'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'من غير', 'without']}

# --- 3. UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        clean_str = re.sub(r'[^0-9.NSEW ]', ' ', dms_str).strip().upper()
        parts = re.findall(r"(\d+)", clean_str); direction = re.findall(r"([NSEW])", clean_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3]); decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None

async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0); return audio_data
    except: return None

def stt_whisper(audio_bytes):
    try:
        response = requests.post("https://api.openai.com/v1/audio/transcriptions", 
                                 headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
                                 files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                                 data={"model": "whisper-1"})
        return response.json().get("text", "")
    except: return ""

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        mapping = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT'], 'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Standard/Allotment Area'], 'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates']}
        for std_name, synonyms in mapping.items():
            for col in df.columns:
                if col in synonyms: df = df.rename(columns={col: std_name}); break
        # Fix for Arrow Display
        for col in df.columns:
            if any(k in col.lower() for k in ['date', 'receipt']): df[col] = df[col].astype(str).replace('nan','')
        return df
    return None

# --- 4. ENGINE v17.0 ---
def engine_v17_0(q, data):
    q_low = q.lower()
    selected_adms = list(dict.fromkeys([code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]))
    if not selected_adms: return None, [], "ADM identification error.", 0, False
    
    is_total = any(x in q_low for x in SYNONYMS['TOTAL_KEY'])
    is_except = any(x in q_low for x in SYNONYMS['EXCEPT_KEY'])
    def get_svc(text):
        s = []
        if any(x in text for x in SYNONYMS['DAB_KEY']): s.extend(['GS1','GS2','DS1','DS2'])
        if any(x in text for x in SYNONYMS['TV_KEY']): s.extend(['T02','G02','GT1','GT2','DT1','DT2'])
        if any(x in text for x in SYNONYMS['FM_KEY']): s.extend(['T01','T03','T04'])
        return s
    
    if is_except:
        parts = re.split('|'.join(SYNONYMS['EXCEPT_KEY']), q_low)
        main_svc = get_svc(parts[0])
        if is_total and not main_svc: main_svc = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']
        svc_codes = [s for s in main_svc if s not in get_svc(parts[1])]
    else:
        svc_codes = get_svc(q_low)
        if is_total and not svc_codes: svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']

    reports = []; final_df = pd.DataFrame()
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        a_count, l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]), len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        reports.append({"Adm": adm, "Total": a_count+l_count, "Assignments": a_count, "Allotments": l_count})
        temp = adm_df
        if mentions_assig and not mentions_allot: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif mentions_allot and not mentions_assig: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Assignments']} Assig, {r['Allotments']} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

st.subheader("🎙️ Voice Command & Signal Analysis")
c1, c2 = st.columns([1, 2])

with c1:
    audio_data = mic_recorder(start_prompt="🎤 Start Listening", stop_prompt="⏹ Stop & Process", key="basira_mic")

voice_query = ""
if audio_data:
    # --- VISUAL INDICATORS ---
    with c2:
        st.write("📊 **Signal Monitoring:**")
        waveform = np.frombuffer(audio_data['bytes'], dtype=np.int16)
        st.line_chart(waveform[:2500], height=100) # ده الـ Wave bar اللي سألت عليه
        
        progress_bar = st.progress(0)
        st.write("⚡ **Processing Spectrum Intelligence...**")
        for p in range(100):
            time.sleep(0.01) # Progress bar simulated for visual effect
            progress_bar.progress(p + 1)
        
        voice_query = stt_whisper(audio_data['bytes'])
        if voice_query:
            st.success(f"✅ Text Captured: {voice_query}")
        else:
            st.error("❌ No voice detected. Try again.")

query = st.text_input("⌨️ Manual Override / Refine Query:", value=voice_query)

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v17_0(query, db)
    if success:
        st.divider()
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=200)
                st.metric(r['Adm'], f"Total: {r['Total']}", f"A: {r['Assignments']} | L: {r['Allotments']}")
        
        st.success(f"📢 {msg}")
        with st.expander("🔍 View Technical Records"):
            st.dataframe(res_df, use_container_width=True)
