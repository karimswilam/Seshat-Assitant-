import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import speech_recognition as sr
import os

# =====================================================

# إعداد الصفحة

# =====================================================

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI Voice Engineering Hub")

# =====================================================

# المرجعية الفنية

# =====================================================

TSV_MAPPING = """Notice_Type\tBroadcasting_Category\tService_Type\tDescription
T01\tSound\tVHF Sound\tVHF Sound broadcasting station
T02\tTV\tVHF/UHF TV\tVHF/UHF Television broadcasting station
GS1\tSound\tDigital Sound\tDigital sound (T-DAB) assignment
GS2\tSound\tDigital Sound\tDigital sound (T-DAB) allotment
GT1\tTV\tDigital TV\tDigital television (DVB-T) assignment
GT2\tTV\tDigital TV\tDigital television (DVB-T) allotment
T03\tSound\tLF/MF Sound\tNotification of LF/MF Sound station
T04\tSound\tMF Sound\tNotification of MF Sound station
TB5\tWithdrawal\tSuppression\tSuppressing or withdrawing a notice
"""
mapping_df = pd.read_csv(io.StringIO(TSV_MAPPING), sep='\t')

# =====================================================

# تحميل البيانات

# =====================================================

@st.cache_data
def load_data():
try:
try:
df = pd.read_csv("Data.csv", encoding='utf-8-sig')
except:
df = pd.read_csv("Data.csv", encoding='cp1252')

```
    df.columns = [str(c).strip() for c in df.columns]

    if 'Notice Type' not in df.columns:
        st.error(f"❌ Column 'Notice Type' not found. Found: {list(df.columns)}")
        return pd.DataFrame()

    df = pd.merge(df, mapping_df, left_on='Notice Type', right_on='Notice_Type', how='left')
    return df

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    return pd.DataFrame()
```

df = load_data()

# =====================================================

# Voice Input

# =====================================================

def speech_to_text():
r = sr.Recognizer()
try:
with sr.Microphone() as source:
st.info("🎤 اتكلم دلوقتي...")
audio = r.listen(source, timeout=5)
text = r.recognize_google(audio, language="ar-EG")
return text
except:
return ""

# =====================================================

# Smart Filter

# =====================================================

def smart_filter(df, query):
q = query.lower()

```
if any(w in q for w in ['egypt', 'مصر', 'egy']):
    df = df[df['Adm'] == 'EGY']

if any(w in q for w in ['tv', 'تلفزيون']):
    df = df[df['Broadcasting_Category'] == 'TV']

if any(w in q for w in ['radio', 'اذاعة', 'إذاعة']):
    df = df[df['Broadcasting_Category'] == 'Sound']

return df
```

# =====================================================

# UI Input

# =====================================================

col1, col2 = st.columns(2)

with col1:
query = st.text_input("💬 اكتب سؤالك:")

with col2:
if st.button("🎤 سجل صوت"):
query = speech_to_text()
st.write("🗣️ قلت:", query)

# =====================================================

# Assistant Logic

# =====================================================

if query and not df.empty:

```
filtered_df = smart_filter(df, query)

count = len(filtered_df)
msg = f"لقيت {count} محطة مطابقة يا هندسة"

st.success(f"🤖 {msg}")

# =================================================
# Voice Output
# =================================================
try:
    tts = gTTS(text=msg, lang='ar')
    tts.save("response.mp3")

    audio_file = open("response.mp3", "rb")
    st.audio(audio_file.read(), format="audio/mp3")

except:
    st.warning("⚠️ الصوت مش اشتغل")

# =================================================
# Charts
# =================================================
st.subheader("📊 تحليل البيانات")

col1, col2 = st.columns(2)

with col1:
    st.write("حسب نوع الخدمة")
    st.bar_chart(filtered_df['Service_Type'].value_counts())

with col2:
    if 'Adm' in filtered_df.columns:
        st.write("حسب الدولة")
        st.bar_chart(filtered_df['Adm'].value_counts())

# =================================================
# Map
# =================================================
if 'Latitude' in filtered_df.columns and 'Longitude' in filtered_df.columns:

    st.subheader("🗺️ الخريطة")

    m = folium.Map(location=[26.8, 30.8], zoom_start=5)

    for _, row in filtered_df.iterrows():
        if pd.notnull(row['Latitude']) and pd.notnull(row['Longitude']):
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                popup=str(row.get('Service_Type', 'N/A'))
            ).add_to(m)

    st_folium(m, width=900)

# =================================================
# Images
# =================================================
if 'Image_URL' in filtered_df.columns:
    st.subheader("🖼️ صور")
    for img in filtered_df['Image_URL'].dropna().head(5):
        st.image(img, width=200)

# =================================================
# Data Table
# =================================================
st.subheader("📄 البيانات")
st.dataframe(filtered_df)
```

else:
st.info("💡 اكتب أو سجل سؤال علشان نبدأ")
