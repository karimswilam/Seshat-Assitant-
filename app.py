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
# 1. DMS → Decimal (Robust & Safe)
# =====================================================
def dms_to_decimal(dms):
    if pd.isna(dms) or str(dms).strip() == "":
        return None, None
    try:
        parts = re.findall(
            r"(\d+)[°\s](\d+)[\'\s](\d+)\"?\s*([NSEWnsew])",
            str(dms)
        )
        lat, lon = None, None
        for d, m, s, dirc in parts:
            dec = float(d) + float(m)/60 + float(s)/3600
            if dirc.upper() in ["S", "W"]:
                dec *= -1
            if dirc.upper() in ["N", "S"]:
                lat = dec
            if dirc.upper() in ["E", "W"]:
                lon = dec
        return lat, lon
    except:
        return None, None

# =====================================================
# 2. LOAD & CLEAN (Excel‑Grade)
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ["adm", "station_class", "notice type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    # Service derivation (ONLY source of truth)
    df["service"] = df["station_class"].map({
        "BC": "SOUND",
        "BT": "TV"
    })

    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])

    return df

df = load_data()

# =====================================================
# 3. ENTITY & INTENT EXTRACTION
# =====================================================
ADM_MAP = {
    "egy": "EGY", "egypt": "EGY", "مصر": "EGY",
    "saudi": "ARS", "ksa": "ARS", "السعودية": "ARS",
    "uae": "UAE", "emirates": "UAE", "الإمارات": "UAE"
}

def extract_entities(query):
    q = query.lower()

    adms = list({v for k, v in ADM_MAP.items() if k in q})

    service = None
    if any(x in q for x in ["sound", "radio", "إذاعة", "صوت"]):
        service = "SOUND"
    elif any(x in q for x in ["tv", "تلفزيون", "مرئي"]):
        service = "TV"

    intent = "OVERVIEW"
    if any(x in q for x in ["كام", "عدد", "how many"]):
        intent = "COUNT"
    elif any(x in q for x in ["قارن", "فرق", "compare"]):
        intent = "COMPARE"

