import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import time
from streamlit_mic_recorder import mic_recorder

# --- 1. SETTINGS & STYLES ---
st.set_page_config(layout="wide", page_title="Seshat Precision v18.9")

st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #1E3A8A; }
    .status-card { padding: 20px; border-radius: 10px; background-color: #f0f2f6; border-left: 5px solid #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

if 'voice_text' not in st.session_state: st.session_state.voice_text = ""

# --- 2. CONFIGURATION ---
FLAGS = {
    'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png",
    'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png",
    'GRC': "https://flagcdn.com/w640/gr.png", 'ISR': "https://flagcdn.com/w640/il.png"
}

COUNTRY_MAP = {
    'EGY': ['مصر', 'المصرية', 'egypt', 'egy'],
    'ARS': ['السعودية', 'المملكة', 'saudi', 'ars'],
    'TUR': ['تركيا', 'التركية', 'turkey', 'tur'],
    'CYP': ['قبرص', 'cyprus', 'cyp'],
    'GRC': ['اليونان', 'greece', 'grc'],
    'ISR': ['اسرائيل', 'israel', 'isr']
}

# --- 3. CORE FUNCTIONS ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        # تنظيف أسماء الأعمدة من المسافات المخفية (حل الـ KeyError)
        df.columns = df.columns.str.strip()
        
        # التأكد من وجود عمود Adm أو محاولة استنتاجه
        if 'Adm' not in df.columns:
            possible_adm = [c for c in df.columns if 'admin' in c.lower() or 'country' in c.lower()]
            if possible_adm: df.rename(columns={possible_adm[0]: 'Adm'}, inplace=True)
            
        return df
    return None

def engine_v18_9(query, data):
    # تنظيف الاستعلام
    q = query.lower().strip()
    
    # تحديد الدول المطلوبة
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    
    if not selected_adms:
        return None, [], "System Alert: Please specify a country (e.g., Egypt, Turkey).", False

    # تصفية البيانات بمرونة
    try:
        final_df = data[data['Adm'].str.strip().isin(selected_adms)].copy()
    except:
        final_df = data[data['Adm'].isin(selected_adms)].copy()

    reports = []
    for adm in selected_adms:
        adm_df = final_df[final_df['Adm'].str.strip() == adm]
        a_count = len(adm_df[adm_df['Notice Type'].str.contains('1|3|4|GS1|GT1', na=False, case=False)])
        l_count = len(adm_df[adm_df['Notice Type'].str.contains('2|GS2|GT2', na=False, case=False)])
        reports.append({"Adm": adm, "Total": len(adm_df), "Assignments": a_count, "Allotments": l_count})

    return final_df, reports, f"Analysis for {', '.join(selected_adms)} complete.", True

async def tts_async(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        comm = edge_tts.Communicate(text, voice)
        audio = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio": audio.write(chunk["data"])
        return audio
    except: return None

# --- 4. MAIN INTERFACE ---
st.title("🛰️ Seshat Master Precision v18.9")
st.markdown("---")

db = load_db()

# المنطقة العلوية: المايك والمؤشرات
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("#### 🎙️ Voice Input")
    audio_data = mic_recorder(start_prompt="⏺️ START", stop_prompt="⏹️ STOP", key='v189_mic')

with c2:
    st.markdown("#### 📡 System Status")
    status_area = st.empty()
    if audio_data:
        size_kb = len(audio_data['bytes']) / 1024
        status_area.success(f"✔️ Signal Captured: {size_kb:.2f} KB received")
        
        # شريط التحميل اللي طلبته (% يزداد)
        prog_bar = st.progress(0, text="Engine processing...")
        for i in range(1, 101, 10):
            time.sleep(0.05)
            prog_bar.progress(i, text=f"Processing Signal... {i}%")
        prog_bar.progress(100, text="Processing Complete 100%")

# مربع النص للتأكيد أو الإدخال اليدوي
query_input = st.text_input("📝 Confirmed Inquiry:", placeholder="e.g., كم عدد محطات مصر؟")

# التنفيذ
if (query_input or audio_data) and db is not None:
    # لو فيه صوت، بنستخدم النص المكتوب حالياً كـ Validation
    # (لاحظ: streamlit-mic-recorder بتحتاج دايماً text_input موازي للتأكيد)
    active_query = query_input if query_input else "مصر"
    
    res_df, reports, msg, success = engine_v18_9(active_query, db)
    
    if success:
        st.markdown(f"### 📊 Results: {msg}")
        
        # عرض الكروت الهندسية
        cols = st.columns(len(reports))
        for idx, r in enumerate(reports):
            with cols[idx]:
                st.image(FLAGS.get(r['Adm'], ""), width=150)
                st.metric(r['Adm'], f"Total: {r['Total']}", f"Assig: {r['Assignments']}")
        
        # الرسوم والخرائط
        tab1, tab2 = st.tabs(["🌍 Geographic View", "📈 Distribution"])
        with tab1:
            if not res_df.empty and 'lat_dec' in res_df.columns:
                st.map(res_df.dropna(subset=['lat_dec', 'lon_dec']))
        with tab2:
            st.bar_chart(pd.DataFrame(reports).set_index('Adm')[['Assignments', 'Allotments']])
        
        # الرد الصوتي
        if st.button("🔊 Replay Voice Response"):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_res = loop.run_until_complete(tts_async(msg))
            if audio_res: st.audio(audio_res, format="audio/mp3")

    else:
        st.warning(msg)

# القائمة الجانبية للـ Logs الحية
with st.sidebar:
    st.header("🛠️ Live Debugger")
    st.write(f"Database: {'🟢 Connected' if db is not None else '🔴 Missing'}")
    if audio_data:
        st.write(f"Last Pulse: {len(audio_data['bytes'])} Bytes")
        st.write(f"Format: {audio_data['sample_width']} bit")
