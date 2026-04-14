import streamlit as st
import pandas as pd
import os

# 1. إعداد الصفحة
st.set_page_config(page_title="Seshat AI - Engineering Assistant", layout="wide")

# 2. القاموس الهندسي
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01']
}

COUNTRIES = {
    'ARS': ['ksa', 'saudi', 'سعودية', 'ars'],
    'EGY': ['egy', 'egypt', 'masr', 'مصر']
}

# 3. دالة تحميل البيانات
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif os.path.exists("Data.xlsx"):
        df = pd.read_excel("Data.xlsx")
    else:
        return pd.DataFrame()
    
    # تنظيف سريع
    df.columns = [str(c).strip() for c in df.columns]
    return df

# 4. واجهة المستخدم
st.title("📡 Seshat AI - Engineering Hub")

uploaded_file = st.file_uploader("Upload Data.xlsx (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

if not df.empty:
    user_query = st.text_input("Ask about your data:")
    
    if user_query:
        q = user_query.lower()
        f_df = df.copy()
        
        # فلتر الدولة
        for code, keys in COUNTRIES.items():
            if any(k in q for k in keys):
                f_df = f_df[f_df['Adm'] == code]
        
        # فلتر الخدمة
        if 'dab' in q:
            f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]
            
        st.write(f"Results Found: {len(f_df)}")
        st.dataframe(f_df.head(100))
else:
    st.info("Waiting for data... Please upload Data.xlsx or add it to GitHub.")
