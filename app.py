import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (ثابت)
MASTER_KNOWLEDGE = {
    'SOUND': ['T01', 'T03', 'T04', 'GS1', 'GS2', 'DS1', 'DS2'],
    'FM': ['T01', 'T03', 'T04'],
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'PLAN_COMPLIANCE': ['TB2', 'TB7'],
    'ADMINISTRATIVE': ['TB1', 'TB3', 'TB4', 'TB6', 'TB8', 'TB5', 'TB9']
}

SYNONYMS = {
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'المملكة'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'توزيع', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تنسيب', 'assign']
}

st.set_page_config(page_title="Seshat AI v12.7 - Interactive", layout="wide")

# محرك التحميل الجينيريك
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

# --- محرك البحث التفاعلي الجديد ---
def advanced_engine(q, data):
    q_clean = re.sub(r'[?؟.!]', '', q.lower()).strip()
    words = q_clean.split()
    
    det_adm = None; det_svc = None; filter_type = None; exclude_code = None
    
    # 1. لقط الإدارة (Priority)
    all_syns = {k: v for k, v in SYNONYMS.items()}
    for word in words:
        for code, keys in all_syns.items():
            match = get_close_matches(word, keys, n=1, cutoff=0.8)
            if match:
                if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP']: det_adm = code
                elif code == 'ALLOT_KEY': filter_type = 'allot'
                elif code == 'ASSIG_KEY': filter_type = 'assig'
                break
    
    # 2. لقط الخدمة أو الأكواد المستبعدة (Logic: Except/ماعدا)
    if 'ماعدا' in q_clean or 'except' in q_clean:
        potential_codes = [w.upper() for w in words if len(w) <= 4]
        for c in potential_codes:
            if any(c in codes for codes in MASTER_KNOWLEDGE.values()):
                exclude_code = c

    for svc in MASTER_KNOWLEDGE.keys():
        if svc.lower().replace("_", " ") in q_clean or (svc == 'FM' and 'راديو' in q_clean) or (svc == 'DAB' and 'داب' in q_clean):
            det_svc = svc; break

    if not det_adm: return None, "Please specify a country (e.g., Egypt, Turkey)."

    # تصفية البيانات الأولية للدولة
    base_data = data[data['Adm'].astype(str).str.contains(det_adm, na=False)]
    
    # السيناريو 1: سؤال عام (إجمالي التوزيعات/التخصيصات لكل الخدمات)
    if det_adm and filter_type and not det_svc:
        res = base_data.copy()
        if filter_type == 'allot': res = res[res['Notice Type'].str.contains('2|G2|T2', na=False)]
        else: res = res[res['Notice Type'].str.contains('1|G1|T1|T01', na=False)]
        return res, f"Total {filter_type}s for {det_adm} across ALL services. (Tip: You can ask for a specific service like FM or TV)"

    # السيناريو 2: سؤال محدد بخدمة
    if det_adm and det_svc:
        res = base_data[base_data['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
        if filter_type == 'allot': res = res[res['Notice Type'].str.contains('2|G2|T2', na=False)]
        elif filter_type == 'assig': res = res[res['Notice Type'].str.contains('1|G1|T1|T01', na=False)]
        
        if exclude_code:
            res = res[res['Notice Type'] != exclude_code]
        
        return res, f"Found {len(res)} records for {det_adm} {det_svc}."

    return base_data, f"Showing all records for {det_adm}. (Tip: Add 'FM', 'TV', 'Allotment', or 'Assignment' to narrow down)"

st.title("📡 Seshat AI – Smart Engineering v12.7")
user_input = st.text_input("Ask: (e.g., تركيا عندها كام توزيع؟ or Egypt TV except T02)")

if db is not None and user_input:
    res_df, msg = advanced_engine(user_input, db)
    
    if res_df is not None:
        st.info(msg)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Records Count", len(res_df))
        with col2:
            # Dashboard البار تشارت اللي طلبت نرجعه
            if not res_df.empty:
                st.subheader("Notice Type Distribution")
                st.bar_chart(res_df['Notice Type'].value_counts())
        
        # عرض البيانات
        st.dataframe(res_df)
        
        # تلميح ذكي (Smart Hint) لو النتائج كتير ومفيش فلتر
        if len(res_df) > 50 and 'assignment' not in user_input.lower():
            st.warning("💡 Hint: You can say 'How many assignments' to filter results.")
    else:
        st.error(msg)
