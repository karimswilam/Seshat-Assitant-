import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS

# --- الإعدادات الفنية للهوية البصرية ---
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide", page_icon="📡")
st.title("📡 Seshat Precision Engineering Hub")

# --- القاموس الهندسي لفك شفرات الـ Notice Type ---
#
TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	Analogue VHF Sound station
GS1	Sound	Digital Sound	Digital sound (T-DAB) assignment
GT1	TV	Digital TV	Digital television (DVB-T) assignment
T02	TV	VHF/UHF TV	Analogue/Digital VHF/UHF TV station
GS2	Sound	Digital Sound	Digital sound (T-DAB) allotment
GT2	TV	Digital TV	Digital television (DVB-T) allotment
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# --- دالة تحميل البيانات من إكسيل (الأكثر استقراراً) ---
@st.cache_data
def load_data():
    try:
        # قراءة ملف الإكسيل الجديد
        df = pd.read_excel("Data.xlsx") 
        
        # تنظيف أسماء الأعمدة لضمان مطابقتها
        df.columns = [str(c).strip() for c in df.columns]
        
        # الربط مع القاموس الهندسي
        if 'Notice Type' in df.columns:
            enriched_df = pd.merge(df, mapping_df, left_on='Notice Type', right_on='Notice_Type', how='left')
            return enriched_df
        else:
            st.error("❌ عمود 'Notice Type' غير موجود في ملف الإكسيل!")
            return df
    except Exception as e:
        st.error(f"❌ خطأ فني أثناء تحميل البيانات: {e}")
        return pd.DataFrame()

df = load_data()

# --- محرك البحث والذكاء الاصطناعي المبسط ---
if not df.empty:
    query = st.text_input("💬 اسأل المساعد الهندسي (مثلاً: محطات التلفزيون في مصر):")
    
    if query:
        q = query.lower()
        f_df = df.copy()
        
        # منطق الفلترة (Filtering Logic)
        if any(w in q for w in ['مصر', 'egy']): f_df = f_df[f_df['Adm'] == 'EGY']
        if any(w in q for w in ['سعودية', 'ars']): f_df = f_df[f_df['Adm'] == 'ARS']
        if any(w in q for w in ['تلفزيون', 'tv']): f_df = f_df[f_df['Broadcasting_Category'] == 'TV']
        if any(w in q for w in ['صوت', 'sound', 'إذاعة']): f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
        
        st.success(f"🤖 لقيتلك {len(f_df)} سجل هندسي مطابق يا هندسة.")
        
        # الرد الصوتي (Audio Response)
        tts_msg = f"تم العثور على {len(f_df)} محطة."
        tts = gTTS(text=tts_msg, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        st.audio(audio_io.getvalue(), format="audio/mp3")

        # عرض النتائج في خريطة وجدول
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📋 تفاصيل البيانات")
            st.dataframe(f_df[['Adm', 'Site/Allotment Name', 'Notice Type', 'Service_Type', 'Description']])
        
        with col2:
            st.subheader("📊 توزيع الخدمات")
            st.bar_chart(f_df['Service_Type'].value_counts())

        # إضافة الخريطة في حالة وجود إحداثيات (لو متوفرة في الملف)
        if 'lat' in f_df.columns and 'lon' in f_df.columns:
            st.subheader("🗺️ التوزيع الجغرافي للمحطات")
            m = folium.Map(location=[f_df['lat'].mean(), f_df['lon'].mean()], zoom_start=5)
            for _, row in f_df.dropna(subset=['lat', 'lon']).head(100).iterrows():
                folium.Marker([row['lat'], row['lon']], popup=row['Site/Allotment Name']).add_to(m)
            st_folium(m, width=1000, height=400)
else:
    st.info("💡 في انتظار رفع ملف Data.xlsx لبدء التحليل.")
