import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# =====================================================
# 1. المرجعية الفنية (Technical Reference Mapping)
#
# =====================================================
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Sub_Service	Description
T01	Sound	VHF Sound	Analogue	VHF Sound broadcasting station
T02	TV	VHF/UHF TV	Analogue/Digital	VHF/UHF Television broadcasting station
GS1	Sound	Digital Sound	T-DAB Assignment	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	T-DAB Allotment	Digital sound (T-DAB) allotment
GT1	TV	Digital TV	DVB-T Assignment	Digital television (DVB-T) assignment
GT2	TV	Digital TV	DVB-T Allotment	Digital television (DVB-T) allotment
T03	Sound	LF/MF Sound	Analogue (R1/3)	LF/MF Sound broadcasting station (R1/3)
T04	Sound	MF Sound	Analogue (R2)	MF Sound broadcasting station (R2)
DS1	Sound	Digital Sound	GE06 T-DAB	GE06: Digital sound (T-DAB) assignment
DT1	TV	Digital TV	GE06 DVB-T	GE06: Digital television (DVB-T) assignment
TB5	Withdrawal	Suppression	Suppression	Suppressing or withdrawing a notice
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# قاموس الدول للربط الذكي
COUNTRY_LOOKUP = {
    "EGY": "مصر", "ARS": "السعودية", "UAE": "الإمارات", 
    "JOR": "الأردن", "TUR": "تركيا", "OMN": "عمان"
}

# =====================================================
# 2. محرك تحميل البيانات (The Engine)
# =====================================================
@st.cache_data
def load_and_clean_data():
    try:
        # القراءة بترميز utf-8-sig لضمان استقرار أسماء الأعمدة
        df = pd.read_csv("Data.csv", encoding='utf-8-sig')
        
        # تنظيف الأعمدة بناءً على تجربة الـ Flags الناجحة
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        
        # الربط مع القاموس الهندسي
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        
        # استبعاد الـ Withdrawal لضمان دقة الإحصائيات
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        return df
    except Exception as e:
        st.error(f"❌ Error during final load: {e}")
        return pd.DataFrame()

# =====================================================
# 3. واجهة المساعد الهندسي (UI & Logic)
# =====================================================
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

df = load_and_clean_data()

if not df.empty:
    query = st.text_input("🎙️ اسأل المساعد الهندسي (مثلاً: كام محطة Sound في السعودية؟):")

    if query:
        q = query.lower()
        f_df = df.copy()
        
        # 1. فلترة الدولة
        found_adm = [code for code, name in COUNTRY_LOOKUP.items() if name in q or code.lower() in q]
        if found_adm:
            f_df = f_df[f_df['Adm'].isin(found_adm)]
        
        # 2. فلترة نوع الخدمة
        if any(word in q for word in ["صوت", "إذاعة", "sound"]):
            f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
        elif any(word in q for word in ["تلفزيون", "مرئي", "tv"]):
            f_df = f_df[f_df['Broadcasting_Category'] == 'TV']
            
        # 3. عرض النتائج
        count = len(f_df)
        response = f"لقيت {count} محطة مطابقة لطلبك يا هندسة."
        st.success(f"🤖 {response}")
        
        # الرد الصوتي
        try:
            audio_io = io.BytesIO()
            gTTS(response, lang="ar").write_to_fp(audio_io)
            st.audio(audio_io.getvalue())
        except: pass

        # 4. الرسوم البيانية
        st.markdown("### 📊 Analysis Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("By Service Type")
            st.bar_chart(f_df['Service_Type'].value_counts())
        with col2:
            st.subheader("By Notice Type")
            st.bar_chart(f_df['Notice Type'].value_counts())

        # 5. الخريطة (Geographical Plotting)
        # ملاحظة: إذا كان الملف لا يحتوي على lat/lon، سنعرض الجدول فقط
        if 'lat' in f_df.columns and 'lon' in f_df.columns:
            st.markdown("### 📍 Station Locations")
            map_df = f_df.dropna(subset=['lat', 'lon'])
            if not map_df.empty:
                m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=5)
                for _, row in map_df.iterrows():
                    folium.Marker(
                        [row['lat'], row['lon']], 
                        popup=f"{row['Site/Allotment Name']} - {row['Notice Type']}"
                    ).add_to(m)
                st_folium(m, width=1200, height=500)

        # 6. الجدول التفصيلي
        st.subheader("📝 Detailed Registry")
        st.dataframe(f_df[['Adm', 'Site/Allotment Name', 'TV Channel / Freq Block', 'Notice Type', 'Service_Type', 'Description']])
else:
    st.warning("⚠️ جاري انتظار تحميل البيانات... تأكد من وجود Data.csv في المسار الصحيح.")
