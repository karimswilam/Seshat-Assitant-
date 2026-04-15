# ======================================================
# 📡 Seshat AI v8.1 – Final Stable Hybrid Analytics
# ======================================================
import streamlit as st
import pandas as pd
import os
import re
import io  # السطر ده هو اللي كان ناقص وعامل الـ NameError
from gtts import gTTS

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Engineering", layout="wide")
st.title("📡 Seshat AI – Engineering Analytics Engine")

# 2. Hybrid Data Loader
@st.cache_data
def load_data(uploaded=None):
    if uploaded:
        return pd.read_excel(uploaded)
    if os.path.exists("Data.xlsx"):
        return pd.read_excel("Data.xlsx")
    return None

# واجهة الرفع ثابتة وموجودة دائماً
st.subheader("📂 1. Data Integration")
uploaded_file = st.file_uploader("Upload New Data (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

if df is not None:
    st.sidebar.success(f"✅ Active Database: {len(df)} records")
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
else:
    st.sidebar.error("⚠️ Please ensure 'Data.xlsx' is on GitHub.")

st.markdown("---")

# 3. Operations Engine
def process_advanced_logic(query, data):
    q = query.lower()
    # دعم كلمات بحث أكثر (Recordings, Stations, etc.)
    COUNTRY_MAP = {'EGY': ['egypt', 'masr', 'مصر'], 'ARS': ['saudi', 'السعودية', 'ars'], 'TUR': ['turkey', 'turkiye', 'تركيا']}
    TECH_MAP = {'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], 'TV': ['T02', 'G02', 'GT1', 'GT2']}
    
    parts = re.split(r'and|compared to|vs|مقارنة| و ', q)
    results = []
    
    for part in parts:
        country = next((c for c, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in TECH_MAP.items() if s.lower() in part or 'recording' in part), 'DAB')
        
        if country:
            mask = (data['Adm'] == country) & (data['Notice Type'].isin(TECH_MAP[service]))
            # منطق الاستثناء (Except)
            if 'except' in q or 'ما عدا' in q:
                match = re.search(r'(except|ما عدا)\s+([a-z0-9]+)', q)
                if match: mask &= (data['Notice Type'] != match.group(2).upper())
            
            results.append({'country': country, 'service': service, 'count': len(data[mask])})
    return results

# 4. Chat & Results Space
st.subheader("💬 2. Engineering Query")
user_query = st.text_input("Ask: (e.g., How many DAB for Egypt compared to Saudi?)")

if df is not None and user_query:
    ans = process_advanced_logic(user_query, df)
    if ans:
        st.subheader("📝 Analysis Result")
        m_cols = st.columns(len(ans))
        chart_data = {}
        speech_text = ""

        for i, r in enumerate(ans):
            m_cols[i].metric(f"{r['service']} | {r['country']}", r['count'])
            chart_data[f"{r['country']} ({r['service']})"] = r['count']
            speech_text += f"The count for {r['service']} in {r['country']} is {r['count']}. "

        # Bar Chart Visualization
        st.bar_chart(pd.Series(chart_data))

        # Level 3: Market Share if requested
        if 'نسبة' in user_query or 'percent' in user_query:
            total = sum(chart_data.values())
            for k, v in chart_data.items():
                st.write(f"📈 **{k}** Share: **{(v/total)*100:.2f}%**")

        # Voice Output (The Fixed Part)
        try:
            tts = gTTS(text=speech_text, lang='en')
            audio_buffer = io.BytesIO() # تم حل الـ NameError هنا
            tts.write_to_fp(audio_buffer)
            st.audio(audio_buffer, format='audio/mp3')
        except Exception as e:
            st.warning("Voice output currently unavailable.")
    else:
        st.info("I'm ready! Just mention a country (EGY, ARS, TUR) and a service (DAB, TV).")
