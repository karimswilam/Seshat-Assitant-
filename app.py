import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz
import plotly.express as px

# --- 1. CONFIG & UI STYLE ---
st.set_page_config(layout="wide", page_title="Seshat AI v15.0 | Spectrum Intelligence", page_icon="📡")

# Custom CSS لتحسين شكل الواجهة والأعلام
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

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'جمهورية مصر'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'التركية'],
    'CYP': ['cyprus', 'cyp', 'قبرص', 'القبرصية'],
    'GRC': ['greece', 'grc', 'اليونان', 'اليونانية'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. VOICE ENGINE ---
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = text.replace("|", " . ").replace(":", " , ")
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        data = asyncio.run(generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 3. LOGIC ENGINE (v15.0 Protected) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def advanced_engine_v15(q, data):
    q_low = q.lower()
    selected_adms = []
    words = re.findall(r'\w+', q_low)
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS: selected_adms.append(word.upper())
    for code, keywords in COUNTRY_MAP.items():
        if any(k in q_low for k in keywords): selected_adms.append(code)
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "No country identified.", 0, False

    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    service_filter = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): service_filter = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): service_filter = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): service_filter = ['T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if service_filter: adm_df = adm_df[adm_df['Notice Type'].isin(service_filter)]
        a_df = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        l_df = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        reports.append({"Adm": adm, "Assignments": len(a_df), "Allotments": len(l_df)})
        if wants_assig and not wants_allot: final_df = pd.concat([final_df, a_df])
        elif wants_allot and not wants_assig: final_df = pd.concat([final_df, l_df])
        else: final_df = pd.concat([final_df, adm_df])

    msg_list = [f"{r['Adm']}: {r['Assignments'] if wants_assig else ''} Assignments, {r['Allotments'] if wants_allot else ''} Allotments" for r in reports]
    return final_df, reports, " | ".join(msg_list), 100, True

# --- 4. UI CONSTRUCTION ---
db = load_db()

# Custom Header
st.markdown('<div class="main-title">📡 Seshat Spectrum Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Advanced ITU Regulatory Analysis Dashboard v15.0</div>', unsafe_allow_html=True)
st.divider()

# Question Area
with st.container():
    query = st.text_input("🎙️ Speak or Type your Spectrum Inquiry:", placeholder="e.g. Compare DAB between Egypt and Turkey", key="main_q")

if query:
    st.markdown("### 🔈 Question Audio")
    play_audio(query)

    if db is not None:
        res_df, reports, msg, conf, success = advanced_engine_v15(query, db)
        
        if success and reports:
            # Section: Comparative Flags (Centered & Large)
            st.divider()
            f_cols = st.columns(len(reports))
            for i, r in enumerate(reports):
                with f_cols[i]:
                    st.markdown(f'<p class="country-header">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                    st.image(FLAGS.get(r['Adm']), use_container_width=True)
                    st.markdown(f'<p class="country-footer">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

            # Section: Metrics & Charts
            st.divider()
            m1, m2 = st.columns([1, 3])
            with m1:
                st.metric("Confidence Score", f"{conf}%")
                # Donut Chart for the first country in query
                if len(reports) > 0:
                    fig_pie = px.pie(values=[reports[0]['Assignments'], reports[0]['Allotments']], 
                                   names=['Assignments', 'Allotments'], hole=.4,
                                   title=f"Ratio for {reports[0]['Adm']}",
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie, use_container_width=True)

            with m2:
                chart_df = pd.DataFrame(reports).set_index('Adm')
                st.bar_chart(chart_df[["Assignments", "Allotments"]])

            # Table Output
            st.table(chart_df)

            # Section: Voice Response
            st.markdown("### 🔊 Neural Assistant Response")
            st.success(msg)
            play_audio(msg)

            with st.expander("📝 Detailed Regulatory Records"):
                st.dataframe(res_df, use_container_width=True)

else:
    st.info("Waiting for your regulatory query... Try asking about Comparisons or Specific Services.")
