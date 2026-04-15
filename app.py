import streamlit as st
import pandas as pd
import os
import re
import io

# 1. الدستور الهندسي (بناءً على جدولك الرسمي 100%)
#
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

st.set_page_config(page_title="Seshat AI - Core Reference", layout="wide")
st.title("📡 Seshat AI – Engineering Reference Model")

# 2. تحميل البيانات (Hybrid Mode)
@st.cache_data
def load_engine_data(uploaded=None):
    if uploaded:
        return pd.read_excel(uploaded)
    if os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
        df.columns = df.columns.str.strip()
        return df
    return None

st.subheader("📂 1. Data Integration")
up_file = st.file_uploader("Upload Excel Database", type=["xlsx"])
db = load_engine_data(up_file)

if db is not None:
    st.sidebar.success(f"✅ Database Active: {len(db)} records")
    # توحيد التنسيق الهندسي
    db['Adm'] = db['Adm'].astype(str).str.strip().str.upper()
    db['Notice Type'] = db['Notice Type'].astype(str).str.strip().str.upper()

# 3. محرك البحث والـ Confidence Indicator
st.subheader("💬 2. Engineering Query Space")
user_q = st.text_input("Ask: (e.g., How many TV in Egypt?)")

def analyze_query(q, data):
    q = q.lower().replace("_", " ")
    conf = 0
    # خريطة الإدارات (Administrations)
    ADM_MAP = {'EGY': ['egypt', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'], 'TUR': ['turkey', 'تركيا'], 'ISR': ['israel', 'اسرائيل']}
    
    adm = next((c for c, keys in ADM_MAP.items() if any(k in q for k in keys)), None)
    if adm: conf += 50
    
    svc = next((s for s in MASTER_KNOWLEDGE.keys() if s.lower().replace("_", " ") in q), None)
    if svc: conf += 50

    if adm and svc:
        mask = (data['Adm'] == adm) & (data['Notice Type'].isin(MASTER_KNOWLEDGE[svc]))
        return data[mask], adm, svc, conf
    return None, None, None, 0

# 4. المخرجات (Validation & Visualization)
if db is not None and user_q:
    res, adm_res, svc_res, c_level = analyze_query(user_q, db)
    
    st.progress(c_level / 100)
    st.write(f"**Confidence Indicator:** {c_level}%")

    if res is not None:
        count = len(res)
        st.metric(f"Total {svc_res} for {adm_res}", count)

        # Dashboard للـ Validation (Bar Chart أضمن من Plotly حالياً)
        st.subheader("📊 Notice Type Breakdown")
        type_dist = res['Notice Type'].value_counts()
        st.bar_chart(type_dist)

        # Voice Output (Safe Implementation)
        try:
            from gtts import gTTS
            tts = gTTS(text=f"Found {count} records for {svc_res} in {adm_res}", lang='en')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io)
        except:
            st.info("Voice engine loading...")

        # Map Visualization
        if 'Lat' in res.columns and 'Long' in res.columns:
            st.subheader("🗺️ Geographic Distribution")
            st.map(res.dropna(subset=['Lat', 'Long'])[['Lat', 'Long']])

        with st.expander("🔍 View Raw Records (Validation)"):
            st.dataframe(res)
    else:
        st.info("Please mention a Country and a Service category from the dictionary.")
