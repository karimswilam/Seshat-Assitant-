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
# 1. القاموس الهندسي للدول (للأعلام والأسماء الكاملة)
# =====================================================
COUNTRY_DETAILS = {
    "EGY": {
        "flag": "🇪🇬",
        "en": "Egypt",
        "ar": "جمهورية مصر العربية",
        "short_ar": "مصر"
    },
    "ARS": {
        "flag": "🇸🇦",
        "en": "Saudi Arabia",
        "ar": "المملكة العربية السعودية",
        "short_ar": "السعودية"
    },
    "UAE": {
        "flag": "🇦🇪",
        "en": "United Arab Emirates",
        "ar": "الإمارات العربية المتحدة",
        "short_ar": "الإمارات"
    }
}

# =====================================================
# 2. DMS → Decimal (Regex مطور)
# =====================================================
def dms_to_decimal(dms):
    if pd.isna(dms) or str(dms).strip() == "": return None, None
    try:
        parts = re.findall(r"(\d+)[°\s](\d+)[\'\s](\d+)\"?\s*([NSEWnsew])", str(dms))
        lat, lon = None, None
        for d, m, s, dirc in parts:
            dec = float(d) + float(m)/60 + float(s)/3600
            if dirc.upper() in ["S", "W"]: dec *= -1
            if dirc.upper() in ["N", "S"]: lat = dec
            if dirc.upper() in ["E", "W"]: lon = dec
        return lat, lon
    except: return None, None

# =====================================================
# 3. LOAD & CLEAN
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # تنظيف الأعمدة الأساسية
    for col in ["adm", "station_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    
    # تحويل الخدمة
    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"}).fillna("OTHER")
    
    # معالجة المواقع
    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])
    return df

df = load_data()

# =====================================================
# 4. ENTITY EXTRACTION
# =====================================================
ADM_MAP = {"egy": "EGY", "مصر": "EGY", "saudi": "ARS", "السعودية": "ARS", "uae": "UAE", "إمارات": "UAE"}

def get_entities(query):
    q = query.lower()
    adms = list({v for k, v in ADM_MAP.items() if k in q})
    service = "SOUND" if any(x in q for x in ["sound", "radio", "إذاعة"]) else "TV" if any(x in q for x in ["tv", "تلفزيون"]) else None
    intent = "COUNT" if any(x in q for x in ["كام", "عدد"]) else "COMPARE" if any(x in q for x in ["قارن", "فرق"]) else "OVERVIEW"
    return adms, service, intent

# =====================================================
# 5. UI & LOGIC
# =====================================================
st.title("📡 Seshat Engineering Voice Assistant")

query = st.text_input("🎙️ اسأل المهندس المساعد:", placeholder="مثلاً: قارن بين مصر والسعودية في الـ sound")

if query:
    adms, service, intent = get_entities(query)
    
    # الفلترة (Single Source of Truth)
    f_df = df.copy()
    if adms: f_df = f_df[f_df["adm"].isin(adms)]
    if service: f_df = f_df[f_df["service"] == service]

    # --- عرض الأعلام والأسماء (الطلب الخاص) ---
    if adms:
        cols = st.columns(len(adms))
        for i, adm in enumerate(adms):
            info = COUNTRY_DETAILS.get(adm, {"flag": "🏳️", "ar": adm, "en": adm})
            with cols[i]:
                st.markdown(f"### {info['flag']} {info['short_ar'] if 'short_ar' in info else adm}")
                st.caption(f"{info['ar']}")
                st.caption(f"{info['en']}")

    # --- بناء الرد الصوتي ---
    total = len(f_df)
    if intent == "COUNT" and adms:
        res = [f"{COUNTRY_DETAILS.get(a, {'short_ar':a})['short_ar']} فيها {len(f_df[f_df['adm']==a])}" for a in adms]
        response = " و ".join(res) + f" محطة {service if service else ''}."
    elif intent == "COMPARE" and len(adms) >= 2:
        res = [f"{a} ({len(f_df[f_df['adm']==a])})" for a in adms]
        response = "المقارنة: " + " مقابل ".join(res)
    else:
        response = f"تم العثور على {total} محطة."

    st.success(response)
    
    # صوت
    try:
        audio_io = io.BytesIO()
        gTTS(response, lang="ar").write_to_fp(audio_io)
        st.audio(audio_io.getvalue())
    except: pass

    # --- الخريطة (Locations بدل Heatmap) ---
    map_df = f_df.dropna(subset=["lat", "lon"]).head(1000) # ليميت لسرعة الأداء
    if not map_df.empty:
        st.subheader("📍 Station Locations")
        m = folium.Map(location=[map_df["lat"].mean(), map_df["lon"].mean()], zoom_start=5)
        marker_cluster = MarkerCluster().add_to(m)
        
        for _, row in map_df.iterrows():
            color = "blue" if row["service"] == "SOUND" else "red"
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=f"Site: {row.get('site_name', 'N/A')}<br>ADM: {row['adm']}",
                icon=folium.Icon(color=color, icon="broadcast-tower", prefix="fa")
            ).add_to(marker_cluster)
        
        st_folium(m, width="100%", height=500)
    else:
        st.warning("لا توجد إحداثيات متاحة لهذه المجموعة.")
