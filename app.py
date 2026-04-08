import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from gtts import gTTS
import io

# 1. إعدادات الهوية الهندسية والأعلام
FLAGS = {
    'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪', 
    'KWT': '🇰🇼', 'JOR': '🇯🇴', 'OMN': '🇴🇲'
}

ENGINEERING_CONTEXT = """
You are Seshat AI Core, a proprietary spectrum coordination engine.
Context: BC=Sound, BT=TV, EGY=Egypt, ARS=Saudi Arabia.
Rules:
- If query mentions 'Sound', filter charts to show only 'Sound/Radio'.
- If query mentions 'TV', filter charts to show only 'Television'.
- Always respond as an engineering system, never as an AI assistant.
"""

# 2. تصميم الـ Dashboard الاحترافي
st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; }
    .stTextInput>div>div>input { background-color: #1a1c23; color: white; border-radius: 10px; }
    .stButton>button { 
        background: linear-gradient(90deg, #004e92 0%, #000428 100%); 
        color: white; border-radius: 8px; border: none; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. محرك معالجة البيانات (Preprocessing)
@st.cache_data
def load_and_clean_data():
    try:
        # تحميل البيانات مع توحيد المسميات لسهولة الفلترة
        df = pd.read_csv("Data.csv", low_memory=False)
        df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound/Radio', 'BT': 'Television'}).fillna('Other')
        return df
    except Exception as e:
        st.error(f"Data Core Error: {e}")
        return None

df = load_and_clean_data()

# 4. واجهة العرض الرئيسية
st.title("📡 Seshat AI: Spectrum Coordination Core")
st.caption("International Regulatory Framework Analysis | V3.6")
st.write("---")

# Metrics Quick View
if df is not None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", f"{len(df):,}")
    m2.metric("Administrations", df['Adm'].nunique())
    m3.metric("Radio (BC)", len(df[df['Service_Type'] == 'Sound/Radio']))
    m4.metric("TV (BT)", len(df[df['Service_Type'] == 'Television']))

st.write("---")

# 5. مركز تنفيذ الأوامر (Command Center)
col_input, col_viz = st.columns([1, 1.2])

with col_input:
    st.subheader("⌨️ Execute Command")
    query = st.text_input("Engineering Query:", placeholder="e.g., show me recorded sound stations for Egypt...")
    run = st.button("🚀 Run System Analysis")

if run and query and df is not None:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    with st.spinner("Seshat Logic Layer processing..."):
        try:
            # اكتشاف الدولة لإظهار العلم
            flag = "🌐"
            country_name = "Global"
            if any(x in query.lower() for x in ["egypt", "masr", "egy"]):
                flag, country_name = FLAGS['EGY'], "Egypt"
            elif any(x in query.lower() for x in ["saudi", "ars", "ksa"]):
                flag, country_name = FLAGS['ARS'], "Saudi Arabia"

            # الفلترة الذكية للبيانات والرسوم بناءً على محتوى السؤال
            analysis_df = df.copy()
            chart_title = f"Data Distribution - {country_name}"
            
            if "sound" in query.lower() or "radio" in query.lower():
                analysis_df = df[df['Service_Type'] == 'Sound/Radio']
                chart_title = f"Sound Service Status - {country_name}"
            elif "tv" in query.lower() or "television" in query.lower():
                analysis_df = df[df['Service_Type'] == 'Television']
                chart_title = f"TV Service Status - {country_name}"

            # توليد التقرير الفني
            prompt = f"{ENGINEERING_CONTEXT}\nQuery: {query}\nResult Count: {len(analysis_df)}\nProvide 1 formal sentence."
            report = model.generate_content(prompt).text

            # العرض النهائي
            st.markdown(f"### {flag} {country_name} Analysis")
            st.success(report)

            with col_viz:
                # رسم بياني تفاعلي يعتمد على "حالة التنسيق" (Intent) لإعطاء عمق أكبر للتحليل
                fig = px.pie(analysis_df, names='Intent', title=chart_title, hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)

            # تحويل التقرير لصوت احترافي
            tts = gTTS(text=report, lang='en')
            audio_file = io.BytesIO()
            tts.write_to_fp(audio_file)
            st.audio(audio_file.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Analysis Error: {e}")

# 6. سجل تتبع النظام (System Trace)
with st.expander("🛠️ Internal Logic Trace"):
    st.code(f"""
    [LOG] Identity: Seshat AI Core V3.6
    [GEO] Country Detection: {country_name if 'country_name' in locals() else 'Idle'}
    [DATA] Preprocessing: Station_Class mapped to Service_Type.
    [SYS] Audio Engine: gTTS Ready.
    """, language="bash")
