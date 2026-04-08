import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - Stable", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant")

# 2. إعداد الـ API - المحاولة الأخيرة لفك شفرة الـ 404
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# استخدام المسار الكامل للموديل (وهو الأضمن حالياً)
# جربنا flash و pro، المرة دي هنستخدم المسمى الرسمي للـ API
MODEL_ID = 'models/gemini-1.5-flash-latest'
model = genai.GenerativeModel(model_name=MODEL_ID)

# 3. تحميل البيانات
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# 4. واجهة المستخدم
st.subheader("⌨️ Execute Command")
user_input = st.text_input("Ask Seshat:", placeholder="e.g. How many ARS recordings are there?")
run_button = st.button("🚀 Run Analysis")

if run_button and user_input:
    with st.spinner("Analyzing Data..."):
        try:
            # صوت الـ Proxy (Input)
            input_tts = gTTS(text=user_input, lang='en')
            audio_in = io.BytesIO()
            input_tts.write_to_fp(audio_in)
            st.audio(audio_in.getvalue(), format='audio/mp3')

            # تجهيز السياق (أول 500 صف فقط للسرعة والـ Validation)
            context = df.head(500).to_string()
            prompt = f"System: Expert Spectrum Engineer.\nData:\n{context}\n\nUser Question: {user_input}"

            # مناداة الموديل بالمسار الجديد
            response = model.generate_content(prompt)
            
            # عرض الرد
            st.markdown("### 🤖 Assistant Response:")
            st.success(response.text)
            
            # صوت الـ Proxy (Output)
            output_tts = gTTS(text=response.text, lang='en')
            audio_out = io.BytesIO()
            output_tts.write_to_fp(audio_out)
            st.audio(audio_out.getvalue(), format='audio/mp3')

        except Exception as e:
            # لو لسه الـ 404 موجود، هنعرض رسالة مساعدة إضافية
            st.error(f"Error Detail: {e}")
            if "404" in str(e):
                st.info("💡 Tip: Go to Google AI Studio and check if 'Gemini 1.5 Flash' is available for your API Key.")
