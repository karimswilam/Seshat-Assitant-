import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي المعتمد
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']
STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1']

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا', 'türkiye'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب']
}

st.set_page_config(page_title="Seshat AI v12.0.1 - Comparison Mode", layout="wide")

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

def advanced_logic_v12_0_1(q, data):
    q_clean = re.sub(r'[?؟.!]', '', q.lower()).strip()
    words = q_clean.split()
    
    adms = []; det_svc = None; filter_type = None; exclude_codes = []
    
    # 1. لقط الدول (Multi-Country detection)
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']:
                        if code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
    
    # 2. لقط الخدمة والاستبعادات
    for svc in MASTER_KNOWLEDGE.keys():
        if svc.lower().replace("_", " ") in q_clean or (svc == 'FM' and 'راديو' in q_clean) or (svc == 'DAB' and 'داب' in q_clean):
            det_svc = svc; break
    
    if 'ماعدا' in q_clean or 'except' in q_clean:
        exclude_codes = [w.upper() for w in words if len(w) <= 4 and any(w.upper() in codes for codes in MASTER_KNOWLEDGE.values())]

    if not adms: return None, "Please specify at least one country.", 0, None, None

    # 3. محرك المقارنة والحسابات
    results_map = {}
    for adm in adms:
        temp_res = data[data['Adm'].astype(str).str.contains(adm, na=False)]
        if det_svc: temp_res = temp_res[temp_res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
        if filter_type == 'allot': temp_res = temp_res[temp_res['Notice Type'].isin(STRICT_ALLOT)]
        elif filter_type == 'assig': temp_res = temp_res[temp_res['Notice Type'].isin(STRICT_ASSIG)]
        if exclude_codes: temp_res = temp_res[~temp_res['Notice Type'].isin(exclude_codes)]
        results_map[adm] = temp_res

    # إعداد البيانات للعرض
    final_df = pd.concat(results_map.values())
    conf = min(len(adms)*30 + (20 if det_svc else 0) + (20 if filter_type else 0), 100)
    
    counts = {k: len(v) for k, v in results_map.items()}
    math_info = ""
    if len(adms) > 1:
        diff = max(counts.values()) - min(counts.values())
        math_info = f"📊 Comparison: {counts} | Difference: {diff} records."
    else:
        math_info = f"Total records for {adms[0]}: {counts[adms[0]]}"

    return final_df, f"Analysis for: {', '.join(adms)}", conf, math_info, counts

st.title("📡 Seshat AI v12.0.1 - Comparison Master")
user_input = st.text_input("Ask (e.g., قارن بين مصر وقبرص في توزيعات التلفزيون):")

if db is not None and user_input:
    res_df, message, confidence, math_msg, stats = advanced_logic_v12_0_1(user_input, db)
    
    # 1. Confidence Indicator
    st.progress(confidence / 100)
    st.write(f"**Confidence Indicator:** {confidence}%")
    
    if res_df is not None:
        st.info(message)
        if math_msg: st.success(math_msg)
        
        # 2. Visual Dashboard
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Total Rows in View", len(res_df))
            for adm, count in stats.items():
                st.write(f"📍 {adm}: {count}")
        with c2:
            if not res_df.empty:
                if len(stats) > 1:
                    st.subheader("Visual Comparison by Country")
                    # رسم بياني للمقارنة بين الدولتين
                    st.bar_chart(pd.Series(stats))
                else:
                    st.subheader("Notice Type Distribution")
                    st.bar_chart(res_df['Notice Type'].value_counts())
        
        # 3. Data Table
        st.dataframe(res_df)
        
        # 4. Voice Output
        try:
            v_txt = f"Analysis complete. {math_msg}"
            tts = gTTS(text=v_txt, lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
    else:
        st.error(message)
