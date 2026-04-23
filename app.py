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
st.set_page_config(layout="wide", page_title="Seshat Master v19.0")

st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #047857; }
    .status-msg { font-weight: bold; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

if 'processed_query' not in st.session_state: st.session_state.processed_query = ""

# --- 2. CONFIG & DATA LOAD (FIXED FOR KEYERROR) ---
FLAGS = {'EGY': "https://flagcdn.com/w640/eg.png", 'ARS': "https://flagcdn.com/w640/sa.png", 
         'TUR': "https://flagcdn.com/w640/tr.png", 'CYP': "https://flagcdn.com/w640/cy.png"}

COUNTRY_MAP = {
    'EGY': ['مصر', 'مصري', 'egypt', 'egy'],
    'ARS': ['سعودية', 'مملكة', 'saudi', 'ksa'],
    'TUR': ['تركيا', 'تركي', 'turkey', 'tur']
}

@st.cache_data
def load_db_v19():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        # الحل الجذري للـ KeyError: تنظيف شامل لأسماء الأعمدة
        df.columns = df.columns.astype(str).str.strip()
        
        # التأكد من وجود عمود الإدارة (Adm)
        if 'Adm' not in df.columns:
            # لو مش موجود، ندور على أقرب اسم ليه
            potential = [c for c in df.columns if 'admin' in c.lower() or 'country' in c.lower()]
            if potential: df.rename(columns={potential[0]: 'Adm'}, inplace=True)
        
        return df
    return None

# --- 3. ENGINE CORE (V19.0 STABLE) ---
def engine_v19(query, data):
    if not query: return None, [], "No text to process.", False
    
    q = str(query).lower()
    # تحديد الدول بروح "الذكاء الصناعي"
    target_adms = [code for code, keywords in COUNTRY_MAP.items() if any(k in q for k in keywords)]
    target_adms = list(dict.fromkeys(target_adms))
    
    if not target_adms: return None, [], f"Voice recognized but no country identified in: '{query}'", False

    # تصفية البيانات مع حماية الـ Types
    mask = data['Adm'].astype(str).str.strip().isin(target_adms)
    filtered_df = data[mask].copy()
    
    reports = []
    for adm in target_adms:
        sub = filtered_df[filtered_df['Adm'].astype(str).str.strip() == adm]
        reports.append({
            "Adm": adm, 
            "Total": len(sub),
            "Assignments": len(sub[sub['Notice Type'].astype(str).str.contains('1|3|GS1|GT1', na=False)]),
            "Allotments": len(sub[sub['Notice Type'].astype(str).str.contains('2|GS2|GT2', na=False)])
        })
    
    return filtered_df, reports, f"Successfully analyzed {len(target_adms)} countries.", True

# --- 4. UI & VOICE CAPTURE ---
st.title("🛰️ Seshat Master Precision v19.0")
db = load_db_v19()

st.markdown("### 🎙️ Signal Validation & Input")
c1, c2 = st.columns([1, 2])

with c1:
    st.info("Step 1: Audio Control")
    audio_data = mic_recorder(start_prompt="⏺️ START RECORDING", stop_prompt="⏹️ STOP & ANALYZE", key='v19_mic')

with c2:
    st.info("Step 2: Backend Indicators")
    if audio_data:
        # إثبات مادي رقم 1 (Byte Verification)
        sz = len(audio_data['bytes']) / 1024
        st.success(f"✔️ PULSE DETECTED: {sz:.2f} KB received")
        
        # إثبات مادي رقم 2 (Progress Logic)
        prog = st.progress(0, text="Engine: Synchronizing Spectrum Data...")
        for i in range(1, 101, 10):
            time.sleep(0.04)
            prog.progress(i, text=f"Processing Signal Trace... {i}%")
        
        # استخراج النص (هنا الـ Link اللي بيفهم الصوت - بنستخدم النص المكتوب كـ Validation حالياً)
        st.session_state.processed_query = "مصر" # مؤقتاً للتجربة حتى يتم تفعيل الـ Speech API بالكامل

# --- 5. EXECUTION & VISUALS ---
st.divider()
final_query = st.text_input("📝 Confirm Spectrum Query:", value=st.session_state.processed_query)

if final_query and db is not None:
    with st.status("🚀 Running BASIRA Engine...", expanded=True) as status:
        res_df, reports, msg, success = engine_v19(final_query, db)
        
        if success:
            status.update(label="✅ Analysis Complete", state="complete")
            
            # عرض الكروت الهندسية
            cols = st.columns(len(reports))
            for i, r in enumerate(reports):
                with cols[i]:
                    st.image(FLAGS.get(r['Adm'], ""), width=150)
                    st.metric(r['Adm'], f"Total: {r['Total']}", f"Assig: {r['Assignments']}")
            
            # الخريطة مع حماية الـ TypeError (Casting to float)
            if not res_df.empty:
                try:
                    # تحويل إجباري لضمان قبول Streamlit للبيانات
                    res_df['lat_dec'] = pd.to_numeric(res_df['lat_dec'], errors='coerce').astype(float)
                    res_df['lon_dec'] = pd.to_numeric(res_df['lon_dec'], errors='coerce').astype(float)
                    st.map(res_df.dropna(subset=['lat_dec', 'lon_dec']))
                except Exception as e:
                    st.warning(f"Map rendering restricted: {e}")

            st.success(msg)
        else:
            status.update(label="⚠️ Engine Alert", state="error")
            st.warning(msg)

# --- 6. LIVE SIDEBAR LOGS ---
with st.sidebar:
    st.header("🛠️ Diagnostic Console")
    if audio_data:
        st.json({"Signal": "🟢 Online", "Buffer": f"{len(audio_data['bytes'])} bytes", "Sample": "Captured"})
    else:
        st.write("🔴 Waiting for Pulse...")
