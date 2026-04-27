import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# =================================================
# 1. CONFIG & INTERFACE
# =================================================
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(
        f"""
        <div style="text-align:center">
            <h1 style="color:#1E3A8A;margin-bottom:0">{PROJECT_NAME}</h1>
            <p style="color:#475569;font-size:18px">{PROJECT_SLOGAN}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# =================================================
# 2. CONSTANTS & MAPS
# =================================================
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': 'جمهورية مصر العربية',
    'ARS': 'المملكة العربية السعودية',
    'TUR': 'الجمهورية التركية',
    'CYP': 'جمهورية قبرص',
    'GRC': 'الجمهورية اليونانية',
    'ISR': 'إسرائيل'
}

COUNTRY_MAP = {
    'EGY': ['egypt','egy','مصر','المصرية'],
    'ARS': ['saudi','ars','ksa','السعودية','المملكة'],
    'TUR': ['turkey','tur','تركيا'],
    'CYP': ['cyprus','cyp','قبرص'],
    'GRC': ['greece','grc','اليونان'],
    'ISR': ['israel','isr','اسرائيل']
}

STRICT_ASSIG = ['T01','T03','T04','GS1','DS1','GT1','DT1','G01']
STRICT_ALLOT = ['T02','G02','GT2','DT2','GS2','DS2']

SYNONYMS = {
    'ASSIG': ['assignment','assignments','تخصيص','تخصيصات'],
    'ALLOT': ['allotment','allotments','توزيع','توزيعات'],
    'DAB': ['dab','داب','صوتية','صوتيه','sound'],
    'TV': ['tv','television','تلفزيون','مرئية'],
    'FM': ['fm','radio','راديو'],
}


# =================================================
# 3. GEOSPATIAL PARSING (ROBUST)
# =================================================
def engine_v17_0(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    # 1. تحديد الدول (يدعم أي عدد بمرونة عالية)
    # أضفنا "تركي" و "التركية" لضمان عدم حدوث Error مع تركيا
    EXTENDED_MAP = {
        'EGY': COUNTRY_MAP['EGY'] + ['المصريه', 'مصرى'],
        'TUR': COUNTRY_MAP['TUR'] + ['تركي', 'التركية', 'turkish', 'tr'],
        'ISR': COUNTRY_MAP['ISR'] + ['اسرائيلية', 'الاسرائيلي']
    }
    
    selected_adms = [code for code, keys in EXTENDED_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms)) 
    
    if not selected_adms: 
        return None, [], "لم يتم التعرف على الدولة في الطلب.", 0, False

    # 2. تحديد الخدمات (نفس الـ Logic المتين بتاعك)
    svc_codes = []
    is_total = any(x in q_low for x in SYNONYMS['TOTAL_KEY'])
    
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes.extend(['GS1','GS2','DS1','DS2'])
    if any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes.extend(['T02','G02','GT1','GT2','DT1','DT2'])
    if any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes.extend(['T01','T03','T04'])
    
    if is_total or not svc_codes:
        svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2','T01','T03','T04']

    # 3. معالجة البيانات
    reports = []; final_df = pd.DataFrame()
    comp_key = "Assignments" if any(x in q_low for x in SYNONYMS['ASSIG_KEY']) else "Total"

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {
            "Adm": adm, 
            "Total": a_count + l_count, 
            "Assignments": a_count, 
            "Allotments": l_count,
            "Name": COUNTRY_DISPLAY[adm]['ar'] if is_ar else COUNTRY_DISPLAY[adm]['en']
        }
        reports.append(res)
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    # 4. الـ Triple Comparison Logic (الترتيب التصاعدي والتنازلي)
    # بنرتب التقارير حسب القيمة المطلوبة (Total أو Assignments)
    sorted_reports = sorted(reports, key=lambda x: x[comp_key], reverse=True)
    
    if len(reports) >= 2:
        if is_ar:
            top_adm = sorted_reports[0]['Name']
            top_val = sorted_reports[0][comp_key]
            msg = f"الترتيب كالتالي: المركز الأول {top_adm} بـ {top_val} سجل. "
            comparison_details = " ثم ".join([f"{r['Name']} ({r[comp_key]})" for r in sorted_reports[1:]])
            msg += "يليه " + comparison_details
        else:
            top_adm = sorted_reports[0]['Adm']
            top_val = sorted_reports[0][comp_key]
            msg = f"Ranking: {top_adm} leads with {top_val}. "
            msg += " Followed by " + ", ".join([f"{r['Adm']} ({r[comp_key]})" for r in sorted_reports[1:]])
    else:
        r = reports[0]
        msg = f"{r['Name']}: {r[comp_key]} {comp_key}."

    return final_df, reports, msg, 100, True
