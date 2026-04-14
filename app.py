import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# =====================================================
# 1. المرجعية الفنية (Technical Reference Mapping)
# =====================================================
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Sub_Service	Description
T01	Sound	VHF Sound	Analogue	VHF Sound broadcasting station
T03	Sound	LF/MF Sound	Analogue (R1/3)	LF/MF Sound broadcasting station (R1/3)
T04	Sound	MF Sound	Analogue (R2)	MF Sound broadcasting station (R2)
GS1	Sound	Digital Sound	T-DAB Assignment	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	T-DAB Allotment	Digital sound (T-DAB) allotment
DS1	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) assignment
DS2	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) allotment
T02	TV	VHF/UHF TV	Analogue/Digital	VHF/UHF Television broadcasting station
G02	TV	Analogue TV	Analogue	Analogue television broadcasting assignment
GT1	TV	Digital TV	DVB-T Assignment	Digital television (DVB-T) assignment
GT2	TV	Digital TV	DVB-T Allotment	Digital television (DVB-T) allotment
DT1	TV	Digital TV	GE06 DVB-T	GE06: Digital television (DVB-T) assignment
DT2	TV	Digital TV	GE06 DVB-T	GE06: Digital television (DVB-T) allotment
GA1	Digital_Shared	Digital Allotment	DVB-T/T-DAB	Allotment sub-area for digital broadcasting
GB1	Digital_Shared	Digital Assignment	Non-Plan	Digital assignment (Non-Plan)
TB2	Plan_Compliance	Article 11 Match	FM/TV Plan	Assignment characteristics as in the Plan
TB7	Plan_Compliance	Article 11 Match	LF/MF Plan	Assignment characteristics as in the Plan (LF/MF)
TB1	Administrative	Modification	Unique ID	Modification to Administration unique identifier
TB3	Administrative	Modification	Part B Request	Publication of modification in Part B
TB4	Administrative	Coordination	Update	Updating coordination info
TB5	Withdrawal	Suppression	Suppression	Suppressing or withdrawing a notice
TB9	Withdrawal	Suppression	Suppression (LF/MF)	Suppressing or withdrawing a notice (LF/MF)"""

mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# قاموس الدول (Lookup)
COUNTRY_LOOKUP = {
    "EGY": "مصر", "ARS": "السعودية", "UAE": "الإمارات", 
    "ISR": "إسرائيل", "TUR": "تركيا", "CYP": "قبرص", "JOR": "الأردن"
}

# =====================================================
# 2. تحميل البيانات (Data Loading)
# =====================================================
@st.cache_data
def load_and_enrich_data():
    try:
        # القراءة بترميز UTF-8 ليتوافق مع الحفظ الجديد
        df = pd.read_csv("Data.csv", encoding='utf-8')
        df.columns = [c.strip() for c in df.columns]
        
        # الربط مع القاموس الهندسي
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        
        # استبعاد الـ Withdrawal Notices لضمان دقة الإحصائيات
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        
        return df
    except Exception as e:
        st.error(f"Error loading Data.csv: {e}")
        return pd.DataFrame()

df = load_and_enrich_data()

# =====================================================
# 3. محرك الاستعلام (Query Engine)
# =====================================================
def process_query(query):
    q = query.lower()
    found_adms = [code for code, name in COUNTRY_LOOKUP.items() if name in q or code.lower() in q]
    
    target_cat = None
    if any(x in q for x in ["إذاعة", "صوت", "sound", "radio"]): target_cat = "Sound"
    elif any(x in q for x in ["تلفزيون", "مرئي", "tv"]): target_cat = "TV"
    
    return found_adms, target_cat

# =====================================================
# 4. واجهة المستخدم (The Dashboard)
# =====================================================
st.set_page_config(page_title="Seshat Engineering Hub (V3)", layout="wide")
st.title("📡 Seshat Precision Engineering")

query = st.text_input("🎙️ Engineering Query (مثلاً: كام محطة Sound في مصر؟):")

if query and not df.empty:
    adms, cat = process_query(query)
    f_df = df.copy()
    
    if adms: f_df = f_df[f_df['Adm'].isin(adms)]
    if cat: f_df = f_df[f_df['Broadcasting_Category'] == cat]
    
    # الرد الصوتي والنصي
    count = len(f_df)
    response = f"لقيت {count} محطة مطابقة لطلبك يا هندسة."
    st.success(f"🤖 {response}")
    
    try:
        audio_io = io.BytesIO()
        gTTS(response, lang="ar").write_to_fp(audio_io)
        st.audio(audio_io.getvalue())
    except: pass

    # =====================================================
    # 5. التحليل البصري (Visuals)
    # =====================================================
    st.markdown("### 📊 Visual Context")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribution by Service")
        st.bar_chart(f_df['Service_Type'].value_counts())
    with c2:
        st.subheader("Notice Type Breakdown")
        st.bar_chart(f_df['Notice Type'].value_counts())

    # =====================================================
    # 6. الخريطة (Geographic Mapping)
    # =====================================================
    if 'lat' in f_df.columns and 'lon' in f_df.columns:
        st.markdown("### 📍 Geographic Mapping")
        map_data = f_df.dropna(subset=['lat', 'lon'])
        if not map_data.empty:
            m = folium.Map(location=[map_data['lat'].mean(), map_data['lon'].mean()], zoom_start=5)
            for idx, row in map_data.iterrows():
                folium.Marker(
                    [row['lat'], row['lon']], 
                    popup=f"{row['Site/Allotment Name']} - {row['Notice Type']}"
                ).add_to(m)
            st_folium(m, width=1200, height=500)
    else:
        st.info("ℹ️ الخريطة معطلة لعدم وجود إحداثيات (lat/lon) في الملف حالياً.")

    # جدول البيانات
    st.subheader("📝 Detailed Registry")
    st.dataframe(f_df[['Adm', 'Site/Allotment Name', 'TV Channel / Freq Block', 'Notice Type', 'Sub_Service', 'Description']])
