import streamlit as st
import pandas as pd
import os
import io
import re
from gtts import gTTS
from difflib import get_close_matches

# --- 1. CONFIG & UI ---
st.set_page_config(layout="wide", page_title="Seshat AI v13.0 - Professional Edition")

FLAGS = {
    'EGY': "https://flagcdn.com/w160/eg.png", 'ARS': "https://flagcdn.com/w160/sa.png",
    'TUR': "https://flagcdn.com/w160/tr.png", 'CYP': "https://flagcdn.com/w160/cy.png",
    'GRC': "https://flagcdn.com/w160/gr.png", 'ISR': "https://flagcdn.com/w160/il.png"
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
    'EGY': ['egypt', 'egy', 'مصر', 'المصرية'],
    'ARS': ['saudi', 'ars', 'السعودية', 'ksa', 'سعودية'],
    'TUR': ['turkey', 'tur', 'تركيا'],
    'ISR': ['israel', 'isr', 'اسرائيل', 'إسرائيل'],
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
    'DAB_KEY': ['dab', 'داب'], 'TV_KEY': ['tv', 'تلفزيون'], 'FM_KEY': ['fm', 'راديو']
}

@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target); df.columns = df.columns.str.strip()
        return df
    return None

db = load_db()

# --- 2. THE OMNI-ENGINE ---
def omni_engine(q, data):
    q_low = q.lower()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    words = re.findall(r'\w+', q_low)
    
    selected_adms = []
    services = []
    filter_type = None # assig, allot, or None (both)

    # التحقق من الدول والخدمات والأنواع
    all_keys = [item for sublist in SYNONYMS.values() for item in sublist]
    for word in words:
        match = get_close_matches(word, all_keys, n=1, cutoff=0.8)
        if match:
            for code, keys in SYNONYMS.items():
                if match[0] in keys:
                    if code in FLAGS and code not in selected_adms: selected_adms.append(code)
                    elif code == 'DAB_KEY' and 'DAB' not in services: services.append('DAB')
                    elif code == 'TV_KEY' and 'TV' not in services: services.append('TV')
                    elif code == 'FM_KEY' and 'FM' not in services: services.append('FM')
                    elif code == 'ASSIG_KEY': filter_type = 'assig'
                    elif code == 'ALLOT_KEY': filter_type = 'allot'

    if not selected_adms: return None, [], 0, "No ADM detected", is_ar, False
    
    # Logical Check: FM Allotments
    if 'FM' in services and filter_type == 'allot':
        msg = "Illogical: FM has no allotments." if not is_ar else "غير منطقي: الـ FM ليس له توزيعات."
        return None, selected_adms, 0, msg, is_ar, False

    # Filtering & Calculation
    final_results = []
    total_df = pd.DataFrame()

    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm]
        adm_report = {"Administration": adm}
        
        # لو مفيش خدمة محددة، نشتغل على كله
        active_services = services if services else ['SOUND', 'TV']
        
        for svc in active_services:
            svc_codes = MASTER_KNOWLEDGE.get(svc, [])
            svc_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
            
            # تفصيل حسب النوع (Assig / Allot)
            assig_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)])
            allot_count = len(svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)])
            
            if filter_type == 'assig':
                adm_report[f"{svc} Assig"] = assig_count
                total_df = pd.concat([total_df, svc_df[svc_df['Notice Type'].isin(STRICT_ASSIG)]])
            elif filter_type == 'allot':
                adm_report[f"{svc} Allot"] = allot_count
                total_df = pd.concat([total_df, svc_df[svc_df['Notice Type'].isin(STRICT_ALLOT)]])
            else:
                adm_report[f"{svc} Assig"] = assig_count
                adm_report[f"{svc} Allot"] = allot_count
                total_df = pd.concat([total_df, svc_df])
        
        final_results.append(adm_report)

    ans_text = "Analysis complete for " + ", ".join(selected_adms)
    return total_df, final_results, 100, ans_text, is_ar, True

# --- 3. UI LAYOUT ---
st.title("🛰️ Seshat Omni-Assistant v13.0")
query = st.text_input("🎙️ Enter your complex query (e.g., Egypt TV Assig vs Saudi DAB Allot):")

if db is not None and query:
    res_df, reports, conf, msg, is_ar, logical = omni_engine(query, db)
    
    # 1. Row for Flags & Confidence
    top_cols = st.columns([3, 1])
    with top_cols[0]:
        flag_cols = st.columns(len(reports) if reports else 1)
        for i, r in enumerate(reports):
            flag_cols[i].image(FLAGS.get(r['Administration']), width=70, caption=r['Administration'])
    with top_cols[1]:
        st.metric("Confidence %", f"{conf}%")
        st.progress(conf)

    if not logical:
        st.error(msg)
    else:
        # 2. Row for Answer & Voice
        st.info(f"📝 {msg}")
        
        # 3. Bar Charts (Non-Stacked / Multi-Service)
        chart_df = pd.DataFrame(reports).set_index('Administration')
        # تنظيف الأعمدة الصفرية لتحسين الرؤية
        chart_df = chart_df.loc[:, (chart_df != 0).any(axis=0)]
        st.bar_chart(chart_df)

        # 4. Data Table
        st.dataframe(res_df, use_container_width=True)

        # 5. THE VOICE (Always Present)
        try:
            tts = gTTS(text=msg, lang='ar' if is_ar else 'en')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: st.warning("Voice engine temporarily unavailable")

elif db is None:
    st.error("Please upload Data.xlsx")
