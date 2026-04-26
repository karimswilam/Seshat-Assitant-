import streamlit as st
import pandas as pd
import os, io, re, asyncio, requests, time, base64
import numpy as np
import edge_tts
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE (Unchanged Logo/Banner) ---
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. FIXED ENGINEERING LOGIC (V17 Core) ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'sound'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'tlfzyon'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي', 'كل', 'all records'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'من غير', 'without']
}

# --- 3. SPEECH RECOGNITION (New Addition - No Deletion) ---
def whisper_stt(audio_bytes):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("Missing OpenAI API Key in Streamlit Secrets!")
        return ""
    try:
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.wav"
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
            files={"file": buf},
            data={"model": "whisper-1"}
        )
        return response.json().get("text", "")
    except: return ""

# --- 4. GEOSPATIAL UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        clean_str = re.sub(r'[^0-9.NSEW ]', ' ', dms_str).strip().upper()
        parts = re.findall(r"(\d+)", clean_str)
        direction = re.findall(r"([NSEW])", clean_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None
    return None

# --- 5. VOICE ENGINE (Text-to-Speech) ---
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

# --- 6. ENGINE CORE v17.0 (Restored Logic) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'ADMS'],
            'Notice Type': ['Notice Type', 'NT'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Standard/Allotment Area'],
            'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates']
        }
        for std_name, syns in mapping.items():
            for col in df.columns:
                if col in syns:
                    df = df.rename(columns={col: std_name})
                    break
        if 'Geographic Coordinates' in df.columns:
            coords_split = df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords_split.shape[1] >= 2:
                df['lon_dec'] = coords_split[0].apply(dms_to_decimal)
                df['lat_dec'] = coords_split[1].apply(dms_to_decimal)
        return df
    return None

def engine_v17_0(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    if not selected_adms: return None, [], "ADM identification error.", 0, False

    is_total = any(x in q_low for x in SYNONYMS['TOTAL_KEY'])
    is_except = any(x in q_low for x in SYNONYMS['EXCEPT_KEY'])
    
    def get_svc_from_text(text):
        svcs = []
        if any(x in text for x in SYNONYMS['DAB_KEY']): svcs.extend(['GS1','GS2','DS1','DS2'])
        if any(x in text for x in SYNONYMS['TV_KEY']): svcs.extend(['T02','G02','GT1','GT2','DT1','DT2'])
        if any(x in text for x in SYNONYMS['FM_KEY']): svcs.extend(['T01','T03','T04'])
        return svcs

    if is_except:
        parts = re.split('|'.join(SYNONYMS['EXCEPT_KEY']), q_low)
        main_svc = get_svc_from_text(parts[0])
        except_svc = get_svc_from_text(parts[1]) if len(parts) > 1 else []
        if is_total and not main_svc: main_svc = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']
        svc_codes = [s for s in main_svc if s not in except_svc]
    else:
        svc_codes = get_svc_from_text(q_low)
        if is_total and not svc_codes: svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']

    reports = []; final_df = pd.DataFrame()
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    for adm in selected_adms:
        # الإصلاح الحرج: استخدام اسم العمود الموحد 'Adm'
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        res = {"Adm": adm, "Total": a_count + l_count, "Assignments": a_count, "Allotments": l_count}
        reports.append(res)
        
        temp = adm_df
        if mentions_assig and not mentions_allot: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif mentions_allot and not mentions_assig: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        final_df = pd.concat([final_df, temp], ignore_index=True)

    # Comparison Logic (v17.0 style)
    if len(reports) >= 2:
        comp_key = "Assignments" if mentions_assig else ("Allotments" if mentions_allot else "Total")
        v1, v2 = reports[0].get(comp_key, 0), reports[1].get(comp_key, 0)
        diff = abs(v1 - v2)
        if v1 > v2: msg = f"Yes, {reports[0]['Adm']} has more {comp_key} than {reports[1]['Adm']} by {diff} records."
        elif v2 > v1: msg = f"No, {reports[1]['Adm']} actually has more {comp_key} than {reports[0]['Adm']} by {diff} records."
        else: msg = f"Both have the same {comp_key} ({v1})."
    else:
        msg = " | ".join([f"{r['Adm']}: A:{r['Assignments']} L:{r['Allotments']}" for r in reports])

    return final_df, reports, msg, 100, True

# --- 7. UI FLOW (Preserving v17 Layout) ---
db = load_db()

# Voice Control Section
st.subheader("🎤 Voice Control & Signal Monitor")
audio = mic_recorder(start_prompt="Start Recording", stop_prompt="Process Audio", key="mic_v17")

# Manual Input (Fallback)
query = st.text_input("🎙️ Manual Override / Refine Query:", key="manual_q")

# Execution Trigger
if audio:
    with st.spinner("Analyzing Signal..."):
        query = whisper_stt(audio['bytes'])
        if query: st.info(f"Recognized: {query}")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    
    res_df, reports, msg, conf, success = engine_v17_0(query, db)
    
    if success and reports:
        # Flags Section
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p style="text-align:center; font-weight:bold;">{COUNTRY_DISPLAY.get(r["Adm"],{}).get("ar",r["Adm"])}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300)
                st.metric(f"{r['Adm']} Statistics", f"Total: {r['Total']}", f"A: {r['Assignments']} | L: {r['Allotments']}")

        st.divider()

        # Geospatial Map
        if PLOTLY_AVAILABLE and not res_df.empty:
            map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
            if not map_data.empty:
                st.markdown("### 🌍 Geospatial Spectrum Distribution")
                fig_map = px.scatter_mapbox(map_data, lat="lat_dec", lon="lon_dec", hover_name="Site/Allotment Name", color="Adm", zoom=3, mapbox_style="carto-positron", height=500)
                st.plotly_chart(fig_map, use_container_width=True)

        # Dashboard Section
        m1, m2 = st.columns([1, 2])
        chart_df = pd.DataFrame(reports).set_index('Adm')
        with m1:
            st.metric("Confidence", f"{conf}%")
            if PLOTLY_AVAILABLE:
                fig = px.bar(chart_df, y=["Assignments", "Allotments"], barmode="group", title="Technical Distribution")
                st.plotly_chart(fig, use_container_width=True)
        with m2: 
            st.bar_chart(chart_df[['Total']])
        
        st.table(chart_df)
        st.markdown("### 🔊 Assistant Response")
        st.success(msg)
        play_audio(msg)
        with st.expander("Technical Records (Filtered)"): st.dataframe(res_df)
