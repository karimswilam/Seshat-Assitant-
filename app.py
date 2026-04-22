import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & UI ---
st.set_page_config(layout="wide", page_title="Seshat AI v16.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v16.0"
PROJECT_SLOGAN = "Project BASIRA | Universal Data Compatibility"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 18px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)
st.divider()

# --- 2. THE SMART MAPPER (تعديل الجوهر) ---
def smart_column_mapper(df):
    """وظيفة لتوحيد أسماء الأعمدة أياً كان مصدر الملف"""
    mapping = {
        'Adm': ['Administration', 'Adm', 'Admin', 'Country'],
        'Notice Type': ['Notice Type', 'NT', 'Type'],
        'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Allotment Name', 'Location'],
        'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'Lat/Long', 'Position']
    }
    
    new_columns = {}
    for standard_name, synonyms in mapping.items():
        for col in df.columns:
            if col in synonyms:
                new_columns[col] = standard_name
                break
    return df.rename(columns=new_columns)

# --- 3. VOICE ENGINE ---
async def generate_audio(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        if data: st.audio(data, format="audio/mp3")
    except: pass

# --- 4. ENGINE CORE ---
@st.cache_data
def load_db():
    # البحث عن أي ملف Excel سواء xlsx أو xls
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else ("Data.xls" if "Data.xls" in files else (files[0] if files else None))
    
    if target:
        # استخدام engine='xlrd' للـ xls و engine='openpyxl' للـ xlsx أوتوماتيكياً
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        df = smart_column_mapper(df) # تطبيق المابر الذكي
        return df
    return None

def engine_v16_0(q, data):
    q_low = q.lower()
    
    # القواميس والمفاهيم الثابتة
    COUNTRY_MAP = {
        'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
        'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
        'TUR': ['turkey', 'tur', 'تركيا'],
        'CYP': ['cyprus', 'cyp', 'قبرص'],
        'GRC': ['greece', 'grc', 'اليونان'],
        'ISR': ['israel', 'isr', 'اسرائيل']
    }
    
    SYNONYMS = {
        'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3'],
        'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees'],
        'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه'],
        'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية'],
        'FM_KEY': ['fm', 'radio'],
        'GENERIC_BR_KEY': ['إذاعية', 'إذاعة', 'broadcasting']
    }

    STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
    STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "ADM Error", 0, False

    # تحديد نوع الخدمة
    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['GENERIC_BR_KEY']): svc_codes = ['GS1','GS2','DS1','DS2','T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {"Adm": adm}
        if any(x in q_low for x in SYNONYMS['ASSIG_KEY']) and not any(x in q_low for x in SYNONYMS['ALLOT_KEY']):
            res["Assignments"] = a_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif any(x in q_low for x in SYNONYMS['ALLOT_KEY']) and not any(x in q_low for x in SYNONYMS['ASSIG_KEY']):
            res["Allotments"] = l_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else:
            res["Assignments"] = a_count
            res["Allotments"] = l_count
            temp = adm_df
            
        reports.append(res)
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg = " | ".join([f"{r['Adm']}: {r.get('Assignments', '')} Assig {r.get('Allotments', '')} Allot" for r in reports])
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()
query = st.text_input("🎙️ Enter Query:", key="main_q")

if query and db is not None:
    play_audio(query)
    res_df, reports, msg, conf, success = engine_v16_0(query, db)
    
    if success and reports:
        # عرض الأعلام والبيانات (نفس الـ Interface المتراكم)
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p style="text-align:center;">{r["Adm"]}</p>', unsafe_allow_html=True)
                # (يمكن إضافة عرض الأعلام هنا كما في v15.9)
        
        st.divider()
        st.success(msg)
        play_audio(msg)
        with st.expander("Technical Records"):
            st.dataframe(res_df)
