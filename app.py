import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (Master Knowledge)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

# 2. قاعدة بيانات الأعلام (ADM Flags)
ADM_DETAILS = {
    'EGY': {'flag': '🇪🇬', 'name': 'Egypt'},
    'ARS': {'flag': '🇸🇦', 'name': 'Saudi Arabia'},
    'TUR': {'flag': '🇹🇷', 'name': 'Turkey'},
    'CYP': {'flag': '🇨🇾', 'name': 'Cyprus'},
    'GRC': {'flag': '🇬🇷', 'name': 'Greece'},
    'ISR': {'flag': '🇮🇱', 'name': 'Israel'}
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة صوتية', 't-dab'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'station']
}

st.set_page_config(page_title="Seshat AI v12.0.3_Stable", layout="wide")

# CSS Pro Interface
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .flag-box { font-size: 80px; text-align: center; padding: 10px; background: white; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .stat-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; }
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

def engine_v12_stable(q, data):
    q_clean = q.lower().replace('؟', '').replace('?', '').strip()
    words = re.findall(r'\w+', q_clean)
    
    adms = []; det_svc = None; filter_type = None; exclude_codes = []
    
    # Matching Logic
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ADM_DETAILS.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'
    
    # Force FM detection if not DAB or TV
    if 'fm' in words or 'راديو' in q_clean: det_svc = 'FM'

    if not adms: return None, "EGY", 0, "No country detected."

    # Filtering
    stats = {}
    final_dfs = []
    for adm in adms:
        res = data[data['Adm'].astype(str).str.contains(adm, na=False)]
        if det_svc:
            res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
        if filter_type == 'allot':
            res = res[res['Notice Type'].isin(STRICT_ALLOT)]
        elif filter_type == 'assig':
            res = res[res['Notice Type'].isin(STRICT_ASSIG)]
        
        stats[adm] = len(res)
        final_dfs.append(res)

    conf = 100 if (adms and det_svc) else 80
    return pd.concat(final_dfs), adms[0], conf, stats

# --- UI Execution ---
user_query = st.text_input("🔍 Search Regulatory Data:", placeholder="e.g., تخصيصات اليونان المرئية")

if db is not None:
    # Default state is Egypt
    active_input = user_query if user_query else "Egypt"
    res_df, top_adm, confidence, stats_data = engine_v12_stable(active_input, db)
    
    # Display Flag Dashboard
    flag_icon = ADM_DETAILS.get(top_adm, {'flag': '🇪🇬'})['flag']
    adm_name = ADM_DETAILS.get(top_adm, {'name': 'Egypt'})['name']
    
    st.markdown(f"<div class='flag-box'>{flag_icon}<br><span style='font-size:20px;'>{adm_name}</span></div>", unsafe_allow_html=True)
    
    if user_query:
        st.progress(confidence / 100)
        st.write(f"**Engine Confidence:** {confidence}%")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"<div class='stat-card'><h3>{len(res_df)}</h3><p>Records Found</p></div>", unsafe_allow_html=True)
            if len(stats_data) > 1:
                st.write("---")
                for a, c in stats_data.items(): st.write(f"{ADM_DETAILS[a]['flag']} {a}: {c}")
        
        with col2:
            if not res_df.empty:
                st.bar_chart(res_df['Notice Type'].value_counts())
            else:
                st.warning("No records match your specific filters.")

        st.dataframe(res_df, use_container_width=True)
        
        # Audio Result
        v_txt = f"Found {len(res_df)} records for {adm_name}."
        try:
            tts = gTTS(text=v_txt, lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
