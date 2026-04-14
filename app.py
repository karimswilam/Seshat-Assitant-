import streamlit as st
import pandas as pd

# --- الوعي الهندسي الصارم ---
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01']
}

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI - Professional Analytics")

@st.cache_data
def load_data(file):
    if file:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        for col in ['Adm', 'Notice Type']:
            if col in df.columns: df[col] = df[col].astype(str).str.strip()
        return df
    return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Data.xlsx", type=["xlsx"])
df = load_data(uploaded_file)

query = st.text_input("💬 اسأل هنا (مثلاً: ksa dab count):")

if query and not df.empty:
    q = query.lower()
    f_df = df.copy()

    # 1. فلترة الدولة
    if any(w in q for w in ['ars', 'ksa', 'saudi', 'سعودية']):
        f_df = f_df[f_df['Adm'] == 'ARS']

    # 2. فلترة الخدمة (DAB)
    if 'dab' in q:
        f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]

    # 3. النتيجة الصافية (بدون أي كلام إنشائي)
    result_count = len(f_df)
    
    # [Anti-Hallucination] جرد الأنواع الحقيقية فقط
    actual_types = f_df['Notice Type'].unique().tolist()
    
    st.metric("📊 Total Records Found", result_count)
    
    if result_count > 0:
        st.success(f"✅ Found {result_count} records. Real Notice Types in file: {', '.join(actual_types)}")
        st.dataframe(f_df[['Adm', 'Site/Allotment Name', 'Notice Type']].head(100))
    else:
        st.error("❌ No matching records found in your Excel file.")

elif not uploaded_file:
    st.warning("⚠️ Please upload the Excel file to start real analysis.")
