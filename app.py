# ======================================================
# 📡 Seshat AI – Dynamic Engineering Analytics v4.0
# ======================================================
import streamlit as st
import pandas as pd
import os
import time
import re
from gtts import gTTS
import io

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Precision Engine", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Professional Engineering Analytics")

# 2. Dynamic Domain Knowledge (Base Mapping)
# دي لسه ثابتة لأنها منطق هندسي (ITU Standards)
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

# الأسماء الشائعة عشان لو اليوزر كتب اسم البلد مش الكود
COMMON_NAME_MAP = {
    'egypt': 'EGY', 'masr': 'EGY',
    'saudi': 'ARS', 'ksa': 'ARS',
    'israel': 'ISR',
    'turkey': 'TUR', 'turkiye': 'TUR',
    'jordan': 'JOR', 'emirates': 'UAE'
}

STOP_WORDS = ['how', 'the', 'for', 'any', 'get', 'all', 'and', 'was', 'has', 'now', 'records']

# 3. Voice Engine
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp.getvalue(), format="audio/mp3", autoplay=True)
    except:
        pass

# 4. Data Engine (Optimized for Large DB)
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    try:
        df = pd.read_excel(target)
        df.columns = [str(c).strip() for c in df.columns]
        # Clean data for dynamic matching
        if 'Adm' in df.columns:
            df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
        if 'Notice Type' in df.columns:
            df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Excel Database", type=["xlsx"])
df = load_data(uploaded_file)

# 5. The Dynamic Hybrid Engine (Future-Proof)
def process_query_dynamic(query, df):
    q = query.lower()
    
    # أ. استخراج البلاد المتاحة في الداتا حالياً (Dynamic Lookup)
    if 'Adm' not in df.columns:
        return None, "Error: 'Adm' column not found in database.", 0.0
    
    available_countries = df['Adm'].unique().tolist()
    
    # ب. التعرف على الدولة (Multi-Step Detection)
    detected_country = None
    
    # 1. البحث عن الاسم الشائع
    for name, code in COMMON_NAME_MAP.items():
        if name in q:
            detected_country = code
            break
            
    # 2. لو ملقاش، يدور على أي كود 3 حروف موجود فعلاً في الداتا
    if not detected_country:
        potential_codes = re.findall(r'\b[a-z]{3}\b', q)
        for code in potential_codes:
            if code.upper() in available_countries and code not in STOP_WORDS:
                detected_country = code.upper()
                break

    # ج. التعرف على الخدمة (Service Detection)
    service = next((s for s in SERVICE_KNOWLEDGE if s.lower() in q), None)

    # د. منطق التحقق (The Logic Gate)
    if not detected_country:
        return None, "🔍 Country not detected or not in database. Try using the 3-letter code (e.g. EGY, TUR).", 0.0
    
    if not service:
        return None, "📡 Service type (DAB, TV, FM) not detected in your query.", 0.0

    # هـ. تصفية البيانات (Precision Filtering)
    fdf = df[(df['Adm'] == detected_country) & (df['Notice Type'].isin(SERVICE_KNOWLEDGE[service]))]
    
    is_count = any(w in q for w in ['count', 'how many', 'kam', 'عدد', 'total', 'records'])
    
    return (fdf, is_count, detected_country, service), None, 1.0

# 6. UI Loop
if df.empty:
    st.info("👋 Welcome! Please upload your Excel database to start the engineering analysis.")
else:
    user_query = st.text_input("💬 Ask about your data (e.g., 'How many TV for TUR' or 'show ISR DAB'):")

    if user_query:
        start = time.time()
        result, error, conf = process_query_dynamic(user_query, df)
        elapsed = time.time() - start

        if error:
            st.warning(error)
            speak(error)
        else:
            fdf, is_count, country, service = result
            
            st.subheader("📊 Analysis Results")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Territory", country)
            with col2: st.metric("Service", service)
            with col3: st.metric("Records Found", len(fdf))

            if is_count:
                st.success(f"Total {service} records for {country}: {len(fdf)}")
                speak(f"Found {len(fdf)} records for {service} in {country}.")
            else:
                st.dataframe(fdf, use_container_width=True)
                speak(f"Showing the database records for {country}.")
            
            # Visualization
            if not fdf.empty:
                st.bar_chart(fdf['Notice Type'].value_counts())
            
            st.caption(f"Engine: Dynamic Lookup | Processing Time: {elapsed:.4f}s")

# Footer
st.divider()
st.caption("Seshat AI v4.0 - Dynamic Database Integration Active.")
