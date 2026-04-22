import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# --- 1. CONFIG & SYSTEM RESET ---
st.set_page_config(layout="wide", page_title="Seshat Voice AI v13.9")

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

# --- 2. THE CLEAN VOICE ENGINE ---
async def generate_clean_voice(text):
    """توليد صوت بشري نقي بدون قراءة الرموز البرمجية"""
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
    voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
    
    # تحسين النص للنطق: استبدال العلامات بوقفات طبيعية
    clean_text = text.replace("|", " . ").replace(":", " , ")
    
    # SSML مخفي تماماً عن العرض، يُستخدم للتوليد فقط
    ssml_text = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{"ar-EG" if is_ar else "en-US"}">
        <voice name="{voice}">
            <prosody rate="-10%">{clean_text}</prosody>
        </voice>
    </speak>
    """
    communicate = edge_tts.Communicate(ssml_text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def play_voice(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_clean_voice(text))
        st.audio(audio_bytes, format="audio/mp3")
    except: pass

# --- 3. LOGICAL ENGINE (Anti-Accumulation) ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

def engineering_engine(q, data):
    q_low = q.lower()
    # Reset local results for this specific query
    selected_adms = []; services = []
    
    wants_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    wants_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    if not wants_assig and not wants_allot: wants_assig = wants_allot = True

    words = re.findall(r'\w+', q_low)
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    
    for word in words:
        if len(word) == 3 and word.upper() in FLAGS:
            selected_adms.append(word.upper()); continue
        best_match = process.extractOne(word, all_keys, scorer=fuzz.WRatio)
        if best_match and best_match[1] > 75:
            for code, keys in SYNONYMS.items():
                if best_match[0] in keys:
                    if code in FLAGS: selected_adms.append(code)
                    elif code in ['DAB_KEY','TV_KEY','FM_KEY']: 
                        services.append(code.replace('_KEY',''))

    if not selected_adms: return None, [], "No Administration detected.", 0, False

    reports = []; final_df = pd.DataFrame()
    # تنظيف الـ services
    clean_svcs = []
    if 'DAB' in services or not services: clean_svcs.append('DAB')
    if 'TV' in services or not services: clean_svcs.append('TV')
    if 'FM' in services or not services: clean_svcs.append('FM')

    for adm in list(set(selected_adms)):
        adm_df = data[data['Adm'] == adm]
        for svc in clean_svcs:
            if svc == 'DAB': codes = ['GS1', 'GS2', 'DS1', 'DS2']
            elif svc == 'FM': codes = ['T01', 'T03', 'T04']
            else: codes = ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2']
            
            svc_df = adm_df[adm_df['Notice Type'].isin(codes)]
            a_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            l_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            if (wants_assig and a_count > 0) or (wants_allot and l_count > 0):
                reports.append({"Administration": f"{adm} ({svc})", "Assignments": a_count, "Allotments": l_count})
                final_df = pd.concat([final_df, svc_df])

    msg = " | ".join([f"{r['Administration']}: {r['Assignments'] if wants_assig else ''} {r['Allotments'] if wants_allot else ''}" for r in reports])
    return final_df, reports, msg, 100, True

# --- 4. UI DISPLAY ---
db = load_db()

st.title("🎙️ Seshat Voice AI Assistant v13.9")

# Section: Voice Input Simulation
st.markdown("### 🎙️ Voice Input Display")
query = st.text_input("Captured Voice (Text):", placeholder="e.g., Show me Egypt and Saudi DAB", key="voice_in")

if query:
    c_q1, c_q2 = st.columns([1, 4])
    with c_q1: 
        if st.button("🔊 Replay Question"): play_voice(query)
    with c_q2: st.info(f"Input Detected: {query}")

    if db is not None:
        res_df, reports, msg, conf, success = engineering_engine(query, db)
        
        if success and reports:
            # Row 1: Flags & Confidence
            col_f, col_c = st.columns([3, 1])
            with col_f:
                adms = list(set([r['Administration'].split()[0] for r in reports]))
                f_cols = st.columns(len(adms))
                for i, a in enumerate(adms): f_cols[i].image(FLAGS.get(a), width=70)
            with col_c:
                st.metric("Confidence Score", f"{conf}%")

            # Row 2: Charts & Data
            chart_df = pd.DataFrame(reports).set_index('Administration')
            st.bar_chart(chart_df[["Assignments", "Allotments"]])
            st.table(chart_df)

            # Section: Voice Output
            st.markdown("### 🔊 Assistant Voice Output")
            st.success(msg)
            play_voice(msg) # نطق الإجابة فوراً بصوت شاكر أو أندرو

            with st.expander("Technical Data Details"):
                st.dataframe(res_df, use_container_width=True)
