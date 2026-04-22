import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz
import plotly.express as px

# --- 1. CONFIG & UI STYLE (Fixed & Stable) ---
st.set_page_config(layout="wide", page_title="Seshat AI v15.1 | Precision Spectrum", page_icon="📡")

st.markdown("""
    <style>
    .country-header { text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 5px; color: #1E3A8A; }
    .country-footer { text-align: center; font-weight: bold; font-size: 16px; margin-top: 5px; color: #64748B; }
    .main-title { text-align: center; font-size: 35px; font-weight: 800; color: #1E3A8A; margin-bottom: 10px; }
    .sub-title { text-align: center; font-size: 18px; color: #475569; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_html=True)

FLAGS = {
    'EGY': "https://flagcdn.com/w320/eg.png", 'ARS': "https://flagcdn.com/w320/sa.png",
    'TUR': "https://flagcdn.com/w320/tr.png", 'CYP': "https://flagcdn.com/w320/cy.png",
    'GRC': "https://flagcdn.com/w320/gr.png", 'ISR': "https://flagcdn.com/w320/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

# ثوابت لا يمكن المساس بها
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
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assign'],
    'DAB_KEY': ['dab', 'داب'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. THE VOICE ENGINE ---
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

# --- 3. PRECISION ENGINE v15.1 ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def engine_v15_1(q, data):
    q_low = q.lower()
    
    # Reset Per-Query Logic
    selected_adms = []
    for code, keys in COUNTRY_MAP.items():
        if any(k in q_low for k in keys): selected_adms.append(code)
    selected_adms = list(set(selected_adms))
    
    if not selected_adms: return None, [], "ADM identification failed.", 0, False

    # Intent & Service Filter
    w_as = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    w_al = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not w_as and not w_al: w_as = w_al = True

    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        # Only add to report if there is actual data
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
        
        # Build Filtered DataFrame for the Expander
        if w_as and not w_al: temp_df = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif w_al and not w_as: temp_df = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else: temp_df = adm_df
        final_df = pd.concat([final_df, temp_df], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r['Assignments'] if w_as else ''} Assig, {r['Allotments'] if w_al else ''} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 4. UI ---
db = load_db()
st.markdown('<div class="main-title">📡 Seshat Spectrum Precision v15.1</div>', unsafe_allow_html=True)

query = st.text_input("🎙️ Enter Query:", placeholder="e.g. Compare Egypt and Saudi DAB", key="main_q")

if query and db is not None:
    # 1. Voice In
    play_audio(query)

    res_df, reports, msg, conf, success = engine_v15_1(query, db)
    
    if success and reports:
        # Flags Section
        f_cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with f_cols[i]:
                st.markdown(f'<p class="country-header">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), use_container_width=True)
                st.markdown(f'<p class="country-footer">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()
        # Charts Section
        m1, m2 = st.columns([1, 2])
        with m1:
            st.metric("Confidence Score", f"{conf}%")
            if len(reports) > 0:
                fig_pie = px.pie(values=[reports[0]['Assignments'], reports[0]['Allotments']], 
                               names=['Assignments', 'Allotments'], hole=.4, 
                               color_discrete_sequence=['#1E3A8A', '#94A3B8'])
                st.plotly_chart(fig_pie, use_container_width=True)
        with m2:
            chart_df = pd.DataFrame(reports).set_index('Adm')
            st.bar_chart(chart_df[["Assignments", "Allotments"]])

        st.table(chart_df)
        
        # 2. Voice Out
        st.success(msg)
        play_audio(msg)

        with st.expander("Technical Log"):
            st.dataframe(res_df)
