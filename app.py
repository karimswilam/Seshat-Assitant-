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

# قاموس الأعلام والرموز
ADM_MAP = {
    'EGY': {'name': 'Egypt', 'flag': '🇪🇬'},
    'ARS': {'name': 'Saudi Arabia', 'flag': '🇸🇦'},
    'TUR': {'name': 'Turkey', 'flag': '🇹🇷'},
    'CYP': {'name': 'Cyprus', 'flag': '🇨🇾'},
    'GRC': {'name': 'Greece', 'flag': '🇬🇷'},
    'ISR': {'name': 'Israel', 'flag': '🇮🇱'}
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية', 'egibt'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'GRC': ['greece', 'grc', 'اليونان', 'يونان', 'المرئية'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'تعيين'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'إذاعة', 't-dab', 'digital sound'],
    'TV_KEY': ['tv', 'تلفزيون', 'تلفزيونية', 'مرئية', 'digital tv', 'station']
}

st.set_page_config(page_title="Seshat AI v12.0.3 - Professional", layout="wide")

# تحسين الواجهة بـ CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .flag-header { font-size: 50px; text-align: center; margin-bottom: 20px; }
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

def engine_v12_0_3(q, data):
    q_clean = q.lower().replace('؟', '').replace('?', '').strip()
    words = re.findall(r'\w+', q_clean)
    
    adms = []; det_svc = None; filter_type = None; exclude_codes = []
    
    # 1. لقط العناصر
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.75)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ADM_MAP.keys() and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'DAB_KEY': det_svc = 'DAB'
                    elif code == 'TV_KEY': det_svc = 'TV'

    # 2. الاستبعادات
    if 'ماعدا' in q_clean or 'except' in q_clean:
        exclude_codes = [w.upper() for w in words if len(w) <= 4 and any(w.upper() in v for v in MASTER_KNOWLEDGE.values())]

    if not adms: return None, "EGY", 0, "Specify a country."

    # 3. التصفية والحساب
    stats = {}
    final_dfs = []
    for adm in adms:
        res = data[data['Adm'].astype(str).str.contains(adm, na=False)]
        if det_svc: res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
        if filter_type == 'allot': res = res[res['Notice Type'].isin(STRICT_ALLOT)]
        elif filter_type == 'assig': res = res[res['Notice Type'].isin(STRICT_ASSIG)]
        if exclude_codes: res = res[~res['Notice Type'].isin(exclude_codes)]
        stats[adm] = len(res); final_dfs.append(res)

    # حساب الثقة (Confidence) بشكل أذكى
    conf = 100 if (adms and (det_svc or filter_type)) else 75
    
    return pd.concat(final_dfs), adms[0], conf, f"Results for {adms}"

# --- الواجهة الرسومية ---
user_input = st.text_input("📡 Regulatory Query (e.g., تخصيصات اليونان مرئية):")

if db is not None:
    res_df, active_adm, confidence, msg = engine_v12_0_3(user_input if user_input else "EGY", db)
    
    # عرض العلم
    flag = ADM_MAP.get(active_adm, {'flag': '🇪🇬'})['flag']
    st.markdown(f"<div class='flag-header'>{flag}</div>", unsafe_allow_html=True)
    
    st.progress(confidence / 100)
    st.write(f"**Confidence Level:** {confidence}%")
    
    if user_input:
        st.info(msg)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Records Found", len(res_df))
        with c2:
            if not res_df.empty: st.bar_chart(res_df['Notice Type'].value_counts())
        
        st.dataframe(res_df)
        
        # Voice
        try:
            tts = gTTS(text=f"Found {len(res_df)} records.", lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
