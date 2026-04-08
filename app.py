import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from gtts import gTTS
import io

# 1. المابينج الهندسي والأعلام (Expanded Flag System)
# ضيف هنا أي دولة محتاجها بالكود بتاعها
FLAGS = {
    'EGY': '🇪🇬', 'ARS': '🇸🇦', 'ISR': '🇮🇱', 
    'UAE': '🇦🇪', 'KWT': '🇰🇼', 'JOR': '🇯🇴'
}

ENGINEERING_CONTEXT = """
You are Seshat AI Core. Professional Spectrum Engine.
Standard Mapping:
- 'Israel' / 'israel' / 'isr' -> Adm: 'ISR'
- 'Egypt' / 'egypt' / 'egy' -> Adm: 'EGY'
- 'Sound' / 'Radio' -> Station_Class: 'BC'
- 'TV' / 'Television' -> Station_Class: 'BT'
Rules:
1. Always provide the exact count from the data provided.
2. If a specific service (TV/Sound) is asked, filter only for that.
"""

st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

# 2. تحسين الواجهة (The Professional Dashboard Look)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stMetricValue"] { font-size: 30px; color: #00d4ff; }
    .stButton>button { 
        background: linear-gradient(90deg, #004e92 0%, #000428 100%); 
        color: white; border-radius: 8px; border: none; font-weight: bold;
    }
    .report-box { padding: 20px; border-radius: 10px; border-left: 5px solid #00d4ff; background-color: #1a1c23; }
    </style>
    """, unsafe_allow_html=True)

# 3. محرك البيانات
@st.cache_data
def load_and_map():
    df = pd.read_csv("Data.csv", low_memory=False)
    # تنظيف وتوحيد المسميات
    df['Service_Type'] = df['Station_Class'].map({'BC': 'Sound/Radio', 'BT': 'Television'}).fillna('Other')
    return df

df = load_and_map()

# 4. واجهة العرض (Header)
st.title("📡 Seshat AI: International Coordination Core")
st.caption("Phase 3: Intelligent Regional Analysis & Mapping")
st.write("---")

if df is not None:
    # العدادات العلوية
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Database Entries", f"{len(df):,}")
    m2.metric("Active Administrations", df['Adm'].nunique())
    m3.metric("Radio Stations (BC)", len(df[df['Service_Type'] == 'Sound/Radio']))
    m4.metric("TV Stations (BT)", len(df[df['Service_Type'] == 'Television']))

    st.write("---")

    # Command Center
    col_in, col_viz = st.columns([1, 1.3])

    with col_in:
        st.subheader("⌨️ Command Center")
        user_input = st.text_input("Engineering Query:", placeholder="e.g., how many TV stations in Israel?")
        btn = st.button("🚀 Run System Analysis")

    if btn and user_input:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
        
        with st.spinner("Analyzing Spectrum Data..."):
            try:
                # محرك اكتشاف الدولة والعلم (Detection Engine)
                detected_flag = "🌐"
                adm_code = ""
                
                if "israel" in user_input.lower() or "isr" in user_input.lower():
                    detected_flag, adm_code = FLAGS['ISR'], "ISR"
                elif "egypt" in user_input.lower() or "egy" in user_input.lower():
                    detected_flag, adm_code = FLAGS['EGY'], "EGY"
                elif "saudi" in user_input.lower() or "ars" in user_input.lower():
                    detected_flag, adm_code = FLAGS['ARS'], "ARS"

                # الفلترة الذكية للبيانات بناءً على "نوع الخدمة" و "الدولة"
                filtered_df = df.copy()
                if adm_code:
                    filtered_df = filtered_df[filtered_df['Adm'] == adm_code]
                
                if "tv" in user_input.lower():
                    filtered_df = filtered_df[filtered_df['Service_Type'] == 'Television']
                    service_label = "Television"
                elif "sound" in user_input.lower() or "radio" in user_input.lower():
                    filtered_df = filtered_df[filtered_df['Service_Type'] == 'Sound/Radio']
                    service_label = "Sound/Radio"
                else:
                    service_label = "General Spectrum"

                # توليد التقرير النهائي
                final_count = len(filtered_df)
                report_prompt = f"{ENGINEERING_CONTEXT}\nQuery: {user_input}\nResult: {final_count} entries found.\nFormat: Short engineering statement."
                report_text = model.generate_content(report_prompt).text

                # عرض النتائج بشكل احترافي
                st.markdown(f"<div class='report-box'><h3>{detected_flag} Analysis Report</h3><p>{report_text}</p></div>", unsafe_allow_html=True)

                with col_viz:
                    # رسم بياني مخصص للخدمة المطلوبة فقط
                    fig = px.pie(filtered_df, names='Intent', 
                                 title=f"{service_label} Status for {adm_code if adm_code else 'Global'}",
                                 hole=0.6, color_discrete_sequence=px.colors.sequential.Cyan_r)
                    st.plotly_chart(fig, use_container_width=True)

                # الرد الصوتي
                tts = gTTS(text=report_text, lang='en')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io.getvalue(), format='audio/mp3')

            except Exception as e:
                st.error(f"Logic Layer Error: {e}")

# Trace Log
with st.expander("🛠️ System Trace Log"):
    st.code(f"[LOG] Engine V3.8 Ready\n[GEO] Flag Mapping Active\n[DATA] Filter Context: {user_input if 'user_input' in locals() else 'None'}")
