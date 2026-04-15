# ======================================================
# 📡 Seshat AI v6.1 – UI Fix & Chat Interface
# ======================================================
import streamlit as st
import pandas as pd
import re
# شلنا المكتبات اللي بتعمل Error في السيرفر وبدلها بـ gTTS
from gtts import gTTS
import io

# 1. Page Configuration (Always at the Top)
st.set_page_config(page_title="Seshat AI – Spectrum Analytics", layout="wide")

# 2. Permanent Chat Space (مكان ثابت للدردشة)
st.title("📡 Seshat AI – Professional Engineering Analytics")
st.markdown("---")

# دي المساحة اللي كانت مختفية - حطيناها في البداية
user_query = st.text_input("💬 اسأل سؤالك هنا (عربي، إنجليزي، مقارنات):", 
                          placeholder="مثلاً: TV in Turkey compared to DAB in Egypt")

st.markdown("---")

# 3. Sidebar for Data Upload (عشان ميزحمش الشاشة)
with st.sidebar:
    st.header("📂 Data Management")
    uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])

# 4. Logic & Dictionaries (نفس الـ Logic القوي بتاعنا)
COUNTRY_MAP = {
    'EGY': ['egypt', 'masr', 'مصر', 'eg'],
    'ARS': ['saudi', 'ksa', 'السعودية', 'ars'],
    'TUR': ['turkey', 'turkiye', 'تركيا', 'tur'],
    'ISR': ['israel', 'اسرائيل', 'isr']
}
SERVICE_MAP = {
    'DAB': ['dab', 'داب', 'اذاعة ديجيتال'],
    'TV': ['tv', 'television', 'تليفزيون', 'مرئي'],
}
TECH_CODES = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

def process_query(query, df):
    # (نفس الـ Logic بتاع المقارنة والاستثناء اللي فات)
    delimiters = ['compared to', 'and', ' vs ', 'مقارنة بـ', ' و ']
    parts = re.split('|'.join(map(re.escape, delimiters)), query.lower())
    results = []
    for part in parts:
        c = next((code for code, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        s = next((ser for ser, keys in SERVICE_MAP.items() if any(k in part for k in keys)), None)
        if c and s:
            fdf = df[(df['Adm'] == c) & (df['Notice Type'].isin(TECH_CODES[s]))]
            results.append({'country': c, 'service': s, 'count': len(fdf), 'data': fdf})
    return results

# 5. Execution
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()

    if user_query:
        ans = process_query(user_query, df)
        if ans:
            st.subheader("📝 نتيجة التحليل")
            cols = st.columns(len(ans))
            for i, r in enumerate(ans):
                cols[i].metric(f"{r['service']} | {r['country']}", r['count'])
            
            if len(ans) == 2:
                diff = abs(ans[0]['count'] - ans[1]['count'])
                st.info(f"💡 الفرق الحسابي بين المجموعتين: {diff} سجل")
        else:
            st.warning("🔍 لم يتم العثور على بيانات مطابقة. تأكد من كتابة الدولة والخدمة.")
else:
    st.info("👈 من فضلك ارفع ملف الداتا من القائمة الجانبية (Sidebar) لتفعيل البحث.")
