import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat AI: Engineer Edition", layout="wide")

# --- 1. تحميل البيانات (إصلاح السطر 38 للأبد) ---
@st.cache_data
def load_data_final_fix():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # حل الـ AttributeError بضمان تحويل الأعمدة لنصوص الأول
        for col in ['adm', 'station_class', 'notice type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except: return pd.DataFrame()

df = load_data_final_fix()

# --- 2. محرك الصوت (إخراج فني مش برمجي) ---
def get_natural_voice(data_summary, user_query):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        # برومبت يكسر الجمود ويخليه يتكلم زينا
        prompt = f"""
        إنت مهندس اتصالات مصري شاطر. 
        بناءً على قاعدة البيانات، لقينا: {data_summary}. 
        اليوزر سألك: "{user_query}".
        رد عليه بلهجة مصرية عامية "صايعة" فنية، بلاش "يا هندسة" كل شوية، اتكلم كأننا في اجتماع تنسيق فني. 
        ركز على الأرقام واشرحها ببساطة.
        """
        response_text = model.generate_content(prompt).text
        tts = gTTS(text=response_text, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        return response_text, audio_io.getvalue()
    except: return "فيه مشكلة في الصوت، بس الأرقام اهي.", None

# --- 3. واجهة التحكم (Logic First) ---
st.title("📡 Seshat AI: Mission Critical Dashboard")
query = st.text_input("Engineering Query:", placeholder="مثلاً: مصر فيها كام محطة TV؟")

if st.button("🚀 Analyze Now") and query:
    q = query.lower()
    
    # فلترة محلية دقيقة (Local DB Search)
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else "ISR" if any(x in q for x in ["isr", "israel"]) else None
    
    # العد الفعلي من الـ Excel
    f_df = df[df['adm'] == target] if target else df
    
    # تحديد الخدمات بدقة
    is_tv = any(x in q for x in ["tv", "تلفزيون", "bt"])
    is_sound = any(x in q for x in ["sound", "صوت", "إذاعة", "bc"])
    
    if is_tv: f_df = f_df[f_df['station_class'] == 'BT']
    if is_sound: f_df = f_df[f_df['station_class'] == 'BC']
    
    final_count = len(f_df)

    # تشغيل الصوت بالرد "الفني"
    data_summary = f"{final_count} محطة {'تلفزيون' if is_tv else 'إذاعة' if is_sound else 'بث'}"
    msg, audio = get_natural_voice(data_summary, query)
    
    # تخزين النتائج عشان الـ KeyErrors تختفي
    st.session_state.result_cache = {
        'msg': msg, 'audio': audio, 'df': f_df, 'count': final_count, 'target': target
    }

# --- 4. العرض (الخريطة والنتائج) ---
if 'result_cache' in st.session_state:
    res = st.session_state.result_cache
    
    if res['audio']:
        st.audio(res['audio'], format='audio/mp3')
    
    st.success(res['msg'])
    st.metric(f"Total Found ({res['target']})", res['count'])
    
    # الخريطة (فقط لو فيه داتا)
    if not res['df'].empty and 'lat' in res['df'].columns:
        st.subheader("📍 Geospatial Distribution")
        map_df = res['df'].dropna(subset=['lat', 'lon']).head(200)
        if not map_df.empty:
            m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=6)
            for _, r in map_df.iterrows():
                folium.CircleMarker([r['lat'], r['lon']], radius=4, color='red', fill=True).add_to(m)
            st_folium(m, width=900, height=500, key="stable_map")
    else:
        st.warning("No geospatial data (lat/lon) found for these stations.")
