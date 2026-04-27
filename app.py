import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# =================================================
# 1. CONFIG & INTERFACE
# =================================================
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


# =================================================
# 2. CONSTANTS & MAPS
# =================================================
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png",
    'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png",
    'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png",
    'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_DISPLAY = {
    'EGY': 'جمهورية مصر العربية',
    'ARS': 'المملكة العربية السعودية',
    'TUR': 'الجمهورية التركية',
    'CYP': 'جمهورية قبرص',
    'GRC': 'الجمهورية اليونانية',
    'ISR': 'إسرائيل'
}

COUNTRY_MAP = {
    'EGY': ['egypt','egy','مصر','المصرية'],
    'ARS': ['saudi','ars','ksa','السعودية','المملكة'],
    'TUR': ['turkey','tur','تركيا'],
    'CYP': ['cyprus','cyp','قبرص'],
    'GRC': ['greece','grc','اليونان'],
    'ISR': ['israel','isr','اسرائيل']
}

STRICT_ASSIG = ['T01','T03','T04','GS1','DS1','GT1','DT1','G01']
STRICT_ALLOT = ['T02','G02','GT2','DT2','GS2','DS2']

SYNONYMS = {
    'ASSIG': ['assignment','assignments','تخصيص','تخصيصات'],
    'ALLOT': ['allotment','allotments','توزيع','توزيعات'],
    'DAB': ['dab','داب','صوتية','صوتيه','sound'],
    'TV': ['tv','television','تلفزيون','مرئية'],
    'FM': ['fm','radio','راديو'],
}


# =================================================
# 3. DATA LOADER
# =================================================
@st.cache_data
def load_db():
    if not os.path.exists("Data.xlsx"):
        st.error("❌ Data.xlsx not found")
        return None

    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()

    if 'Administration' in df.columns:
        df = df.rename(columns={'Administration':'Adm'})

    return df


# =================================================
# 4. TTS
# =================================================
async def generate_audio(text):
    is_ar = any(c in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    communicate = edge_tts.Communicate(text, voice, rate="-10%")
    buf = io.BytesIO()
    async for ch in communicate.stream():
        if ch["type"] == "audio":
            buf.write(ch["data"])
    buf.seek(0)
    return buf

def play_audio(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio = loop.run_until_complete(generate_audio(text))
        st.audio(audio, format="audio/mp3")
    except:
        pass


# =================================================
# 5. ENGINE CORE v17.0 (PATCHED)
# =================================================
def engine_v17_0(query, data):
    q = query.lower()

    selected = []
    for adm, keys in COUNTRY_MAP.items():
        if any(k in q for k in keys):
            selected.append(adm)
    selected = list(dict.fromkeys(selected))

    if not selected:
        return None, [], "لم يتم تحديد دولة.", 0, False

    svc_codes = []
    if any(x in q for x in SYNONYMS['DAB']):
        svc_codes = ['GS1','GS2','DS1','DS2']
    elif any(x in q for x in SYNONYMS['TV']):
        svc_codes = ['T02','G02','GT1','GT2','DT1','DT2']
    elif any(x in q for x in SYNONYMS['FM']):
        svc_codes = ['T01','T03','T04']

    reports = []
    final_df = pd.DataFrame()

    for adm in selected:
        df_adm = data[data['Adm'] == adm].copy()
        if svc_codes:
            df_adm = df_adm[df_adm['Notice Type'].isin(svc_codes)]

        a = len(df_adm[df_adm['Notice Type'].isin(STRICT_ASSIG)])
        l = len(df_adm[df_adm['Notice Type'].isin(STRICT_ALLOT)])
        t = a + l

        reports.append({
            'Adm': adm,
            'Assignments': a,
            'Allotments': l,
            'Total': t
        })

        final_df = pd.concat([final_df, df_adm], ignore_index=True)

    if len(reports) == 2:
        r1, r2 = reports
        msg = f"{r1['Adm']} ({r1['Total']}) vs {r2['Adm']} ({r2['Total']})"
    else:
        msg = " | ".join([
            f"{r['Adm']}: A={r['Assignments']} L={r['Allotments']} T={r['Total']}"
            for r in reports
        ])

    return final_df, reports, msg, 100, True


# =================================================
# 6. UI FLOW
# =================================================
db = load_db()
query = st.text_input("🎙️ Enter Spectrum Inquiry (Supports Comparison & Total):")

if query and db is not None:
    st.markdown("### 🔈 Question Replay")
    play_audio(query)
    st.divider()

    res_df, reports, msg, conf, ok = engine_v17_0(query, db)

    if ok:
        cols = st.columns(len(reports))
        for i, r in enumerate(reports):
            with cols[i]:
                st.image(FLAGS.get(r['Adm']), width=250)
                st.metric(
                    COUNTRY_DISPLAY.get(r['Adm'], r['Adm']),
                    f"Total: {r['Total']}",
                    f"A: {r['Assignments']} | L: {r['Allotments']}"
                )

        if PLOTLY_AVAILABLE:
            chart_df = pd.DataFrame(reports).set_index('Adm')
            for c in ['Assignments','Allotments','Total']:
                chart_df[c] = pd.to_numeric(chart_df[c], errors='coerce').fillna(0)

            fig = px.bar(
                chart_df,
                y=['Assignments','Allotments'],
                barmode='group',
                title="Technical Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.metric("Confidence", f"{conf}%")
        st.success(msg)
        play_audio(msg)

        if not res_df.empty:
            with st.expander("📊 Technical Records"):
                st.dataframe(res_df)
