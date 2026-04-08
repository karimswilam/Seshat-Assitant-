import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة والتصميم
st.set_page_config(page_title="Seshat AI - Spectrum Phase 1", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant")
st.markdown("---")

# 2. إعداد الـ API Key والموديل
# تأكد من وضع المفتاح في Secrets بـ Streamlit تحت اسم GEMINI_API_KEY
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key! Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# استخدام نسخة مستقرة لضمان عدم حدوث NotFound Error
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. معالجة البيانات (الـ 5000 صف)
@st.cache_data
def load_spectrum_data():
    try:
        # تحميل البيانات مع معالجة الأنواع لتقليل استهلاك الذاكرة
        df = pd.read_csv("Data.csv", low_memory=False)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

df = load_spectrum_data()

# 4. واجهة المستخدم (UI Layout)
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("⌨️ Execute Command")
    user_input = st.text_input("Ask Seshat about the frequency sheet:", 
                                placeholder="e.g., How many ARS recordings are there?")
    run_button = st.button("🚀 Run Analysis")

with col2:
    if df is not None:
        st.subheader("📊 Sheet Overview")
        st.write(f"Total Records in File: **{len(df)}**")
        st.write("Status: **Ready for Validation**")
    else:
        st.error("Data file not found or corrupted.")

# 5. منطق التشغيل (Core Logic)
if run_button and user_input and df is not None:
    with st.spinner("Processing Proxy Voice & Data..."):
        try:
            # أ- توليد صوت الـ Proxy (مدخلات المستخدم)
            # تمهيداً للمستقبل: هنا يمكن استبدال gTTS بموديل بصمة صوتك
            input_tts = gTTS(text=user_input, lang='en')
            audio_in_fp = io.BytesIO()
            input_tts.write_to_fp(audio_in_fp)
            st.audio(audio_in_fp.getvalue(), format='audio/mp3')

            # ب- تجهيز السياق (Context)
            # سنرسل أول 1000 صف للـ Validation لضمان استقرار الـ API
            data_context = df.head(1000).to_string()
            
            full_prompt = (
                f"You are an expert International Coordination Engineer. "
                f"Analyze the following spectrum data (first 1000 rows):\n\n"
                f"{data_context}\n\n"
                f"User Question: {user_input}\n"
                f"Please provide a precise, engineering-focused answer."
            )
            
            # ج- طلب الرد من Gemini
            response = model.generate_content(full_prompt)
            
            # د- عرض وتحويل الرد لصوت
            st.markdown("### 🤖 Assistant Response:")
            st.success(response.text)
            
            # توليد صوت الرد (مخرج المساعد)
            output_tts = gTTS(text=response.text, lang='en')
            audio_out_fp = io.BytesIO()
            output_tts.write_to_fp(audio_out_fp)
            st.audio(audio_out_fp.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.info("Check if your API Key is valid and active in Google AI Studio.")

# 6. قسم التطوير المستقبلي
st.sidebar.markdown("### 🛠️ Roadmap")
st.sidebar.info("Phase 1: Validation (Current)\nPhase 2: Custom Voice Training\nPhase 3: Full ITU Database RAG")
