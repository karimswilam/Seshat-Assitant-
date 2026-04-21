import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from rapidfuzz import process, fuzz

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Seshat Voice-to-Voice v13.4")

ENABLE_VOICE = False  # ✅ خليه False على Streamlit Cloud

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

STOP_WORDS = [
    'does','is','how','many','have','has','show','give',
    'me','the','between','compared','to'
]

SYNONYMS = {
    'EGY': ['egypt','egy','مصر'],
    'ARS': ['saudi','ars','ksa','السعودية'],
    'TUR': ['turkey','tur','تركيا'],
    'CYP': ['cyprus','cyp','قبرص'],
    'GRC': ['greece','grc','اليونان'],
    'ISR': ['israel','isr','اسرائيل'],
    'ALLOT_KEY': ['allotment','allotments','توزيع'],
    'ASSIG_KEY': ['assignment','assignments','تخصيص'],
    'DAB_KEY': ['dab','داب'],
    'TV_KEY': ['tv','تلفزيون'],
    'FM_KEY': ['fm','راديو']
}

# =========================
# LOAD DATABASE
# =========================
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

# =========================
# LOGICAL ENGINE
# =========================
def advanced_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)

    clean_q = re.sub(r'\b(' + '|'.join(STOP_WORDS) + r')\b', '', q_low)
    words = re.findall(r'\w+', clean_q)

    selected_adms = []
    services = []

    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot:
        wants_assig = wants_allot = True

    all_keys = [k for sub in SYNONYMS.values() for k in sub]

    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper())
            continue

        match = process.extractOne(word, all_keys, scorer=fuzz.WRatio)
        if match and match[1] > 75:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS:
                        selected_adms.append(code)
                    elif code == 'DAB_KEY':
                        services.append('DAB')
                    elif code == 'TV_KEY':
                        services.append('TV')
                    elif code == 'FM_KEY':
                        services.append('FM')

    selected_adms = list(set(selected_adms))
    services = list(set(services)) if services else ['SOUND','TV']

    if not selected_adms:
        return None, [], 0, "No administration detected", is_ar, False

    reports = []
    final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]

        for svc in services:
            svc_codes = (
                ['T01','T03','T04','GS1','GS2','DS1','DS2']
                if svc == 'SOUND' else
                ['GS1','GS2','DS1','DS2'] if svc == 'DAB' else
                ['T01','T03','T04'] if svc == 'FM' else
                ['T02','G02','GT1','GT2','DT1','DT2']
            )

            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]

            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])

            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig: row["Assignments"] = a_count
            if wants_allot: row["Allotments"] = l_count

            if a_count > 0 or l_count > 0:
                reports.append(row)
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join(
        [f"{r['Administration']}: "
         f"{r.get('Assignments','')} {r.get('Allotments','')}"
         for r in reports]
    )

    return final_df, reports, 100, msg, is_ar, True

# =========================
# UI
# =========================
st.title("🛰️ Seshat Voice AI v13.4")

st.markdown("### ✍️ Text / Voice Input")

if ENABLE_VOICE:
    st.warning("Voice input enabled (Local only)")
else:
    st.info("Voice input disabled on Streamlit Cloud")

voice_query = st.text_input(
    "Enter your query:",
    placeholder="e.g. How many FM assignments in Egypt?"
)

if voice_query and db is not None:
    res_df, reports, conf, msg, is_ar, logical = advanced_engine(voice_query, db)

    if logical and reports:
        hf, hc = st.columns([3,1])
        with hf:
            adms = list(set(r['Administration'].split()[0] for r in reports))
            cols = st.columns(len(adms))
            for i, a in enumerate(adms):
                cols[i].image(FLAGS[a], width=60)

        with hc:
            st.metric("Confidence", f"{conf}%")

        chart_df = pd.DataFrame(reports).set_index("Administration")
        st.bar_chart(chart_df)
        st.table(chart_df)

        st.markdown("### 🔊 Voice Output")
        st.success(msg)

        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            st.audio(buf)
        except:
            st.error("TTS failed")

        with st.expander("📊 Detailed Spectrum Data"):
            st.dataframe(res_df, use_container_width=True)
