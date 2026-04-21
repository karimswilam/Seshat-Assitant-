import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. Flags & Knowledge Base ---
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
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'تلفزيون']
}

st.set_page_config(page_title="Seshat AI v12.0.7 - Hybrid Analysis", layout="wide")

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def hybrid_engine(q, data):
    q_lower = q.lower()
    is_ar = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
    words = re.findall(r'\w+', q_lower)
    
    adms = []; det_svc = None; filter_type = None
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words or 'راديو' in q_lower: det_svc = 'FM'
    if not adms: return None, [], 0, "No ADM found", is_ar

    # Filtering Logic
    res = data[data['Adm'].isin(adms)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]

    # بناء التقرير الهجين
    report = []
    for adm in adms:
        adm_df = res[res['Adm'] == adm]
        allot_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        assig_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        
        report.append({
            "Administration": adm,
            "Assignments": assig_count,
            "Allotments": allot_count,
            "Total": len(adm_df)
        })

    ans_text = " | ".join([f"{d['Administration']}: {d['Total']} (Assig:{d['Assignments']}, Allot:{d['Allotments']})" for d in report])
    return res, report, 100, ans_text, is_ar

# --- UI ---
user_input = st.text_input("💬 Hybrid Query (Comparison or Single ADM Analysis):")

if db is not None and user_input:
    res_df, report_list, conf, ans_text, is_ar = hybrid_engine(user_input, db)
    
    if report_list:
        # 1. Metrics & Flags
        cols = st.columns(len(report_list))
        for i, r in enumerate(report_list):
            with cols[i]:
                st.image(FLAGS.get(r['Administration']), width=80)
                st.metric(f"{r['Administration']} Total", r['Total'])
                st.write(f"✅ Assig: {r['Assignments']}")
                st.write(f"📋 Allot: {r['Allotments']}")

        # 2. Side-by-Side Bar Chart (The Core Request)
        st.markdown("### 📊 Statistical Comparison")
        chart_df = pd.DataFrame(report_list).set_index('Administration')[['Assignments', 'Allotments']]
        
        # استخدام st.bar_chart مع Dataframe مفصولة يضمن ظهورهم بجانب بعض
        st.bar_chart(chart_df)

        # 3. Data Details
        with st.expander("Show Raw Data Table"):
            st.dataframe(res_df, use_container_width=True)

        # 4. Voice Output
        try:
            tts = gTTS(text=ans_text, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
