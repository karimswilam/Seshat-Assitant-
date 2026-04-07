import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
import tempfile
import os

# 1. إعداد واجهة المستخدم
st.set_page_config(page_title="Seshat AI Assistant", page_icon="📡", layout="wide")
st.title("📡 Seshat: Voice Spectrum Assistant")
st.markdown("---")

# 2. إعدادات الأمان والـ API
# ملحوظة: هنضيف المفتاح ده في إعدادات Streamlit Cloud مش في الكود
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please add the GEMINI_API_KEY to Streamlit Secrets.")

model = genai.GenerativeModel('gemini-1.5-flash')

# 3. تحميل البيانات (تأكد أن اسم الملف Data.csv موجود في نفس الفولدر على GitHub)
@st.cache_data
def load_data():
    try:
        return pd.read_csv("Data.csv")
    except FileNotFoundError:
        st.error("File 'Data.csv' not found. Please upload it to your GitHub repository.")
        return None

df = load_data()

if df is not None:
    st.sidebar.success(f"Loaded {len(df)} records successfully!")
    
    # 4. المساعد الصوتي
    st.subheader("🎤 Ask Seshat (Voice Recognition)")
    st.write("Click the mic, ask your question about the broadcasting data, then stop.")
    
    # تسجيل الصوت
    audio = mic_recorder(
        start_prompt="⏺️ Start Recording",
        stop_prompt="⏹️ Stop Recording",
        key='recorder'
    )

    if audio:
        # عرض ملف الصوت للتأكد
        st.audio(audio['bytes'])
        
        with st.spinner("Analyzing data and generating response..."):
            # تجهيز سياق البيانات (أول 100 سطر كمثال للسرعة)
            data_context = df.head(100).to_string()
            
            # إرسال الطلب لـ Gemini
            prompt = f"""
            You are a Spectrum Management Expert. 
            Answer the user's question based ONLY on this data context:
            {data_context}
            
            User is asking via voice. Be concise and professional.
            """
            
            # إرسال الصوت مباشرة لـ Gemini (Multimodal)
            response = model.generate_content([
                prompt,
                {"mime_type": "audio/wav", "data": audio['bytes']}
            ])
            
            # 5. عرض النتيجة
            st.markdown("### 🤖 Assistant Response:")
            st.info(response.text)
            
            # (إضافة اختيارية) تحويل النص لصوت للرد عليك
            # ملحوظة: دي بتحتاج مكتبة gTTS لو حابب نفعلها في الخطوة الجاية
else:
    st.info("Waiting for Data.csv to be uploaded...")
