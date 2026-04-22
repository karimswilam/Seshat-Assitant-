import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
from rapidfuzz import process, fuzz

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & STYLING ---
st.set_page_config(layout="wide", page_title="Seshat AI v15.8")

# وظيفة ذكية لجلب اللوجو حتى لو الاسم فيه اختلاف بسيط
def get_logo_html():
    possible_names = ["Designer.jpg", "designer.jpg", "Designer.png", "Designer.jpeg"]
    logo_path = None
    for name in possible_names:
        if os.path.exists(name):
            logo_path = name
            break
    
    if logo_path:
        with open(logo_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
            return f'<img src="data:image/jpeg;base64,{b64}" style="width:120px; border-radius:10px; margin-bottom:10px;">'
    return "" # يرجع فاضي لو مفيش صورة بدل ما يبوظ الصفحة

logo_code = get_logo_html()

st.markdown(f"""
    <style>
    .header-container {{ text-align: center; padding: 20px; background-color: #f8fafc; border-radius: 15px; margin-bottom: 20px; }}
    .main-title {{ font-size: 32px; font-weight: 800; color: #1E3A8A; margin: 5px 0; }}
    .sub-title {{ font-size: 16px; color: #475569; }}
    </style>
    <div class="header-container">
        {logo_code}
        <div class="main-title">Seshat Master Precision v15.8</div>
        <div class="sub-title">Project BASIRA | Spectrum Intelligence & Governance</div>
    </div>
    """, unsafe_allow_html=True)

# --- 2. THE PROTECTED LOGIC (v15.6 Core) ---
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
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'tlfzyon'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'GENERIC_BR_KEY': ['إذاعية', 'إذاعة', 'اذاعة', 'اذاعية', 'broadcasting']
}

# --- 3. VOICE ENGINE ---
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

# --- 4. DATA ENGINE v15.6 (Logic Unchanged) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def engine_v15_8(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "ADM Identification failed.", 0, False

    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    svc_codes = []
    is_dab = any(x in q_low for x in SYNONYMS['DAB_KEY'])
    is_tv = any(x in q_low for x in SYNONYMS['TV_KEY'])
    is_fm = any(x in q_low for x in SYNONYMS['FM_KEY'])
    is_gen = any(x in q_low for x in SYNONYMS['GENERIC_BR_KEY'])

    if is_dab: svc_codes = ['GS1','GS2','DS1','DS2']
    elif is_tv: svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif is_fm: svc_codes = ['T01','T03','T04']
    elif is_gen: svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {"Adm": adm}
        if mentions_assig and not mentions_allot:
            res["Assignments"] = a_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif mentions_allot and not mentions_assig:
            res["Allotments"] = l_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else:
            res["Assignments"] = a_count
            res["Allotments"] = l_count
            temp = adm_df
        reports.append(res)
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: " + (f"{r['Assignments']} Assig " if "Assignments" in r else "") + (f"{r['Allotments']} Allot" if "Allotments" in r else "") for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. RUNTIME ---
db = load_db()
query = st.text_input("🎙️ Enter Query:", key="main_q")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    st.divider()

    res_df, reports, msg, conf, success = engine_v15_8(query, db)
    
    if success and reports:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p class="country-header">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300)
                st.markdown(f'<p class="country-footer">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()
        m1, m2 = st.columns([1, 2])
        chart_df = pd.DataFrame(reports).set_index('Adm')
        with m1:
            st.metric("Confidence", f"{conf}%")
            if PLOTLY_AVAILABLE and "Assignments" in chart_df.columns and "Allotments" in chart_df.columns:
                fig = px.pie(values=[reports[0].get('Assignments', 0), reports[0].get('Allotments', 0)], 
                             names=['Assignments', 'Allotments'], hole=.4, color_discrete_sequence=['#1E3A8A', '#94A3B8'])
                st.plotly_chart(fig, use_container_width=True)
        with m2: st.bar_chart(chart_df)
        st.table(chart_df)
        st.markdown("### 🔊 Assistant Response")
        st.success(msg)
        play_audio
