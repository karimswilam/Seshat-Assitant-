import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
from rapidfuzz import process, fuzz

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(layout="wide", page_title="Seshat AI v16.4")

# وظيفة ذكية لجلب اللوجو (Designer.jpg أو Designer.png)
def get_logo_html():
    possible_names = ["Designer.jpg", "Designer.png", "Designer.jpeg"]
    logo_path = None
    for name in possible_names:
        if os.path.exists(name):
            logo_path = name
            break
    if logo_path:
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f'<div style="text-align: center;"><img src="data:image/png;base64,{data}" width="120"></div>'
    return ""

# الثوابت
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

# --- 2. GEOSPATIAL & DATA ENGINE ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        parts = re.findall(r"(\d+)", dms_str)
        direction = re.findall(r"([NSEW])", dms_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60) + (sec / 3600)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None
    return None

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        # Smart Mapping
        mapping = {'Adm':['Administration','Adm','Country'], 'Notice Type':['Notice Type','NT'], 
                   'Site/Allotment Name':['Site/Allotment Name','Site Name'], 
                   'Geographic Coordinates':['Geographic Coordinates','Coordinates']}
        for std, syns in mapping.items():
            for col in df.columns:
                if col.strip() in syns: df = df.rename(columns={col: std}); break
        # Map Conversion
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
    return None

# --- 3. VOICE & AUDIO ENGINE ---
async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def play_audio(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(generate_audio(text))
    if data: st.audio(data, format="audio/mp3")

# --- 4. PRECISION LOGIC ENGINE ---
def engine_v16_4(q, data):
    q_low = q.lower()
    COUNTRY_MAP = {'EGY':['egypt','مصر'], 'ARS':['saudi','السعودية'], 'TUR':['turkey','تركيا'], 'ISR':['israel','اسرائيل']}
    STRICT_ASSIG = ['T01','T03','T04','GS1','DS1','GT1','DT1','G01']
    STRICT_ALLOT = ['T02','G02','GT2','DT2','GS2','DS2']
    
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM Error", 0, False

    is_assig = any(x in q_low for x in ['assignment', 'تخصيص'])
    is_allot = any(x in q_low for x in ['allotment', 'توزيع'])
    if not is_assig and not is_allot: is_assig = is_allot = True

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]) if is_assig else 0
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]) if is_allot else 0
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
        
        if is_assig: final_df = pd.concat([final_df, adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]])
        if is_allot: final_df = pd.concat([final_df, adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]])

    msg = " | ".join([f"{r['Adm']}: {r['Assignments']} Assig, {r['Allotments']} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. APP LAYOUT ---
st.markdown(get_logo_html(), unsafe_allow_html=True)
st.markdown('<h1 style="text-align: center; color: #1E3A8A;">Seshat Master Precision v16.4</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center;">Project BASIRA | Spectrum Intelligence & Governance</p>', unsafe_allow_html=True)

db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry (Voice or Text):")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query) # رجعت الـ Replay
    
    res_df, reports, msg, conf, success = engine_v16_4(query, db)
    
    if success:
        # Flags
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=200, caption=r['Adm'])
        
        st.divider()
        # Map
        if PLOTLY_AVAILABLE and 'lat_dec' in res_df.columns:
            st.markdown("### 🌍 Geospatial Spectrum Distribution")
            fig_map = px.scatter_mapbox(res_df, lat="lat_dec", lon="lon_dec", hover_name="Site/Allotment Name", 
                                        color="Adm", zoom=3, mapbox_style="carto-positron", height=500)
            st.plotly_chart(fig_map, use_container_width=True)

        # Charts
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Confidence Score", f"{conf}%")
            fig_pie = px.pie(pd.DataFrame(reports), values='Assignments', names='Adm', hole=0.4, title="Assignments Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.bar_chart(pd.DataFrame(reports).set_index('Adm')[['Assignments', 'Allotments']])
        
        st.success(msg)
        play_audio(msg) # رجعت الـ Assistant Response
        
        with st.expander("Technical Records"):
            st.dataframe(res_df)
