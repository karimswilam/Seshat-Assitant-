import streamlit as st
import pandas as pd
import os
import io

# 1. الدستور الهندسي (ثابت كما هو)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

# 2. القاموس المرن (تمت إضافة FM والعربي الجديد)
SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    # إضافة مرادفات الخدمات
    'FM_KEY': ['fm', 'اف ام', 'radio', 'راديو'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تخصيص', 'تخصيصات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تكليف', 'تنسيب']
}

st.set_page_config(page_title="Seshat AI - Smart Ref", layout="wide")
st.title("📡 Seshat AI – Engineering Reference v11.1")

@st.cache_data
def load_db(uploaded=None):
    if uploaded: return pd.read_excel(uploaded)
    if os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
        df.columns = df.columns.str.strip()
        return df
    return None

up_file = st.file_uploader("Upload Excel", type=["xlsx"])
db = load_db(up_file)

if db is not None:
    db['Adm'] = db['Adm'].astype(str).str.strip().str.upper()
    db['Notice Type'] = db['Notice Type'].astype(str).str.strip().str.upper()

user_q = st.text_input("Ask: (e.g., How many FM in Egypt? or DAB Allotments)")

def smart_analyze(q, data):
    q = q.lower()
    conf = 0
    detected_adm = None
    detected_svc = None
    sub_filter = None
    
    # لقط الإدارة (كما كانت)
    for code, keywords in SYNONYMS.items():
        if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP'] and any(k in q for k in keywords):
            detected_adm = code
            conf += 50
            break
            
    # لقط الخدمة (دعم FM و Radio الجديد)
    for svc, types in MASTER_KNOWLEDGE.items():
        if svc.lower().replace("_", " ") in q or \
           (svc == 'SOUND' and any(k in q for k in SYNONYMS['FM_KEY'])) or \
           (svc == 'TV' and 'تلفزيون' in q):
            detected_svc = svc
            conf += 50
            break

    # لقط نوع التخصيص/التنسيب (الفرز الداخلي)
    if any(k in q for k in SYNONYMS['ALLOT_KEY']): sub_filter = "ALLOTMENT"
    if any(k in q for k in SYNONYMS['ASSIG_KEY']): sub_filter = "ASSIGNMENT"

    if detected_adm and detected_svc:
        mask = (data['Adm'] == detected_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[detected_svc]))
        final_res = data[mask]
        
        # تطبيق الفلتر الداخلي لو المستخدم طلبه
        if sub_filter == "ALLOTMENT":
            final_res = final_res[final_res['Notice Type'].str.contains('2|G2|T2', na=False)]
        elif sub_filter == "ASSIGNMENT":
            final_res = final_res[final_res['Notice Type'].str.contains('1|G1|T1', na=False)]
            
        return final_res, detected_adm, detected_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm_res, svc_res, c_level = smart_analyze(user_q, db)
    st.progress(c_level / 100)
    
    if res is not None:
        st.metric(f"Results for {adm_res} ({svc_res})", len(res))
        st.bar_chart(res['Notice Type'].value_counts())
        
        with st.expander("🔍 View Data Detail (Assignments/Allotments)"):
            st.dataframe(res)
    else:
        st.warning("Please specify Country (e.g. Egypt) and Service (e.g. FM or DAB Allotment).")
