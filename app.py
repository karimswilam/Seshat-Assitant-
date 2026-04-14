import streamlit as st
import pandas as pd
import io
from gtts import gTTS

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide", page_icon="📡")
st.title("📡 Seshat AI - Data Analytics Mode")

# --- القاموس الهندسي الموحد ---
mapping_dict = {
    'GS1': 'T-DAB Assignment',
    'GS2': 'T-DAB Allotment',
    'DS1': 'Digital Sound Assignment',
    'DS2': 'Digital Sound Allotment'
}

# --- تحميل البيانات بذكاء ---
@st.cache_data(ttl=600)
def load_data(file):
    try:
        df = pd.read_excel(file)
        # تنظيف أسماء الأعمدة
        df.columns = [str(c).strip() for c in df.columns]
        
        # تنظيف القيم داخل الأعمدة المهمة لمنع أخطاء الفلترة
        for col in ['Adm', 'Notice Type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        if 'Notice Type' in df.columns:
            df['Notice_Description'] = df['Notice Type'].map(mapping_dict)

        return df
    except Exception as e:
        st.error(f"❌ خطأ في قراءة الملف: {e}")
        return pd.DataFrame()

# --- واجهة رفع الملف ---
uploaded_file = st.file_uploader("📂 ارفع ملف الإكسيل (Data.xlsx)", type=["xlsx"])

df = load_data(uploaded_file) if uploaded_file else pd.DataFrame()

# --- محرك البحث والتحليل ---
query = st.text_input(
    "💬 اسأل عن البيانات (مثلاً: ars 3ndha kam gs1?):",
    placeholder="Franko, Arabic, or English..."
)

if query and not df.empty:
    with st.spinner("🔍 جاري التحليل الهندسي..."):
        q = query.lower()
        f_df = df.copy()

        # الفلاتر الذكية
        has_adm = 'Adm' in f_df.columns
        has_notice = 'Notice Type' in f_df.columns

        # 1. فلتر الدول (دعم موسع للفرانكو)
        country_filters = {
            'ARS': ['ars', 'سعودية', 'saudi', 'ksa', 'saudia'],
            'EGY': ['egy', 'مصر', 'egypt', 'masr']
        }

        if has_adm:
            for code, words in country_filters.items():
                if any(w in q for w in words):
                    f_df = f_df[f_df['Adm'] == code]

        # 2. فلتر نوع الإشعار (Notice Type)
        if has_notice:
            for n_type in mapping_dict.keys():
                if n_type.lower() in q:
                    f_df = f_df[f_df['Notice Type'] == n_type]

        # 3. اكتشاف نية السؤال (إحصاء أم عرض)
        is_count_query = any(w in q for w in [
            'kam', '3dd', 'count', 'total', 'كم', 'عدد', 'إجمالي', 'wa7da', 'record'
        ])

        # --- عرض النتائج ---
        if is_count_query:
            result_count = len(f_df)
            st.metric("📊 إجمالي السجلات المطابقة", result_count)
            
            # الرد الصوتي
            try:
                tts_text = f"العدد الإجمالي هو {result_count}"
                tts = gTTS(text=tts_text, lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io.getvalue(), format="audio/mp3")
            except:
                pass 
        else:
            st.success(f"🤖 تم العثور على {len(f_df)} سجل:")
            cols_to_show = [c for c in ['Adm', 'Site/Allotment Name', 'Notice Type', 'Notice_Description'] if c in f_df.columns]
            st.dataframe(f_df[cols_to_show].head(100))

        # --- الرسم البياني الإحصائي ---
        if not f_df.empty and has_notice:
            st.subheader("📊 توزيع أنواع الإشعارات (Notice Types)")
            st.bar_chart(f_df['Notice Type'].value_counts())

elif not uploaded_file:
    st.info("💡 برجاء رفع ملف Data.xlsx أولاً للبدء.")
