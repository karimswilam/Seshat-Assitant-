import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from gtts import gTTS
import io
import re

# إعدادات الصفحة
st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# =====================================================
# 1. المرجعية الهندسية للدول والأعلام
# =====================================================
COUNTRY_INFO = {
    "EGY": {"flag": "🇪🇬", "ar": "جمهورية مصر العربية", "en": "Egypt", "short": "مصر"},
    "ARS": {"flag": "🇸🇦", "ar": "المملكة العربية السعودية", "en": "Saudi Arabia", "short": "السعودية"},
    "UAE": {"flag": "🇦🇪", "ar": "الإمارات العربية المتحدة", "en": "United Arab Emirates", "short": "الإمارات"}
}

# =====================================================
# 2. تحويل الإحداثيات (أكثر استقراراً)
# =====================================================
def parse_coords(text):
    if pd.isna(text) or str(text).strip() == "": return None, None
    try:
        # Regex محدد جداً عشان ما يلقطش أرقام غلط
        parts = re.findall(r"(\d+)[°\s](\d+)[\'\s](\d+)\"?\s*([NSEW])", str(text).upper())
        lat = lon = None
        for d, m, s, drc in parts:
            dec = float(d) + float(m)/60 + float(s)/3600
            if drc in ["S", "W"]: dec *= -1
            if drc in ["N", "S"]: lat = dec
            else: lon = dec
        return lat, lon
    except: return None, None

# =====================================================
# 3. تحميل البيانات (تنظيف بمستوى الإكسيل)
# =====================================================
@st.cache_data
def load_and_clean():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # تنظيف الأعمدة الأساسية
    for col in ["adm", "station_class", "notice type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            
    # اشتقاق الخدمة (المصدر الوحيد للحقيقة)
    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"}).fillna("OTHER")
    
    # معالجة الإحداثيات
    if "location" in df.columns:
        coords = df["location"].apply(parse_coords)
        df["lat"] = coords.apply(lambda x: x[0])
        df["lon"] = coords.apply(lambda x: x[1])
    return df

df = load_and_clean()

# =====================================================
# 4. محرك استخراج الكيانات (Entity Extraction)
# =====================================================
def nlp_engine(query):
    q = query.lower()
    # تحديد الدول
    found_adms = []
    if any(x in q for x in ["مصر", "egypt", "egy"]): found_adms.append("EGY")
    if any(x in q for x in ["سعودية", "saudi", "ars", "ksa"]): found_adms.append("ARS")
    if any(x in q for x in ["امارات", "uae"]): found_adms.append("UAE")
    
    # تحديد الخدمة
    service = None
    if any(x in q for x in ["sound", "radio", "إذاعة", "صوت"]): service = "SOUND"
    elif any(x in q for x in ["tv", "تلفزيون", "مرئي"]): service = "TV"
    
    return found_adms, service

# =====================================================
# 5. الواجهة (UI)
# =====================================================
st.title("📡 Seshat Precision Engineering")

query = st.text_input("🎙️ Engineering Query:", placeholder="مثال: كام محطة sound في مصر؟")

if query:
    adms, service = nlp_engine(query)
    
    # --- الفلترة الصارمة (هنا سر الدقة) ---
    f_df = df.copy()
    if adms: f_df = f_df[f_df["adm"].isin(adms)]
    if service: f_df = f_df[f_df["service"] == service]
    
    # 1. عرض الأعلام والبيانات الرسمية
    if adms:
        cols = st.columns(len(adms))
        for i, code in enumerate(adms):
            meta = COUNTRY_INFO.get(code)
            with cols[i]:
                st.metric(label=f"{meta['flag']} {meta['en']}", value=len(f_df[f_df['adm']==code]))
                st.caption(f"**{meta['ar']}**")

    # 2. الرد الصوتي والعددي
    count_val = len(f_df)
    response = f"لقيت {count_val} محطة مطابقة لطلبك يا هندسة."
    if adms:
        parts = [f"{COUNTRY_INFO[a]['short']} فيها {len(f_df[f_df['adm']==a])}" for a in adms]
        response = " و ".join(parts) + f" في خدمة {service if service else 'البث'}."
        
    st.success(response)
    
    # توليد الصوت
    audio_io = io.BytesIO()
    gTTS(response, lang="ar").write_to_fp(audio_io)
    st.audio(audio_io.getvalue())

    # 3. الـ Visual Charts (إعادة الميزات القديمة)
    st.markdown("### 📊 Visual Context")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Distribution by Service**")
        st.bar_chart(f_df["service"].value_counts())
    with c2:
        if "notice type" in f_df.columns:
            st.write("**Notice Type Breakdown**")
            st.bar_chart(f_df["notice type"].value_counts())

    # 4. الخريطة (فقط للداتا المفلترة)
    map_data = f_df.dropna(subset=["lat", "lon"])
    if not map_data.empty:
        st.markdown("### 📍 Geographic Mapping")
        m = folium.Map(location=[map_data.lat.mean(), map_data.lon.mean()], zoom_start=5)
        cluster = MarkerCluster().add_to(m)
        for _, r in map_data.head(500).iterrows(): # ليميت للأداء
            folium.Marker(
                [r.lat, r.lon], 
                popup=f"ADM: {r.adm} | Site: {r.get('site_name', 'N/A')}",
                icon=folium.Icon(color="blue" if r.service=="SOUND" else "red")
            ).add_to(cluster)
        st_folium(m, width="100%", height=500, key="fixed_map")
    else:
        st.warning("⚠️ لا توجد إحداثيات للعرض على الخريطة لهذه المجموعة.")
