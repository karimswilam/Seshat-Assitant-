import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - V3 Flash", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant (V3)")

# 2. إعداد الـ API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# استخدام أقوى وأحدث موديل متاح في قائمتك
MODEL_ID = 'models/gemini-3-flash-preview'
model = genai.GenerativeModel(model_name=MODEL_ID)

# 3. تحميل البيانات
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# 4. الواجهة
st.subheader("⌨️ Execute Engineering Command")
user_input = st.text_input("Ask Seshat:", placeholder="e.g. How many ARS recordings are there?")
run_button = st.button("🚀 Run Analysis")

if run_button and user_input:
    with st.spinner(f"Analyzing via {MODEL_ID}..."):
        try:
            # 1. صوت الـ Proxy (Input)
            input_tts = gTTS(text=user_input, lang='en')
            audio_in = io.BytesIO()
            input_tts.write_to_fp(audio_in)
            st.audio(audio_in.getvalue(), format='audio/mp3')

            # 2. تجهيز البيانات (بما إن الموديل ده قوي، هنبعت الـ 2277 سجل كلهم)
            data_context = df.to_string()
            prompt = (
                f"Context: You are a professional Spectrum Management Engineer.\n"
                f"Data:\n{data_context}\n\n"
                f"Task: Answer the following question based ONLY on the data provided.\n"
                f"Question: {user_input}"
            )

            # 3. مناداة الموديل
            response = model.generate_content(prompt)
            
            # 4. الرد النصي والصوتي
            st.markdown("### 🤖 Assistant Response:")
            st.success(response.text)
            
            output_tts = gTTS(text=response.text, lang='en')
            audio_out = io.BytesIO()
            output_tts.write_to_fp(audio_out)
            st.audio(audio_out.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Error during execution: {e}")
