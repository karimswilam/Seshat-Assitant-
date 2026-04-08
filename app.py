import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# 1. إعدادات الواجهة
st.set_page_config(page_title="Seshat Proxy-Voice", page_icon="🛡️")
st.title("🛡️ Seshat: Proxy-Voice Spectrum Assistant")

# 2. إعداد الـ API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. تحميل البيانات
@st.cache_data
def load_data():
    return pd.read_csv("Data.csv")

df = load_data()

# 4. واجهة كتابة الأوامر (Text-to-Voice Proxy)
st.subheader("⌨️ Write your command (Proxy Voice Mode)")
user_text_command = st.text_input("Enter your request for the spectrum data:", placeholder="e.g. Find all Turkish FM stations...")

if st.button("🚀 Execute via Proxy Voice"):
    if user_text_command:
        with st.spinner("Generating Proxy Voice and fetching response..."):
            # أ- تحويل النص لصوت AI (Proxy Voice)
            tts = gTTS(text=user_text_command, lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_bytes = audio_fp.getvalue()
            
            # ب- عرض الصوت المستعار ليك عشان تسمعه
            st.audio(audio_bytes, format='audio/mp3')
            
            # ج- إرسال ملف الصوت لـ Gemini (كده Gemini بيسمع صوت الـ AI مش صوتك)
            data_context = df.head(100).to_string()
            prompt = f"Analyze the following spectrum data context and answer the user's voice command: \n{data_context}"
            
            response = model.generate_content([
                prompt,
                {"mime_type": "audio/mp3", "data": audio_bytes}
            ])
            
            # د- عرض الرد النصي من Gemini
            st.markdown("### 🤖 Assistant Response:")
            st.info(response.text)
            
            # هـ- (اختياري) تحويل رد Gemini نفسه لصوت عشان يرد عليك
            res_tts = gTTS(text=response.text, lang='en')
            res_audio_fp = io.BytesIO()
            res_tts.write_to_fp(res_audio_fp)
            st.audio(res_audio_fp.getvalue(), format='audio/mp3')
    else:
        st.warning("Please enter a command first.")
