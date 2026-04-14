import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder # البديل الآمن للـ Cloud

# إعداد الصفحة والقاموس الهندسي
st.set_page_config(page_title="Seshat AI Hub", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

# القاموس الفني من الـ PDF
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	Analogue VHF Sound station
GS1	Sound	Digital Sound	T-DAB Assignment
GT1	TV	Digital TV	DVB-T Assignment
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# تحميل البيانات مع معالجة الـ BOM لضمان عدم حدوث KeyError
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Data.csv", encoding='utf-8-sig')
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        return pd.merge(df, mapping_df, on='Notice Type', how='left')
    except Exception as e:
        st.error(f"⚠️ مشكلة في الملف: {e}")
        return pd.DataFrame()

df = load_data()

# واجهة البحث (Search UI)
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input("💬 اكتب سؤالك (مثلاً: محطات السعودية):")
with col2:
    st.write("🎙️ سجل سؤالك:")
    audio = mic_recorder(start_prompt="Record", stop_prompt="Stop", key='recorder')

# معالجة الطلب
if (query or audio) and not df.empty:
    # ملاحظة: لتحويل صوت الـ mic_recorder لنص أونلاين، بنحتاج API key 
    # حالياً هنركز إن الـ App يفتح ويشتغل بالبحث النصي الأول
    q = query.lower() if query else ""
    f_df = df.copy()
    
    if 'egy' in q or 'مصر' in q: f_df = f_df[f_df['Adm'] == 'EGY']
    
    st.success(f"🤖 لقيت {len(f_df)} محطة يا هندسة.")
    st.dataframe(f_df)

    # الخريطة
    if 'lat' in f_df.columns and not f_df.empty:
        m = folium.Map(location=[f_df['lat'].mean(), f_df['lon'].mean()], zoom_start=5)
        st_folium(m, width=1000, height=400)
