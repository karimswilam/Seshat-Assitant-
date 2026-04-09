import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# =====================================================
# 1. DMS → Decimal (Regex مرن جداً)
# =====================================================
def dms_to_decimal(dms):
    if pd.isna(dms) or str(dms).strip() == "": return None, None
    try:
        # يقبل درجات ودقائق وثواني بأي شكل مسافات
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
# 2. LOAD & CLEAN (The Excel Matcher)
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    # تنظيف رؤوس الأعمدة
    df.columns = [c.lower().strip() for c in df.columns]

    # تنظيف البيانات الأساسية من أي مسافات أو حروف صغيرة
    categorical_cols = ["adm", "station_class", "notice type"]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    # تحويل الخدمة (تأمين ضد الـ NaN)
    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"}).fillna("UNKNOWN")

    # معالجة الإحداثيات
    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])

    return df

df = load_data()

# =====================================================
# 3. INTELLIGENT EXTRACTION
# =====================================================
ADM_MAP = {
    "egy": "EGY", "egypt": "EGY", "مصر": "EGY",
    "saudi": "ARS", "ksa": "ARS", "السعودية": "ARS",
    "emirates": "UAE", "uae": "UAE", "الإمارات": "UAE"
}

def get_entities(q):
    q = q.lower()
    found_adms = [v for k, v in ADM_MAP.items() if k in q]
    
    service = None
    if any(x in q for x in ["tv", "تلفزيون", "مرئي"]): service = "TV"
    elif any(x in q for x in ["sound", "radio", "إذاعة", "صوتي"]): service = "SOUND"
    
    intent = "OVERVIEW"
    if any(x in q for x in ["كام", "عدد", "how many"]): intent = "COUNT"
    elif any(x in q for x in ["قارن", "فرق", "compare"]): intent = "COMPARE"
    
    return list(set(found_adms)), service, intent

# =====================================================
# 4. UI & LOGIC
# =====================================================
st.title("🗣️ Seshat Engineering Voice Assistant")
query = st.text_input("🎙️ اسأل عن محطات البث (مصر، السعودية...):")

if query:
    adms, service, intent = get_entities(query)
    
    # الفلترة (Single Source of Truth)
    f_df = df.copy()
    if adms: f_df = f_df[f_df["adm"].isin(adms)]
    if service: f_df = f_df[f_df["service"] == service]

    # بناء الرد (Logic سليم 100%)
    if intent == "COUNT" and adms:
        results = []
        for a in adms:
            count = len(f_df[f_df["adm"] == a])
            results.append(f"{a} فيها {count}")
        response = " و ".join(results) + f" محطة {service if service else ''}."
    
    elif intent == "COMPARE" and len(adms) >= 2:
        results = [f"{a} ({len(f_df[f_df['adm'] == a])})" for a in adms]
        response = "المقارنة كالآتي: " + " مقابل ".join(results)
    
    else:
        response = f"إجمالي المحطات المفلترة هو {len(f_df)} محطة."

    # الصوت
    st.success(response)
    try:
        tts = gTTS(response, lang="ar")
        audio_data = io.BytesIO()
        tts.write_to_fp(audio_data)
        st.audio(audio_data.getvalue())
    except: st.error("Voice Error")

    # الرسوم البيانية (Contextual)
    col1, col2 = st.columns(2)
    with col1:
        st.write("### توزيع الخدمات")
        st.bar_chart(f_df["service"].value_counts())
    with col2:
        st.write("### حالات الإخطار (Notice Type)")
        st.bar_chart(f_df["notice type"].value_counts())

    # الخريطة الحرارية
    map_df = f_df.dropna(subset=["lat", "lon"])
    if not map_df.empty:
        st.write("### 🔥 كثافة التوزيع الجغرافي")
        m = folium.Map(location=[map_df["lat"].mean(), map_df["lon"].mean()], zoom_start=5)
        HeatMap(map_df[["lat", "lon"]].values.tolist(), radius=15).add_to(m)
        st_folium(m, width=1100, height=500, key="geo_map")
