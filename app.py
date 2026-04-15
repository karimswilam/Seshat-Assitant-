# ======================================================
# 📡 Seshat AI v6.2 – The Final Hybrid Interface
# ======================================================
import streamlit as st
import pandas as pd
import re
from gtts import gTTS
import io

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Hybrid Mode", layout="wide")

st.title("📡 Seshat AI – Engineering Voice Assistant")
st.markdown("---")

# 2. FIXED UPLOADING SPACE (المكان اللي كان تايه)
# بنحط مساحة الرفع في صدر الصفحة زي ما طلبت
st.subheader("📂 1. Upload Database")
uploaded_file = st.file_uploader("Upload your Excel file here", type=["xlsx"], key="main_uploader")

st.markdown("---")

# 3. FIXED CHATTING SPACE
st.subheader("💬 2. Engineering Query")
user_query = st.text_input("Ask about comparisons, counts, or exceptions:", 
                          placeholder="Example: How many TV in Turkey compared to DAB in Egypt?",
                          key="main_chat")

# 4. Global Dictionaries (For Logic)
COUNTRY_MAP = {
    'EGY': ['egypt', 'masr', 'مصر', 'eg'],
    'ARS': ['saudi', 'ksa', 'السعودية', 'ars'],
    'TUR': ['turkey', 'turkiye', 'تركيا', 'tur'],
    'ISR': ['israel', 'اسرائيل', 'isr']
}
SERVICE_MAP = {
    'DAB': ['dab', 'داب', 'ديجيتال'],
    'TV': ['tv', 'television', 'تليفزيون'],
}
TECH_CODES = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

# 5. Hybrid Logic Engine
def process_hybrid_query(query, df):
    # تفكيك السؤال (Multi-Query Logic)
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

# 6. Runtime Execution
if uploaded_file:
    # تحميل البيانات مرة واحدة وتخزينها في الـ Cache
    @st.cache_data
    def load_data(file):
        data = pd.read_excel(file)
        data['Adm'] = data['Adm'].astype(str).str.strip().str.upper()
        data['Notice Type'] = data['Notice Type'].astype(str).str.strip().str.upper()
        return data

    df = load_data(uploaded_file)
    st.success("✅ Database loaded successfully!")

    if user_query:
        st.markdown("### 🧠 Analysis Results")
        ans = process_hybrid_query(user_query, df)
        
        if ans:
            # عرض النتائج في Columns للمقارنة
            cols = st.columns(len(ans))
            for i, r in enumerate(ans):
                with cols[i]:
                    st.metric(label=f"{r['service']} in {r['country']}", value=r['count'])
            
            # عملية حسابية بسيطة لو فيه مقارنة
            if len(ans) == 2:
                diff = abs(ans[0]['count'] - ans[1]['count'])
                st.info(f"💡 Calculated Difference: {diff} records")
                
            # عرض الجدول لآخر نتيجة لزيادة التأكيد
            with st.expander("Show detailed data view"):
                st.dataframe(ans[0]['data'].head(50))
        else:
            st.warning("Could not detect Country or Service in your question.")
else:
    st.info("Waiting for database upload to start analysis...")

st.markdown("---")
st.caption("Seshat AI v6.2 | Hybrid Mode: Fixed Upload + Fixed Chat")
