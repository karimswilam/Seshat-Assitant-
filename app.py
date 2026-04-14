# ======================================================
# 📡 Seshat AI v6.0 – Advanced Logic & Math Engine
# ======================================================
import streamlit as st
import pandas as pd
import re
from gtts import gTTS
import io

# 1. القواميس المحدثة (دعم كامل للعربية والفرانكو)
COUNTRY_MAP = {
    'EGY': ['egypt', 'masr', 'مصر', 'eg'],
    'ARS': ['saudi', 'ksa', 'السعودية', 'المملكة', 'ars'],
    'TUR': ['turkey', 'turkiye', 'تركيا', 'tur'],
    'ISR': ['israel', 'اسرائيل', 'isr']
}

SERVICE_MAP = {
    'DAB': ['dab', 'داب', 'اذاعة ديجيتال', 'راديو رقمي'],
    'TV': ['tv', 'television', 'تليفزيون', 'تلفزيون', 'مرئي'],
    'FM': ['fm', 'اف ام', 'اذاعة'],
    'AM': ['am', 'اي ام']
}

TECH_CODES = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

# 2. Advanced Parsing Engine
def parse_and_execute(query, df):
    q = query.lower()
    
    # أ. معالجة الاستثناء (Except / ما عدا)
    excluded_type = None
    if 'except' in q or 'ما عدا' in q or 'من غير' in q:
        match = re.search(r'(except|ما عدا|من غير)\s+([a-z0-9]+)', q)
        if match: excluded_type = match.group(2).upper()

    # ب. تفكيك السؤال المركب (Compared to / And / و)
    delimiters = ['compared to', 'and', ' vs ', 'مقارنة بـ', ' و ', ' مع ']
    pattern = '|'.join(map(re.escape, delimiters))
    parts = re.split(pattern, q)
    
    results = []
    for part in parts:
        country = next((code for code, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in SERVICE_MAP.items() if any(k in part for k in keys)), None)
        
        if country and service:
            # فلترة أساسية
            mask = (df['Adm'] == country) & (df['Notice Type'].isin(TECH_CODES[service]))
            # تطبيق الاستثناء لو موجود
            if excluded_type:
                mask &= (df['Notice Type'] != excluded_type)
            
            fdf = df[mask]
            results.append({'country': country, 'service': service, 'count': len(fdf), 'data': fdf})

    return results

# 3. UI logic
st.set_page_config(page_title="Seshat AI v6.0", layout="wide")
st.title("📡 Seshat AI – Advanced Spectrum Analytics")

uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()

    user_query = st.text_input("💬 اسأل سؤال معقد (مقارنة، استثناء، إحصاء):")

    if user_query:
        ans_list = parse_and_execute(user_query, df)
        
        if len(ans_list) > 0:
            st.subheader("📊 التحليل الهندسي")
            cols = st.columns(len(ans_list))
            
            for i, res in enumerate(ans_list):
                with cols[i]:
                    st.metric(f"{res['service']} | {res['country']}", res['count'])
                    st.caption(f"داتا {res['country']} جاهزة")

            # منطق العمليات الحسابية (الفرق والنسبة)
            if len(ans_list) == 2:
                v1, v2 = ans_list[0]['count'], ans_list[1]['count']
                diff = v1 - v2
                st.info(f"💡 الفرق الحسابي: {abs(diff)} سجل")
                
                # حساب النسبة لو السؤال فيه "نسبة" أو "percent"
                if 'نسبة' in user_query or 'percent' in user_query:
                    total = v1 + v2
                    if total > 0:
                        p1 = (v1 / total) * 100
                        st.write(f"📈 حصة {ans_list[0]['country']} من الإجمالي: {p1:.2f}%")

            # عرض الداتا لو مش طلب "كم عدد"
            if not any(w in user_query for w in ['كم', 'count', 'how many']):
                for res in ans_list:
                    with st.expander(f"تفاصيل بيانات {res['country']} - {res['service']}"):
                        st.dataframe(res['data'].head(50))
        else:
            st.warning("⚠️ مقدرتش أحلل السؤال.. اتأكد من كتابة الدولة والخدمة بوضوح.")
