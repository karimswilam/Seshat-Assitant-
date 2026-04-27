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

# -------------------------------------------------
# 1. CONFIG & INTERFACE
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Seshat AI v17.0")

LOGO_FILE = "Designer.png"
PROJECT_NAME = "Seshat Master Precision v17.0"
PROJECT_SLOGAN = "Project BASIRA | Spectrum Intelligence & Governance"

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=150)
    st.markdown(
        f"""
        <div style="text-align:center">
            <h1 style="color:#1E3A8A;margin-bottom:0">{PROJECT_NAME}</h1>
            <p style="color:#475569;font-size:18px">{PROJECT_SLOGAN}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# -------------------------------------------------
# 2. FIXED ENGINEERING LOGIC
# -------------------------------------------------
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': {'ar': 'جمهورية مصر العربية', 'en': 'Egypt'},
    'ARS': {'ar': 'المملكة العربية السعودية', 'en': 'Saudi Arabia'},
    'TUR': {'ar': 'الجمهورية التركية', 'en': 'Turkey'},
    'CYP': {'ar': 'جمهورية قبرص', 'en': 'Cyprus'},
    'GRC': {'ar': 'الجمهورية اليونانية', 'en': 'Greece'},
    'ISR': {'ar': 'إسرائيل', 'en': 'Israel'}
}

STRICT_ASSIG = ['T01','T03','T04','GS1','DS1','GT1','DT1','G01']
STRICT_ALLOT = ['T02','G02','GT2','DT2','GS2','DS2']

COUNTRY_MAP = {
    'EGY': ['egypt','egy','مصر','المصرية'],
    'ARS': ['saudi','ars','ksa','السعودية','المملكة'],
    'TUR': ['turkey','tur','تركيا'],
    'CYP': ['cyprus','cyp','قبرص'],
    'GRC': ['greece','grc','اليونان'],
    'ISR': ['israel','isr','اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment','allotments','توزيع','توزيعات','twze3'],
    'ASSIG_KEY': ['assignment','assignments','تخصيص','تخصيصات','ta5sees'],
    'DAB_KEY': ['dab','داب','صوتية','صوتيه','sound'],
    'TV_KEY': ['tv','television','تلفزيون','تلفزيونية','مرئية','tlfzyon'],
    'FM_KEY': ['fm','radio','راديو'],
    'TOTAL_KEY': ['total','egmali','إجمالي','اجمالي','كل'],
    'EXCEPT_KEY': ['except','ma3ada','ماعدا','من غير','without']
}

# -------------------------------------------------
# 3. GEOSPATIAL UTILITIES
# -------------------------------------------------
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str,str):
            return None
        clean = re.sub(r'[^0-9NSEW ]',' ',dms_str).upper()
        parts = re.findall(r'(\d+)',clean)
        dirc = re.findall(r'([NSEW])',clean)
        if len(parts)>=3 and dirc:
            d,m,s = map(float,parts[:3])
            val = d + m/60 + s/3600
            if dirc[0] in ['S','W']:
                val *= -1
            return val
    except:
        return None
    return None

# -------------------------------------------------
# 4. VOICE OUTPUT (TTS)
# -------------------------------------------------
async def generate_audio(text):
    is_ar = any(c in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    clean_text = re.sub(r'<[^>]*>','',text).replace("|"," . ")
    communicate = edge_tts.Communicate(clean_text,voice,rate="-10%")
    buf = io.BytesIO()
    async for ch in communicate.stream():
        if ch["type"]=="audio":
            buf.write(ch["data"])
    buf.seek(0)
    return buf

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_audio(text))
        st.audio(audio,format="audio/mp3")
    except:
        pass

# -------------------------------------------------
# 5. DATA LOADER
# -------------------------------------------------
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        return None
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()

    mapping = {
        'Adm': ['Administration','Adm','Country'],
        'Notice Type': ['Notice Type','NT'],
        'Site/Allotment Name': ['Site Name','Standard/Allotment Area'],
        'Geographic Coordinates': ['Geographic Coordinates','Coordinates']
    }

    for std, alts in mapping.items():
        for c in df.columns:
            if c in alts:
                df = df.rename(columns={c:std})
                break

    if 'Geographic Coordinates' in df.columns:
        sp = df['Geographic Coordinates'].astype(str).str.split(expand=True)
        if sp.shape[1]>=2:
            df['lon_dec'] = sp[0].apply(dms_to_decimal)
            df['lat_dec'] = sp[1].apply(dms_to_decimal)

    return df

# -------------------------------------------------
# 6. ENGINE CORE v17.0 (PATCHED)
# -------------------------------------------------
def engine_v17_0(q,data):
    ql = q.lower()

    selected_adms = list(dict.fromkeys(
        [c for c,keys in COUNTRY_MAP.items() if any(k in ql for k in keys)]
    ))
    if not selected_adms:
        return None,[], "ADM identification error.",0,False

    mentions_assig = any(x in ql for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in ql for x in SYNONYMS['ALLOT_KEY'])

    def get_svc(text):
        if any(x in text for x in SYNONYMS['DAB_KEY']):
            return ['GS1','GS2','DS1','DS2']
        if any(x in text for x in SYNONYMS['TV_KEY']):
            return ['T02','G02','GT1','GT2','DT1','DT2']
        if any(x in text for x in SYNONYMS['FM_KEY']):
            return ['T01','T03','T04']
        return []

    svc_codes = get_svc(ql)

    reports = []
    final_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm']==adm].copy()
        if svc_codes:
            adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]

        a = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        t = a + l

        row = {'Adm':adm,'Total':t,'Assignments':a,'Allotments':l}
        reports.append(row)
        final_df = pd.concat([final_df,adm_df],ignore_index=True)

    # ----- Comparison Logic -----
    if len(reports)==2:
        key = 'Assignments' if mentions_assig else ('Allotments' if mentions_allot else 'Total')
        r1,r2 = reports
        if r1[key]>r2[key]:
            msg = f"{r1['Adm']} has more {key} than {r2['Adm']} by {r1[key]-r2[key]}"
        elif r2[key]>r1[key]:
            msg = f"{r2['Adm']} has more {key} than {r1['Adm']} by {r2[key]-r1[key]}"
        else:
            msg = f"{r1['Adm']} and {r2['Adm']} have equal {key}"
    else:
        msg = " | ".join(
            [f"{r['Adm']}: A={r['Assignments']} L={r['Allotments']} T={r['Total']}" for r in reports]
        )

    return final_df,reports,msg,100,True

# -------------------------------------------------
# 7. UI FLOW
# -------------------------------------------------
db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry (Supports Comparison & Total):")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    st.divider()

    res_df,reports,msg,conf,ok = engine_v17_0(query,db)

    if ok:
        cols = st.columns(len(reports))
        for i,r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']),width=250)
                st.metric(
                    f"{r['Adm']} Statistics",
                    f"Total: {r['Total']}",
                    f"A: {r['Assignments']} | L: {r['Allotments']}"
                )

        st.divider()

        if PLOTLY_AVAILABLE and reports:
            chart_df = pd.DataFrame(reports).set_index('Adm')

            # ✅ FIX for Plotly
            for c in ['Assignments','Allotments','Total']:
                chart_df[c] = pd.to_numeric(chart_df[c],errors='coerce').fillna(0)

            fig = px.bar(
                chart_df,
                y=['Assignments','Allotments'],
                barmode='group',
                title="Technical Distribution"
            )
            st.plotly_chart(fig,use_container_width=True)

        st.metric("Confidence",f"{conf}%")
        st.success(msg)
        play_audio(msg)

        if not res_df.empty:
            with st.expander("📊 Technical Records (Filtered)"):
                st.dataframe(res_df)
``
