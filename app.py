import streamlit as st
import pandas as pd
import io
from gtts import gTTS

# --- الهيكل التنظيمي للخدمات (الجدول اللي إنت بعته) ---
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04'],
    'ADMIN': ['TB1', 'TB2', 'TB3', 'TB4', 'TB5', 'TB6', 'TB7', 'TB8', 'TB9']
}

# قاموس الوصف التفصيلي (Mapping)
NOTICE_MAP = {
    'GS1': 'T-DAB Assignment', 'GS2': 'T-DAB Allotment',
    'DS1': 'GE06 T-DAB Assignment', 'DS2': 'GE06 T-DAB Allotment',
    'GT1': 'DVB-T Assignment', 'GT2': 'DVB-T Allotment',
    'T01': 'VHF Sound (FM)', 'T02': 'VHF/UHF TV'
}

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI - Professional Telecom Mode")

@st.cache_data(ttl=600)
def load_data(file):
    if file:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        # تنظيف الداتا من المسافات المخفية
        for col in ['Adm', 'Notice Type']:
            if col in df.columns: df[col] = df[col].astype(str).str.strip()
        return df
    return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Data.xlsx", type=["xlsx"])
df = load_data(uploaded_file)

query = st.text_input("💬 اسأل بالمعنى (مثلاً: ksa 3ndha kam DAB assignment?):")

if query and not df.empty:
    q = query.lower()
    f_df = df.copy()

    # 1. ذكاء تحديد الخدمة (The Domain Logic)
    target_types = []
    if 'dab' in q: target_types.extend(SERVICE_KNOWLEDGE['DAB'])
    if 'tv' in q or 'تلفزيون' in q: target_types.extend(SERVICE_KNOWLEDGE['TV'])
    if 'fm' in q or 'إذاعة' in q: target_types.extend(SERVICE_KNOWLEDGE['FM'])
    
    # فلترة نوع الإشعار بناءً على الفهم الهندسي
    if target_types:
        f_df = f_df[f_df['Notice Type'].isin(target_types)]
    
    # 2. ذكاء تحديد الدولة
    countries = {'ARS': ['ars', 'ksa', 'saudi'], 'EGY': ['egy', 'مصر', 'masr']}
    for code, terms in countries.items():
        if any(t in q for t in terms):
            f_df = f_df[f_df['Adm'] == code]

    # 3. ذكاء التفرقة بين Assignment و Allotment
    if 'assignment' in q or 'تخصيص' in q:
        f_df = f_df[f_df['Notice Type'].str.contains('1')] # GS1, GT1, DS1
    elif 'allotment' in q or 'حجز' in q:
        f_df = f_df[f_df['Notice Type'].str.contains('2')] # GS2, GT2, DS2

    # --- النتيجة ---
    result_count = len(f_df)
    if any(w in q for w in ['kam', '3dd', 'count', 'عدد']):
        st.metric("📊 النتيجة التحليلية", f"{result_count} Record")
    else:
        st.success(f"🤖 لقيتلك {result_count} سجل مطابق:")
        st.dataframe(f_df.head(100))

    # رسم بياني يوضح الفئات المفلترة
    if not f_df.empty:
        st.bar_chart(f_df['Notice Type'].value_counts())
