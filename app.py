import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import re

# =====================================================
# 1. المرجعية الفنية (The Ground Truth Mapping)
# =====================================================
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Sub_Service	Description
T01	Sound	VHF Sound	Analogue	VHF Sound station
T03	Sound	LF/MF Sound	Analogue (R1/3)	LF/MF Sound station
T04	Sound	MF Sound	Analogue (R2)	MF Sound station
GS1	Sound	Digital Sound	T-DAB Assignment	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	T-DAB Allotment	Digital sound (T-DAB) allotment
DS1	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) assignment
DS2	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) allotment
T02	TV	VHF/UHF TV	Analogue/Digital	VHF/UHF TV station
G02	TV	Analogue TV	Analogue	Analogue TV assignment
GT1	TV	Digital TV	DVB-T Assignment	Digital TV (DVB-T) assignment
GT2	TV	Digital TV	DVB-T Allotment	Digital TV (DVB-T) allotment
DT1	TV	Digital TV	GE06 DVB-T	GE06: Digital TV (DVB-T) assignment
DT2	TV	Digital TV	GE06 DVB-T	GE06: Digital TV (DVB-T) allotment
GA1	Digital_Shared	Digital Allotment	DVB-T/T-DAB	Digital allotment sub-area
GB1	Digital_Shared	Digital Assignment	Non-Plan	Digital assignment (Non-Plan)
TB2	Plan_Compliance	Article 11 Match	FM/TV Plan	Full technical match (Plan)
TB7	Plan_Compliance	Article 11 Match	LF/MF Plan	Full technical match (LF/MF Plan)
TB5	Withdrawal	Suppression	Suppression	Suppress/Withdraw notice
TB9	Withdrawal	Suppression	Suppression (LF/MF)	Suppress/Withdraw notice (LF/MF)"""

mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# قاموس الدول للعرض
COUNTRY_INFO = {
    "EGY": {"flag": "🇪🇬", "ar": "جمهورية مصر العربية", "short": "مصر"},
    "ARS": {"flag": "🇸🇦", "ar": "المملكة العربية السعودية", "short": "السعودية"},
    "UAE": {"flag": "🇦🇪", "ar": "الإمارات العربية المتحدة", "short": "الإمارات"}
}

# =====================================================
# 2. تحميل ومعالجة البيانات (The Pre-processing)
# =====================================================
@st.cache_data
def load_and_enrich_data():
    try:
        df = pd.read_csv("Data.csv")
        df.columns = [c.strip() for c in df.columns] # تنظيف الـ Headers
        
        # الربط مع القاموس الهندسي
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        
        # فلترة المحطات النشطة فقط (استبعاد الانسحاب)
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        
        return df
    except Exception as e:
        st.error(f"Error loading Data.csv: {e}")
        return pd.DataFrame()

df = load_and_enrich_data()

# =====================================================
# 3. محرك الاستعلام (NLP & Intent Engine)
# =====================================================
def process_query(query):
    q = query.lower()
    found_adms = [code for code, info in COUNTRY_INFO.items() if info['short'] in q or code.lower() in q]
    
    # تحديد نوع الخدمة المطلوبة
    target_cat = None
    if any(x in q for x in ["إذاعة", "صوت", "sound", "radio"]): target_cat = "Sound"
    elif any(x in q for x in ["تلفزيون", "مرئي", "tv"]): target_cat = "TV"
    
    return found_adms, target_cat

# =====================================================
# 4. واجهة المستخدم (The Dashboard)
# =====================================================
st.set_page_config(page_title="Seshat Spectrum Hub", layout="wide")
st.title("📡 Seshat Engineering Hub (V3)")

query = st.text_input("🎙️ اسأل عن الترددات (مثلاً: كام محطة Sound في مصر؟):")

if query and not df.empty:
    adms, cat = process_query(query)
    
    # الفلترة بناءً على الـ Schema المحددة
    f_df = df.copy()
    if adms: f_df = f_df[f_df['Adm'].isin(adms)]
    if cat: f_df = f_df[f_df['Broadcasting_Category'] == cat]
    
    # عرض الأعلام
    if adms:
        cols = st.columns(len(adms))
        for i, adm in enumerate(adms):
            info = COUNTRY_INFO[adm]
            with cols[i]:
                st.metric(label=f"{info['flag']} {info['short']}", value=len(f_df[f_df['Adm'] == adm]))
                st.caption(info['ar'])

    # الرد الصوتي
    count = len(f_df)
    response = f"تم العثور على {count} محطة {cat if cat else ''}."
    if adms:
        res_parts = [f"{COUNTRY_INFO[a]['short']} فيها {len(f_df[f_df['Adm']==a])}" for a in adms]
        response = " و ".join(res_parts) + f" محطة {cat if cat else ''}."
    
    st.success(f"🤖 {response}")
    
    # توليد الصوت
    try:
        audio_io = io.BytesIO()
        gTTS(response, lang="ar").write_to_fp(audio_io)
        st.audio(audio_io.getvalue())
    except: pass

    # العرض البياني (Charts)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 Service Distribution")
        st.bar_chart(f_df['Sub_Service'].value_counts())
    with c2:
        st.subheader("📑 Top Sites")
        st.bar_chart(f_df['Site/Allotment Name'].value_counts().head(10))

    # جدول البيانات التفصيلي
    st.subheader("📝 Detailed Registry View")
    st.dataframe(f_df[['Adm', 'Site/Allotment Name', 'TV Channel / Freq Block', 'Notice Type', 'Sub_Service', 'Description']])
