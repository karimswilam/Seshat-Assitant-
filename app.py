import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# 1. إعدادات الهوية والأعلام
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI", page_icon="📡", layout="wide")

# CSS لتنسيق الواجهة
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .answer-box { background-color: #1a1c23; padding: 20px; border-radius: 10px; border-left: 5px solid #00d4ff; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # قراءة الداتا وتوحيد أسامي الأعمدة بناءً على الصورة اللي بعتها
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    return df

df = load_data()

# --- واجهة المستخدم ---
st.title("📡 Seshat AI: Precision Spectrum Engine")
query = st.text_input("Engineering Query:", placeholder="How many TV stations in Egypt?")

if st.button("🚀 Run Analysis") and query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

    # 2. منطق الفلترة الصارم (بدون تأليف)
    target_adm = None
    if any(x in query.lower() for x in ["egy", "egypt", "مصر"]): target_adm = "EGY"
    elif any(x in query.lower() for x in ["isr", "israel", "إسرائيل"]): target_adm = "ISR"
    
    # تنفيذ الفلترة على الأعمدة الحقيقية
    f_df = df.copy()
    if target_adm:
        f_df = f_df[f_df['adm'] == target_adm]
    
    if "tv" in query.lower():
        f_df = f_df[f_df['station_class'] == 'BT']
    elif "sound" in query.lower() or "radio" in query.lower():
        f_df = f_df[f_df['station_class'] == 'BC']

    # 3. استخراج الإجابة الرقمية
    res_count = len(f_df)
    
    # توجيه الـ AI ليعطي إجابة هندسية قصيرة جداً
    prompt = f"Analyze: {res_count} records found for {target_adm}. Reply in one short technical sentence only."
    ai_response = model.generate_content(prompt).text

    # --- العرض النهائي ---
    st.markdown(f"<div class='answer-box'>{FLAGS.get(target_adm, '🌐')} {ai_response}</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Data Distribution")
        fig = px.pie(f_df, names='intent', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top Locations")
        # عرض أهم المواقع بدل الخريطة المعطلة بسبب نقص الـ lat/long
        if 'location' in f_df.columns:
            loc_counts = f_df['location'].value_counts().head(10)
            st.bar_chart(loc_counts)
