import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (ثابت لا يتغير)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

# 2. القاموس المرن (Generic Synonyms) - تم تقويته بالعربي والإخطاء الإملائية
SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'egibt', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'israil', 'إسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا', 'turkia'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'تعيينات', 'توزيع', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب', 'assign'],
    'DAB_KEY': ['dab', 'داب', 'ديجيتال'],
    'FM_KEY': ['fm', 'اف ام', 'راديو', 'radio']
}

st.set_page_config(page_title="Seshat AI v12.6 - Smart Core", layout="wide")
st.title("📡 Seshat AI – Professional Engineering Assistant")

def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s+([NSEW])", dms_str)
        if len(parts) == 2:
            results = []
            for d, m, s, direction in parts:
                decimal = int(d) + int(m)/60 + int(s)/3600
                if direction in ['S', 'W']: decimal *= -1
                results.append(decimal)
            return results[1], results[0]
    except: return None, None
    return None, None

@st.cache_data
def load_db(uploaded=None):
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = uploaded if uploaded else ("Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None))
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db(st.sidebar.file_uploader("Upload Database", type=["xlsx"]))
user_q = st.text_input("Ask Seshat (العربي والإنجليزي متاح):")

def smart_engine(q, data):
    # تنظيف السؤال من الرموز عشان العربي يظبط
    q_clean = re.sub(r'[?؟.!]', '', q.lower()).strip()
    words = q_clean.split()
    
    conf = 0
    detected_adm = None
    detected_svc = None
    filter_type = None # للنظام الجديد في الـ Assignment/Allotment
    
    # محرك البحث المرن (Fuzzy Match)
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.7)
        if match:
            found = match[0]
            # تحديد الإدارة
            for code, keywords in SYNONYMS.items():
                if found in keywords:
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']:
                        detected_adm = code
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': detected_svc = 'DAB'
                    elif code == 'FM_KEY': detected_svc = 'FM'
                    break

    # لو ملقاش الخدمة من القاموس، يدور في الـ MASTER_KNOWLEDGE
    if not detected_svc:
        for svc in MASTER_KNOWLEDGE.keys():
            if svc.lower().replace("_", " ") in q_clean:
                detected_svc = svc; break

    # حساب الـ Confidence
    if detected_adm: conf += 50
    if detected_svc: conf += 50

    if detected_adm and detected_svc:
        mask = (data['Adm'].astype(str).str.contains(detected_adm)) & \
               (data['Notice Type'].isin(MASTER_KNOWLEDGE[detected_svc]))
        res = data[mask]
        
        # تطبيق فلتر التخصيص والتعيين بصرامة بناءً على الفهم المرن
        if filter_type == 'allot':
            res = res[res['Notice Type'].str.contains('2|G2|T2', na=False)]
        elif filter_type == 'assig':
            res = res[res['Notice Type'].str.contains('1|G1|T1|T01|T03|T04', na=False)]
            
        return res, detected_adm, detected_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.progress(confidence / 100)
    st.write(f"**Confidence Indicator:** {confidence}%")

    if res is not None:
        count = len(res)
        st.metric(f"Total {svc} for {adm}", count)
        
        try:
            tts = gTTS(text=f"Found {count} records.", lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        if 'Location' in res.columns:
            coords = res['Location'].apply(dms_to_decimal)
            res['lat'], res['lon'] = zip(*coords)
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty: st.map(map_df[['lat', 'lon']])

        st.dataframe(res)
