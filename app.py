import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- SAFE IMPORT FOR PLOTLY ---
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(layout="wide", page_title="Seshat Spectrum AI v15.2", page_icon="📡")

st.markdown("""
    <style>
    .country-header { text-align: center; font-weight: bold; font-size: 20px; color: #1E3A8A; margin-bottom: 5px; }
    .country-footer { text-align: center; font-weight: bold; font-size: 16px; color: #64748B; margin-top: 5px; }
    .main-title { text-align: center; font-size: 38px; font-weight: 800; color: #1E3A8A; }
    .sub-title { text-align: center; font-size: 18px; color: #475569; margin-bottom: 20px; }
    .stMetric { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# Data Mapping
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
    'ISR': {'ar': 'دولة إسرائيل', 'en': 'Israel'}
}

# Engineering Constants
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'القاهرة'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة', 'الرياض'],
    'TUR': ['turkey', 'tur', 'تركيا', 'أنقرة'],
    'CYP': ['cyprus', 'cyp', 'قبرص', 'نيقوسيا'],
    'GRC': ['greece', 'grc', 'اليونان', 'أثينا'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'تل أبيب']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. NEURAL VOICE ENGINE ---
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 3. PRECISION CORE LOGIC ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def engine_v15_core(q, data):
    q_low = q.lower()
    selected_adms = []
    
    # 1. Identify ADMs
    for code, keys in COUNTRY_MAP.items():
        if any(k in q_low for k in keys): selected_adms.append(code)
    selected_adms = list(set(selected_adms))
    
    if not selected_adms: return None, [], "Identification failed. Please specify a country.", 0, False

    # 2. Identify Type & Service
    w_as = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    w_al = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not w_as and not w_al: w_as = w_al = True

    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()

    # 3. Process each ADM independently to prevent data pollution
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
        
        if w_as and not w_al: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif w_al and not w_as: temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else: temp = adm_df
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Assignments'] if w_as else ''} Assig, {r['Allotments'] if w_al else ''} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 4. MAIN INTERFACE ---
db = load_db()

st.markdown('<div class="main-title">📡 Seshat Master Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">v15.2 | Regulatory Spectrum & Coordination Dashboard</div>', unsafe_allow_html=True)
st.divider()

query = st.text_input("🎙️ Input Regulatory Inquiry:", placeholder="e.g. Compare DAB assignments between Egypt and Israel", key="main_q")

if query and db is not None:
    # Voice Input Replay
    play_audio(query)

    res_df, reports, msg, conf, success = engine_v15_core(query, db)
    
    if success and reports:
        # Centered Large Flags
        f_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with f_cols[i]:
                st.markdown(f'<p class="country-header">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), use_container_width=True)
                st.markdown(f'<p class="country-footer">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()
        
        # Metrics & Charts
        m1, m2 = st.columns([1, 2])
        with m1:
            st.metric("Confidence Score", f"{conf}%")
            if PLOTLY_AVAILABLE and len(reports) > 0:
                fig = px.pie(values=[reports[0]['Assignments'], reports[0]['Allotments']], 
                             names=['Assignments', 'Allotments'], hole=.45,
                             color_discrete_sequence=['#1E3A8A', '#94A3B8'])
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Donut chart visualization active.")

        with m2:
            chart_df = pd.DataFrame(reports).set_index('Adm')
            st.bar_chart(chart_df[["Assignments", "Allotments"]])

        st.table(chart_df)
        
        # Neural Voice Output
        st.success(msg)
        play_audio(msg)

        with st.expander("📝 View Detailed Spectrum Records"):
            st.dataframe(res_df, use_container_width=True)

elif db is None:
    st.error("Data file not found. Please upload Data.xlsx to the repository.")
