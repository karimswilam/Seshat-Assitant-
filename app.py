import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- 1. CONFIG & STANDARDS ---
st.set_page_config(layout="wide", page_title="Seshat AI v14.5 Masterpiece")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

# المنطق الهندسي الصارم للـ Notice Types
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'], 
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assign'],
    'DAB_KEY': ['dab', 'داب', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'FM_KEY': ['fm', 'radio', 'راديو']
}

# --- 2. NEURAL VOICE ENGINE (Input & Output) ---
async def generate_neural_audio(text):
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
        data = asyncio.run(generate_neural_audio(text))
        st.audio(data, format="audio/mp3")
    except: pass

# --- 3. THE CORE LOGICAL ENGINE (Hybrid & Comparative) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def advanced_engine(q, data):
    q_low = q.lower()
    words = re.findall(r'\w+', q_low)
    
    # 1. Identify Intent (Assignment vs Allotment)
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    # 2. Identify Service (DAB, FM, TV)
    service_target = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): service_target.append('DAB')
    if any(x in q_low for x in SYNONYMS['FM_KEY']): service_target.append('FM')
    if any(x in q_low for x in SYNONYMS['TV_KEY']): service_target.append('TV')

    # 3. Identify Administrations (Multi-target for Comparisons)
    selected_adms = []
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper())
        for code, keys in SYNONYMS.items():
            if code in FLAGS and word in keys: selected_adms.append(code)
    
    selected_adms = list(set(selected_adms))
    if not selected_adms: return None, [], "No country identified.", 0, False

    reports = []; final_df = pd.DataFrame()
    
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        # Filter by Service
        if 'DAB' in service_target: adm_df = adm_df[adm_df['Notice Type'].isin(['GS1','GS2','DS1','DS2'])]
        elif 'FM' in service_target: adm_df = adm_df[adm_df['Notice Type'].isin(['T01','T03','T04'])]
        elif 'TV' in service_target: adm_df = adm_df[adm_df['Notice Type'].isin(['T02','G02','GT1','GT2','DT1','DT2'])]

        # Calculate Results based on STRICT logic
        a_df = adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]
        l_df = adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]
        
        res_row = {"Adm": adm}
        if wants_assig: res_row["Assignments"] = len(a_df)
        if wants_allot: res_row["Allotments"] = len(l_df)
        
        if (wants_assig and len(a_df) > 0) or (wants_allot and len(l_df) > 0):
            reports.append(res_row)
            if wants_assig and not wants_allot: final_df = pd.concat([final_df, a_df])
            elif wants_allot and not wants_assig: final_df = pd.concat([final_df, l_df])
            else: final_df = pd.concat([final_df, adm_df])

    # 4. Construct Speech Message
    msg_parts = []
    for r in reports:
        part = f"In {r['Adm']}: "
        if "Assignments" in r: part += f"{r['Assignments']} Assignments "
        if "Allotments" in r: part += f"and {r['Allotments']} Allotments"
        msg_parts.append(part)
    
    msg = " | ".join(msg_parts)
    return final_df, reports, msg, 100, True

# --- 4. UI DESIGN ---
db = load_db()
st.title("🎙️ Seshat Master AI Assistant v14.5")

query = st.text_input("🎙️ Speak or Type Question:", placeholder="e.g. Compare DAB assignments between Egypt and Israel", key="voice_input")

if query:
    # 1. Question Playback
    st.markdown("### 🔈 Recorded Input")
    play_audio(query)

    if db is not None:
        res_df, reports, msg, conf, success = advanced_engine(query, db)
        
        if success and reports:
            # Row 1: Flags & Confidence
            c1, c2 = st.columns([3, 1])
            with c1:
                f_cols = st.columns(len(reports))
                for i, r in enumerate(reports): f_cols[i].image(FLAGS.get(r['Adm']), width=70, caption=r['Adm'])
            with c2: st.metric("Confidence Score", f"{conf}%")

            # Row 2: Visual Comparison
            chart_df = pd.DataFrame(reports).set_index('Adm')
            st.bar_chart(chart_df)
            st.table(chart_df)

            # Row 3: Human Voice Output
            st.markdown("### 🔊 Assistant Response")
            st.success(msg)
            play_audio(msg)

            with st.expander("Show Engineering Records"):
                st.dataframe(res_df, use_container_width=True)
