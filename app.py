import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from gtts import gTTS
import io

# 1. إعدادات الهوية
FLAGS = {'ISR': '🇮🇱', 'EGY': '🇪🇬', 'ARS': '🇸🇦', 'UAE': '🇦🇪'}

st.set_page_config(page_title="Seshat AI: Egyptian Intelligence", layout="wide")

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
    for col in ['adm', 'station_class', 'notice type']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

df = load_data()

if 'results' not in st.session_state:
    st.session_state.results = {}

st.title("📡 Seshat AI: Spectrum Intelligence")

query = st.text_input("Engineering Query (العامية المصرية):", placeholder="مثلاً: مصر عندها كام محطة صوت نوعها TB2")

if st.button("🚀 تحليل البيانات"):
    q = query.lower()
    
    # منطق الفلترة
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "إسرائيل"]) else None
    f_df = df[df['adm'] == target] if target else df
    
    n_type = None
    notice_match = re.search(r'tb\d+', q)
    if notice_match:
        n_type = notice_match.group(0).upper()
        f_df = f_df[f_df['notice type'] == n_type]
    
    is_tv = any(x in q for x in ["tv", "تلفزيون", "bt"])
    f_df = f_df[f_df['station_class'] == ('BT' if is_tv else 'BC')]
    s_label = "تلفزيون" if is_tv else "إذاعة صوتية"
    res_count = len(f_df)
    
    # --- الرد بالعامية المصرية (Humanized Arabic) ---
    country_name = "مصر" if target == "EGY" else "المنطقة اللي اخترتها"
    
    # صياغة الجملة بالعامية
    voice_txt = f"يا هندسة، بالنسبة لـ{country_name}، أنا لقيت {res_count} محطة {s_label}."
    if n_type:
        voice_txt += f" ودول اللي نوعهم {n_type} زي ما طلبت."
    
    # توليد الصوت باللغة العربية
    tts = gTTS(text=voice_txt, lang='ar')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    
    st.session_state.results = {
        'df': f_df,
        'count': res_count,
        'adm': target,
        'label': s_label,
        'audio': audio_fp.getvalue(),
        'n_type': n_type
    }

# --- واجهة العرض ---
res = st.session_state.results
if res:
    if 'audio' in res:
        st.audio(res['audio'], format='audio/mp3')
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"## {FLAGS.get(res.get('adm'), '🌐')} {res.get('adm')}")
        st.metric(label=f"إجمالي محطات {res.get('label')}", value=res.get('count'))
        if res.get('n_type'):
            st.info(f"الفلتر المستخدم: {res['n_type']}")
        
    with col2:
        m_df = res['df'].dropna(subset=['lat', 'lon'])
        if not m_df.empty:
            m = folium.Map(location=[m_df['lat'].mean(), m_df['lon'].mean()], zoom_start=6, 
                           tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr="CartoDB")
            for _, row in m_df.head(200).iterrows():
                folium.CircleMarker([row['lat'], row['lon']], radius=5, color="#00FBFF", fill=True).add_to(m)
            st_folium(m, key="egy_map", width=800, height=480, returned_objects=[])
