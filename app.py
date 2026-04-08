import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات هندسية للواجهة
st.set_page_config(page_title="Seshat AI - Spectrum Phase 1", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant")
st.markdown("---")

# 2. إعداد الـ API (المخ)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. معالجة البيانات (الـ 5000 صف)
@st.cache_data
def load_spectrum_data():
    # التحميل بطريقة تحافظ على رامات السيرفر
    df = pd.read_csv("Data.csv", low_memory=False)
    return df

df = load_spectrum_data()

# 4. واجهة المستخدم
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("⌨️ Execute Command")
    user_input = st.text_input("Ask Seshat about the frequency sheet:", placeholder="How many ARS recordings are there?")
    run_button = st.button("🚀 Run Analysis")

with col2:
    st.subheader("📊 Sheet Overview")
    st.write(f"Total Records: **{len(df)}**")
    st.write("Target: *International Coordination Validation*")

# 5. منطق التشغيل (Core Logic)
if run_button and user_input:
    with st.spinner("Processing through Proxy Voice..."):
        # أ- توليد صوت الـ Proxy (يمكن استبداله مستقبلاً بـ Custom Voice Model)
        input_tts = gTTS(text=user_input, lang='en')
        audio_in_fp = io.BytesIO()
        input_tts.write_to_fp(audio_in_fp)
        st.audio(audio_in_fp.getvalue(), format='audio/mp3')

        # ب- تحليل البيانات (نبعت الداتا كـ Context)
        # ملاحظة للمستقبل: لو الداتا زادت عن 10 آلاف، هنستخدم Vector Database
        data_summary = df.to_string() 
        full_prompt = f"System: You are an International Coordination Engineer. Use the following data:\n{data_summary}\n\nUser Question: {user_input}"
        
        response = model.generate_content(full_prompt)
        
        # ج- عرض النتيجة
        st.markdown("### 🤖 Assistant Response:")
        st.success(response.text)
        
        # د- رد صوتي (جاهز للتطوير لبصمة صوت محددة)
        output_tts = gTTS(text=response.text, lang='en')
        audio_out_fp = io.BytesIO()
        output_tts.write_to_fp(audio_out_fp)
        st.audio(audio_out_fp.getvalue(), format='audio/mp3')

elif run_button:
    st.warning("Please enter a command first.")

# 6. قسم التطوير المستقبلي (Placeholder for Voice Training)
st.sidebar.markdown("### 🛠️ Future Work")
st.sidebar.info("Phase 2: Voice Fingerprinting & Custom TTS Training for specific Coordination Phrases.")
