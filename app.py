import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# ----------------- DMS → Decimal FUNCTION -----------------
def dms_to_decimal(dms_str):
    """
    Convert DMS string like:
    042°07'03" E - 16°41'33" N
    to decimal lat, lon
    """
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"?\s*([NSEW])", dms_str)
        lat, lon = None, None

        for d, m, s, direction in parts:
            decimal = float(d) + float(m)/60 + float(s)/3600
            if direction in ['S', 'W']:
                decimal *= -1
            if direction in ['N', 'S']:
                lat = decimal
            if direction in ['E', 'W']:
                lon = decimal

        return lat, lon
    except:
        return None, None


# ----------------- LOAD DATA -----------------
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    # Normalize text columns
    for col in ['adm', 'station_class', 'intent', 'notice type', 'geo area']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    # Convert location → lat / lon
    if 'location' in df.columns:
        lats, lons = [], []
        for loc in df['location']:
            lat, lon = dms_to_decimal(str(loc))
            lats.append(lat)
            lons.append(lon)
        df['lat'] = lats
        df['lon'] = lons

    return df


df = load_data()

# ----------------- UI -----------------
st.title("📡 Seshat Engineering Hub")
query = st.text_input("🎙️ Ask like an engineer:", placeholder="e.g. radio stations in egypt")

if query:
    q = query.lower()
    f_df = df.copy()

    # -------- Country Logic --------
    if any(x in q for x in ["egy", "masr", "مصر"]):
        f_df = f_df[f_df['adm'] == 'EGY']
        country_name = "مصر"
    else:
        country_name = "القاعدة كاملة"

    # -------- Service Logic --------
    service = "محطات"
    if any(x in q for x in ["radio", "sound", "إذاعة", "bc"]):
        f_df = f_df[f_df['station_class'] == 'BC']
        service = "إذاعات"
    elif any(x in q for x in ["tv", "television", "bt", "تلفزيون"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        service = "تلفزيون"

    final_count = len(f_df)

    # ---------------- KPIs ----------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Stations", final_count)
    c2.metric("Radio (BC)", len(f_df[f_df['station_class'] == 'BC']))
    c3.metric("TV (BT)", len(f_df[f_df['station_class'] == 'BT']))

    # ---------------- VOICE ----------------
    if final_count == 0:
        voice_text = "مفيش ولا محطة مطابقة للطلب ده يا هندسة."
    elif final_count < 100:
        voice_text = f"العدد {final_count} {service} في {country_name}."
    else:
        voice_text = f"فيه حوالي {final_count} {service} في {country_name}."

    try:
        tts = gTTS(text=voice_text, lang='ar')
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        st.audio(audio.getvalue(), format="audio/mp3")
    except:
        st.warning("⚠️ Voice output failed.")

    # ---------------- CHART ----------------
    st.subheader("📊 Station Class Distribution")
    st.bar_chart(f_df['station_class'].value_counts())

    # ---------------- MAP ----------------
    map_df = f_df.dropna(subset=['lat', 'lon']).head(300)

    if not map_df.empty:
        st.subheader("📍 Geospatial View")
        m = folium.Map(
            location=[map_df['lat'].mean(), map_df['lon'].mean()],
            zoom_start=6
        )

        for _, r in map_df.iterrows():
            folium.CircleMarker(
                location=[r['lat'], r['lon']],
                radius=4,
                color='blue' if r['station_class'] == 'BC' else 'red',
                fill=True,
                fill_opacity=0.7,
                popup=str(r.get('site name', 'Station'))
            ).add_to(m)

        st_folium(m, width=1000, height=500, key="main_map")
    else:
        st.info("No geographic data available for this selection.")
``
