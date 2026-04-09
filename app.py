import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from gtts import gTTS
import io

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI: Location Intelligence", layout="wide")

def dms_to_decimal(dms_str):
    try:
        parts = re.findall(r"(\d+)°(\d+)'(\d+)\"\s*([NSEW])", str(dms_str))
        if not parts: return None, None
        res = {}
        for deg, mins, sec, direction in parts:
            decimal = float(deg) + float(mins)/60 + float(sec)/3600
            if direction in ['S', 'W']: decimal *= -1
            res[direction] = decimal
        return res.get('N') or res.get('S'), res.get('E') or res.get('W')
    except: return None, None

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    if 'location' in df.columns:
        coords = df['location'].apply(dms_to_decimal)
        df['lat'] = coords.apply(lambda x: x[0])
        df['lon'] = coords.apply(lambda x: x[1])
    # توحيد البيانات لضمان الفلترة
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

# تهيئة الذاكرة المؤقتة بشكل آمن
if 'results' not in st.session_state:
    st.session_state.results = {}

st.title("📡 Seshat AI: Spectrum Intelligence Dashboard")

query = st.text_input("Engineering Query:", placeholder="e.g., hya masr 3ndha kam m7ta sound notice type TB2")

if st.button("🚀 Analyze Data") and query:
    q = query.lower()
    
    # تحديد الدولة والخدمة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel", "إسرائيل"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    # التقاط الـ Notice Type بذكاء
    n_type = None
    notice_match = re.search(r'tb\d+', q)
    if notice_match:
        n_type = notice_match.group(0).upper()
        f_df = f_df[f_df['notice type'] == n_type]
    
    # تحديد نوع المحطة
    if any(x in q for x in ["tv", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        s_label = "TV Stations"
    else:
        f_df = f_df[f_df['station_class'] == 'BC']
        s_label = "Sound Stations"

    res_count = len(f_df)
    
    # إنشاء الرد الصوتي (English Humanized)
    voice_txt = f"Engineer, for {target or 'Global'}, I found {res_count} {s_label}."
    if n_type: voice_txt += f" under notice type {n_type}."
    
    tts = gTTS(text=voice_txt, lang='en')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    
    # حفظ النتائج
    st.session_state.results = {
        'df': f_df,
        'count': res_count,
        'adm': target,
        'label': s_label,
        'audio': audio_fp.getvalue(),
        'n_type': n_type
    }

# --- واجهة العرض (UI) المستقرة ---
res = st.session_state.results
if res:
    # تشغيل الصوت
    if 'audio' in res:
        st.audio(res['audio'], format='audio/mp3')
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"## {FLAGS.get(res.get('adm'), '🌐')} {res.get('adm', 'Global')}")
        st.metric(label=f"Total {res.get('label')}", value=res.get('count', 0))
        
        # التأكد من وجود n_type قبل
