import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي الشامل
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SUB_TYPE_MAP = {
    'assignment': ['T01', 'GS1', 'DS1', 'G02', 'GT1', 'DT1'],
    'allotment': ['GS2', 'DS2', 'GT2', 'DT2', 'GA1', 'GB1']
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

st.set_page_config(page_title="Seshat AI - Final Core", layout="wide")

# 2. محرك الإحداثيات المطور
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None, None
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s+([NSEW])", dms_str)
        if len(parts) == 2:
            results = []
            for d, m, s, direction in parts:
                val = int(d) + int(m)/60 + int(s)/3600
                if direction in ['S', 'W']: val *= -1
                results.append(val)
            return results[1], results[0] # Lat, Lon
    except: return None, None
    return None, None

# 3. تحميل البيانات مع دعم الملف الجديد
@st.cache_data
def load_db(uploaded=None):
    # الأولوية للملف المرفوع، ثم All Broadcasting، ثم أي ملف Excel متاح
    if uploaded: return pd.read_excel(uploaded)
    
    potential_files = ["All Broadcasting.xlsx", "Data.xlsx"]
    for f in potential_files:
        if os.path.exists(f):
            df = pd.read_excel(f)
            df.columns = df.columns.str.strip()
            return df
    return None

db = load_db(st.sidebar.file_uploader("Upload Database", type=["xlsx"]))

st.title("📡 Seshat AI – Final Engineering Core")
user_q = st.text_input("Ask about any Record, Category or Administration:")

def smart_engine(q, data):
    q = q.lower()
    conf = 0; det_adm = None; det_svc = None; specific_notice = None
    
    # لقط الإدارة
    all_syns = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in q.split():
        match = get_close_matches(word, all_syns, n=1, cutoff=0.7)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys: det_adm = code; conf += 50; break
            if det_adm: break

    # لقط الكود الصريح (DS1, GS2...)
    all_notices = [n for sub in MASTER_KNOWLEDGE.values() for n in sub]
    for word in q.upper().split():
        if word in all_notices:
            specific_notice = word; conf = 100; break

    # لقط الخدمة
    if not specific_notice:
        for svc in MASTER_KNOWLEDGE.keys():
            if svc.lower().replace("_", " ") in q: det_svc = svc; conf += 50; break

    if det_adm:
        if specific_notice:
            mask = (data['Adm'] == det_adm) & (data['Notice Type'] == specific_notice)
            return data[mask], det_adm, specific_notice, conf
        elif det_svc:
            mask = (data['Adm'] == det_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc]))
            res = data[mask]
            if any(k in q for k in SYNONYMS['ALLOT_KEY']):
                res = res[res['Notice Type'].isin(SUB_TYPE_MAP['allotment'])]
            elif any(k in q for k in SYNONYMS['ASSIG_KEY']):
                res = res[res['Notice Type'].isin(SUB_TYPE_MAP['assignment'])]
            return res, det_adm, det_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.progress(confidence / 100)
    
    if res is not None:
        st.metric(f"Total {svc} for {adm}", len(res))
        
        # Voice Assistant
        try:
            tts = gTTS(text=f"Found {len(res)} results for {svc} in {adm}.", lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        # Map Visualization
        if 'Location' in res.columns:
            coords = res['Location'].apply(dms_to_decimal)
            res['lat'] = [c[0] for c in coords]
            res['lon'] = [c[1] for c in coords]
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty:
                st.subheader("🗺️ Geographic Distribution")
                st.map(map_df[['lat', 'lon']])

        st.bar_chart(res['Notice Type'].value_counts())
        with st.expander("🔍 Engineering Data Table"):
            st.dataframe(res)
