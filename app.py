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
# 1. ENHANCED COUNTRY DATA
# =====================================================
COUNTRY_DETAILS = {
    "EGY": {"flag": "🇪🇬", "en": "Egypt", "ar": "جمهورية مصر العربية", "short_ar": "مصر"},
    "ARS": {"flag": "🇸🇦", "en": "Saudi Arabia", "ar": "المملكة العربية السعودية", "short_ar": "السعودية"},
    "UAE": {"flag": "🇦🇪", "en": "United Arab Emirates", "ar": "الإمارات العربية المتحدة", "short_ar": "الإمارات"}
}

# =====================================================
# 2. ROBUST DMS → DECIMAL
# =====================================================
def dms_to_decimal(text):
    if pd.isna(text) or str(text).strip() == "": return None, None
    try:
        # Regex مرن جداً لاقتناص الأرقام والاتجاهات مهما كان شكل الرموز
        matches = re.findall(r"(\d+)[°\s]+(\d+)[\'\s]+(\d+)[\"\s]*([NSEW])", str(text).upper())
        lat = lon = None
        for d, m, s, drc in matches:
            dec = float(d) + float(m)/60 + float(s)/3600
            if drc in ["S", "W"]: dec *= -1
            if drc in ["N", "S"]: lat = dec
            else: lon = dec
        return lat, lon
    except: return None, None

# =====================================================
# 3. HIGH-PRECISION LOAD
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = df.columns.str.lower().str.strip()
    
    # تنظيف شامل للداتا
    for col in ["adm", "station_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            
    # توحيد مسميات الخدمة
    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"}).fillna("OTHER")
    
    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])
    return df

df = load_data()

# =====================================================
# 4. INTENT & ENTITY (The NLP Engine)
# =====================================================
ADM_MAP = {"مصر": "EGY", "egypt": "EGY", "سعودي": "ARS", "saudi": "ARS", "إمارات": "UAE", "uae": "UAE"}

def get_entities(query):
    q = query.lower()
    adms = list({v for k, v in ADM_MAP.items() if k in q})
    service = "SOUND" if any(x in q for x in ["radio", "sound", "إذاعة", "صوت"]) else "TV" if any(x in q for x in ["tv", "تلفزيون", "مرئي"]) else None
    intent = "COUNT" if any(x in q for x in ["عدد", "كام"]) else "COMPARE" if any(x in q for x in ["قارن", "فرق"]) else "OVERVIEW"
    return adms, service, intent

# =====================================================
# 5. UI DESIGN
# =====================================================
st.title("📡 Seshat Engineering Assistant")
st.markdown("---")

query = st.text_input("🎙️ اسأل عن محطات البث (مثلاً: قارن مصر والسعودية في الإذاعات):")

if query:
    adms, service, intent = get_entities(query)
    
    # الفلترة (Single Source of Truth)
    f_df = df.copy()
    if adms: f_df = f_df[f_df["adm"].isin(adms)]
    if service: f_df = f_df[f_df["service"] == service]

    # عرض الأعلام في Container منفصل
    if adms:
        with st.container():
            cols = st.columns(len(adms))
            for i, a in enumerate(adms):
                info = COUNTRY_DETAILS.get(a, {"flag": "🏳️", "short_ar": a, "ar": a, "en": a})
                with cols[i]:
                    st.markdown(f"### {info['flag']} {info['short_ar']}")
                    st.info(f"**{info['ar']}**\n\n{info['en']}")

    # بناء الاستجابة الصوتي
    if intent == "COUNT" and adms:
        parts = [f"{COUNTRY_DETAILS.get(a, {'short_ar':a})['short_ar']} فيها {len(f_df[f_df['adm']==a])}" for a in adms]
        response = " و ".join(parts) + f" محطة {service if service else ''}."
    elif intent == "COMPARE" and len(adms) >= 2:
        parts = [f"{a} ({len(f_df[f_df['adm']==a])})" for a in adms]
        response = "المقارنة: " + " مقابل ".join(parts)
    else:
        response = f"لقيت {len(f_df)} محطة مطابقة لطلبك يا هندسة."

    st.success(f"🤖 {response}")

    # الصوت
    try:
        audio_io = io.BytesIO()
        gTTS(response, lang="ar").write_to_fp(audio_io)
        st.audio(audio_io.getvalue())
    except: pass

    # الخريطة المطورة
    map_df = f_df.dropna(subset=["lat", "lon"]).head(1000)
    if not map_df.empty:
        st.subheader("📍 Geospatial Mapping")
        m = folium.Map(location=[map_df.lat.mean(), map_df.lon.mean()], zoom_start=5, tiles="cartodb positron")
        cluster = MarkerCluster().add_to(m)

        for _, r in map_df.iterrows():
            color = "blue" if r.service == "SOUND" else "red"
            folium.Marker(
                [r.lat, r.lon],
                popup=f"<b>Site:</b> {r.get('site_name', 'N/A')}<br><b>ADM:</b> {r.adm}<br><b>Class:</b> {r.station_class}",
                icon=folium.Icon(color=color, icon="broadcast-tower", prefix="fa")
            ).add_to(cluster)

        st_folium(m, width="100%", height=600, key="main_map")
    else:
        st.warning("⚠️ مفيش بيانات مواقع (GPS) متاحة للفلترة دي.")
