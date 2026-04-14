import streamlit as st  # السطر ده لازم يفضل رقم 1 عشان نخلص من NameError
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# =====================================================
# 1. المرجعية الفنية (Technical Reference Mapping)
#
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
# 2. تحميل البيانات (Bulletproof Loading)
# =====================================================
@st.cache_data
def load_and_enrich_data():
    try:
        # تجربة القراءة بأكثر من ترميز لحل مشكلة utf-8 codec error
        try:
            df = pd.read_csv("Data.csv", encoding='utf-8-sig') # utf-8-sig بتشيل أي علامات مخفية في أول الملف
        except:
            df = pd.read_csv("Data.csv", encoding='cp1252') # الحل البديل لملفات إكسيل العربية
            
        # حل مشكلة KeyError: 'Notice Type' عن طريق تنظيف أسماء الأعمدة أوتوماتيكياً
        df.columns = [str(c).strip() for c in df.columns]
        
        # التأكد من وجود العمود بالظبط
        target_col = 'Notice Type'
        if target_col not in df.columns:
            st.error(f"⚠️ مش لاقي عمود '{target_col}'. الأعمدة اللي قريتها هي: {list(df.columns)}")
            return pd.DataFrame()

        # الربط مع المرجعية
        df = pd.merge(df, mapping_df, on=target_col, how='left')
        return df
    except Exception as e:
        st.error(f"❌ خطأ غير متوقع: {e}")
        return pd.DataFrame()

# =====================================================
# 3. تشغيل الـ Dashboard
# =====================================================
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

df = load_and_enrich_data()

query = st.text_input("🎙️ اسأل المساعد الهندسي:")

if query and not df.empty:
    q = query.lower()
    f_df = df.copy()
    
    # فلاتر ذكية بسيطة
    if 'مصر' in q or 'egy' in q: f_df = f_df[f_df['Adm'] == 'EGY']
    if 'sound' in q or 'إذاعة' in q: f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
    
    count = len(f_df)
    msg = f"لقيت {count} محطة مطابقة يا هندسة."
    st.success(f"🤖 {msg}")
    
    # الرسم البياني
    st.bar_chart(f_df['Service_Type'].value_counts())
    
    # عرض البيانات
    st.dataframe(f_df)
