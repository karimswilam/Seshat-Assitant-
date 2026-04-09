import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Voice Assistant", layout="wide")

# =====================================================
# DMS → Decimal
# =====================================================
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

# =====================================================
# LOAD DATA
# =====================================================
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

    # 🔑 Service derivation (critical)
    df["service"] = df["station_class"].map({
        "BC": "SOUND",
        "BT": "TV"
    })

    return df

df = load_data()

# =====================================================
# INTENT & ENTITY EXTRACTION
# =====================================================
ADM_MAP = {
    "egy": "EGY", "egypt": "EGY", "مصر": "EGY",
    "saudi": "ARS", "ksa": "ARS", "السعودية": "ARS"
}

def detect_intent(q):
    q = q.lower()
    if "قارن" in q or "compare" in q:
        return "COMPARE"
    if "كام" in q or "how many" in q:
        return "COUNT"
    return "OVERVIEW"

def extract_adms(q):
    found = []
    for k, v in ADM_MAP.items():
        if k in q.lower():
            found.append(v)
    return list(set(found))

def extract_service(q):
    q = q.lower()
    if "tv" in q or "تلفزيون" in q:
        return "TV"
    if "sound" in q or "radio" in q or "إذاعة" in q:
        return "SOUND"
    return None

# =====================================================
# UI
# =====================================================
st.title("🗣️ Seshat Engineering Voice Assistant")

query = st.text_input(
    "🎙️ اكتب سؤالك كأنك بتكلم مهندس:",
    placeholder="مثال: قارنلي مصر والسعودية في الإذاعات"
)

# =====================================================
# MAIN LOGIC
# =====================================================
if query:
    intent = detect_intent(query)
    adms = extract_adms(query)
    service = extract_service(query)

    result_df = df.copy()

    if adms:
        result_df = result_df[result_df["adm"].isin(adms)]

    if service:
        result_df = result_df[result_df["service"] == service]

    # ================= RESPONSE =================
    if intent == "COUNT" and adms and service:
        counts = []
        for adm in adms:
            c = len(df[(df["adm"] == adm) & (df["service"] == service)])
            counts.append(f"{adm} عندها {c}")

        response_text = "، ".join(counts) + f" محطة {service.lower()}."

    elif intent == "COMPARE" and len(adms) == 2 and service:
        a, b = adms
        ca = len(df[(df["adm"] == a) & (df["service"] == service)])
        cb = len(df[(df["adm"] == b) & (df["service"] == service)])

        response_text = (
            f"مقارنة الإذاعات: "
            f"{a} عندها {ca} محطة، "
            f"بينما {b} عندها {cb} محطة."
        )

    elif adms and service:
        response_text = f"تم عرض محطات {service.lower()} الخاصة بـ {' و '.join(adms)}."

    else:
        response_text = f"عدد المحطات المختارة {len(result_df)}."

    # ================= VOICE OUTPUT =================
    try:
        audio = io.BytesIO()
        gTTS(response_text, lang="ar").write_to_fp(audio)
        st.audio(audio.getvalue())
    except:
        st.warning("Voice synthesis failed")

    st.success(response_text)

    # ================= VISUALS (CONTEXTUAL) =================
    st.subheader("📊 Visual Context")

    col1, col2 = st.columns(2)

    with col1:
        st.bar_chart(result_df["service"].value_counts())

    with col2:
        if "notice type" in result_df.columns:
            st.bar_chart(result_df["notice type"].value_counts())

    # ================= MAP / HEATMAP =================
    map_df = result_df.dropna(subset=["lat", "lon"])

    if not map_df.empty:
        st.subheader("🔥 Geographic Density")
        m = folium.Map(
            location=[map_df["lat"].mean(), map_df["lon"].mean()],
            zoom_start=5
        )
        HeatMap(map_df[["lat", "lon"]].values.tolist(), radius=25).add_to(m)
        st_folium(m, width=1100, height=550)
