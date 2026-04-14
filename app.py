import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import speech_recognition as sr
import re

# =====================================================
# 1. الإعدادات والقاموس الهندسي (The Ground Truth)
#
# =====================================================
st.set_page_config(page_title="Seshat AI Engineering Hub", layout="wide")
st.title("📡 Seshat AI Voice Engineering Hub")

TSV_MAPPING = """Notice_Type	Broadcasting_Category	Service_Type	Description
T01	Sound	VHF Sound	Analogue VHF Sound broadcasting station
T02	TV	VHF/UHF TV	Analogue/Digital VHF/UHF TV station
GS1	Sound	Digital Sound	Digital sound (T-DAB) assignment
GS2	Sound	Digital Sound	Digital sound (T-DAB) allotment
GT1	TV	Digital TV	Digital television (DVB-T) assignment
GT2	TV	Digital TV	Digital television (DVB-T) allotment
T03	Sound	LF/MF Sound	LF/MF Sound broadcasting station
T04	Sound	MF Sound	MF Sound broadcasting station
TB5	Withdrawal	Suppression	Suppressing or withdrawing a notice
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# =====================================================
# 2. تحميل البيانات (Bulletproof Loading)
# =====================================================
@st.cache_data
def load_data():
    try:
        # حل مشكلة الـ Encoding والـ BOM
        df = pd.read_csv("Data.csv", encoding='utf-8-sig')
        
        # تنظيف أسماء الأعمدة لمنع KeyError
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        
        # الربط مع القاموس الهندسي
        enriched_df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        return enriched_df
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")
        return pd.DataFrame()

df = load_data()

# =====================================================
# 3. وظائف الصوت (Voice Engine)
# =====================================================
def speech_to_text():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.toast("🎤 سامعك يا هندسة، اتفضل اسأل...")
            audio = r.listen(source, timeout=5)
            text = r.recognize_google(audio, language="ar-EG")
            return text
    except:
        return ""

def text_to_speech(message):
    try:
        tts = gTTS(text=message, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        st.audio(audio_io.getvalue(), format="audio/mp3")
    except:
        st.warning("⚠️ عذراً، مشكلة في الرد الصوتي.")

# =====================================================
# 4. واجهة المستخدم والمنطق (UI & Intelligence)
# =====================================================
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("💬 اكتب سؤالك الهندسي هنا:", placeholder="مثال: كام محطة Sound في مصر؟")
with col2:
    st.write(" ") # موازنة المحاذاة
    if st.button("🎤 اسأل بصوتك"):
        query = speech_to_text()

if query and not df.empty:
    st.info(f"🔍 جاري البحث عن: {query}")
    
    # محرك الفلترة الذكي (Smart Filter)
    q = query.lower()
    f_df = df.copy()
    
    if any(w in q for w in ['مصر', 'egy']): f_df = f_df[f_df['Adm'] == 'EGY']
    if any(w in q for w in ['سعودية', 'ars']): f_df = f_df[f_df['Adm'] == 'ARS']
    if any(w in q for w in ['sound', 'صوت', 'إذاعة']): f_df = f_df[f_df['Broadcasting_Category'] == 'Sound']
    if any(w in q for w in ['tv', 'تلفزيون']): f_df = f_df[f_df['Broadcasting_Category'] == 'TV']
    
    count = len(f_df)
    msg = f"لقيت {count} محطة مطابقة لطلبك يا هندسة."
    st.success(f"🤖 {msg}")
    text_to_speech(msg)

    # الرسوم البيانية
    st.subheader("📊 تحليل هندسي سريع")
    c1, c2 = st.columns(2)
    with c1:
        st.write("حسب نوع الخدمة")
        st.bar_chart(f_df['Service_Type'].value_counts())
    with c2:
        st.write("التوزيع الجغرافي (Adm)")
        st.bar_chart(f_df['Adm'].value_counts())

    # الخريطة (Geographic Plotting)
    # ملاحظة: تأكد إن أعمدة الإحداثيات في ملفك هي 'lat' و 'lon'
    if 'lat' in f_df.columns and 'lon' in f_df.columns:
        st.subheader("🗺️ التوزيع المكاني للمحطات")
        m = folium.Map(location=[f_df['lat'].mean(), f_df['lon'].mean()], zoom_start=5)
        for _, row in f_df.dropna(subset=['lat', 'lon']).iterrows():
            folium.Marker([row['lat'], row['lon']], popup=row['Site/Allotment Name']).add_to(m)
        st_folium(m, width=1000, height=400)

    # عرض البيانات
    st.subheader("📋 سجل البيانات التفصيلي")
    st.dataframe(f_df)
else:
    st.write("💡 جرب تسأل عن محطات الـ Sound في دولة معينة.")
