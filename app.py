import streamlit as st
import pandas as pd
import os

# --- 1. القاموس الهندسي الشامل (المرجع بتاعك) ---
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

NOTICE_MAP = {
    'GS1': 'T-DAB Assignment', 'GS2': 'T-DAB Allotment',
    'DS1': 'GE06 T-DAB Assignment', 'DS2': 'GE06 T-DAB Allotment',
    'GT1': 'DVB-T Assignment', 'GT2': 'DVB-T Allotment',
    'T01': 'VHF Sound (FM)', 'T02': 'VHF/UHF TV'
}

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide", page_icon="📡")
st.title("📡 Seshat AI - Hybrid Data Analytics")

# --- 2. منطق الـ Hybrid Loading ---
@st.cache_data(ttl=600)
def load_data(uploaded_file, default_path="Data.xlsx"):
    target_file = None
    
    # أولاً: لو اليوزر رفع ملف، نستخدمه
    if uploaded_file is not None:
        target_file = uploaded_file
        st.sidebar.success("✅ Working with Uploaded File")
    # ثانياً: لو مفيش رفع، ندور على الملف الأساسي في السيرفر/GitHub
    elif os.path.exists(default_path):
        target_file = default_path
        st.sidebar.info("📂 Working with Default Master File")
    
    if target_file:
        try:
            df = pd.read_excel(target_file)
            # تنظيف البيانات
            df.columns = [str(c).strip() for c in df.columns]
            for col in ['Adm', 'Notice Type']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            return df
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
    return pd.DataFrame()

# مساحة الرفع (اختيارية)
st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload new Excel (Optional)", type=["xlsx"])

# تحميل البيانات (Hybrid)
df = load_data(uploaded_file)

# --- 3. محرك الاستعلام ---
if not df.empty:
    query = st.text_input("💬 اسأل عن البيانات (مثلاً: ksa dab records):")
    
    if query:
        q = query.lower()
        f_df = df.copy()

        # أ) فلتر الدولة
        countries = {'ARS': ['ars', 'ksa', 'saudi', 'سعودية'], 'EGY': ['egy', 'مصر', 'masr']}
        for code, terms in countries.items():
            if any(t in q for t in terms):
                f_df = f_df[f_df['Adm'] == code]

        # ب) فلتر الخدمة (DAB/TV/FM)
        if 'dab' in q:
            f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]
        elif any(w in q for w in ['tv', 'تلفزيون']):
            f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['TV'])]

        # ج) تحديد نوع السؤال (Count vs View)
        is_count = any(w in q for w in ['kam', '3dd', 'count', 'total', 'عدد'])
        res_count = len(f_df)

        if is_count:
            st.metric("📊 Result Count", f"{res_count} Records")
            if res_count > 0:
                actual_types = f_df['Notice Type'].unique()
                st.info(f"Notice Types found: {', '.join([f'{t} ({NOTICE_MAP.get(t, 'N/A')})' for t in actual_types])}")
        else:
            st.success(f"🤖 Found {res_count} records:")
            st.dataframe(f_df.head(100))

        # د) الرسم البياني التلقائي
        if not f_df.empty:
            st.bar_chart(f_df['Notice Type'].value_counts())
else:
    st.warning("⚠️ No data source found. Please upload a file or ensure Data.xlsx exists in the root folder.")
