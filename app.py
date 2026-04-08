import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io

# ---------------------------------------------------------
# 1. ENGINEERING BRAIN (The "Identity" and "Knowledge" Layer)
# ---------------------------------------------------------
# ده السر اللي بيخلي الموديل ينسى إنه من جوجل ويتكلم كأنه سيستم خاص بيك
ENGINEERING_CONTEXT = """
You are Seshat AI, a proprietary Spectrum Management & International Coordination Engine.
Your identity is a specialized model developed for spectrum governance and frequency coordination.

STRICT RULES:
1. IDENTITY: Never mention Gemini, Google, or being an AI. If asked, you are 'Seshat AI Core'.
2. MAPPING: 
   - 'Sound', 'Radio', 'Audio' -> Filter by Station_Class: 'BC'
   - 'TV', 'Television', 'Video' -> Filter by Station_Class: 'BT'
   - 'Egypt', 'Masr' -> Filter by Adm: 'EGY'
   - 'Saudi', 'KSA', 'ARS' -> Filter by Adm: 'ARS'
3. RESPONSE STYLE: Professional, technical, and direct. No "Here is the result". Just the facts.
4. LANGUAGE: Respond in the same language style as the user (Arabic/English/Franco).
"""

# ---------------------------------------------------------
# 2. CONFIGURATION & UI
# ---------------------------------------------------------
st.set_page_config(page_title="Seshat AI Core", page_icon="📡", layout="wide")

# إخفاء الـ "Made with Streamlit" وعمل واجهة Dashboard
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.stButton > button { background-color: #002b5b; color: white; height: 3em; border-radius: 10px; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Access Denied: Infrastructure Key Missing.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# ---------------------------------------------------------
# 3. DATA ENGINE
# ---------------------------------------------------------
@st.cache_data
def load_data():
    # تحميل الداتا بنظام الـ Low Memory للتعامل مع المليون صف مستقبلاً
    return pd.read_csv("Data.csv", low_memory=False)

try:
    df = load_data()
except Exception as e:
    st.error(f"Data Connection Error: {e}")
    st.stop()

# ---------------------------------------------------------
# 4. DASHBOARD VIEW
# ---------------------------------------------------------
st.title("📡 Seshat AI: International Coordination Core")
st.caption("Proprietary Spectrum Analysis Engine | Phase 2 Active")

# عرض عدادات احترافية
m1, m2, m3 = st.columns(3)
m1.metric("Database Size", f"{len(df):,}")
m2.metric("Active Admins", df['Adm'].nunique())
m3.metric("Engine Health", "Stable")

st.markdown("---")

# منطقة الاستعلام
query = st.text_input("Engineering Command Center:", placeholder="Ask about specific records, Admins, or Frequencies...")
execute = st.button("🚀 Run System Analysis")

if execute and query:
    with st.spinner("Executing Logic Layer..."):
        try:
            # الخطوة الأولى: توليد كود الاستعلام (الـ Python Logic)
            prompt_logic = f"""
            {ENGINEERING_CONTEXT}
            Data Columns: {df.columns.tolist()}
            User Query: {query}
            Write 1 line of Python code using 'df' to get the numeric answer or result.
            Example: df[(df['Adm']=='EGY') & (df['Station_Class']=='BC')].shape[0]
            Return ONLY the code.
            """
            generated_code = model.generate_content(prompt_logic).text.strip().replace('```python', '').replace('```', '')

            # الخطوة الثانية: التنفيذ الفعلي على الـ DataFrame
            local_scope = {'df': df}
            exec(f"final_val = {generated_code}", {}, local_scope)
            result = local_scope['final_val']

            # الخطوة الثالثة: صياغة التقرير الهندسي النهائي
            prompt_report = f"""
            {ENGINEERING_CONTEXT}
            The user asked: {query}
            The data engine returned: {result}
            Format this into a professional, one-sentence engineering response.
            """
            final_report = model.generate_content(prompt_report).text

            # ---------------------------------------------------------
            # 5. RESULTS DISPLAY
            # ---------------------------------------------------------
            st.markdown("### 🤖 Analysis Report:")
            st.success(final_report)
            
            # عرض الكود "للإبهار" فقط في الـ Expander
            with st.expander("System Trace Log (Logical Verification)"):
                st.code(f"# Logic Path:\n{generated_code}", language='python')

            # الرد الصوتي (Proxy Voice)
            voice_engine = gTTS(text=final_report, lang='en')
            audio_data = io.BytesIO()
            voice_engine.write_to_fp(audio_data)
            st.audio(audio_data.getvalue(), format='audio/mp3')

        except Exception as e:
            st.error(f"Analysis failed to resolve. Please refine the query terminology. (Error: {e})")

# تذييل الصفحة لإعطاء طابع رسمي
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Seshat AI Core v3.1 | Authorized Access Only</p>", unsafe_allow_html=True)
