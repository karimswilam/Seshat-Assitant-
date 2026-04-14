import streamlit as st
import pandas as pd
import os
import time
from gtts import gTTS # بديل pyttsx3 للسيرفرات
import io

# ===============================
# CONFIG & KNOWLEDGE
# ===============================
st.set_page_config(page_title="Seshat AI – Voice Engineering", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Engineering Voice Assistant")

SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

# تأكد من تطابق الكود مع ملفك (ARS بدل KSA في الداتا)
COUNTRIES = {
    'ARS': ['ksa', 'saudi', 'سعودية', 'saudia'],
    'EGY': ['egy', 'egypt', 'masr', 'مصر']
}

# ===============================
# AUDIO FUNCTION (Server-Compatible)
# ===============================
def speak_server(text):
    try:
        tts = gTTS(text=text, lang='en') # أو 'ar' حسب الإجابة
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp)
    except:
        pass

# ===============================
# DATA LOADING
# ===============================
@st.cache_data(ttl=600)
def load_data(uploaded, default="Data.xlsx"):
    target = uploaded if uploaded else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    df = pd.read_excel(target)
    df.columns = [str(c).strip() for c in df.columns]
    # تنظيف الأعمدة الأساسية
    for col in ['Adm', 'Notice Type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df

uploaded_file = st.file_uploader("📂 Upload Data.xlsx", type=["xlsx"])
df = load_data(uploaded_file)

# ===============================
# SMART QUERY ENGINE (Anti-Hallucination)
# ===============================
def process_query(query, df):
    fdf = df.copy()
    intent = []
    conf = 0.4
    q = query.lower()

    # 1. فلتر الدولة (Strict Mapping)
    country_found = False
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            fdf = fdf[fdf['Adm'] == code]
            intent.append(f"Country: {code}")
            conf += 0.3
            country_found = True

    # 2. فلتر الخدمة
    service_found = False
    if 'dab' in q:
        fdf = fdf[fdf['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]
        intent.append("Service: DAB")
        conf += 0.3
        service_found = True
    elif 'tv' in q:
        fdf = fdf[fdf['Notice Type'].isin(SERVICE_KNOWLEDGE['TV'])]
        intent.append("Service: TV")
        conf += 0.3
        service_found = True

    is_count = any(w in q for w in ['count', 'kam', 'عدد', 'total', 'how many'])
    
    # لو اليوزر سأل سؤال عام جداً، قلل الثقة
    if not country_found and not service_found:
        conf = 0.2

    return fdf, is_count, intent, min(conf, 1.0)

# ===============================
# UI & EXECUTION
# ===============================
if df.empty:
    st.warning("⚠️ Waiting for Data.xlsx or Upload...")
else:
    user_query = st.text_input("💬 Ask Seshat (e.g., 'KSA DAB count'):")

    if user_query:
        start = time.time()
        result, is_count, intent, conf = process_query(user_query, df)
        elapsed = time.time() - start

        # العرض الذكي
        st.subheader("🧠 Analysis Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Intent", intent[0] if intent else "General")
        c2.metric("Records Found", len(result))
        c3.progress(conf, text=f"Confidence: {int(conf*100)}%")

        if len(result) > 0:
            if is_count:
                msg = f"Found {len(result)} records for your request."
                st.success(msg)
                speak_server(msg)
            else:
                st.dataframe(result.head(50))
                speak_server(f"Displaying {len(result)} records.")
            
            # منع التخريف: الرسم البياني بيطلع من الداتا المفلترة فعلياً
            st.bar_chart(result['Notice Type'].value_counts())
        else:
            st.error("❌ No records found matching these criteria in your file.")

        st.caption(f"Processed in {elapsed:.4f} seconds")
