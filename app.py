import streamlit as st  # تأكد إن ده أول سطر عشان ما يظهرش Error 'st'
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# =====================================================
# 1. المرجعية الهندسية (ITU Notice Types Reference)
#
# =====================================================
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Sub_Service	Description
T01	Sound	VHF Sound	Analogue	VHF Sound broadcasting station
T02	TV	VHF/UHF TV	Analogue/Digital	VHF/UHF Television broadcasting station
GS1	Sound	Digital Sound	T-DAB Assignment	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	T-DAB Allotment	Digital sound (T-DAB) allotment
GT1	TV	Digital TV	DVB-T Assignment	Digital television (DVB-T) assignment
GT2	TV	Digital TV	DVB-T Allotment	Digital television (DVB-T) allotment
DS1	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) assignment
DT1	TV	Digital TV	GE06 DVB-T	GE06: Digital television (DVB-T) assignment
TB5	Withdrawal	Suppression	Suppression	Suppressing or withdrawing a notice
"""

mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# =====================================================
# 2. معالجة وتحميل البيانات (Data Handling)
# =====================================================
@st.cache_data
def load_and_enrich_data():
    try:
        # حل مشكلة الـ UTF-8
        try:
            df = pd.read_csv("Data.csv", encoding='utf-8')
        except:
            df = pd.read_csv("Data.csv", encoding='cp1252')
            
        # حل مشكلة الـ KeyError 'Notice Type'
        df.columns = df.columns.str.strip()
        
        # الربط الهندسي
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        
        # استبعاد الانسحابات لضمان دقة الأرقام
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        return df
    except Exception as e:
        st.error(f"خطأ أثناء تحميل البيانات: {e}")
        return pd.DataFrame()

df = load_and_enrich_data()

# =====================================================
# 3. واجهة المستخدم (The Interface)
# =====================================================
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

query = st.text_input("🎙️ اسأل المساعد الهندسي:")

if query and not df.empty:
    # منطق الفلترة (Query Engine)
    q = query.lower()
    f_df = df.copy()
    
    # فلترة الدولة (مثال لمصر والسعودية)
    if 'مصر' in q or 'egy' in q: f_df = f_df[f_df['Adm'] == 'EGY']
    elif 'سعودية' in q or 'ars' in q: f_df = f_df[f_df['Adm'] == 'ARS']
    
    # فلترة الخدمة
    if 'sound' in q or 'إذاعة' in q: f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
    elif 'tv' in q or 'تلفزيون' in q: f_df = f_df[f_df['Broadcasting_Category'] == 'TV']
    
    # عرض النتائج
    count = len(f_df)
    st.success(f"🤖 لقيت {count} محطة مطابقة لطلبك يا هندسة.")
    
    # الرسم البياني
    st.bar_chart(f_df['Service_Type'].value_counts())
    
    # الخريطة (فقط إذا وجدت إحداثيات)
    if 'lat' in f_df.columns and 'lon' in f_df.columns:
        m = folium.Map(location=[f_df['lat'].mean(), f_df['lon'].mean()], zoom_start=5)
        st_folium(m, width=1200, height=500)
    
    st.dataframe(f_df)
