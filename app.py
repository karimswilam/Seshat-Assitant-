import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. Flags & Knowledge ---
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
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
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'تركيا'], 'ISR': ['israel', 'اسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو']
}

st.set_page_config(page_title="Seshat AI v12.0.8 - Logical Sense", layout="wide")

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def smart_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
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
                    elif code == 'FM_KEY': det_svc = 'FM'

    if not adms: return None, None, 0, "Adm not found", is_ar, False

    # --- Logical Check ---
    is_logical = True
    if det_svc == 'FM' and filter_type == 'allot': is_logical = False # FM has no allotments

    if not is_logical:
        msg = "This is illogical: FM service operates on Assignments only, no Allotments." if not is_ar else "طلب غير منطقي: خدمة الـ FM تعمل بنظام التخصيص فقط ولا يوجد لها توزيعات."
        return None, adms, 0, msg, is_ar, False

    # --- Filtering ---
    res = data[data['Adm'].isin(adms)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    
    # الصرامة في الفلترة: لو طلب تخصيص بس، يمسح التوزيع تماماً
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    report = []
    for adm in adms:
        df_a = res[res['Adm'] == adm]
        report.append({
            "Administration": adm,
            "Assignments": len(df_a[df_a['Notice Type'].isin(STRICT_ASSIG)]),
            "Allotments": len(df_a[df_a['Notice Type'].isin(STRICT_ALLOT)]),
            "Total": len(df_a)
        })

    return res, report, 100, "Logic Success", is_ar, True

# --- UI ---
query = st.text_input("💬 Ask Seshat:")

if db is not None and query:
    res_df, report, conf, msg, is_ar, logical = smart_engine(query, db)
    
    if not logical:
        st.error(msg)
        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
    else:
        # Display Metrics
        cols = st.columns(len(report))
        for i, r in enumerate(report):
            with cols[i]:
                st.image(FLAGS.get(r['Administration']), width=80)
                st.metric(r['Administration'], r['Total'])
        
        # الشارت المنفصل (Non-Stacked)
        if report:
            chart_data = pd.DataFrame(report).set_index('Administration')
            # تحديد الأعمدة بناءً على الطلب (لو سأل عن واحد بس يظهر واحد بس)
            if 'allot' in query.lower() and 'assign' not in query.lower():
                st.bar_chart(chart_data[['Allotments']])
            elif 'assign' in query.lower() and 'allot' not in query.lower():
                st.bar_chart(chart_data[['Assignments']])
            else:
                st.bar_chart(chart_data[['Assignments', 'Allotments']])

        st.dataframe(res_df, use_container_width=True)
