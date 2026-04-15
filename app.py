import streamlit as st
import pandas as pd
import os
import io
from gtts import gTTS

# 1. الدستور الهندسي المحدث (الفصل بين التماثلي والرقمي)
#
MASTER_KNOWLEDGE = {
    'FM': ['T01', 'T03', 'T04'], # Analogue Sound
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], # Digital Sound
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'],
    'ARS': ['saudi', 'ars', 'السعودية'],
    'ISR': ['israel', 'isr', 'اسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'FM_KEY': ['fm', 'اف ام', 'analogue sound', 'راديو'],
    'DAB_KEY': ['dab', 'digital sound', 'دي اي بي'],
    'ALLOT_KEY': ['allotment', 'تخصيص'],
    'ASSIG_KEY': ['assignment', 'تنسيب']
}

st.set_page_config(page_title="Seshat Voice Assistant", layout="wide")
st.title("📡 Seshat AI – Engineering Voice Assistant")

@st.cache_data
def load_db(uploaded=None):
    if uploaded: return pd.read_excel(uploaded)
    if os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
        df.columns = df.columns.str.strip()
        return df
    return None

up_file = st.file_uploader("Upload Database", type=["xlsx"])
db = load_db(up_file)

if db is not None:
    db['Adm'] = db['Adm'].astype(str).str.strip().str.upper()
    db['Notice Type'] = db['Notice Type'].astype(str).str.strip().str.upper()
    # تحويل التردد لرقمي للفلترة لاحقاً
    if 'Freq' in db.columns:
        db['Freq'] = pd.to_numeric(db['Freq'], errors='coerce')

user_q = st.text_input("Engineering Query:")

def smart_analyze(q, data):
    q = q.lower()
    conf = 0
    detected_adm = None
    detected_svc = None
    sub_filter = None
    
    # 1. لقط الإدارة
    for code, keywords in SYNONYMS.items():
        if code in ['EGY', 'ARS', 'ISR', 'TUR'] and any(k in q for k in keywords):
            detected_adm = code
            conf += 50
            break
            
    # 2. لقط الخدمة (تفرقة FM عن DAB عن TV)
    if any(k in q for k in SYNONYMS['FM_KEY']):
        detected_svc = 'FM'
        conf += 50
    elif any(k in q for k in SYNONYMS['DAB_KEY']):
        detected_svc = 'DAB'
        conf += 50
    elif 'tv' in q or 'television' in q or 'تلفزيون' in q:
        detected_svc = 'TV'
        conf += 50

    if detected_adm and detected_svc:
        # فلترة بناءً على الـ Notice Type المخصص في MASTER_KNOWLEDGE
        mask = (data['Adm'] == detected_adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[detected_svc]))
        final_res = data[mask]
        
        # فلترة إضافية للـ FM بناءً على التردد (87.5 - 108 MHz) لضمان الدقة
        if detected_svc == 'FM' and 'Freq' in final_res.columns:
            final_res = final_res[(final_res['Freq'] >= 87.5) & (final_res['Freq'] <= 108)]
            
        # فحص الـ Allotments والـ Assignments
        if any(k in q for k in SYNONYMS['ALLOT_KEY']):
            final_res = final_res[final_res['Notice Type'].str.contains('2|G2|T2', na=False)]
        elif any(k in q for k in SYNONYMS['ASSIG_KEY']):
            final_res = final_res[final_res['Notice Type'].str.contains('1|G1|T1', na=False)]
            
        return final_res, detected_adm, detected_svc, conf
    return None, None, None, 0

if db is not None and user_q:
    res, adm_res, svc_res, c_level = smart_analyze(user_q, db)
    
    if res is not None:
        count = len(res)
        st.metric(f"Total {svc_res} for {adm_res}", count)
        
        # --- Voice Assistant Output ---
        voice_text = f"The total number of {svc_res} stations in {adm_res} is {count}."
        if any(k in user_q for k in SYNONYMS['ALLOT_KEY']): voice_text += " Specifically for allotments."
        
        try:
            tts = gTTS(text=voice_text, lang='en')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io, format="audio/mp3")
        except Exception as e:
            st.error("Voice output error. Check connection.")

        st.bar_chart(res['Notice Type'].value_counts())
        with st.expander("🔍 View Technical Records"):
            st.dataframe(res)
