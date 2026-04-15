import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (Strict & Official)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

# 2. تحسين الربط بين المسميات والـ Notice Types الهندسية
SUB_TYPE_MAP = {
    'assignment': ['T01', 'GS1', 'DS1', 'G02', 'GT1', 'DT1'], # كل ما هو تخصيص (ينتهي بـ 1 أو T02/G02)
    'allotment': ['GS2', 'DS2', 'GT2', 'DT2', 'GA1', 'GB1']     # كل ما هو تعيين (ينتهي بـ 2 أو G/D T2)
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'israil'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'تعيين', 'allotments'],
    'ASSIG_KEY': ['assignment', 'تخصيص', 'assignments']
}

st.set_page_config(page_title="Seshat AI v12.1", layout="wide")
st.title("📡 Seshat AI – Precision Engineering Assistant")

# --- Coordinates Parser (كما هو بلا تغيير) ---
def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s+([NSEW])", dms_str)
        if len(parts) == 2:
            results = []
            for d, m, s, direction in parts:
                val = int(d) + int(m)/60 + int(s)/3600
                if direction in ['S', 'W']: val *= -1
                results.append(val)
            return results[1], results[0]
    except: return None, None
    return None, None

@st.cache_data
def load_db(uploaded=None):
    target = uploaded if uploaded else ("All Broadcasting.xlsx" if os.path.exists("All Broadcasting.xlsx") else "Data.xlsx")
    if isinstance(target, str) and os.path.exists(target):
        return pd.read_excel(target)
    elif uploaded:
        return pd.read_excel(uploaded)
    return None

db = load_db(st.sidebar.file_uploader("Upload Database", type=["xlsx"]))

# 3. محرك البحث المطور بدقة الـ Exact Match
user_q = st.text_input("Ask Seshat (Precision Mode Active):")

def smart_engine(q, data):
    q = q.lower()
    conf = 0
    det_adm = None
    det_svc = None
    specific_notice = None
    
    # أ) لقط الإدارة (Fuzzy)
    all_syns = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in q.split():
        match = get_close_matches(word, all_syns, n=1, cutoff=0.7)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys: det_adm = code; conf += 50; break
            if det_adm: break

    # ب) لقط الـ Notice Type الصريح (زي DS1) - Exact Match
    all_notices = [n for sub in MASTER_KNOWLEDGE.values() for n in sub]
    for word in q.upper().split():
        if word in all_notices:
            specific_notice = word
            conf = 100 # ثقة كاملة لو لقط الكود صراحة
            break

    # ج) لقط الخدمة (Category)
    if not specific_notice:
        for svc in MASTER_KNOWLEDGE.keys():
            if svc.lower().replace("_", " ") in q: det_svc = svc; conf += 50; break

    if det_adm:
        # لو سأل عن كود محدد (زي DS1)
        if specific_notice:
            mask = (data['Adm'] == det_adm) & (data['Notice Type'] == specific_notice)
            return data[mask], det_adm, specific_notice, conf
        
        # لو سأل عن فئة (زي DAB)
        elif det_svc:
            mask = (data['Adm'] == det_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc]))
            res = data[mask]
            
            # تطبيق فلتر التخصيص/التعيين بدقة
            if any(k in q for k in SYNONYMS['ALLOT_KEY']):
                res = res[res['Notice Type'].isin(SUB_TYPE_MAP['allotment'])]
            elif any(k in q for k in SYNONYMS['ASSIG_KEY']):
                res = res[res['Notice Type'].isin(SUB_TYPE_MAP['assignment'])]
            return res, det_adm, det_svc, conf
            
    return None, None, None, 0

# 4. Dashboard & Results
if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.progress(confidence / 100)
    
    if res is not None:
        st.metric(f"Total {svc} for {adm}", len(res))
        
        # Voice (كما هو)
        tts = gTTS(text=f"I found {len(res)} results.", lang='en')
        b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)

        # Map Logic (باستخدام الـ Parser الجديد)
        if 'Location' in res.columns:
            res['lat'], res['lon'] = zip(*res['Location'].apply(dms_to_decimal))
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty:
                st.subheader("🗺️ Geographic Distribution")
                st.map(map_df[['lat', 'lon']])

        st.bar_chart(res['Notice Type'].value_counts())
        with st.expander("🔍 Engineering Data"):
            st.dataframe(res)
