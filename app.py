import streamlit as st
import pandas as pd
import os
import io

# 1. القاموس المرجعي الشامل (الدستور)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

# 2. قاموس المرادفات (Synonyms Map) - عشان يفهم ISR و مصر و stations
SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص']
}

st.set_page_config(page_title="Seshat AI - Smart Ref", layout="wide")
st.title("📡 Seshat AI – Engineering Reference v11.0")

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

# 3. محرك البحث الذكي (Pattern Matching)
user_q = st.text_input("Ask about Countries, Codes, or Notice Categories:")

def smart_analyze(q, data):
    q = q.lower()
    conf = 0
    detected_adm = None
    detected_svc = None
    
    # تحسين لقط الـ Administration (يدعم ISR و Israel و اسرائيل)
    for code, keywords in SYNONYMS.items():
        if any(k in q for k in keywords):
            detected_adm = code
            conf += 50
            break
            
    # تحسين لقط الـ Service (يدعم العربي والإنجليزي)
    for svc, types in MASTER_KNOWLEDGE.items():
        # لو السؤال فيه اسم الخدمة أو اسم الفئة
        if svc.lower().replace("_", " ") in q or (svc == 'TV' and 'تلفزيون' in q) or (svc == 'SOUND' and 'صوت' in q):
            detected_svc = svc
            conf += 50
            break

    if detected_adm and detected_svc:
        mask = (data['Adm'] == detected_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[detected_svc]))
        return data[mask], detected_adm, detected_svc, conf
    return None, None, None, 0

# 4. العرض والتحقق
if db is not None and user_q:
    res, adm_res, svc_res, c_level = smart_analyze(user_q, db)
    st.progress(c_level / 100)
    
    if res is not None:
        st.metric(f"Results for {adm_res} ({svc_res})", len(res))
        st.bar_chart(res['Notice Type'].value_counts())
        
        # ميزة إضافية: الـ Audio مبرمج يشتغل لو المكتبة موجودة بس
        try:
            from gtts import gTTS
            txt = f"Total {svc_res} for {adm_res} is {len(res)}."
            tts = gTTS(text=txt, lang='en')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io)
        except: pass
        
        with st.expander("🔍 Validation Data"):
            st.dataframe(res)
    else:
        st.warning("⚠️ Try using keywords like 'ISR TV' or 'مصر Sound'.")
