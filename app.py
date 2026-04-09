import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# ---------- DMS → Decimal ----------
def dms_to_decimal(dms):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", dms)
        lat, lon = None, None
        for d, m, s, dirc in parts:
            dec = float(d) + float(m)/60 + float(s)/3600
            if dirc in ["S", "W"]:
                dec *= -1
            if dirc in ["N", "S"]:
                lat = dec
            if dirc in ["E", "W"]:
                lon = dec
        return lat, lon
    except:
        return None, None

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ["adm", "station_class", "intent", "notice type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    if "location" in df.columns:
        df["lat"], df["lon"] = zip(
            *df["location"].astype(str).apply(dms_to_decimal)
        )

    # ✅ Service Type Derivation
    df["service"] = df["station_class"].map({
        "BC": "SOUND",
        "BT": "TV"
    })

    return df

df = load_data()

# ---------- SIDEBAR ----------
st.sidebar.title("🎚 Dashboard Filters")
adm_list = sorted(df["adm"].dropna().unique())
selected_adm = st.sidebar.multiselect(
    "Select ADM",
    adm_list,
    default=["EGY"] if "EGY" in adm_list else adm_list[:1]
)

f_df = df[df["adm"].isin(selected_adm)]

# ---------- MAIN ----------
st.title("📡 Seshat Engineering Hub")

# KPIs
c1, c2, c3 = st.columns(3)
c1.metric("ADM Selected", ", ".join(selected_adm))
c2.metric("Total Stations", len(f_df))
c3.metric("Service Types", f_df["service"].nunique())

# ---------- SERVICE SPLIT ----------
st.subheader("🔀 Service Discrimination")
service_counts = f_df["service"].value_counts()
st.bar_chart(service_counts)

# ---------- NOTICE TYPE ----------
st.subheader("📜 Notice Type Distribution")
st.bar_chart(f_df["notice type"].value_counts())

# ---------- VOICE SUMMARY ----------
if len(selected_adm) == 1:
    adm = selected_adm[0]
    tv = len(f_df[f_df["service"] == "TV"])
    sound = len(f_df[f_df["service"] == "SOUND"])
    voice_text = f"إدارة {adm} عندها {tv} محطة تلفزيون و {sound} محطة إذاعة."
else:
    voice_text = (
        f"تم اختيار {len(selected_adm)} إدارات للمقارنة. "
        f"إجمالي المحطات {len(f_df)}."
    )

try:
    audio = io.BytesIO()
    gTTS(voice_text, lang="ar").write_to_fp(audio)
    st.audio(audio.getvalue())
except:
    pass

# ---------- MAP / HEATMAP ----------
map_df = f_df.dropna(subset=["lat", "lon"])
if not map_df.empty:
    st.subheader("🔥 Station Density (Heatmap)")
    m = folium.Map(
        location=[map_df["lat"].mean(), map_df["lon"].mean()],
        zoom_start=5
    )
    HeatMap(map_df[["lat", "lon"]].values.tolist()).add_to(m)
    st_folium(m, width=1100, height=550)
else:
    st.info("No location data available.")
