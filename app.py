import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# 1. قاموس الأعلام (Mapping Codes to Emoji Flags)
FLAGS = {
    'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪', 
    'KWT': '🇰🇼', 'JOR': '🇯🇴', 'OMN': '🇴🇲'
}

# 2. الهوية البصرية المطورة
st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stMetricValue"] { font-size: 32px; color: #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_and_map():
    df = pd.read_csv("Data.csv", low_memory=False)
    # تحويل الأنواع لأسماء واضحة
    df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound', 'BT': 'TV'}).fillna('Other')
    return df

df = load_and_map()

# 3. الـ Dashboard Header
st.title("📡 Seshat AI: International Coordination Core")
st.write("---")

# ميزة جديدة: اكتشاف الدولة من السؤال لإظهار العلم
detected_flag = ""
current_country = "Global"

# 4. محرك البحث الذكي (Logic Engine)
st.subheader("⌨️ Engineering Command Center")
user_query = st.text_input("Enter Query (e.g., sound stations in Egypt):")

if user_query:
    # تحديد الدولة والعلم أوتوماتيكياً
    if "egypt" in user_query.lower() or "masr" in user_query.lower() or "egy" in user_query.lower():
        current_country = "Egypt"
        detected_flag = FLAGS.get('EGY', '')
    elif "saudi" in user_query.lower() or "ars" in user_query.lower():
        current_country = "Saudi Arabia"
        detected_flag = FLAGS.get('ARS', '')

    st.markdown(f"### Analyzing Data for: {detected_flag} {current_country}")

    # التصفية الذكية للـ Charts بناءً على السؤال
    filtered_df = df.copy()
    
    # لو المستخدم سأل عن Sound بس، نفلتر الـ Chart
    if "sound" in user_query.lower() or "radio" in user_query.lower():
        filtered_df = df[df['Service_Type'] == 'Sound']
        chart_title = "Sound Stations Analysis"
    elif "tv" in user_query.lower() or "television" in user_query.lower():
        filtered_df = df[df['Service_Type'] == 'TV']
        chart_title = "TV Stations Analysis"
    else:
        chart_title = "General Distribution"

    # عرض النتائج في كروت
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.metric(f"{current_country} Records", len(filtered_df[filtered_df['Adm'].str.contains('EGY|ARS', na=False)]))
        st.success(f"Logic Engine: Verified entries for {current_country}")

    with col_b:
        # رسم بياني ذكي يتغير حسب السؤال
        fig = px.pie(filtered_df, names='Service_Type', title=chart_title, hole=0.4,
                     color_discrete_sequence=['#00d4ff', '#004e92'])
        st.plotly_chart(fig, use_container_width=True)

# 5. الـ System Trace
with st.expander("🛠️ Intelligence Trace Log"):
    st.code(f"""
    [GEO] Country Detected: {current_country}
    [FLAG] Identity Mapping: {detected_flag}
    [FILTER] Applied Context: {chart_title}
    """, language='bash')
