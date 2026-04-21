import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# 1. الدستور الهندسي (المرجع الصارم)
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
    'TUR': ['turkey', 'tur', 'تركيا'],
    'CYP': ['cyprus', 'cyp', 'قبرص'],
    'ALLOT_KEY': ['allotment', 'allotments', 'تعيين', 'توزيع', 'توزيعات', 'allot'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'تنسيب', 'assign'],
    'TOTAL_KEY': ['total', 'count', 'sum', 'إجمالي', 'عدد', 'مجموع', 'كل']
}

st.set_page_config(page_title="Seshat AI v12.0.2 - Precision Logic", layout="wide")

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

def engine_v12_0_2(q, data):
    # تنظيف السؤال ومعالجة النصوص المختلطة
    q_clean = q.lower().replace('؟', '').replace('?', '').strip()
    words = re.findall(r'\w+', q_clean) # استخراج الكلمات بدقة مهما كان الترتيب
    
    adms = []; det_svc = None; filter_type = None; exclude_codes = []
    
    # 1. لقط الدول والكلمات المفتاحية
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in ['EGY', 'ARS', 'ISR', 'TUR', 'CYP'] and code not in adms: adms.append(code)
                    elif code == 'ALLOT_KEY': filter_type = 'allot'
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
    
    # 2. تحديد الخدمة (إلزامي لضمان عدم خلط الأكواد)
    if 'fm' in words or 'راديو' in q_clean: det_svc = 'FM'
    elif 'dab' in words or 'داب' in q_clean: det_svc = 'DAB'
    elif 'tv' in words or 'تلفزيون' in q_clean: det_svc = 'TV'

    # 3. الاستبعادات
    if 'ماعدا' in q_clean or 'except' in q_clean:
        exclude_codes = [w.upper() for w in words if len(w) <= 4 and any(w.upper() in v for v in MASTER_KNOWLEDGE.values())]

    if not adms: return None, "Please specify a country.", 0, {}

    # 4. التصفية الصارمة (Strict Intersection)
    stats = {}
    final_dfs = []
    for adm in adms:
        res = data[data['Adm'].astype(str).str.contains(adm, na=False)]
        
        # تطبيق الخدمة (Service Filter)
        if det_svc:
            res = res[res['Notice Type'].isin(MASTER_KNOWLEDGE[det_svc])]
        
        # تطبيق التخصيص/التعيين (Type Filter)
        if filter_type == 'allot':
            res = res[res['Notice Type'].isin(STRICT_ALLOT)]
        elif filter_type == 'assig':
            res = res[res['Notice Type'].isin(STRICT_ASSIG)]
            
        if exclude_codes:
            res = res[~res['Notice Type'].isin(exclude_codes)]
            
        stats[adm] = len(res)
        final_dfs.append(res)

    final_df = pd.concat(final_dfs) if final_dfs else pd.DataFrame()
    
    # حساب الثقة بناءً على وضوح الخدمة والنوع والدولة
    conf = (50 if adms else 0) + (25 if det_svc else 0) + (25 if filter_type else 0)
    
    msg = f"Analysis for {', '.join(adms)} | Service: {det_svc if det_svc else 'All'} | Type: {filter_type if filter_type else 'All'}"
    return final_df, msg, conf, stats

st.title("📡 Seshat AI v12.0.2 - Precision Analytics")
user_input = st.text_input("Enter your query (Arabic/English/Mixed):")

if db is not None and user_input:
    res_df, msg, conf, stats = engine_v12_0_2(user_input, db)
    
    st.progress(conf / 100)
    st.write(f"**Confidence:** {conf}%")
    
    if res_df is not None:
        st.info(msg)
        
        # عرض النتائج الحسابية
        if len(stats) > 1:
            diff = max(stats.values()) - min(stats.values())
            st.success(f"📊 Comparison Results: {stats} | Difference: {diff}")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Total Records", len(res_df))
            for a, c in stats.items(): st.write(f"📍 {a}: {c}")
        with c2:
            if not res_df.empty:
                st.bar_chart(pd.Series(stats) if len(stats) > 1 else res_df['Notice Type'].value_counts())

        st.dataframe(res_df)
        
        # Voice Output
        try:
            v_msg = f"Found {len(res_df)} records. " + (f"Difference is {diff}" if len(stats)>1 else "")
            tts = gTTS(text=v_msg, lang='en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
