import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# ----------------- 1. LOAD DATA (تأمين الأعمدة) -----------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        # توحيد أسماء الأعمدة (lower case)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # التأكد من وجود lat و lon بأسماء واضحة
        # لو الإكسيل فيه أسامي تانية، عدلها هنا
        cols_to_fix = ['adm', 'station_class', 'intent', 'notice type', 'geo area']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        # تحويل الإحداثيات لأرقام (مهم جداً للـ dropna)
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = load_data()

# ----------------- 2. UI & Logic (تفكيرك الهندسي) -----------------
st.title("📡 Seshat Engineering Hub")
query = st.text_input("🎙️ Ask like an engineer:", placeholder="e.g. radio stations in egypt")

if query:
    q = query.lower()
    f_df = df.copy()

    # فلترة البلد
    if any(x in q for x in ["egy", "masr", "مصر"]):
        f_df = f_df[f_df['adm'] == 'EGY']
        country_name = "مصر"
    else:
        country_name = "القاعدة كاملة"

    # فلترة الخدمة
    service = "محطات"
    if any(x in q for x in ["radio", "sound", "إذاعة", "bc"]):
        f_df = f_df[f_df['station_class'] == 'BC']
        service = "إذاعات"
    elif any(x in q for x in ["tv", "television", "bt", "تلفزيون"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        service = "تلفزيون"

    final_count = len(f_df)

    # ---------------- 3. KPIs (شغالة تمام) ----------------
    col1, col2, col3 = st.columns(3)
    col1.metric("Selected Stations", final_count)
    col2.metric("Radio (BC)", len(f_df[f_df['station_class'] == 'BC']))
    col3.metric("TV (BT)", len(f_df[f_df['station_class'] == 'BT']))

    # ---------------- 4. Voice & Chart ----------------
    voice_text = f"النتيجة {final_count} {service} في {country_name}."
    try:
        tts = gTTS(text=voice_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        st.audio(audio_fp.getvalue(), format="audio/mp3")
    except: pass

    st.subheader("📊 Station Class Distribution")
    st.bar_chart(f_df['station_class'].value_counts())

    # ---------------- 5. MAP (حل مشكلة KeyError) ----------------
    # التأكد إن الأعمدة موجودة قبل الـ dropna
    if 'lat' in f_df.columns and 'lon' in f_df.columns:
        map_df = f_df.dropna(subset=['lat', 'lon']).head(300)
        
        if not map_df.empty:
            st.subheader("📍 Geospatial View")
            m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=6)
            
            for _, r in map_df.iterrows():
                folium.CircleMarker(
                    location=[r['lat'], r['lon']],
                    radius=5,
                    color='blue' if r['station_class'] == 'BC' else 'red',
                    fill=True,
                    popup=f"ID: {r.get('id', 'N/A')}"
                ).add_to(m)
            
            st_folium(m, width=1000, height=500, key="map_stable")
        else:
            st.warning("No geospatial data (lat/lon) found for this selection.")
    else:
        st.error("Columns 'lat' or 'lon' are missing from the dataset!")
