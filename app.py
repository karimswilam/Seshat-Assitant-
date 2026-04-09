import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# --- 1. تحميل الداتا (إصلاح السطر 38 للأبد) ---
@st.cache_data
def load_data_final():
    try:
        # قراءة الملف بـ low_memory لسرعة الأداء
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # التأمين ضد AttributeError: تحويل كل خلية لنص أولاً
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].map(str).str.upper().str.strip()
        
        # تحويل الإحداثيات لأرقام
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data_final()

# --- 2. واجهة البحث الفوري ---
st.title("📡 Seshat Engineering Hub")
query = st.text_input("Engineering Query (e.g., masr sound):", placeholder="Enter your command here...")

if query:
    q = query.lower()
    
    # فلترة مصر (Local Logic)
    target_adm = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else None
    
    # تنفيذ الفلترة على الداتا
    if target_adm:
        f_df = df[df['adm'] == target_adm]
    else:
        f_df = df
        
    # تحديد نوع الخدمة (Sound vs TV)
    svc = "بث"
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        svc = "تلفزيون"
    elif any(x in q for x in ["sound", "صوت", "إذاعة", "bc"]):
        f_df = f_df[f_df['station_class'] == 'BC']
        svc = "إذاعة"

    # النتيجة النهائية
    final_count = len(f_df)

    # --- 3. العرض (النتائج + الصوت) ---
    st.subheader(f"Total {svc} Stations: {final_count}")
    
    # صوت gTTS سريع ومستقر (مش محتاج Gemini)
    voice_text = f"يا هندسة، الداتا بتقول إن فيه {final_count} محطة {svc} في {'مصر' if target_adm else 'القاعدة'}."
    try:
        tts = gTTS(text=voice_text, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        st.audio(audio_io.getvalue(), format='audio/mp3')
    except:
        st.warning("الصوت فيه مشكلة، بس الأرقام اهي.")

    # --- 4. الخريطة الثابتة ---
    if final_count > 0:
        # فلترة الصفوف اللي فيها إحداثيات بس
        map_df = f_df.dropna(subset=['lat', 'lon'])
        
        if not map_df.empty:
            st.info(f"Showing {min(len(map_df), 500)} locations on map.")
            
            # سنتر الخريطة
            m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=6)
            
            # إضافة الـ Markers (أول 500 للسرعة)
            for _, row in map_df.head(500).iterrows():
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=4,
                    color='blue' if svc=="إذاعة" else 'red',
                    fill=True,
                    popup=f"ID: {row.get('id', 'N/A')}"
                ).add_to(m)
            
            # عرض الخريطة بـ Key ثابت عشان متهنجش
            st_folium(m, width=900, height=500, key="map_stable")
        else:
            st.warning("No geospatial data found for these stations.")
    else:
        st.error("No stations found matching your query.")
