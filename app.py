import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (تم تنقيحه بناءً على ملفاتك الفعليه)
# حذفنا T02 وأي أكواد مش موجودة في الـ 2 Databases
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['TB2', 'DT1', 'DT2', 'GT1', 'GT2', 'G02'], # تحديث شامل لأكواد التلفزيون عندك
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'israil'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تليفزيون', 'مرئي'], # تقوية البحث العربي
    'ALLOT_KEY': ['allotment', 'تعيين', 'allotments', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'تخصيص', 'assignments', 'تنسيب']
}

st.set_page_config(page_title="Seshat AI - Precise Core", layout="wide")

# --- محرك الإحداثيات (ثابت) ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None, None
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s+([NSEW])", dms_str)
        if len(parts) == 2:
            res = []
            for d, m, s, direction in parts:
                val = int(d) + int(m)/60 + int(s)/3600
                if direction in ['S', 'W']: val *= -1
                res.append(val)
            return res[1], res[0]
    except: return None, None
    return None, None

# 2. محرك الدمج الذكي (v3 - Unified Storage)
@st.cache_data
def load_and_merge_dbs():
    all_dfs = []
    potential_files = ["All Broadcasting.xlsx", "Data.xlsx"]
    for f in potential_files:
        if os.path.exists(f):
            df = pd.read_excel(f)
            df.columns = df.columns.str.strip()
            all_dfs.append(df)
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        if 'BR Id' in combined.columns:
            combined = combined.drop_duplicates(subset=['BR Id'])
        return combined
    return None

db = load_and_merge_dbs()

# 3. محرك البحث (النسخة الأكثر دقة)
st.title("📡 Seshat AI – Engineering Precision v12.4")
user_q = st.text_input("Ask: (English or Arabic)")

def smart_engine(q, data):
    q = q.lower()
    conf = 0; det_adm = None; det_svc = None; specific_notice = None
    
    # أ) لقط الإدارة (عربي/إنجليزي)
    all_syns = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in q.split():
        match = get_close_matches(word, all_syns, n=1, cutoff=0.7)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys: 
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']: det_adm = code; conf += 50
            if det_adm: break

    # ب) لقط الـ Notice Type الصريح (DS1, TB2...)
    all_notices = [n for sub in MASTER_KNOWLEDGE.values() for n in sub]
    for word in q.upper().split():
        if word in all_notices:
            specific_notice = word; conf = 100; break

    # ج) لقط الخدمة (TV, FM, DAB)
    if not specific_notice:
        if any(k in q for k in SYNONYMS['TV_KEY']): det_svc = 'TV'; conf += 50
        elif 'fm' in q or 'radio' in q or 'راديو' in q: det_svc = 'FM'; conf += 50
        elif 'dab' in q: det_svc = 'DAB'; conf += 50
        else:
            for svc in MASTER_KNOWLEDGE.keys():
                if svc.lower().replace("_", " ") in q: det_svc = svc; conf += 50; break

    if det_adm:
        data['Adm'] = data['Adm'].astype(str).str.strip().str.upper()
        if specific_notice:
            res = data[(data['Adm'] == det_adm) & (data['Notice Type'] == specific_notice)]
            return res, det_adm, specific_notice, conf
        elif det_svc:
            res = data[(data['Adm'] == det_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc]))]
            # فلتر التعيين/التخصيص
            if any(k in q for k in SYNONYMS['ALLOT_KEY']):
                res = res[res['Notice Type'].str.contains('2|G2|T2|GA1|GB1', na=False)]
            elif any(k in q for k in SYNONYMS['ASSIG_KEY']):
                res = res[res['Notice Type'].str.contains('1|G1|T1|T01|T03|T04', na=False)]
            return res, det_adm, det_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.progress(confidence / 100)
    
    if res is not None:
        count = len(res)
        st.metric(f"Results for {adm} ({svc})", count)
        
        # Voice Output (English only for numbers)
        try:
            tts = gTTS(text=f"Total {svc} for {adm} is {count}.", lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        # Map & Dashboard (ثابتين)
        if 'Location' in res.columns:
            coords = res['Location'].apply(dms_to_decimal)
            res['lat'], res['lon'] = zip(*coords)
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty: st.map(map_df[['lat', 'lon']])

        st.bar_chart(res['Notice Type'].value_counts())
        st.dataframe(res)
