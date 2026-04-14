import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import speech_recognition as sr # ميزتك القوية

# دمج المرجعية الهندسية الكاملة
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	Analogue VHF Sound station
GS1	Sound	Digital Sound	T-DAB Assignment
GT1	TV	Digital TV	DVB-T Assignment
# ... كمل الباقي من الجدول الكامل
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# دالة التحميل المؤمنة بالـ Flags
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Data.csv", encoding='utf-8-sig') #
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns] #
        return pd.merge(df, mapping_df, on='Notice Type', how='left')
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame()

# ... باقي الـ Logic بتاعك مع إضافة الـ Regex للبحث
