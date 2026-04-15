import streamlit as st
import pandas as pd
import re
import os

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI v7.1", layout="wide")
st.title("📡 Seshat AI – Engineering Analytics Engine")

# 2. Hybrid Data Loading (Internal: Data.xlsx)
@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file:
        return pd.read_excel(uploaded_file)
    elif os.path.exists("Data.xlsx"):
        return pd.read_excel("Data.xlsx")
    return None

# Sidebar for transparency
with st.sidebar:
    st.header("📂 Data Integration")
    uploaded = st.file_uploader("Upload New Data (Optional)", type=["xlsx"])
    df = load_data(uploaded)
    if df is not None:
        st.success(f"Database Active: {len(df)} records")

# 3. Complex Operation Engine (Math & Logic)
def advanced_engine(query, data):
    q = query.lower()
    data['Adm'] = data['Adm'].astype(str).str.strip().str.upper()
    data['Notice Type'] = data['Notice Type'].astype(str).str.strip().str.upper()
    
    # Mapping
    COUNTRY_MAP = {'EGY': ['egypt', 'مصر'], 'ARS': ['saudi', 'السعودية'], 'TUR': ['turkey', 'تركيا']}
    TECH_MAP = {'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], 'TV': ['T02', 'G02', 'GT1', 'GT2']}

    parts = re.split(r'and|compared to|vs|مقارنة| و ', q)
    results = []

    for part in parts:
        country = next((c for c, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in TECH_MAP.items() if s.lower() in part), 'DAB')
        
        if country:
            mask = (data['Adm'] == country) & (data['Notice Type'].isin(TECH_MAP[service]))
            
            # Level 2: Negative Filtering (Except / ما عدا)
            if 'except' in q or 'ما عدا' in q:
                match = re.search(r'(except|ما عدا)\s+([a-z0-9]+)', q)
                if match: mask &= (data['Notice Type'] != match.group(2).upper())
            
            fdf = data[mask]
            results.append({'country': country, 'service': service, 'count': len(fdf), 'data': fdf})
    return results

# 4. User Interface
user_query = st.text_input("💬 Ask your complex query (Comparisons, Exceptions, Shares):")

if df is not None and user_query:
    res_list = advanced_engine(user_query, df)
    
    if res_list:
        st.subheader("📊 Engineering Dashboard")
        m_cols = st.columns(len(res_list))
        chart_data = {}

        for i, r in enumerate(res_list):
            m_cols[i].metric(f"{r['service']} | {r['country']}", r['count'])
            chart_data[f"{r['country']} ({r['service']})"] = r['count']

        # Level 1 & 5: Bar Chart Visualization
        st.bar_chart(pd.Series(chart_data))

        # Level 3: Percentage Logic
        if 'نسبة' in user_query or 'percent' in user_query:
            total = sum(chart_data.values())
            for key, val in chart_data.items():
                st.write(f"📈 **{key}** Market Share: **{(val/total)*100:.2f}%**")

        with st.expander("🔍 View Raw Records"):
            st.dataframe(pd.concat([r['data'] for r in res_list]))
    else:
        st.warning("Could not parse query. Please mention Country and Service.")
