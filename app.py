import streamlit as st
import pandas as pd
import io
from gtts import gTTS

# --- 1. الوعي الهندسي (قاعدة بيانات الخدمات) ---
#
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04'],
    'ADMIN': ['TB1', 'TB2', 'TB3', 'TB4', 'TB5', 'TB6', 'TB7', 'TB8', 'TB9'],
    'DIGITAL_SHARED': ['GA1', 'GB1']
}

# قاموس الوصف التفصيلي للأكواد
NOTICE_MAP = {
    'GS1': 'T-DAB Assignment', 'GS2': 'T-DAB Allotment',
    'DS1': 'GE06 T-DAB Assignment', 'DS2': 'GE06 T-DAB Allotment',
    'GT1': 'DVB-T Assignment', 'GT2': 'DVB-T Allotment',
    'T01': 'VHF Sound (FM)', 'T02': 'VHF/UHF TV',
    'G02': 'Analogue TV Assignment'
}

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide", page_icon="📡")
st.title("📡 Seshat AI - Telecom Professional Mode")

# --- 2. تحميل البيانات وتجهيزها ---
@st.cache_data(ttl=600)
def load_data(file):
    if file:
        try:
            df = pd.read_excel(file)
            df.columns = [str(c).strip() for c in df.columns]
            # تنظيف القيم من المسافات لضمان دقة الفلترة
            for col in ['Adm', 'Notice Type']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            # إضافة الوصف الهندسي لكل سجل
            if 'Notice Type' in df.columns:
                df['Notice_Description'] = df['Notice Type'].map(NOTICE_MAP).fillna("Other Service")
            return df
        except Exception as e:
            st.error(f"❌ Error: {e}")
    return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Excel (Data.xlsx)", type=["xlsx"])
df = load_data(uploaded_file)

# --- 3. واجهة الاستعلام ---
query = st.text_input("💬 اسأل المساعد الهندسي (مثلاً: ksa 3ndha kam DAB records?):")

if query and not df.empty:
    with st.spinner("🔍 جاري تحليل البيانات هندسياً..."):
        q = query.lower()
        f_df = df.copy()

        # أ) فلتر الدولة (دعم الفرانكو)
        countries = {'ARS': ['ars', 'ksa', 'saudi', 'سعودية'], 'EGY': ['egy', 'مصر', 'masr']}
        for code, terms in countries.items():
            if any(t in q for t in terms):
                f_df = f_df[f_df['Adm'] == code]

        # ب) ذكاء تحديد الخدمة (الربط بالجدول الهندسي)
        target_types = []
        if 'dab' in q: target_types.extend(SERVICE_KNOWLEDGE['DAB'])
        if any(w in q for w in ['tv', 'تلفزيون']): target_types.extend(SERVICE_KNOWLEDGE['TV'])
        if any(w in q for w in ['fm', 'إذاعة']): target_types.extend(SERVICE_KNOWLEDGE['FM'])
        
        if target_types:
            f_df = f_df[f_df['Notice Type'].isin(target_types)]

        # ج) التفرقة بين Assignment و Allotment
        if 'assignment' in q or 'تخصيص' in q:
            f_df = f_df[f_df['Notice Type'].str.endswith('1', na=False)]
        elif 'allotment' in q or 'حجز' in q:
            f_df = f_df[f_df['Notice Type'].str.endswith('2', na=False)]

        # --- 4. عرض النتائج (بدون تأليف) ---
        is_count_query = any(w in q for w in ['kam', '3dd', 'count', 'total', 'عدد', 'إجمالي'])
        result_count = len(f_df)

        if is_count_query:
            st.metric("📊 إجمالي السجلات المطابقة فعلياً", result_count)
            
            if result_count > 0:
                # [Anti-Hallucination] استخراج الأنواع الموجودة في الداتا المفلترة فقط
                actual_types = f_df['Notice Type'].unique()
                descriptions = [f"{t} ({NOTICE_MAP.get(t, 'N/A')})" for t in actual_types]
                
                st.info(f"✅ السجلات دي متصنفة في الملف تحت أنواع: {', '.join(descriptions)}")
                
                # صوتي
                try:
                    tts = gTTS(text=f"العدد هو {result_count}", lang='ar')
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io.getvalue(), format="audio/mp3")
                except: pass
            else:
                st.warning("⚠️ لا توجد سجلات مطابقة لهذا البحث في الملف المرفوع.")
        else:
            st.success(f"🤖 عثرت على {result_count} سجل:")
            st.dataframe(f_df.head(100))

        # د) الرسم البياني (دليل بصري)
        if not f_df.empty:
            st.subheader("📊 توزيع أنواع الإشعارات في النتائج")
            st.bar_chart(f_df['Notice Type'].value_counts())

elif not uploaded_file:
    st.info("💡 برجاء رفع ملف البيانات للبدء في التحليل.")
