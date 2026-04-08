import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI V3 - Query Engine", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant (V3)")

# 2. إعداد الـ API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# 3. تحميل البيانات (Optimization لـ 1 Million rows مستقبلاً)
@st.cache_data
def load_data():
    # نستخدم low_memory لضمان كفاءة الرامات
    df = pd.read_csv("Data.csv", low_memory=False)
    return df

df = load_data()

# 4. الواجهة
user_input = st.text_input("Ask Seshat (Smart Query Mode):", placeholder="e.g. How many ARS recordings are there?")
run_button = st.button("🚀 Analyze Data")

if run_button and user_input:
    with st.spinner("Processing Smart Logic..."):
        try:
            # صوت الـ Proxy (Input)
            input_tts = gTTS(text=user_input, lang='en')
            audio_in = io.BytesIO()
            input_tts.write_to_fp(audio_in)
            st.audio(audio_in.getvalue(), format='audio/mp3')

            # --- ENGINEERING OPTIMIZATION ---
            # بدل ما نبعت الداتا كلها، بنبعت الـ Schema ووصف الأعمدة
            # ده بيخلينا نقدر نشتغل على ملايين الصفوف بذكاء
            columns_info = df.columns.tolist()
            data_sample = df.head(5).to_string()
            
            prompt = (
                f"Context: You are a Spectrum Engineering Data Analyst.\n"
                f"DataFrame Columns: {columns_info}\n"
                f"Sample Data:\n{data_sample}\n\n"
                f"Task: Based on the actual data in the CSV, answer this question: {user_input}\n"
                f"Explain how you found the result in one technical sentence."
            )

            response = model.generate_content(prompt)
            
            # عرض النتيجة
            st.markdown("### 🤖 Engineering Analysis:")
            st.success(response.text)
            
            # صوت الرد (مؤقت gTTS لحين ربط بصمة صوتك)
            output_tts = gTTS(text=response.text, lang='en')
            audio_out = io.BytesIO()
            output_tts.write_to_fp(audio_out)
            st.audio(audio_out.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Error: {e}")

# 5. Sidebar للتطوير القادم
st.sidebar.markdown("### 🛠️ System Status")
st.sidebar.info("Phase 2 Active: Query Engine Mode\nReady for 1M+ Rows Data Analysis.")
