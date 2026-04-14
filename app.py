import streamlit as st
import pandas as pd
import re
from gtts import gTTS
import io

# 1. القواميس الشاملة (عربي، إنجليزي، فرانكو)
COUNTRY_MAP = {
    'EGY': ['egypt', 'masr', 'مصر', 'eg'],
    'ARS': ['ksa', 'saudi', 'السعودية', 'ars'],
    'ISR': ['israel', 'اسرائيل', 'isr'],
    'TUR': ['turkey', 'turkiye', 'تركيا', 'tur']
}

SERVICE_MAP = {
    'DAB': ['dab', 'داب', 'ديجيتال'],
    'TV': ['tv', 'television', 'تليفزيون', 'تلفزيون', 'مرئي'],
    'FM': ['fm', 'اف ام', 'اذاعة'],
}

SERVICE_KNOWLEDGE_BASE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01']
}

# 2. وظيفة تحليل النص (The Multi-Tasker)
def parse_compound_query(query):
    # تفكيك السؤال لو فيه كلمات ربط
    delimiters = ['compared to', 'and', 'و', 'مقارنة بـ', 'vs']
    pattern = '|'.join(map(re.escape, delimiters))
    parts = re.split(pattern, query.lower())
    return [p.strip() for p in parts if p.strip()]

# 3. وظيفة استخراج البيانات من كل جزء
def extract_entities(sub_query):
    country = next((code for code, keys in COUNTRY_MAP.items() if any(k in sub_query for k in keys)), None)
    service = next((s for s, keys in SERVICE_MAP.items() if any(k in sub_query for k in keys)), None)
    return country, service

# 4. المحرك الرئيسي
def run_comparison(query, df):
    parts = parse_compound_query(query)
    results = []

    for part in parts:
        country, service = extract_entities(part)
        if country and service:
            fdf = df[(df['Adm'] == country) & (df['Notice Type'].isin(SERVICE_KNOWLEDGE_BASE[service]))]
            results.append({'country': country, 'service': service, 'count': len(fdf)})
    
    return results

# --- UI Streamlit ---
st.title("📡 Seshat AI – Multi-Tasking Engine")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    # تنظيف سريع
    df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()

    user_query = st.text_input("اسأل سؤال مركب (مثلاً: TV in Turkey vs DAB in Egypt):")

    if user_query:
        comparisons = run_comparison(user_query, df)
        
        if len(comparisons) >= 2:
            st.subheader("📊 Comparison Results")
            cols = st.columns(len(comparisons))
            for i, res in enumerate(comparisons):
                cols[i].metric(f"{res['service']} in {res['country']}", res['count'])
            
            # حساب الفرق برمجياً (Zero Intelligence Math)
            diff = abs(comparisons[0]['count'] - comparisons[1]['count'])
            st.info(f"الفرق بين المجموعتين هو: {diff} سجل")
        elif len(comparisons) == 1:
            res = comparisons[0]
            st.metric(f"{res['service']} in {res['country']}", res['count'])
        else:
            st.error("مقدرتش أفهم المقارنة، اتأكد إنك كتبت الدولتين والخدمتين صح.")
