import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

# إعداد الصفحة بلمسة احترافية
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide", initial_sidebar_state="collapsed")

# ----------------- 1. ENHANCED DMS → DECIMAL -----------------
def dms_to_decimal(dms_str):
    if pd.isna(dms_str) or str(dms_str).strip() == "":
        return None, None
    try:
        # نمط مطور لاكتشاف الإحداثيات حتى لو الرموز مختلفة
        parts = re.findall(r"(\d+)[°\s](\d+)[\'\s](\d+)\"?\s*([NSEWnsew])", str(dms_str))
        lat, lon = None, None

        for d, m, s, direction in parts:
            decimal = float(d) + float(m)/60 + float(s)/3600
            direction = direction.upper()
            if direction in ['S', 'W']:
                decimal *= -1
            if direction in ['N', 'S']:
                lat = decimal
            if direction in ['E', 'W']:
                lon = decimal
        return lat, lon
    except:
        return None, None

# ----------------- 2. OPTIMIZED LOAD DATA -----------------
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    # توحيد النصوص لسهولة الفلترة
    text_cols = ['adm', 'station_class', 'intent', 'notice type', 'geo area']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    # تحويل الإحداثيات باستخدام Vectorized Approach (أسرع بكتير)
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])

    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

# ----------------- 3. UI & VOICE COMMAND -----------------
st.title("📡 Seshat Engineering Hub")
st.markdown("---")

query = st.text_input("🎙️ Engineering Command Center:", placeholder="e.g. kam m7tet radio fe masr?")

if query:
    q = query.lower()
    f_df = df.copy()

    # Logical Mapping
    is_egypt = any(x in q for x in ["egy", "masr", "مصر", "egypt"])
    is_radio = any(x in q for x in ["radio", "sound", "إذاعة", "bc", "صوت"])
    is_tv = any(x in q for x in ["tv", "television", "bt", "تلفزيون"])

    if is_egypt:
        f_df = f_df[f_df['adm'] == 'EGY']
        country_txt = "مصر"
    else:
        country_txt = "النطاق المتاح"

    if is_radio:
        f_df = f_df[f_df['station_class'] == 'BC']
        service_txt = "إذاعات"
    elif is_tv:
        f_df = f_df[f_df['station_class'] == 'BT']
        service_txt = "تلفزيون"
    else:
        service_txt = "محطات"

    final_count = len(f_df)

    # ---------------- 4. SMART KPIs ----------------
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Count", f"{final_count:,}")
    kpi2.metric("Radio (BC)", f"{len(f_df[f_df['station_class'] == 'BC']):,}")
    kpi3.metric("TV (BT)", f"{len(f_df[f_df['station_class'] == 'BT']):,}")

    # ---------------- 5. DYNAMIC VOICE ----------------
    voice_msg = f"يا هندسة، لقيت {final_count} {service_txt} في {country_txt}." if final_count > 0 else "مفيش داتا مطابقة يا فندم."
    
    with st.expander("🔊 Audio Briefing"):
        try:
            tts = gTTS(text=voice_msg, lang='ar')
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io.getvalue(), format="audio/mp3")
        except:
            st.caption("Audio engine offline.")

    # ---------------- 6. VISUAL ANALYSIS ----------------
    tab1, tab2 = st.tabs(["📍 Geospatial Map", "📊 Statistical Distribution"])

    with tab1:
        map_data = f_df.dropna(subset=['lat', 'lon']).head(500) # زيادة الـ limit لـ 500
        if not map_data.empty:
            m = folium.Map(location=[map_data['lat'].mean(), map_data['lon'].mean()], zoom_start=6, tiles="cartodb positron")
            
            for _, r in map_data.iterrows():
                color = '#1f77b4' if r['station_class'] == 'BC' else '#d62728'
                folium.CircleMarker(
                    location=[r['lat'], r['lon']],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"<b>Site:</b> {r.get('site name', 'N/A')}<br><b>Class:</b> {r['station_class']}"
                ).add_to(m)
            
            st_folium(m, width="100%", height=550, key="seshat_map")
        else:
            st.info("No GPS coordinates available for this subset.")

    with tab2:
        if not f_df.empty:
            st.bar_chart(f_df['station_class'].value_counts())
            if 'adm' in f_df.columns:
                st.write("Top Administrations in selection:")
                st.dataframe(f_df['adm'].value_counts().head(10))
