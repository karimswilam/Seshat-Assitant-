import streamlit as st
import pandas as pd
import os

# --- 1. القاموس الهندسي (العقل المدبر) ---
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

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI - Hybrid Data Analytics")

# --- 2. منطق التحميل الهجين ---
@st.cache_data(ttl=600)
def load_data(uploaded_file, default_path="Data.xlsx"):
    target_file = None
    if uploaded_file is not None:
        target_file = uploaded_file
    elif os.path.exists(default_path):
        target_file = default_path
    
    if target_file:
        try:
            df = pd.read_excel(target_file)
            df.columns = [str(c).strip() for c in df.columns]
            for col in ['Adm', 'Notice Type']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Excel (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

# رسالة حالة البيانات لليوزر
if not df.empty and uploaded_file is None:
    st.info("💡 Working with Default Master File (Data.xlsx)")

# --- 3. محرك البحث الذكي (Strict Filter) ---
if not df.empty:
    query = st.text_input("💬 اسأل هنا (مثلاً: hya masr 3ndha kam m7ta sound?):")
    
    if query:
        q = query.lower()
        f_df = df.copy()

        # أ) فلترة الدولة - صارمة جداً
        if any(w in q for w in ['egy', 'مصر', 'masr']):
            f_df = f_df[f_df['Adm'] == 'EGY']
        elif any(w in q for w in ['ars', 'ksa', 'saudi', 'سعودية']):
            f_df = f_df[f_df['Adm'] == 'ARS']

        # ب) فلتر النوع (Sound vs TV vs DAB)
        # لو سأل عن sound يبقى عايز كل حاجة إذاعية (FM + AM + DAB)
        if 'sound' in q or 'صوت' in q or 'إذاعة' in q:
            sound_codes = SERVICE_KNOWLEDGE['DAB'] + SERVICE_KNOWLEDGE['FM'] + SERVICE_KNOWLEDGE['AM']
            f_df = f_df[f_df['Notice Type'].isin(sound_codes)]
        elif 'dab' in q:
            f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]
        elif 'tv' in q or 'تلفزيون' in q:
            f_df = f_df[f_df['Notice Type'].isin(SERVICE_KNOWLEDGE['TV'])]

        # ج) النتيجة
        res_count = len(f_df)
        st.metric("📊 Result Count", f"{res_count} Records")
        
        if res_count > 0:
            # منع التأليف: هات اللي موجود فعلاً في الداتا المفلترة
            actual_types = f_df['Notice Type'].unique()
            type_desc = [f"{t} ({NOTICE_MAP.get(t, 'Other')})" for t in actual_types]
            st.success(f"✅ Found types: {', '.join(type_desc)}")
            st.dataframe(f_df.head(100))
            st.bar_chart(f_df['Notice Type'].value_counts())
else:
    st.warning("⚠️ ارفع ملف Data.xlsx عشان نبدأ بجد.")
