# ======================================================
# 📡 Seshat AI – Engineering Analytics (Final Hybrid)
# ======================================================
import streamlit as st
import pandas as pd
import os
import time
import re
from gtts import gTTS
import io

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Ultra Precision", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Professional Engineering Analytics")

# 2. Engineering Domain Knowledge
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

COUNTRIES = {
    'EGY': ['egy', 'masr', 'مصر', 'egypt'],
    'ARS': ['ksa', 'saudi', 'سعودية', 'ars']
}

# كلمات الربط اللي Regex بتاعك كان بيعتبرها "كود دولة" غلط
STOP_WORDS = ['how', 'the', 'for', 'any', 'get', 'all', 'and', 'was', 'has', 'now']

# 3. Cloud-Friendly Voice Engine
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp.getvalue(), format="audio/mp3", autoplay=True)
    except:
        pass

# 4. Data Engine (Optimized)
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    try:
        df = pd.read_excel(target)
        df.columns = [str(c).strip() for c in df.columns]
        df['Adm'] = df['Adm'].astype(str).str.strip()
        df['Notice Type'] = df['Notice Type'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Excel (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

# 5. Hybrid Query Engine (The Fix for Turkey/Israel/How)
def process_query_hybrid(query, df):
    q = query.lower()
    
    # أ. الـ Regex Guard المطور: بيمسك الأكواد الغريبة بس بيعدي الكلمات العادية
    potential_codes = re.findall(r'\b[a-z]{3}\b', q)
    for code in potential_codes:
        code_upper = code.upper()
        if code not in STOP_WORDS and code_upper not in COUNTRIES and code_upper not in SERVICE_KNOWLEDGE:
            return None, f"⚠️ Security Alert: Entity '{code_upper}' is not in the database scope.", 1.0

    # ب. استخراج الكيانات (Explicit Matching)
    country = next((c for c, k in COUNTRIES.items() if any(key in q for key in k)), None)
    service = next((s for s in SERVICE_KNOWLEDGE if s.lower() in q or 
                    any(word in q for word in ['digital', 'television', 'radio'] if s in ['DAB', 'TV', 'FM'])), None)

    # ج. Logic Gate: لو ذكر مكان (Israel/Turkey) بس مش في الـ Whitelist
    # أو لو سأل سؤال عايم من غير تحديد صريح
    if not country and any(prep in q for prep in ['for ', 'in ', 'at ']):
        return None, "🚫 Unsupported Location: I cannot process data for this territory yet.", 0.0

    if not country or not service:
        return None, "🔍 Specification Required: Please mention both Country (EGY/KSA) and Service Type.", 0.0

    # د. تصفية البيانات (Precision Filtering)
    fdf = df[(df['Adm'] == country) & (df['Notice Type'].isin(SERVICE_KNOWLEDGE[service]))]
    
    is_count = any(w in q for w in ['count', 'how many', 'kam', 'عدد', 'total', 'records'])
    
    return (fdf, is_count, country, service), None, 1.0

# 6. UI Loop
if df.empty:
    st.warning("⚠️ Waiting for Excel data... (Please upload Data.xlsx)")
else:
    user_query = st.text_input("💬 Engineering Query (e.g., 'How many DAB for KSA'):")

    if user_query:
        start = time.time()
        result, error, conf = process_query_hybrid(user_query, df)
        elapsed = time.time() - start

        st.subheader("🧠 Analysis Results")
        
        if error:
            st.error(error)
            speak(error)
        else:
            fdf, is_count, country, service = result
            
            # عرض البيانات
            col_a, col_b = st.columns(2)
            with col_a: st.write(f"**Detected Territory:** {country}")
            with col_b: st.caption(f"Processing: {elapsed:.4f}s | Confidence: {int(conf*100)}%")
            st.progress(conf)

            if is_count:
                st.metric(f"📊 {service} Records", len(fdf))
                speak(f"Analysis complete. I found {len(fdf)} records for {service} in {country}.")
            else:
                st.dataframe(fdf.head(100), use_container_width=True)
                speak(f"Displaying matching records.")
            
            # الرسم البياني للـ Notice Types
            if not fdf.empty:
                st.bar_chart(fdf['Notice Type'].value_counts())

# Footer
st.divider()
st.caption("Seshat AI v3.0 - Hybrid Precision Engine Enabled.")
