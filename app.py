import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import time
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIG & SYSTEM UI ---
st.set_page_config(layout="wide", page_title="Seshat AI v21.0")

st.markdown("""
    <style>
    .reportview-container { background: #f8fafc; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    .engine-status { font-family: 'Courier New', monospace; font-size: 14px; color: #059669; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE CONSTANTS (V17.0 PROTECTED) ---
COUNTRY_MAP = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'ksa', 'السعودية', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان'],
    'ISR': ['israel', 'isr', 'اسرائيل']
}

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية'],
    'TV_KEY': ['tv', 'television', 'تلفزيون'],
    'TOTAL_KEY': ['total', 'egmali', 'إجمالي', 'اجمالي']
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

# --- 3. FAIL-SAFE DATA LOADER (THE FIX) ---
@st.cache_data
def load_and_standardize_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    
    if not target:
        st.error("❌ Data file missing from root directory!")
        return None

    try:
        df = pd.read_excel(target)
        # Force column names to be clean and detectable
        df.columns = df.columns.astype(str).str.strip()
        
        # Mapping to prevent KeyError: 'Adm'
        col_mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'ADMS'],
            'Notice Type': ['Notice Type', 'NT', 'Form', 'Type'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'Name']
        }
        
        for standard, aliases in col_mapping.items():
            for col in df.columns:
                if col in aliases:
                    df = df.rename(columns={col: standard})
                    break
        
        # Final Verification
        if 'Adm' not in df.columns:
            st.error("❌ Critical: 'Adm' column not found or renamed correctly.")
            return None
            
        return df
    except Exception as e:
        st.error(f"❌ Excel Processing Error: {e}")
        return None

# --- 4. THE CORE ENGINE (V17.0 LOGIC REBORN) ---
def engine_v21(q, data):
    q_low = q.lower()
    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    
    if not selected_adms:
        return None, [], "No countries identified in query.", 0, False

    reports = []
    final_df = pd.DataFrame()
    mentions_assig = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    mentions_allot = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])

    for adm in selected_adms:
        # Secure slicing to avoid KeyError or Empty Returns
        adm_df = data[data['Adm'].astype(str).str.strip().str.upper() == adm].copy()
        
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)])
        
        res = {
            "Adm": adm,
            "Total": a_count + l_count,
            "Assignments": a_count,
            "Allotments": l_count
        }
        reports.append(res)
        final_df = pd.concat([final_df, adm_df], ignore_index=True)

    # Simple Comparison Text for Voice
    if len(reports) >= 2:
        msg = f"Analysis complete for {len(reports)} countries. Comparison shows {reports[0]['Adm']} has {reports[0]['Total']} records vs {reports[1]['Adm']} with {reports[1]['Total']}."
    else:
        msg = f"Found {reports[0]['Total']} records for {reports[0]['Adm']}."

    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
st.markdown("## 🛰️ Seshat Master Precision v21.0")
db = load_and_standardize_db()

if db is not None:
    st.markdown('<p class="engine-status">✔️ DB_CORE: CONNECTED | ADM_FIELD: READY</p>', unsafe_allow_html=True)
    
    # Input Area
    c1, c2 = st.columns([1, 2])
    with c1:
        audio = mic_recorder(start_prompt="⏺️ START", stop_prompt="⏹️ STOP", key='v21_mic')
    
    with c2:
        # Simulation of Voice-to-Text for testing (Should be replaced by actual STT)
        input_text = st.text_input("Confirm Inquiry:", value="هي مصر عندها كم تخصيص اجمالي مقارنة بتركيا")

    if input_text:
        res_df, reports, msg, conf, success = engine_v21(input_text, db)
        
        if success:
            st.divider()
            cols = st.columns(len(reports))
            for i, r in enumerate(reports):
                with cols[i]:
                    st.metric(f"Country: {r['Adm']}", f"Total: {r['Total']}")
                    st.write(f"Assig: {r['Assignments']} | Allot: {r['Allotments']}")
            
            st.success(f"🔊 {msg}")
