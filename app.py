import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة والـ API
st.set_page_config(page_title="Seshat AI V3 - Accurate Engine", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant (V3)")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3-flash-preview')

@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# 2. الواجهة
user_input = st.text_input("Ask Seshat:", placeholder="How many ARS recordings are there?")
run_button = st.button("🚀 Analyze Full Dataset")

if run_button and user_input:
    with st.spinner("Calculating via Python Engine..."):
        try:
            # الخطوة الذكية: نطلب من الموديل كتابة كود Pandas للوصول للإجابة
            columns_info = df.columns.tolist()
            
            prompt = (
                f"You are a Data Engineer. Given a DataFrame 'df' with columns: {columns_info}\n"
                f"Write a Python snippet to answer: '{user_input}'\n"
                f"Just output the code, no explanation. Example: df[df['Adm'] == 'ARS'].shape[0]"
            )
            
            # توليد الكود
            code_response = model.generate_content(prompt).text.strip().replace('```python', '').replace('```', '')
            
            # تنفيذ الكود على الداتا الحقيقية (الحل الهندسي للدقة)
            # بنستخدم الـ local context عشان الـ exec يشوف الـ df
            local_vars = {'df': df}
            exec(f"result = {code_response}", {}, local_vars)
            final_result = local_vars['result']

            # صياغة الرد النهائي
            final_prompt = f"The user asked: {user_input}. The calculated result is: {final_result}. Formulate a professional one-sentence engineering response."
            narrative_response = model.generate_content(final_prompt).text

            # عرض النتائج
            st.markdown("### 🤖 Accurate Engineering Response:")
            st.success(narrative_response)
            st.info(f"Verified via Logic: `{code_response}`")

            # صوت الرد
            output_tts = gTTS(text=narrative_response, lang='en')
            audio_out = io.BytesIO()
            output_tts.write_to_fp(audio_out)
            st.audio(audio_out.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Logic Error: {e}. I will try the direct analysis method instead.")
            # Fallback للـ direct analysis لو الكود فشل
            response = model.generate_content(f"Data Sample:\n{df.head(10).to_string()}\nQuestion: {user_input}")
            st.warning(response.text)
