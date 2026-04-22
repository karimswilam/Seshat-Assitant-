import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & UI ---
st.set_page_config(layout="wide", page_title="Seshat AI v16.6 | Project BASIRA")

def get_logo_html():
    for name in ["Designer.jpg", "Designer.png", "Designer.jpeg"]:
        if os.path.exists(name):
            with open(name, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f'<div style="text-align: center;"><img src="data:image/png;base64,{data}" width="120"></div>'
    return ""

FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

# --- 2. THE GEOSPATIAL CONVERTER ---
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

# --- 3. THE CORE BASIRA ENGINE (Logic Preservation) ---
def engine_v16_6(q, data):
    q_low = q.lower()
    
    # القواميس الموحدة
    ADMS = {'EGY':['egy','مصر','قاهرة'], 'ARS':['ars','saudi','سعودية','رياض'], 
            'TUR':['tur','turkey','تركيا','انقرة'], 'ISR':['isr','israel','اسرائيل']}
    
    # تصنيف الخدمات (ممنوع الخلط بين DAB و TV)
    DAB_KEYS = ['dab', 'صوت', 'إذاعة', 'اذاعة', 'راديو', 'digital audio']
    TV_KEYS = ['tv', 'television', 'تلفزيون', 'تليفزيون', 'مرئي']
    
    # تصنيف السجلات (ممنوع الخلط بين التخصيص والتوزيع)
    ASSIG_KEYS = ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'محطة', 'محطات']
    ALLOT_KEYS = ['allotment', 'allotments', 'توزيع', 'توزيعات', 'منطقة', 'مناطق']

    STRICT_ASSIG_TYPES = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
    STRICT_ALLOT_TYPES = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

    selected_adms = [code for code, keys in ADMS.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "برجاء تحديد الإدارة", 0, False

    # فلاتر الخدمة
    svc_filter = []
    is_dab = any(k in q_low for k in DAB_KEYS)
    is_tv = any(k in q_low for k in TV_KEYS)
    
    if is_dab: svc_filter += ['GS1','GS2','DS1','DS2']
    if is_tv: svc_filter += ['T01','T02','T03','T04','GT1','GT2','DT1','DT2','G01','G02']

    # فلاتر السجل
    is_assig_req = any(k in q_low for k in ASSIG_KEYS)
    is_allot_req = any(k in q_low for k in ALLOT_KEYS)
    if not is_assig_req and not is_allot_req: is_assig_req = is_allot_req = True

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_filter: adm_df = adm_df[adm_df['Notice Type'].isin(svc_filter)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG_TYPES)]) if is_assig_req else 0
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT_TYPES)]) if is_allot_req else 0
        
        reports.append({"Adm": adm, "Assignments": a_count, "Allotments": l_count})
        
        current_filter = []
        if is_assig_req: current_filter += STRICT_ASSIG_TYPES
        if is_allot_req: current_filter += STRICT_ALLOT_TYPES
        final_df = pd.concat([final_df, adm_df[adm_df['Notice Type'].isin(current_filter)]])

    msg = " | ".join([f"{r['Adm']}: {r['Assignments']} Assig, {r['Allotments']} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 4. VOICE ENGINE ---
async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-5%")
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

# --- 5. UI & DATA LOADING ---
st.markdown(get_logo_html(), unsafe_allow_html=True)
st.markdown('<h1 style="text-align: center; color: #1E3A8A;">Seshat Master Precision v16.6</h1>', unsafe_allow_html=True)

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        # Mapping & Geospatial process
        m = {'Adm':['Administration','Adm','Country'], 'Notice Type':['Notice Type','NT'], 
             'Site/Allotment Name':['Site/Allotment Name','Site Name'], 'Geographic Coordinates':['Geographic Coordinates','Coordinates']}
        for s, sy in m.items():
            for c in df.columns:
                if c.strip() in sy: df = df.rename(columns={c:s}); break
        if 'Geographic Coordinates' in df.columns:
            coords = df['Geographic Coordinates'].str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        return df
    return None

db = load_db()
query = st.text_input("🎙️ اسأل عن الترددات (تلفزيون، DAB، تخصيص، توزيع):")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    
    res_df, reports, msg, conf, success = engine_v16_6(query, db)
    
    if success:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=200, caption=r['Adm'])
        
        st.divider()
        if PLOTLY_AVAILABLE and not res_df.empty and 'lat_dec' in res_df.columns:
            st.markdown("### 🌍 Geospatial Spectrum Distribution")
            fig_map = px.scatter_mapbox(res_df, lat="lat_dec", lon="lon_dec", hover_name="Site/Allotment Name", color="Adm", mapbox_style="carto-positron", zoom=3, height=500)
            st.plotly_chart(fig_map, use_container_width=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Confidence Score", f"{conf}%")
            fig_pie = px.pie(pd.DataFrame(reports), values='Assignments', names='Adm', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.bar_chart(pd.DataFrame(reports).set_index('Adm')[['Assignments', 'Allotments']])
        
        st.success(msg)
        play_audio(msg)
        with st.expander("Technical Records"): st.dataframe(res_df)
