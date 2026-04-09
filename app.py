import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# --- 1. تحميل الداتا (أسرع طريقة للأبد) ---
@st.cache_data
def load_clean_data():
    try:
        df = pd.read_csv("Data.csv", low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        # تنظيف الأعمدة الأساسية عشان الفلترة متغلطش
        for col in ['adm', 'station_class']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except: return pd.DataFrame()

df = load_clean_data()

# --- 2. واجهة البحث الفورية ---
st.title("📡 Seshat Engineering Hub")
query = st.text_input("Enter Command:", placeholder="e.g., masr sound")

if query:
    q = query.lower()
    
    # فلترة Logic صريحة (مصر vs غيرها)
    target = "EGY" if any(x in q for x in ["egy", "masr", "مصر"]) else None
    
    # تنفيذ البحث في الداتا اللي معانا فعلياً
    f_df = df[df['adm'] == target] if target else df
    
    # تحديد نوع الخدمة
    if any(x in q for x in ["tv", "تلفزيون", "bt"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        svc_name = "تلفزيون"
    elif any(x in q for x in ["sound", "صوت", "إذاعة", "bc"]):
        f_df = f_df[f_df['station_class'] == 'BC']
        svc_name = "إذاعة"
    else:
        svc_name = "بث"

    count = len(f_df)

    # --- 3. عرض النتائج (الأرقام + الصوت) ---
    st.header(f"Results: {count} Stations")
    
    # صوت سريع بـ gTTS (أضمن بمليون مرة من Gemini في الأرقام)
    voice_msg = f"يا هندسة، عدد محطات الـ {svc_name} في {'مصر' if target=='EGY' else 'الداتا'} هو {count} محطة."
    tts = gTTS(text=voice_msg, lang='ar')
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    st.audio(audio_io.getvalue(), format='audio/mp
