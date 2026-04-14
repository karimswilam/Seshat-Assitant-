import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# إعداد الصفحة
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI Engineering Hub")

# القاموس الهندسي
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	Analogue VHF Sound station
GS1	Sound	Digital Sound	T-DAB Assignment
GT1	TV	Digital TV	DVB-T Assignment
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# تحميل البيانات المؤمن (اللي اشتغل في الصورة 7010a7)
@st.cache_data
def load_data():
    try:
        # القراءة بترميز utf-8-sig لضمان استقرار أسماء الأعمدة
        df = pd.read_csv("Data.csv", encoding='utf-8-sig')
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        # الربط مع القاموس الهندسي
        return pd.merge(df, mapping_df, on='Notice Type', how='left')
    except Exception as e:
        st.error(f"⚠️ مشكلة في تحميل الملف: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    query = st.text_input("💬 اسأل المساعد (نصياً حالياً لضمان الاستقرار):", placeholder="مثلاً: محطات ARS")
    
    if query:
        q = query.lower()
        f_df = df.copy()
        
        # فلترة بسيطة وسريعة
        if 'ars' in q or 'سعودية' in q: f_df = f_df[f_df['Adm'] == 'ARS']
        if 'egy' in q or 'مصر' in q: f_df = f_df[f_df['Adm'] == 'EGY']
        
        st.success(f"🤖 لقيت {len(f_df)} محطة مطابقة.")
        
        # الرسم البياني
        st.bar_chart(f_df['Notice Type'].value_counts())
        
        # الجدول
        st.dataframe(f_df)
else:
    st.warning("⚠️ جاري انتظار الملف... تأكد من رفع Data.csv")
