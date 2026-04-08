import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - Stable", page_icon="📡")
st.title("📡 Seshat: International Coordination Assistant")

# 2. إعداد الـ API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# مصفوفة احتمالات للموديلات (عشان نكسر الـ 404)
model_names = [
    'gemini-1.5-flash', 
    'gemini-pro', 
    'models/gemini-1.5-pro-latest',
    'models/gemini-pro'
]

model = None
for name in model_names:
    try:
        model = genai.GenerativeModel(name)
        # تجربة وهمية للتأكد إن الموديل شغال
        model.generate_content("test") 
        st.sidebar.success(f"Connected to: {name}")
        break
    except:
        continue

if model is None:
    st.error("All models failed. Please check your API Key permissions.")
    # كود لإظهار الموديلات المتاحة ليك فعلياً (للتصحيح)
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    st.write("Available models for you:", available_models)
    st.stop()

# 3. تحميل البيانات
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# 4. الواجهة والتشغيل
user_input = st.text_input("Ask Seshat:", placeholder="How many ARS recordings are there?")

if st.button("🚀 Run Analysis") and user_input:
    with st.spinner("Analyzing..."):
        try:
            # Proxy Voice Input
            tts_in = gTTS(text=user_input, lang='en')
            fp_in = io.BytesIO()
            tts_in.write_to_fp(fp_in)
            st.audio(fp_in.getvalue())

            # تجهيز السياق (Context)
            context = df.head(500).to_string()
            prompt = f"Data context:\n{context}\n\nQuestion: {user_input}"

            # الرد
            response = model.generate_content(prompt)
            st.success(response.text)

            # Proxy Voice Output
            tts_out = gTTS(text=response.text, lang='en')
            fp_out = io.BytesIO()
            tts_out.write_to_fp(fp_out)
            st.audio(fp_out.getvalue())
            
        except Exception as e:
            st.error(f"Error: {e}")
