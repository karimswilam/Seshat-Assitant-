import streamlit as st
import pandas as pd
import io
from gtts import gTTS

# المرجعية الهندسية لأنواع الإخطارات
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type
T01	Sound	VHF Sound
GS1	Sound	Digital Sound
GT1	TV	Digital TV
T02	TV	VHF/UHF TV
""" # كمل باقي الجدول هنا زي ما عملنا

mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

@st.cache_data
def load_and_enrich_data():
    try:
        # القراءة بترميز UTF-8 مع تجربة التحايل على الأخطاء
        df = pd.read_csv("Data.csv", encoding='utf-8')
        
        # أهم سطر: تنظيف أسماء الأعمدة من المسافات المخفية
        df.columns = df.columns.str.strip() 
        
        # التأكد من وجود العمود المطلوب
        if 'Notice Type' not in df.columns:
            st.error(f"⚠️ مش لاقي عمود 'Notice Type'. الأعمدة المتاحة هي: {list(df.columns)}")
            return pd.DataFrame()

        df = pd.merge(df, mapping_df, left_on='Notice Type', right_on='Notice_Type', how='left')
        return df
    except Exception as e:
        st.error(f"❌ Error loading Data.csv: {e}")
        return pd.DataFrame()

# ... باقي كود الـ Dashboard
