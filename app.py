import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - Validation", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant")

# 2. إعداد الـ API - استخدام أسلوب الـ Stable Version
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# الحل الجذري: نستخدم اسم الموديل "gemini-pro" فقط بدون أرقام إصدارات معقدة
# ده الموديل الأكثر استقراراً للـ Text Context حالياً
try:
    model = genai.GenerativeModel('gemini-pro')
except Exception:
    model = genai.GenerativeModel('gemini-1.5-flash')

# 3. تحميل البيانات
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    return df

df = load_data()

# 4. واجهة المستخدم
st.subheader("⌨️ Execute Command")
user_input = st.text_input("Ask Seshat:", placeholder="How many ARS recordings are there?")
run_button = st.button("🚀 Run Analysis")

if run_button and user_input:
    with st.spinner("Analyzing..."):
        try:
            # توليد صوت الـ Proxy (Input)
            input_tts = gTTS(text=user_input, lang='en')
            audio_in = io.BytesIO()
            input_tts.write_to_fp(audio_in)
            st.audio(audio_in.getvalue(), format='audio/mp3')

            # تجهيز البيانات (أول 1500 صف لضمان عدم تجاوز حدود الـ API)
            context = df.head(1500).to_string()
            prompt = f"Data:\n{context}\n\nQuestion: {user_input}\nAnswer as an engineer:"

            # مناداة الموديل
            response = model.generate_content(prompt)
            
            # العرض والرد الصوتي (Output)
            st.markdown("### 🤖 Assistant Response:")
            st.success(response.text)
            
            output_tts = gTTS(text=response.text, lang='en')
            audio_out = io.BytesIO()
            output_tts.write_to_fp(audio_out)
            st.audio(audio_out.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Error: {e}")
            st.info("If you see '404', check if Gemini API is enabled in your Google Cloud Project.")
