import streamlit as st  # لازم يكون أول سطر
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# =====================================================
# 1. المرجعية الفنية (Technical Reference Mapping) 
# مستخلصة من وثائق الـ ITU
# =====================================================
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	VHF Sound broadcasting station
T02	TV	VHF/UHF TV	VHF/UHF Television broadcasting station
GS1	Sound	Digital Sound	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	Digital sound (T-DAB) allotment
GT1	TV	Digital TV	Digital television (DVB-T) assignment
GT2	TV	Digital TV	Digital television (DVB-T) allotment
T03	Sound	LF/MF Sound	Notification of LF/MF Sound station
T04	Sound	MF Sound	Notification of MF Sound station
TB5	Withdrawal	Suppression	Suppressing or withdrawing a notice
"""

mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# =====================================================
# 2. تحميل البيانات ومعالجة الأخطاء (Data Loading)
# =====================================================
@st.cache_data
def load_and_enrich_data():
    try:
        # حل مشكلة الـ UTF-8
        try:
            df = pd.read_csv("Data.csv", encoding='utf-8')
        except:
            df = pd.read_csv("Data.csv", encoding='cp1252')
            
        # تنظيف أسماء الأعمدة من أي مسافات مخفية
        df.columns = df.columns.str.strip()
        
        # التأكد من وجود العمود المطلوب
        if 'Notice Type' not in df.columns:
            st.error(f"⚠️ مش لاقي عمود 'Notice Type'. الأعمدة الموجودة هي: {list(df.columns)}")
            return pd.DataFrame()

        # الربط الهندسي بالقاموس
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        
        # استبعاد المحطات الملغية
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        
        return df
    except Exception as e:
        st.error(f"❌ خطأ فني: {e}")
        return pd.DataFrame()

df = load_and_enrich_data()

# =====================================================
# 3. واجهة المساعد الهندسي (UI)
# =====================================================
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

query = st.text_input("🎙️ اسأل المساعد الهندسي (مثلاً: كام محطة Sound في مصر؟):")

if query and not df.empty:
    q = query.lower()
    f_df = df.copy()
    
    # فلترة بسيطة بناءً على النص
    if 'مصر' in q or 'egy' in q: f_df = f_df[f_df['Adm'] == 'EGY']
    elif 'سعودية' in q or 'ars' in q: f_df = f_df[f_df['Adm'] == 'ARS']
    
    if 'sound' in q or 'إذاعة' in q: f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
    elif 'tv' in q or 'تلفزيون' in q: f_df = f_df[f_df['Broadcasting_Category'] == 'TV']
    
    # النتائج
    count = len(f_df)
    msg = f"لقيت {count} محطة مطابقة لطلبك يا هندسة."
    st.success(f"🤖 {msg}")
    
    # الرد الصوتي
    try:
        audio_io = io.BytesIO()
        gTTS(msg, lang="ar").write_to_fp(audio_io)
        st.audio(audio_io.getvalue())
    except: pass

    # العرض البياني
    st.subheader("📊 Service Distribution")
    st.bar_chart(f_df['Service_Type'].value_counts())
    
    # الجدول
    st.subheader("📝 Detailed Registry")
    st.dataframe(f_df)
