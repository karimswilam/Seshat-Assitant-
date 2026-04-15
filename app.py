# ======================================================
# 📡 SESHAT AI – THE COMPLETE ENGINEERING REFERENCE (v9.2)
# ======================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import io
from gtts import gTTS

# 1. القاموس الهندسي الشامل والنهائي (بناءً على جدولك الرسمي)
# تم إدراج كل الـ Notice Types لضمان عدم حدوث أي Skip
ENGINEERING_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], # تفريع من Sound للسهولة
    'FM': ['T01', 'T03', 'T04'], # تفريع من Sound للسهولة
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'DIGITAL_SHARED': ['GA1', 'GB1'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

st.set_page_config(page_title="Seshat Complete Reference", layout="wide")
st.title("📡 Seshat AI – Complete Engineering Reference")

# 2. Hybrid Data Loading
@st.cache_data
def load_db(uploaded=None):
    if uploaded:
        return pd.read_excel(uploaded)
    if os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
        df.columns = df.columns.str.strip()
        return df
    return None

st.subheader("📂 1. Data Integration")
uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])
active_df = load_db(uploaded_file)

if active_df is not None:
    st.sidebar.success(f"✅ Database Ready: {len(active_df)} records")
    # توحيد التنسيق لضمان دقة البحث
    active_df['Adm'] = active_df['Adm'].astype(str).str.strip().str.upper()
    active_df['Notice Type'] = active_df['Notice Type'].astype(str).str.strip().str.upper()

# 3. Operations Engine (Enhanced to cover all categories)
st.subheader("💬 2. Engineering Query Space")
query = st.text_input("Ask: (e.g., How many Administrative notices in Egypt?)", key="v92_q")

def get_comprehensive_analysis(q, data):
    q = q.lower().replace("_", " ") # لضمان فهم Digital_Shared كـ Digital Shared
    conf = 0
    COUNTRY_MAP = {'EGY': ['egypt', 'masr', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'], 'TUR': ['turkey', 'تركيا'], 'ISR': ['israel', 'اسرائيل']}
    
    adm = next((code for code, keys in COUNTRY_MAP.items() if any(k in q for k in keys)), None)
    if adm: conf += 50
    
    # البحث عن الفئة المطلوبة من القاموس الجديد
    svc = next((s for s in ENGINEERING_KNOWLEDGE.keys() if s.lower().replace("_", " ") in q), None)
    if svc: conf += 50

    if adm and svc:
        allowed_types = ENGINEERING_KNOWLEDGE[svc]
        mask = (data['Adm'] == adm) & (data['Notice Type'].isin(allowed_types))
        return data[mask], adm, svc, conf
    return None, None, None, 0

# 4. Results & Validation Dashboards
if active_df is not None and query:
    res_df, adm_code, svc_name, confidence_level = get_comprehensive_analysis(query, active_df)
    
    st.progress(confidence_level / 100)
    st.write(f"**Engine Confidence:** {confidence_level}%")

    if res_df is not None:
        count = len(res_df)
        
        # Audio Response
        text_resp = f"The total records for {svc_name} in {adm_code} is {count}."
        tts = gTTS(text=text_resp, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp)
        
        # Visualization & Validation
        col1, col2 = st.columns([1, 2])
        col1.metric(f"Total {svc_name} for {adm_code}", count)
        
        # رسم بياني يوضح توزيع الـ Notice Types داخل الفئة المختارة للتأكد من الشمولية
        type_breakdown = res_df['Notice Type'].value_counts().reset_index()
        fig = px.bar(type_breakdown, x='Notice Type', y='count', 
                     title=f"Detailed Breakdown of {svc_name} (Validation Mode)")
        col2.plotly_chart(fig, use_container_width=True)

        if 'Lat' in res_df.columns and 'Long' in res_df.columns:
            st.subheader("🗺️ Geographic Distribution")
            st.map(res_df.dropna(subset=['Lat', 'Long'])[['Lat', 'Long']])
        
        with st.expander("🔍 View Raw Engineering Data"):
            st.dataframe(res_df)
    else:
        st.warning("⚠️ Category or Country not detected. Please use names like 'Administrative', 'Digital Shared', or 'TV'.")
