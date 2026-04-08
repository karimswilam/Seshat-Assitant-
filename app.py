import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Seshat AI - Spectrum Phase 1", page_icon="📡", layout="wide")
st.title("📡 Seshat: International Coordination Assistant")
st.markdown("---")

# 2. إعداد الـ API Key والموديل
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Missing API Key! Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# الحل النهائي لمشكلة الـ 404: تجربة المسار الكامل للموديل
# جربنا 'gemini-1.5-flash' وفشل، هنستخدم 'models/gemini-1.5-pro' كأضمن نسخة مستقرة
try:
    model = genai.GenerativeModel('models/gemini-1.5-pro')
except:
    model = genai.GenerativeModel('gemini-1.5-pro')

# 3. معالجة البيانات (2277 سجل كما ظهر في الـ Logs)
@st.cache_data
def load_spectrum_data():
    try:
        # قراءة الملف بـ low_memory لضمان السرعة
        df = pd.read_csv("Data.csv", low_memory=False)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

df = load_spectrum_data()

# 4. واجهة المستخدم
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("⌨️ Execute Command")
    user_input = st.text_input("Ask Seshat about the frequency sheet:", 
                                placeholder="How many ARS recordings are there?")
    run_button = st.button("🚀 Run Analysis")

with col2:
    if df is not None:
        st.subheader("📊 Sheet Overview")
        st.write(f"Total Records in File: **{len(df)}**")
        st.write("Status: **System Online & Ready**")
    else:
        st.error("Data.csv file not found.")

# 5. منطق التشغيل (Core Logic)
if run_button and user_input and df is not None:
    with st.spinner("Analyzing Spectrum Data..."):
        try:
            # صوت الـ Proxy كـ Input (لحماية بصمة صوتك)
            input_tts = gTTS(text=user_input, lang='en')
            audio_in_fp = io.BytesIO()
            input_tts.write_to_fp(audio_in_fp)
            st.audio(audio_in_fp.getvalue(), format='audio/mp3')

            # إرسال البيانات كاملة لـ Gemini
            # بما إنهم حوالي 2200 سجل، Gemini Pro يقدر يستوعبهم كلهم بسهولة
            data_context = df.to_string()
            
            full_prompt = (
                f"You are an International Coordination Engineer. Use this spectrum data:\n\n"
                f"{data_context}\n\n"
                f"User Question: {user_input}\n"
                f"Provide a professional engineering answer."
            )
            
            # طلب الرد
            response = model.generate_content(full_prompt)
            
            # عرض الرد الصوتي والنصي
            st.markdown("### 🤖 Assistant Response:")
            st.success(response.text)
            
            # صوت الـ Proxy كـ Output
            output_tts = gTTS(text=response.text, lang='en')
            audio_out_fp = io.BytesIO()
            output_tts.write_to_fp(audio_out_fp)
            st.audio(audio_out_fp.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Processing Error: {e}")
            st.info("Try checking your API usage limits in Google AI Studio.")

# 6. Roadmap
st.sidebar.markdown("### 🛠️ Roadmap")
st.sidebar.info("Phase 1: Validation (Current)\nPhase 2: Custom Voice Integration\nPhase 3: Automated Coordination Reporting")
