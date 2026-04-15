import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os

# 1. Page Config & Setup
st.set_page_config(page_title="Seshat AI v7.0", layout="wide")
st.title("📡 Seshat AI – Advanced Spectrum Analytics")

# 2. Hybrid Data Loading (Internal + Optional Upload)
@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file:
        return pd.read_excel(uploaded_file)
    elif os.path.exists("Data.xlsx"): # الملف الثابت اللي اتفقنا عليه
        return pd.read_excel("Data.xlsx")
    return None

with st.sidebar:
    st.header("📂 Data Source")
    file = st.file_uploader("Upload New Data (Optional)", type=["xlsx"])
    df = load_data(file)
    if df is not None:
        st.success(f"Loaded {len(df)} records.")

# 3. Intelligent Operation Engine (The 5 Levels)
def complex_engine(query, data):
    q = query.lower()
    # تنظيف البيانات
    data['Adm'] = data['Adm'].astype(str).str.strip().str.upper()
    data['Notice Type'] = data['Notice Type'].astype(str).str.strip().str.upper()
    
    # القواميس
    COUNTRY_MAP = {'EGY': ['egypt', 'مصر', 'eg'], 'ARS': ['saudi', 'so3deya', 'السعودية', 'ars'], 'TUR': ['turkey', 'turkiye', 'تركيا']}
    TECH_MAP = {'DAB': ['GS1', 'GS2', 'DS1', 'DS2'], 'TV': ['T02', 'G02', 'GT1', 'GT2'], 'FM': ['T01']}

    # تفكيك السؤال (Parallel & Comparison)
    parts = re.split(r'and|compared to|vs|مقارنة| و ', q)
    extracted_results = []

    for part in parts:
        country = next((c for c, keys in COUNTRY_MAP.items() if any(k in part for k in keys)), None)
        service = next((s for s, keys in TECH_MAP.items() if s.lower() in part), None)
        
        if country and service:
            mask = (data['Adm'] == country) & (data['Notice Type'].isin(TECH_MAP[service]))
            
            # منطق الاستثناء (Negative Filtering)
            if 'except' in q or 'ما عدا' in q:
                match = re.search(r'(except|ما عدا)\s+([a-z0-9]+)', q)
                if match: mask &= (data['Notice Type'] != match.group(2).upper())
            
            fdf = data[mask]
            extracted_results.append({'country': country, 'service': service, 'count': len(fdf), 'data': fdf})
    
    return extracted_results

# 4. Main Interface & Dashboard
user_query = st.text_input("💬 Ask your complex query (e.g., DAB in Egypt vs Saudi excluding T02):")

if df is not None and user_query:
    results = complex_engine(user_query, df)
    
    if results:
        # A. Metrics Row
        cols = st.columns(len(results))
        plot_data = []
        for i, res in enumerate(results):
            cols[i].metric(f"{res['service']} in {res['country']}", res['count'])
            plot_data.append({'Location': res['country'], 'Count': res['count'], 'Service': res['service']})

        # B. Interactive Dashboard (The Bar Chart we missed)
        st.markdown("---")
        chart_df = pd.DataFrame(plot_data)
        fig = px.bar(chart_df, x='Location', y='Count', color='Service', barmode='group', title="Comparative Analysis")
        st.plotly_chart(fig, use_container_width=True)

        # C. Market Share Logic (Level 3)
        if 'نسبة' in user_query or 'percent' in user_query:
            total = sum(d['Count'] for d in plot_data)
            for d in plot_data:
                share = (d['Count'] / total) * 100
                st.write(f"📈 Share of {d['Location']}: **{share:.2f}%**")

        # D. Data View
        with st.expander("Show Detailed Records"):
            combined_df = pd.concat([res['data'] for res in results])
            st.dataframe(combined_df)
    else:
        st.warning("Please specify country and service clearly.")
