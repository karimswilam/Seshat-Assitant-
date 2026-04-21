import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. Flags System ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

# --- 2. Master Knowledge Base ---
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
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'سعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 't-dab'],
    'TV_KEY': ['tv', 'تلفزيون', 'مرئية']
}

st.set_page_config(page_title="Seshat AI v12.0.6 - Deep Analysis", layout="wide")

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def deep_analytical_engine(q, data):
    q_lower = q.lower()
    is_arabic = any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in q)
    words = re.findall(r'\w+', q_lower)
    
    adms = []; det_svc = None; filter_type = None; exclude_code = None
    
    # Matching Logic
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for i, word in enumerate(words):
        if word in ['except', 'ماعدا'] and i+1 < len(words): exclude_code = words[i+1].upper()
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'

    if 'fm' in words: det_svc = 'FM'
    if not adms: return None, [], 0, "No Administration detected.", is_arabic

    # filtering
    res = data[data['Adm'].isin(adms)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if exclude_code: res = res[res['Notice Type'] != exclude_code]

    # --- logic الجديد: التفصيل لكل دولة (The Justification) ---
    report_data = []
    human_msg = ""
    
    for adm in adms:
        adm_df = res[res['Adm'] == adm]
        allots = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        assigs = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        
        # بناء نص التقرير
        if is_arabic:
            msg = f"الدولة {adm}: إجمالي {len(adm_df)} (تخصيص: {len(assigs)} | توزيع: {len(allots)})"
        else:
            msg = f"{adm}: Total {len(adm_df)} (Assig: {len(assigs)} | Allot: {len(allots)})"
        
        report_data.append({"adm": adm, "total": len(adm_df), "assig": len(assigs), "allot": len(allots), "msg": msg})

    final_text = " | ".join([d['msg'] for d in report_data])
    return res, report_data, 100, final_text, is_arabic

# --- UI ---
user_input = st.text_input("💬 Ask Seshat (Analytical Mode):", placeholder="Compare Egypt and Israel DAB")

if db is not None and user_input:
    res_df, report, conf, ans_text, is_ar = deep_analytical_engine(user_input, db)
    
    if report:
        # عرض الأعلام والبيانات لكل دولة بشكل منفصل
        flag_cols = st.columns(len(report))
        for i, data in enumerate(report):
            with flag_cols[i]:
                st.image(FLAGS.get(data['adm'], ""), width=80)
                st.metric(data['adm'], f"{data['total']} Records")
                st.caption(f"Assignments: {data['assig']}")
                st.caption(f"Allotments: {data['allot']}")

        st.success(ans_text)
        
        # الرسوم البيانية - المقارنة التفصيلية
        if len(report) > 1:
            chart_data = pd.DataFrame(report).set_index('adm')[['assig', 'allot']]
            st.bar_chart(chart_data)
        
        st.dataframe(res_df, use_container_width=True)
        
        # الصوت
        try:
            tts = gTTS(text=ans_text, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
