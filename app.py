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
st.set_page_config(layout="wide", page_title="Seshat AI v15.3")

st.markdown("""
    <style>
    .country-header { text-align: center; font-weight: bold; font-size: 18px; color: #1E3A8A; }
    .country-footer { text-align: center; font-weight: bold; font-size: 15px; color: #64748B; }
    .main-title { text-align: center; font-size: 32px; font-weight: 800; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

# التنصيفات الهندسية الصارمة
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'twze3', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'ta5sees', 'assign'],
    'DAB_KEY': ['dab', 'داب'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. VOICE ---
async def generate_audio(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
    communicate = edge_tts.Communicate(clean_text, voice, rate="-10%")
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data.write(chunk["data"])
    audio_data.seek(0)
    return audio_data

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 3. THE SURGICAL ENGINE ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def engine_v15_3(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(set(selected_adms))
    
    if not selected_adms: return None, [], "ADM not found.", 0, False

    # تحديد النية بدقة: هل المستخدم ذكر كلمة تخصيص أو توزيع؟
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    # فلترة الخدمة (DAB, FM, TV)
    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q_low for x in SYNONYMS['FM_KEY']): svc_codes = ['T01','T03','T04']
    elif any(x in q_low for x in SYNONYMS['TV_KEY']): svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']

    reports = []; final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        # بناء التقرير بناءً على الفلتر الصارم
        res = {"Adm": adm}
        if mentions_assig and not mentions_allot:
            res["Assignments"] = a_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        elif mentions_allot and not mentions_assig:
            res["Allotments"] = l_count
            temp = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        else: # في حالة سأل عن الاتنين أو مسألش عن حاجة محددة
            res["Assignments"] = a_count
            res["Allotments"] = l_count
            temp = adm_df
            
        reports.append(res)
        final_df = pd.concat([final_df, temp], ignore_index=True)

    msg_parts = []
    for r in reports:
        txt = f"{r['Adm']}: "
        if "Assignments" in r: txt += f"{r['Assignments']} Assignments "
        if "Allotments" in r: txt += f"{r['Allotments']} Allotments"
        msg_parts.append(txt)
    
    return final_df, reports, " | ".join(msg_parts), 100, True

# --- 4. UI ---
db = load_db()
st.markdown('<div class="main-title">📡 Seshat Master Precision v15.3</div>', unsafe_allow_html=True)
st.divider()

query = st.text_input("🎙️ Input Question:", placeholder="e.g. Compare DAB assignments in Egypt and Israel", key="main_q")

if query and db is not None:
    res_df, reports, msg, conf, success = engine_v15_3(query, db)
    
    if success and reports:
        # 1. Flags (Reduced Size & Centered)
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.markdown(f'<p class="country-header">{COUNTRY_DISPLAY[r["Adm"]]["ar"]}</p>', unsafe_allow_html=True)
                st.image(FLAGS.get(r['Adm']), width=300) # تم تصغير الحجم لـ 300
                st.markdown(f'<p class="country-footer">{COUNTRY_DISPLAY[r["Adm"]]["en"]}</p>', unsafe_allow_html=True)

        st.divider()
        
        # 2. Results & Charts
        m1, m2 = st.columns([1, 2])
        chart_df = pd.DataFrame(reports).set_index('Adm')
        
        with m1:
            st.metric("Confidence", f"{conf}%")
            if PLOTLY_AVAILABLE and "Assignments" in chart_df.columns and "Allotments" in chart_df.columns:
                fig = px.pie(values=[reports[0].get('Assignments', 0), reports[0].get('Allotments', 0)], 
                             names=['Assignments', 'Allotments'], hole=.4)
                st.plotly_chart(fig, use_container_width=True)
        
        with m2:
            st.bar_chart(chart_df)

        st.table(chart_df)
        
        # 3. Voice
        st.success(msg)
        play_audio(msg)

        with st.expander("Technical Records"):
            st.dataframe(res_df)
