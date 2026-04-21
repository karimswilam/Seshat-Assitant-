import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from difflib import get_close_matches

# --- 1. Flags & Knowledge Mapping ---
# استخدام CDN سريع جداً ومستقر للأعلام
FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png",
    'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png",
    'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png",
    'ISR': "https://flagcdn.com/w160/il.png"
}

MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب', 'assign'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab', 'digital sound', 'audio'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station', 'digital tv', 'television']
}

st.set_page_config(page_title="Seshat AI v12.0.6 - Elite Pro", layout="wide")

# --- 2. Advanced Neural Voice Engine (Edge-TTS) ---
async def speak_human(text, is_ar):
    # أصوات مايكروسوفت سحابة (Neural) - قمة الواقعية
    voice = "ar-EG-SalmaNeural" if is_ar else "en-US-GuyNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 3. Professional UI Styling ---
st.markdown("""
    <style>
    .main { background: #f4f7f9; }
    .ans-card { 
        background: white; 
        padding: 30px; 
        border-radius: 20px; 
        border-right: 10px solid #1e3a8a; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .flag-img { width: 140px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 15px; }
    .stProgress > div > div > div > div { background-color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def process_elite_query(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    adms = []; det_svc = None; filter_type = None
    
    # Matching Logic
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'
    
    if 'fm' in words or 'راديو' in q_low: det_svc = 'FM'
    if not adms: return None, "EGY", 0, "Unknown Request", is_ar

    # Strict Filtering Logic
    res = data[data['Adm'].astype(str).str.contains(adms[0], na=False)]
    if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
    if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
    elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]

    # Humanized Voice & Text Response
    found = len(res) > 0
    if is_ar:
        prefix = "نعم يا هندسة،" if found else "للاسف يا هندسة، مفيش"
        ans = f"{prefix} لقيت {len(res)} سجلات مطابقة في {adms[0]}."
    else:
        prefix = "Yes, sir." if found else "I'm sorry, sir. No"
        ans = f"{prefix} I found {len(res)} records for {adms[0]}."
    
    return res, adms[0], 100, ans, is_ar

# --- UI Layout ---
st.title("📡 Seshat AI v12.0.6 - Regulatory Elite Pro")
user_input = st.text_input("💬 Ask about spectrum data (Arabic or English):", placeholder="Does Israel have FM assignments?")

if db is not None:
    current_adm = "EGY"
    if user_input:
        res_df, top_adm, conf, human_ans, is_arabic = process_elite_query(user_input, db)
        
        # Header Dynamic Flag
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS[top_adm]}' class='flag-img'><br><h3>{top_adm} Intelligence Report</h3></div>", unsafe_allow_html=True)
        
        # Professional Answer Card
        st.markdown(f"<div class='ans-card'><h2>{human_ans}</h2><p>Confidence: {conf}%</p></div>", unsafe_allow_html=True)
        
        if not res_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Total Count", len(res_df))
                st.write("**Notice Types:**")
                st.write(res_df['Notice Type'].value_counts())
            with c2:
                st.bar_chart(res_df['Notice Type'].value_counts())
            
            st.dataframe(res_df, use_container_width=True)
        
        # 🎙️ Professional Human Voice (Microsoft Neural)
        try:
            audio_bytes = asyncio.run(speak_human(human_ans, is_arabic))
            st.audio(audio_bytes, format="audio/mp3")
        except:
            st.warning("Voice engine momentarily unavailable.")
    else:
        # Default State
        st.markdown(f"<div style='text-align:center;'><img src='{FLAGS['EGY']}' class='flag-img'></div>", unsafe_allow_html=True)
        st.info("System Ready. Please enter your query to begin analysis.")
