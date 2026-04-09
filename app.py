import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Core Engine", layout="wide")

# --- 1. محرك البيانات (Pandas Only - No Gemini here) ---
@st.cache_data
def load_and_clean_data():
    try:
        # تحميل الملف مباشرة وبسرعة
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # حل مشكلة الـ AttributeError نهائياً (السطر 38)
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except:
        return pd.DataFrame()

df = load_and_clean_data()

# --- 2. واجهة المستخدم ---
st.title("📡 Seshat Precision Dashboard")
query = st.text_input("Engineering Command:", placeholder="e.g., مصر فيها كام محطة صوت؟")

if st.button("🚀 Run Analysis") and query:
    q = query.lower()
    
    # فلترة البيانات برمجياً (مش بالذكاء الاصطناعي)
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else None
    
    # تنفيذ الفلترة
    results_df = df.copy()
    if target:
        results_df = results_df[results_df['adm'] == target]
    
    # تحديد نوع الخدمة (Sound vs TV)
    is_tv = any(x in q for x in ["tv", "تلفزيون", "bt"])
    is_sound = any(x in q for x in ["sound", "صوت", "إذاعة", "bc"])
    
    if is_tv: results_df = results_df[results_df['station_class'] == 'BT']
    if is_sound: results_df = results_df[results_df['station_class'] == 'BC']

    # --- 3. العرض اللحظي ---
    count = len(results_df)
    st.metric(label=f"Total Records Found ({target if target else 'Global'})", value=count)
    
    # عرض الخريطة فوراً
    if count > 0 and 'lat' in results_df.columns and 'lon' in results_df.columns:
        st.subheader("📍 Geospatial Trace")
        # تنظيف الإحداثيات
        map_df = results_df.dropna(subset=['lat', 'lon'])
        if not map_df.empty:
            m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=5)
            for _, row in map_df.head(100).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=5, color='cyan', fill=True).add_to(m)
            st_folium(m, width=700, height=450, key="main_map")
    else:
        st.warning("No coordinates found for this selection.")

    # --- 4. الصوت (باستخدام gTTS البسيط - أسرع وأضمن) ---
    response_text = f"يا هندسة، لقينا {count} محطة {'تلفزيون' if is_tv else 'إذاعة' if is_sound else ''} لـ {target if target else 'الكل'}."
    tts = gTTS(text=response_text, lang='ar')
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    st.audio(audio_io.getvalue(), format='audio/mp3')
