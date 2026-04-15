# ======================================================
# 📡 Seshat AI v6.4 – Clean Hybrid Engine (Stable)
# ======================================================
import streamlit as st
import pandas as pd
import re

# 1. الاعدادات الأساسية وتجنب الـ Errors الصوتية
st.set_page_config(page_title="Seshat AI – Stable Mode", layout="wide")

# 2. تحميل الداتا الثابتة (Internal Database)
@st.cache_data
def load_internal_data():
    try:
        # تأكد إن الملف ده موجود في نفس فولدر الكود على GitHub
        return pd.read_excel("ITU_Data.xlsx") 
    except:
        return None

internal_df = load_internal_data()

# 3. واجهة المستخدم (UI)
st.title("📡 Seshat AI – Engineering Voice Assistant")

# مساحة الرفع (اختيارية لدعم الـ Hybrid)
uploaded_file = st.file_uploader("1. Upload New Data (Optional)", type=["xlsx"])

# مساحة الدردشة (موجودة دايماً)
user_query = st.text_input("2. Engineering Query:", placeholder="How many DAB in Egypt?")

# 4. اختيار مصدر البيانات
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.info("Using Uploaded File")
elif internal_df is not None:
    df = internal_df
    st.info("Using Internal Database")
else:
    df = None
    st.error("No Data Source Found! Please upload a file or check ITU_Data.xlsx")

# 5. محرك البحث الذكي (Logic)
COUNTRY_MAP = {'EGY': ['egypt', 'مصر'], 'TUR': ['turkey', 'تركيا'], 'ISR': ['israel', 'اسرائيل'], 'ARS': ['saudi', 'السعودية']}
TECH_CODES = {'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], 'TV': ['T02', 'G02', 'GT1', 'GT2']}

if df is not None and user_query:
    # تنظيف الداتا
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
    
    # فك السؤال (Simple Logic for Parallel Queries)
    q = user_query.lower()
    results = []
    
    # تقسيم السؤال لو فيه مقارنة
    parts = re.split('and|compared to|vs|و', q)
    for part in parts:
        country = next((code for code, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = 'DAB' if 'dab' in part else ('TV' if 'tv' in part or 'مرئي' in part else None)
        
        if country and service:
            count = len(df[(df['Adm'] == country) & (df['Notice Type'].isin(TECH_CODES[service]))])
            results.append(f"**{service}** in **{country}**: {count} records")

    # عرض النتائج فوراً
    if results:
        st.subheader("📝 Analysis Result:")
        for r in results:
            st.success(r)
    else:
        st.warning("I understood your query, but I couldn't find matching criteria.")
