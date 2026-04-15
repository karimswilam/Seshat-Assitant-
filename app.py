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

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'israil'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'تعيين', 'تعيينات'],
    'ASSIG_KEY': ['assignment', 'تخصيص', 'تخصيصات']
}

st.set_page_config(page_title="Seshat AI - Generic Edition", layout="wide")
st.title("📡 Seshat AI – Professional Engineering Assistant")

# 2. Coordinates Parser (ثابت)
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

# 3. محرك تحميل البيانات المرن (Generic Loader)
@st.cache_data
def load_db(uploaded=None):
    # أولاً: لو فيه ملف مرفوع يدوياً
    if uploaded:
        return pd.read_excel(uploaded)
    
    # ثانياً: البحث عن أي ملف إكسيل في الفولدر (Generic Approach)
    files = [f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.xls')]
    
    if files:
        # لو فيه ملفات، اختار أول واحد متاح (أو Data.xlsx لو موجود)
        target = "Data.xlsx" if "Data.xlsx" in files else files[0]
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

up_file = st.file_uploader("Upload Database", type=["xlsx"])
db = load_db(up_file)

# 4. محرك البحث الذكي (Core Logic v12.0)
user_q = st.text_input("Ask Seshat (Generic Mode):")

def smart_engine(q, data):
    q = q.lower()
    conf = 0; detected_adm = None; detected_svc = None
    
    all_keys = [k for sublist in SYNONYMS.values() for k in sublist]
    words = q.split()
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.7)
        if match:
            for code, keywords in SYNONYMS.items():
                if match[0] in keywords:
                    detected_adm = code; conf += 50; break
            if detected_adm: break

    for svc in MASTER_KNOWLEDGE.keys():
        if svc.lower().replace("_", " ") in q or (svc == 'FM' and 'راديو' in q):
            detected_svc = svc; conf += 50; break

    if detected_adm and detected_svc:
        mask = (data['Adm'].astype(str).str.contains(detected_adm)) & \
               (data['Notice Type'].isin(MASTER_KNOWLEDGE[detected_svc]))
        res = data[mask]
        
        if any(k in q for k in SYNONYMS['ALLOT_KEY']):
            res = res[res['Notice Type'].str.contains('2|G2|T2', na=False)]
        elif any(k in q for k in SYNONYMS['ASSIG_KEY']):
            res = res[res['Notice Type'].str.contains('1|G1|T1', na=False)]
            
        return res, detected_adm, detected_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm, svc, confidence = smart_engine(user_q, db)
    st.progress(confidence / 100)
    st.write(f"**Confidence Indicator:** {confidence}%")

    if res is not None:
        count = len(res)
        st.metric(f"Total {svc} for {adm}", count)
        
        voice_msg = f"Found {count} {svc} records for {adm}."
        try:
            tts = gTTS(text=voice_msg, lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        st.bar_chart(res['Notice Type'].value_counts())

        if 'Location' in res.columns:
            coords = res['Location'].apply(dms_to_decimal)
            res['lat'] = [c[0] for c in coords]; res['lon'] = [c[1] for c in coords]
            map_df = res.dropna(subset=['lat', 'lon'])
            if not map_df.empty:
                st.subheader("🗺️ Geographic Distribution")
                st.map(map_df[['lat', 'lon']])

        with st.expander("🔍 Engineering Data"):
            st.dataframe(res)
