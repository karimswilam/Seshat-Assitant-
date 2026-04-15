# ======================================================
# 📡 Seshat AI v6.6 – Final Corrected Hybrid Path
# ======================================================
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Seshat AI – Stable Hybrid", layout="wide")

# 1. الدالة المسؤولة عن قراءة الداتا الثابتة بالاسم الصحيح
@st.cache_data
def get_internal_data():
    # تعديل الاسم هنا عشان يطابق ملفك على GitHub
    file_name = "Data.xlsx" 
    if os.path.exists(file_name):
        try:
            return pd.read_excel(file_name)
        except Exception as e:
            st.error(f"Error reading Data.xlsx: {e}")
            return None
    return None

internal_df = get_internal_data()

# 2. UI Configuration
st.title("📡 Seshat AI – Engineering Assistant")

# الرفع اختياري
uploaded_file = st.file_uploader("Upload New Data (Optional)", type=["xlsx"])

# 3. Hybrid Logic (تحديد الـ Data Source)
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    data_source_msg = "✅ Using: Uploaded File"
elif internal_df is not None:
    df = internal_df
    data_source_msg = "✅ Using: Fixed Database (Data.xlsx)"
else:
    df = None
    data_source_msg = "⚠️ No Data Source Found! Check Data.xlsx on GitHub."

st.sidebar.markdown(data_source_msg)

# 4. Chatting Space (متاح دائماً)
user_query = st.text_input("Engineering Query:", placeholder="How many DAB for Egypt?")

# 5. Execution Logic
if df is not None and user_query:
    # تنظيف البيانات
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
    
    # الـ Logic المطور للمقارنات (Zero Intelligence Mode)
    # [هنا بنحط الـ Parsing اللي عملناه قبل كدة للمقارنة والاستثناء]
    st.write("Processing query...")
