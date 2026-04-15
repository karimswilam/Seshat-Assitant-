# ======================================================
# 📡 Seshat AI v8.0 – The Ultimate Hybrid Analytics
# ======================================================
import streamlit as st
import pandas as pd
import os
import re
from gtts import gTTS
import base64

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Professional Engineering", layout="wide")
st.title("📡 Seshat AI – Engineering Analytics Engine")

# 2. Hybrid Data Loader (Correct Path for Data.xlsx)
@st.cache_data
def load_data(uploaded=None):
    if uploaded:
        return pd.read_excel(uploaded)
    # استخدام المسار الصحيح للملف الثابت
    if os.path.exists("Data.xlsx"):
        return pd.read_excel("Data.xlsx")
    return None

# مساحة الرفع (موجودة دايماً ومش هتختفي)
st.subheader("📂 1. Data Integration")
uploaded_file = st.file_uploader("Upload New Data (Optional)", type=["xlsx"], key="hybrid_uploader")
df = load_data(uploaded_file)

if df is not None:
    st.sidebar.success(f"✅ Database Active: {len(df)} records")
    # تنظيف البيانات لضمان القراءة الصحيحة
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
else:
    st.sidebar.error("⚠️ No database found. Please check Data.xlsx on GitHub.")

st.markdown("---")

# 3. Chat & Logic Space
st.subheader("💬 2. Engineering Query")
user_query = st.text_input("Ask about comparisons, shares, or exclusions:", 
                          placeholder="e.g., DAB in Egypt compared to Saudi")

# 4. Operations Engine (The Complex Logic)
def process_logic(query, data):
    q = query.lower()
    COUNTRY_MAP = {'EGY': ['egypt', 'مصر', 'eg'], 'ARS': ['saudi', 'so3deya', 'السعودية', 'ars'], 'TUR': ['turkey', 'تركيا']}
    TECH_MAP = {'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], 'TV': ['T02', 'G02', 'GT1', 'GT2']}
    
    parts = re.split(r'and|compared to|vs|مقارنة| و ', q)
    results = []
    
    for part in parts:
        country = next((c for c, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in TECH_MAP.items() if s.lower() in part), 'DAB')
        
        if country:
            mask = (data['Adm'] == country) & (data['Notice Type'].isin(TECH_MAP[service]))
            # منطق الاستثناء (Except)
            if 'except' in q or 'ما عدا' in q:
                match = re.search(r'(except|ما عدا)\s+([a-z0-9]+)', q)
                if match: mask &= (data['Notice Type'] != match.group(2).upper())
            
            count = len(data[mask])
            results.append({'country': country, 'service': service, 'count': count})
    return results

# 5. Output Display & Voice Logic
if df is not None and user_query:
    ans = process_logic(user_query, df)
    if ans:
        st.subheader("📝 Analysis Result")
        cols = st.columns(len(ans))
        chart_data = {}
        text_output = ""

        for i, r in enumerate(ans):
            cols[i].metric(f"{r['service']} | {r['country']}", r['count'])
            chart_data[f"{r['country']} ({r['service']})"] = r['count']
            text_output += f"Number of {r['service']} stations in {r['country']} is {r['count']}. "

        # Dashboards (الـ Bar Chart رجع)
        st.bar_chart(pd.Series(chart_data))

        # Voice Output (بدون مكتبات بتعمل Crash)
        tts = gTTS(text=text_output, lang='en')
        audio_file = io.BytesIO()
        tts.write_to_fp(audio_file)
        st.audio(audio_file, format='audio/mp3')
    else:
        st.warning("⚠️ Could not detect country or service. Use codes like EGY, ARS, TUR.")
