import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from gtts import gTTS
import io
import matplotlib.pyplot as plt

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")

# ----------------- LOAD DATA -----------------
@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ['adm', 'station_class', 'intent', 'notice type', 'geo area']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    if 'lat' in df.columns and 'lon' in df.columns:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    return df

df = load_data()

# ----------------- UI -----------------
st.title("📡 Seshat Engineering Hub")
query = st.text_input("🎙️ Ask like an engineer:", placeholder="e.g. radio stations in egypt")

if query:
    q = query.lower()
    f_df = df.copy()

    # -------- Country --------
    if any(x in q for x in ["egy", "masr", "مصر"]):
        f_df = f_df[f_df['adm'] == 'EGY']
        country_name = "مصر"
    else:
        country_name = "القاعدة كاملة"

    # -------- Service --------
    service = "محطات"
    if any(x in q for x in ["radio", "sound", "إذاعة", "bc"]):
        f_df = f_df[f_df['station_class'] == 'BC']
        service = "إذاعات"
    elif any(x in q for x in ["tv", "television", "bt", "تلفزيون"]):
        f_df = f_df[f_df['station_class'] == 'BT']
        service = "تلفزيون"

    final_count = len(f_df)

    # ---------------- KPIs ----------------
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Stations", final_count)
    col2.metric("Radio (BC)", len(f_df[f_df['station_class'] == 'BC']))
    col3.metric("TV (BT)", len(f_df[f_df['station_class'] == 'BT']))

    # ---------------- Voice Logic ----------------
    if final_count == 0:
        voice_text = "مفيش ولا محطة مطابقة للطلب ده."
    elif final_count < 10:
        voice_text = f"النتيجة قليلة شوية، حوالي {final_count} {service} في {country_name}."
    elif final_count < 100:
        voice_text = f"العدد متوسط، تقريبًا {final_count} {service} في {country_name}."
    else:
        voice_text = f"العدد كبير، حوالي {final_count} {service} منتشرين في {country_name}."

    try:
        tts = gTTS(text=voice_text, lang='ar')
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        st.audio(audio.getvalue(), format="audio/mp3")
    except:
        st.warning("⚠️ Voice failed, text result shown only.")

    st.subheader("📊 Station Class Distribution")
    fig, ax = plt.subplots()
    f_df['station_class'].value_counts().plot(kind='bar', ax=ax)
    st.pyplot(fig)

    # ---------------- MAP ----------------
    map_df = f_df.dropna(subset=['lat', 'lon']).head(500)
    if not map_df.empty:
        m = folium.Map(
            location=[map_df['lat'].mean(), map_df['lon'].mean()],
            zoom_start=6
        )

        for _, r in map_df.iterrows():
            folium.CircleMarker(
                location=[r['lat'], r['lon']],
                radius=4,
                color='blue' if r['station_class'] == 'BC' else 'red',
                fill=True
            ).add_to(m)

        st_folium(m, width=1000, height=500)
