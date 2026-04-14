# ======================================================
# 📡 Seshat AI v5.0 – Multi-Lingual Engineering Engine
# ======================================================
import streamlit as st
import pandas as pd
import os
import time
import re
from gtts import gTTS
import io

# 1. Page Configuration
st.set_page_config(page_title="Seshat AI – Multi-Lingual", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Professional Engineering Analytics")

# 2. THE MASTER DICTIONARY (Training Data for LLM Context)
# دي القائمة الشاملة اللي بتغطي العامية، الفصحى، والفرانكو
COUNTRY_MAP = {
    'EGY': ['egypt', 'masr', 'مصر', 'ام الدنيا', 'eg', 'egy', 'مصرية'],
    'ARS': ['ksa', 'saudi', 'السعودية', 'المملكة', 'سعودية', 'ars', 'saudia'],
    'ISR': ['israel', 'اسرائيل', 'isr', 'الاحتلال'],
    'TUR': ['turkey', 'turkiye', 'تركيا', 'tur', 'اتراك', 'torkia']
}

SERVICE_MAP = {
    'DAB': ['dab', 'داب', 'اذاعة ديجيتال', 'راديو رقمي', 'digital radio', 'digital audio'],
    'TV': ['tv', 'television', 'تليفزيون', 'تلفزيون', 'مرئي', 'شاشات', 'محطات'],
    'FM': ['fm', 'اف ام', 'اذاعة اف ام', 'radio fm'],
    'AM': ['am', 'اي ام', 'اذاعة اي ام']
}

# كلمات السؤال عشان الـ Logic ميتلخبطش (Stop Words & Intents)
INTENT_KEYWORDS = {
    'count': ['how many', 'kam', 'عدد', 'كم', 'كام', 'total', 'اجمالي', 'قد ايه'],
    'show': ['show', 'عرض', 'وريني', 'هات', 'list', 'display']
}

# 3. Enhanced Voice Engine (Multi-Language Support)
def speak(text):
    try:
        # كشف اللغة تلقائياً (عربي أو إنجليزي)
        lang = 'ar' if any('\u0600' <= char <= '\u06FF' for char in text) else 'en'
        tts = gTTS(text=text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp.getvalue(), format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"Voice Error: {e}")

# 4. Data Engine
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    try:
        df = pd.read_excel(target)
        df.columns = [str(c).strip() for c in df.columns]
        if 'Adm' in df.columns: df['Adm'] = df['Adm'].astype(str).str.strip().str.upper()
        if 'Notice Type' in df.columns: df['Notice Type'] = df['Notice Type'].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Database", type=["xlsx"])
df = load_data(uploaded_file)

# 5. The Universal Query Processor (The Heart of the Model)
def process_universal_query(query, df):
    q = query.lower()
    detected_country = None
    detected_service = None
    is_count_request = False

    # أ. الكشف عن الدولة (Mapping Loop)
    for code, keywords in COUNTRY_MAP.items():
        if any(word in q for word in keywords):
            detected_country = code
            break
    
    # ب. الكشف عن الخدمة (Mapping Loop)
    for code, keywords in SERVICE_MAP.items():
        if any(word in q for word in keywords):
            detected_service = code
            break

    # ج. الكشف عن نية السؤال (Count vs Show)
    if any(word in q for word in INTENT_KEYWORDS['count']):
        is_count_request = True

    # د. منطق الفلترة الهندسية
    if detected_country and detected_service:
        # التأكد إن الدولة موجودة في ملف الإكسيل المرفوع فعلياً
        if detected_country in df['Adm'].unique():
            fdf = df[(df['Adm'] == detected_country) & (df['Notice Type'].isin(SERVICE_KNOWLEDGE_BASE[detected_service]))]
            return (fdf, is_count_request, detected_country, detected_service), None
        else:
            return None, f"⚠️ كود الدولة {detected_country} غير موجود في ملف البيانات الحالي."
    
    return None, "🔍 مش فاهم السؤال أوي.. جرب تحدد الدولة والخدمة (مثلاً: عدد الـ DAB في تركيا)"

# قاموس الأكواد التقنية (ITU)
SERVICE_KNOWLEDGE_BASE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

# 6. UI Implementation
if df.empty:
    st.info("قم برفع ملف الـ Excel لبدء التحليل الهندي.")
else:
    user_query = st.text_input("💬 اسأل بأي لغة (عربي، إنجليزي، فرانكو):", placeholder="مثلاً: كم عدد محطات الداب في تركيا؟")

    if user_query:
        start_time = time.time()
        result, error = process_universal_query(user_query, df)
        
        if error:
            st.warning(error)
            speak(error)
        else:
            fdf, is_count, country, service = result
            elapsed = time.time() - start_time
            
            st.subheader("📝 نتيجة التحليل")
            
            if is_count:
                count_val = len(fdf)
                st.metric(label=f"إجمالي سجلات {service} في {country}", value=count_val)
                msg = f"لقيت {count_val} سجل لخدمة {service} في {country}"
                st.success(msg)
                speak(msg)
            else:
                st.write(f"عرض سجلات {service} لـ {country}:")
                st.dataframe(fdf.head(100), use_container_width=True)
                speak(f"تم استخراج البيانات المطلوبة لـ {country}")

            st.caption(f"زمن المعالجة: {elapsed:.4f} ثانية")

# Footer
st.divider()
st.caption("Seshat AI v5.0 | Dynamic Multi-Lingual Support Enabled")
