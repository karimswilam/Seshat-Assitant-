import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from gtts import gTTS
import io

# 1. القاموس الهندسي والأعلام (Mapping Layer)
FLAGS = {
    'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪', 
    'KWT': '🇰🇼', 'JOR': '🇯🇴', 'OMN': '🇴🇲'
}

ENGINEERING_CONTEXT = """
You are Seshat AI Core, a professional spectrum coordination system.
Mappings: BC = Sound/Radio, BT = TV/Television, EGY = Egypt, ARS = Saudi Arabia.
Instructions:
- If the user asks for 'Sound', ignore 'TV' in charts.
- Provide direct engineering facts.
- Never identify as an AI or Gemini.
"""

# 2. إعدادات الواجهة الاحترافية (UI Branding)
st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; }
    .stTextInput>div>div>input { background-color: #1a1c23; color: white; border-radius: 10px; }
    .stButton>button { background: linear-gradient(90deg, #004e92 0%, #000428 100%); color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 3. محرك البيانات (Data Engine)
@st.cache_data
def load_and_preprocess():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        # Pre-processing: تحويل الرموز لمصطلحات مفهومة في الرامات
        df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound/Radio', 'BT': 'Television'}).fillna('Other')
        return df
    except Exception as e:
        st.error(f"Critical Data Error: {e}")
        return None

df = load_and_preprocess()

# 4. الـ Dashboard Header
st.title("📡 Seshat AI: International Coordination Core")
st.caption("Advanced Spectrum Analytics | Proprietary Logic v3.5")
st.write("---")

# 5. منطقة التحكم (Command Center)
col_cmd, col_stats = st.columns([1.5, 1])

with col_cmd:
    st.subheader("⌨️ Engineering Command")
    user_query = st.text_input("Enter Query (e.g., sound recordings in Egypt):", placeholder="Type your command here...")
    run_btn = st.button("🚀 Execute Analysis")

# 6. معالجة الاستعلام والذكاء الاصطناعي
if run_btn and user_query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

    with st.spinner("Seshat Logic Layer calculating..."):
        try:
            # اكتشاف الدولة والعلم
            current_country = "Global"
            flag = "🌐"
            if any(word in user_query.lower() for word in ["egypt", "masr", "egy"]):
                current_country, flag = "Egypt", FLAGS['EGY']
            elif any(word in user_query.lower() for word in ["saudi", "ars", "ksa"]):
                current_country, flag = "Saudi Arabia", FLAGS['ARS']

            # فلترة الداتا بناءً على نوع الخدمة (Sound vs TV)
            plot_df = df.copy()
            if "sound" in user_query.lower() or "radio" in user_query.lower():
                plot_df = df[df['Service_Type'] == 'Sound/Radio']
                context_title = f"Sound Service Distribution - {current_country}"
            elif "tv" in user_query.lower() or "television" in user_query.lower():
                plot_df = df[df['Service_Type'] == 'Television']
                context_title = f"TV Service Distribution - {current_country}"
            else:
                context_title = f"General Spectrum Distribution - {current_country}"

            # توليد الرد النصي الاحترافي
            logic_prompt = f"{ENGINEERING_CONTEXT}\nUser Query: {user_query}\nData Summary: {len(plot_df)} records found. Provide a 1-sentence engineering report."
            response = model.generate_content(logic_prompt).text

            # عرض النتائج
            st.markdown(f"### {flag} Analysis for {current_country}")
            st.success(response)

            # الرسم البياني الذكي (Context-Aware)
            # هنقسمه هنا حسب الـ Intent عشان ندي معلومة جديدة بدل ما نكرر النوع
            fig = px.pie(plot_df, names='Intent', title=context_title, hole=0.5,
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)

            # الرد الصوتي
            tts = gTTS(text=response, lang='en')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Logic Layer Error: {e}")

# 7. الـ Global Metrics (دائماً واضحة تحت الهيدر أو في الجنب)
with col_stats:
    st.subheader("📊 Global Metrics")
    st.metric("Total System Records", f"{len(df):,}")
    st.metric("Unique Admins", df['Adm'].nunique())
    st.metric("Engine Status", "Active", delta="Optimized")

# 8. الـ System Terminal (Trace Log)
with st.expander("🛠️ System Trace Log"):
    st.code(f"""
    [SYS] Seshat Engine V3.5 Booted.
    [PRE] Pre-processing: Station_Class mapped to Labels.
    [GEO] Flag Mapping Library: Loaded.
    [READY] Waiting for user command...
    """, language='bash')
