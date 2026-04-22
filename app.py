import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- 1. CONFIG & RECOVERY ---
st.set_page_config(layout="wide", page_title="Seshat Natural AI v13.8.1")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa', 'السعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'], 'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'], 'ISR': ['israel', 'isr', 'اسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص'],
    'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو']
}

# --- 2. HUMAN RHYTHM ENGINE (SSML) ---
async def generate_ssml_voice(text):
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    
    # تحويل النص لـ SSML مع وقفات بشرية (Breaks) وسرعة أبطأ
    rate = "-12%" # أبطأ قليلاً لزيادة الوقار
    
    # استبدال الفواصل بوقفات زمنية
    clean_text = text.replace("|", ' <break time="1000ms"/> ')
    clean_text = clean_text.replace(":", ' <break time="500ms"/> ')

    ssml_text = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{"ar-EG" if is_ar else "en-US"}">
        <voice name="{voice}">
            <prosody rate="{rate}">
                {clean_text}
            </prosody>
        </voice>
    </speak>
    """
    
    communicate = edge_tts.Communicate(ssml_text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def play_human_audio(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio_bytes = loop.run_until_complete(generate_ssml_voice(text))
    st.audio(audio_bytes, format="audio/mp3")

# --- 3. LOGICAL ENGINE (Integrated to avoid Duplicate ID Error) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

def engineering_engine(q, data):
    q_low = q.lower()
    words = re.findall(r'\w+', q_low)
    selected_adms = []; services = []
    
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper()); continue
        best_match = process.extractOne(word, all_keys, scorer=fuzz.WRatio)
        if best_match and best_match[1] > 75:
            for code, keys in SYNONYMS.items():
                if best_match[0] in keys:
                    if code in FLAGS: selected_adms.append(code)
                    elif code == 'DAB_KEY': services.append('DAB')
                    elif code == 'TV_KEY': services.append('TV')
                    elif code == 'FM_KEY': services.append('FM')

    if not selected_adms: return None, [], "Administration not identified", False

    reports = []; final_df = pd.DataFrame()
    services = list(set(services)) if services else ['SOUND', 'TV']

    for adm in list(set(selected_adms)):
        adm_df = data[data['Adm'] == adm]
        for svc in services:
            svc_codes = ['GS1', 'GS2', 'DS1', 'DS2'] if svc == 'DAB' else (['T01', 'T03', 'T04'] if svc == 'FM' else ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            row = {"Administration": f"{adm} ({svc})"}
            if wants_assig: row["Assignments"] = a_count
            if wants_allot: row["Allotments"] = l_count
            
            if (wants_assig and a_count > 0) or (wants_allot and l_count > 0):
                reports.append(row)
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r.get('Assignments','')} {r.get('Allotments','')}" for r in reports])
    return final_df, reports, msg, True

# --- 4. UI ---
db = load_db()

st.title("🎙️ Seshat Natural Assistant v13.8.1")
st.info("Human-like rhythm and error-free logic.")

query = st.text_input("✍️ Question:", placeholder="e.g. Compare Egypt and Saudi DAB", key="main_input")

if query and db is not None:
    res_df, reports, msg, success = engineering_engine(query, db)
    
    if success and reports:
        # Flags
        adms = list(set([r['Administration'].split()[0] for r in reports]))
        f_cols = st.columns(len(adms))
        for i, a in enumerate(adms): f_cols[i].image(FLAGS.get(a), width=70)

        # Charts
        chart_df = pd.DataFrame(reports).set_index('Administration')
        st.bar_chart(chart_df)
        st.table(chart_df)

        # Voice Output
        st.markdown("### 🔊 Assistant Voice Response")
        st.success(msg)
        play_human_audio(msg)

        with st.expander("Engineering Records"):
            st.dataframe(res_df, use_container_width=True)
