# ======================================================
# 📡 Seshat AI v6.7 – Lightning Fast Logic (Stable)
# ======================================================
import streamlit as st
import pandas as pd
import os
import re

# 1. منع أي مكتبات صوتية مسببة للأعطال
st.set_page_config(page_title="Seshat AI – Stable", layout="wide")

# 2. تحميل البيانات (Hybrid Mode) من Data.xlsx
@st.cache_data
def get_data():
    file_path = "Data.xlsx" # الاسم اللي اتفقنا عليه
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return None

db_df = get_data()

# 3. واجهة المستخدم البسيطة
st.title("📡 Seshat AI – Engineering Assistant")
uploaded_file = st.file_uploader("Upload Excel (Optional)", type=["xlsx"])

# اختيار مصدر البيانات
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.sidebar.success("Using: Uploaded File")
elif db_df is not None:
    df = db_df
    st.sidebar.info("Using: Internal Data.xlsx")
else:
    df = None
    st.sidebar.error("No Data Found! Check Data.xlsx on GitHub")

# 4. محرك المعالجة السريع (Logic Engine)
user_query = st.text_input("Engineering Query:", key="query_input")

if df is not None and user_query:
    # تنظيف سريع للداتا
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
    
    # القواميس (DAB, TV, FM)
    TECH_MAP = {
        'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
        'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
        'FM': ['T01']
    }
    COUNTRY_MAP = {'EGY': ['egypt', 'مصر'], 'ARS': ['saudi', 'ksa', 'السعودية'], 'TUR': ['turkey', 'تركيا']}

    # معالجة السؤال المركب (Compared to / And)
    parts = re.split(r'and|compared to|vs|و', user_query.lower())
    
    st.subheader("📝 Analysis Results")
    cols = st.columns(len(parts))
    
    for i, part in enumerate(parts):
        country = next((code for code, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in TECH_MAP.items() if s.lower() in part), 'DAB') # افتراضي DAB لو محددش
        
        if country:
            count = len(df[(df['Adm'] == country) & (df['Notice Type'].isin(TECH_MAP[service]))])
            with cols[i]:
                st.metric(f"{service} in {country}", count)
        else:
            st.warning(f"Could not identify country in: '{part}'")
