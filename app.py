import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (ممنوع اللمس)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['TB2', 'DT1', 'DT2', 'GT1', 'GT2', 'G02'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'israil'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'مرئي'],
    'ALLOT_KEY': ['allotment', 'تعيين', 'allotments'],
    'ASSIG_KEY': ['assignment', 'تخصيص', 'assignments']
}

st.set_page_config(page_title="Seshat AI v12.5 - No Nonsense", layout="wide")

# --- محرك الإحداثيات (ثابت) ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None, None
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s+([NSEW])", dms_str)
        if len(parts) == 2:
            res = []
            for d, m, s, dir in parts:
                v = int(d) + int(m)/60 + int(s)/3600
                if dir in ['S', 'W']: v *= -1
                res.append(v)
            return res[1], res[0]
    except: return None, None
    return None, None

# 2. محرك الدمج الآمن (Safe Loading)
@st.cache_data
def load_and_merge_dbs():
    all_dfs = []
    for f in ["All Broadcasting.xlsx", "Data.xlsx"]:
        if os.path.exists(f):
            temp_df = pd.read_excel(f)
            temp_df.columns = temp_df.columns.str.strip()
            # توحيد نوع البيانات في الأعمدة الحساسة
            if 'Adm' in temp_df.columns: temp_df['Adm'] = temp_df['Adm'].astype(str).str.upper()
            if 'Notice Type' in temp_df.columns: temp_df['Notice Type'] = temp_df['Notice Type'].astype(str).str.upper()
            all_dfs.append(temp_df)
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        return combined.drop_duplicates(subset=['BR Id']) if 'BR Id' in combined.columns else combined
    return None

db = load_and_merge_dbs()

# 3. المحرك الجراحي (المنع البات للتخريف)
st.title("📡 Seshat AI – Precision Engineering v12.5")
user_q = st.text_input("Engineering Query (Fixed Logic):")

def smart_engine(q, data):
    q_clean = q.lower()
    conf = 0; det_adm = None; det_svc = None; specific_notice = None
    
    # أ) لقط الكود الصريح أولاً (Absolute Priority)
    all_codes = [n for sub in MASTER_KNOWLEDGE.values() for n in sub]
    words = q.upper().replace('?', '').split()
    for w in words:
        if w in all_codes:
            specific_notice = w
            conf = 100
            break

    # ب) لقط الإدارة بدقة أعلى
    all_syns = {k: v for k, v in SYNONYMS.items() if k not in ['TV_KEY', 'ALLOT_KEY', 'ASSIG_KEY']}
    for word in q_clean.split():
        for code, keywords in all_syns.items():
            if any(k == word for k in keywords) or (word in ['egypt', 'turkey', 'saudi', 'israel']):
                det_adm = code
                conf = max(conf, 50)
                break
        if det_adm: break

    # ج) لقط الخدمة لو مفيش كود صريح
    if not specific_notice:
        if any(k in q_clean for k in SYNONYMS['TV_KEY']): det_svc = 'TV'
        elif 'fm' in q_clean or 'radio' in q_clean: det_svc = 'FM'
        elif 'dab' in q_clean: det_svc = 'DAB'
        if det_svc: conf = max(conf, 50)

    # د) تنفيذ الفلترة الصارمة
    if det_adm:
        mask = (data['Adm'] == det_adm)
        if specific_notice:
            # لو سألت عن GT1 لتركيا، لازم السطر يكون فيه الاتنين مع بعض
            res = data[mask & (data['Notice Type'] == specific_notice)]
            return res, det_adm, specific_notice, 100
        elif det_svc:
            res = data[mask & (data['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc]))]
            # فلتر التعيين والتخصيص
            if 'allot' in q_clean or 'تعيين' in q_clean:
                res = res[res['Notice Type'].str.contains('2|G2|T2|GA1|GB1', na=False)]
            elif 'assign' in q_clean or 'تخصيص' in q_clean:
                res = res[res['Notice Type'].str.contains('1|G1|T1|T01', na=False)]
            return res, det_adm, det_svc, conf
            
    return None, None, None, 0

if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.write(f"**Confidence:** {confidence}%")
    
    if res is not None and not res.empty:
        st.metric(f"Found for {adm}", len(res))
        # Voice (English Only)
        try:
            tts = gTTS(text=f"Total records found is {len(res)}", lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        if 'Location' in res.columns:
            coords = res['Location'].apply(dms_to_decimal)
            res['lat'], res['lon'] = zip(*coords)
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty: st.map(map_df[['lat', 'lon']])

        st.dataframe(res)
    elif user_q:
        st.error("No exact match found. Please check Country and Notice Type.")
