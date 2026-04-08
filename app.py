import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - Stable Build", page_icon="📡")
st.title("📡 Seshat: International Coordination Assistant")

# 2. إعداد الـ API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key! Please check Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# مصفوفة احتمالات للموديلات (عشان نكسر الـ 404)
# الترتيب يبدأ بالأحدث للأقدم
model_options = [
    'gemini-1.5-flash', 
    'models/gemini-1.5-flash',
    'gemini-pro', 
    'models/gemini-pro'
]

selected_model = None

# محاولة الاتصال التلقائي
for m_name in model_options:
    try:
        tmp_model = genai.GenerativeModel(m_name)
        # اختبار بسيط جداً للتأكد من الصلاحية
        tmp_model.generate_content("ping") 
        selected_model = tmp_model
        st.sidebar.success(f"✔️ Connected to: {m_name}")
        break
    except Exception:
        continue

# لو كل المحاولات فشلت، هنطلع القائمة المتاحة فعلياً للـ Key ده
if selected_model is None:
    st.error("🚨 Critical Error: All predefined models returned 404.")
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.write("### 🛠️ Action Required")
        st.write("Your API Key only supports these models. Please tell me which one you see:")
        st.code(available_models)
    except Exception as e:
        st.write("Could not even list models. Please check if your API Key is restricted.")
    st.stop()

# 3. تحميل البيانات (2277 سجل)
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv", low_memory=False)

df = load_data()

# 4. الواجهة والتشغيل
user_input = st.text_input("Ask Seshat:", placeholder="How many ARS recordings are there?")

if st.button("🚀 Run Analysis") and user_input:
    with st.spinner("Analyzing..."):
        try:
            # صوت الـ Proxy (Input)
            tts_in = gTTS(text=user_input, lang='en')
            fp_in = io.BytesIO()
            tts_in.write_to_fp(fp_in)
            st.audio(fp_in.getvalue())

            # تجهيز السياق (أول 500 صف للـ Validation)
            context = df.head(500).to_string()
            prompt = f"Data context:\n{context}\n\nQuestion: {user_input}\nAnswer as an Engineer:"

            # الرد من الموديل الذي نجح في الاتصال
            response = selected_model.generate_content(prompt)
            st.markdown(f"### 🤖 Response:\n{response.text}")

            # صوت الـ Proxy (Output)
            tts_out = gTTS(text=response.text, lang='en')
            fp_out = io.BytesIO()
            tts_out.write_to_fp(fp_out)
            st.audio(fp_out.getvalue())
            
        except Exception as e:
            st.error(f"Processing Error: {e}")
