import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# =====================================================
# 1. COUNTRY DETAILS
# =====================================================
COUNTRY_DETAILS = {
    "EGY": {"flag": "🇪🇬", "en": "Egypt", "ar": "جمهورية مصر العربية", "short_ar": "مصر"},
    "ARS": {"flag": "🇸🇦", "en": "Saudi Arabia", "ar": "المملكة العربية السعودية", "short_ar": "السعودية"},
    "UAE": {"flag": "🇦🇪", "en": "United Arab Emirates", "ar": "الإمارات العربية المتحدة", "short_ar": "الإمارات"}
}

# =====================================================
# 2. DMS → Decimal
# =====================================================
def dms_to_decimal(text):
    if pd.isna(text): 
        return None, None

    pattern = r"(\d+)[°\s]+(\d+)[\'\s]+(\d+)[\"\s]*([NSEW])"
    matches = re.findall(pattern, str(text).upper())

    lat = lon = None
    for d, m, s, drc in matches:
        dec = float(d) + float(m)/60 + float(s)/3600
        if drc in ["S", "W"]:
            dec *= -1
        if drc in ["N", "S"]:
            lat = dec
        else:
            lon = dec
    return lat, lon

# =====================================================
# 3. LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = df.columns.str.lower().str.strip()

    for col in ["adm", "station_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"}).fillna("OTHER")

    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])

    return df

df = load_data()

# =====================================================
# 4. NLP ENTITY EXTRACTION
# =====================================================
ADM_MAP = {
    "مصر": "EGY", "egypt": "EGY",
    "السعودية": "ARS", "saudi": "ARS",
    "الإمارات": "UAE", "uae": "UAE"
}

def get_entities(query):
    q = query.lower()
    adms = list({v for k, v in ADM_MAP.items() if k in q})

    service = None
    if any(x in q for x in ["radio", "sound", "إذاعة"]):
        service = "SOUND"
    elif any(x in q for x in ["tv", "تلفزيون"]):
        service = "TV"

    intent = "OVERVIEW"
    if any(x in q for x in ["عدد", "كام"]):
        intent = "COUNT"
    elif any(x in q for x in ["قارن", "فرق"]):
        intent = "COMPARE"

    return adms, service, intent

# =====================================================
# 5. UI
# =====================================================
st.title("📡 Seshat Engineering Voice Assistant")
query = st.text_input("🎙️ اسأل المهندس المساعد:")

if query:
    adms, service, intent = get_entities(query)

    f_df = df.copy()
    if adms:
        f_df = f_df[f_df["adm"].isin(adms)]
    if service:
        f_df = f_df[f_df["service"] == service]

    # ---- FLAGS ----
    if adms:
        cols = st.columns(len(adms))
        for i, a in enumerate(adms):
            info = COUNTRY_DETAILS[a]
            with cols[i]:
                st.markdown(f"### {info['flag']} {info['short_ar']}")
                st.caption(info["ar"])
                st.caption(info["en"])

    # ---- RESPONSE ----
    if intent == "COUNT" and adms:
        parts = []
        for a in adms:
            name = COUNTRY_DETAILS[a]["short_ar"]
            cnt = len(f_df[f_df["adm"] == a])
            parts.append(f"{name} فيها {cnt} محطة")
        response = " و ".join(parts)
    elif intent == "COMPARE" and len(adms) >= 2:
        parts = []
        for a in adms:
            name = COUNTRY_DETAILS[a]["short_ar"]
            cnt = len(f_df[f_df["adm"] == a])
            parts.append(f"{name} ({cnt})")
        response = "مقارنة بين " + " مقابل ".join(parts)
    else:
        response = f"تم العثور على {len(f_df)} محطة."

    st.success(response)

    # ---- AUDIO ----
    try:
        audio = io.BytesIO()
        gTTS(response, lang="ar").write_to_fp(audio)
        st.audio(audio.getvalue())
    except:
        pass

    # ---- MAP ----
    map_df = f_df.dropna(subset=["lat", "lon"]).head(1000)
    if not map_df.empty:
        m = folium.Map(
            location=[map_df.lat.mean(), map_df.lon.mean()],
            zoom_start=5
        )
        cluster = MarkerCluster().add_to(m)

        for _, r in map_df.iterrows():
            folium.Marker(
                [r.lat, r.lon],
                popup=f"ADM: {r.adm}",
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(cluster)

        st_folium(m, height=500)
