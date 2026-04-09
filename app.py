import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# ---------- DMS → Decimal ----------
def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", dms_str)
        lat, lon = None, None

        for d, m, s, direction in parts:
            decimal = float(d) + float(m)/60 + float(s)/3600
            if direction in ["S", "W"]:
                decimal *= -1
            if direction in ["N", "S"]:
                lat = decimal
            if direction in ["E", "W"]:
                lon = decimal

        return lat, lon
    except:
        return None, None

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ["adm", "station_class", "intent", "notice type", "geo area"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    if "location" in df.columns:
        df["lat"], df["lon"] = zip(
            *df["location"].astype(str).apply(dms_to_decimal)
        )

    return df

df = load_data()

# ---------- UI ----------
st.title("📡 Seshat Engineering Hub")
query = st.text_input("🎙️ Ask like an engineer", placeholder="radio stations in egypt")

if query:
    q = query.lower()
    f_df = df.copy()

    if "egy" in q or "masr" in q or "مصر" in q:
        f_df = f_df[f_df["adm"] == "EGY"]
        country_name = "مصر"
    else:
        country_name = "القاعدة كاملة"

    service = "محطات"

    if "radio" in q or "sound" in q or "إذاعة" in q or "bc" in q:
        f_df = f_df[f_df["station_class"] == "BC"]
        service = "إذاعات"
    elif "tv" in q or "bt" in q or "تلفزيون" in q:
        f_df = f_df[f_df["station_class"] == "BT"]
        service = "تلفزيون"

    final_count = len(f_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Stations", final_count)
    c2.metric("Radio (BC)", len(f_df[f_df["station_class"] == "BC"]))
    c3.metric("TV (BT)", len(f_df[f_df["station_class"] == "BT"]))

    if final_count == 0:
        voice_text = "مفيش ولا محطة مطابقة للطلب."
    elif final_count < 100:
        voice_text = f"العدد {final_count} {service} في {country_name}."
    else:
        voice_text = f"فيه حوالي {final_count} {service} في {country_name}."

    try:
        tts = gTTS(voice_text, lang="ar")
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        st.audio(audio.getvalue())
    except:
        st.warning("Voice failed.")

    st.subheader("📊 Station Class Distribution")
    st.bar_chart(f_df["station_class"].value_counts())

    map_df = f_df.dropna(subset=["lat", "lon"]).head(300)

    if not map_df.empty:
        m = folium.Map(
            location=[map_df["lat"].mean(), map_df["lon"].mean()],
            zoom_start=6
        )

        for _, r in map_df.iterrows():
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=4,
                color="blue" if r["station_class"] == "BC" else "red",
                fill=True
            ).add_to(m)

        st_folium(m, width=1000, height=500, key="map")
    else:
        st.info("No valid location data.")
