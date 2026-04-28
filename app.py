import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import numpy as np
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment
import nest_asyncio

# تفعيل nest_asyncio للتعامل مع edge-tts
nest_asyncio.apply()

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. CONFIG & INTERFACE ---
st.set_page_config(layout="wide", page_title="Se-Chat v18.6", page_icon="📡")

st.markdown("""
    <style>
    .flag-container { display: flex; justify-content: center; margin-bottom: 10px; }
    .flag-img { width: 120px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stButton button { width: 100%; border-radius: 10px; }
    .centered-msg { 
        text-align: center; font-size: 20px; color: #1E3A8A; 
        padding: 20px; border: 2px solid #1E3A8A; border-radius: 10px; 
        background-color: #F0F4F8; margin: 20px 0;
    }
    /* Horizontal Scroll for Flags */
    .scroll-container {
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        padding: 10px;
        gap: 15px;
        background: #f8f9fa;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

LOGO_FILE = "Designer.png" 
PROJECT_NAME = "Se-Chat التنسيق الدولي للطيف v18.6"
PROJECT_SLOGAN = " Spectrum Intelligence & Governance"

header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
with header_col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=120)
    st.markdown(f'<div style="text-align: center;"><h1 style="color: #1E3A8A; margin-bottom: 0;">{PROJECT_NAME}</h1><p style="color: #475569; font-size: 16px;">{PROJECT_SLOGAN}</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. EXTENDED DATA FOR ALL ADMs ---
# القائمة الكاملة التي زودتنا بها
ADM_LIST = {
    'AFG': 'Afghanistan', 'AFS': 'South Africa', 'AGL': 'Angola', 'ALB': 'Albania', 'ALG': 'Algeria',
    'AND': 'Andorra', 'ARG': 'Argentine', 'ARM': 'Armenia', 'ARS': 'Saudi Arabia', 'ATG': 'Antigua and Barbuda',
    'AUS': 'Australia', 'AUT': 'Austria', 'AZE': 'Azerbaijan', 'B': 'Brazil', 'BAH': 'Bahamas',
    'BDI': 'Burundi', 'BEL': 'Belgium', 'BEN': 'Benin', 'BFA': 'Burkina Faso', 'BGD': 'Bangladesh',
    'BHR': 'Bahrain', 'BIH': 'Bosnia and Herzegovina', 'BLR': 'Belarus', 'BLZ': 'Belize', 'BOL': 'Bolivia',
    'BOT': 'Botswana', 'BRB': 'Barbados', 'BRM': 'Myanmar', 'BRU': 'Brunei', 'BTN': 'Bhutan',
    'BUL': 'Bulgaria', 'CAF': 'Central African Republic', 'CAN': 'Canada', 'CBG': 'Cambodia', 'CHL': 'Chile',
    'CHN': 'China', 'CLM': 'Colombia', 'CLN': 'Sri Lanka', 'CME': 'Cameroon', 'COD': 'DR Congo',
    'COG': 'Congo', 'COM': 'Comoros', 'CPV': 'Cabo Verde', 'CTI': 'Côte d\'Ivoire', 'CTR': 'Costa Rica',
    'CUB': 'Cuba', 'CVA': 'Vatican', 'CYP': 'Cyprus', 'CZE': 'Czech Republic', 'D': 'Germany',
    'DJI': 'Djibouti', 'DMA': 'Dominica', 'DNK': 'Denmark', 'DOM': 'Dominican Republic', 'E': 'Spain',
    'EGY': 'Egypt', 'EQA': 'Ecuador', 'ERI': 'Eritrea', 'EST': 'Estonia', 'ETH': 'Ethiopia',
    'F': 'France', 'FIN': 'Finland', 'FJI': 'Fiji', 'FSM': 'Micronesia', 'G': 'United Kingdom',
    'GAB': 'Gabon', 'GEO': 'Georgia', 'GHA': 'Ghana', 'GMB': 'Gambia', 'GNB': 'Guinea-Bissau',
    'GNE': 'Equatorial Guinea', 'GRC': 'Greece', 'GRD': 'Grenada', 'GTM': 'Guatemala', 'GUI': 'Guinea',
    'GUY': 'Guyana', 'HND': 'Honduras', 'HNG': 'Hungary', 'HOL': 'Netherlands', 'HRV': 'Croatia',
    'HTI': 'Haiti', 'I': 'Italy', 'IND': 'India', 'INS': 'Indonesia', 'IRL': 'Ireland',
    'IRN': 'Iran', 'IRQ': 'Iraq', 'ISL': 'Iceland', 'ISR': 'Israel', 'J': 'Japan',
    'JMC': 'Jamaica', 'JOR': 'Jordan', 'KAZ': 'Kazakhstan', 'KEN': 'Kenya', 'KGZ': 'Kyrgyzstan',
    'KIR': 'Kiribati', 'KNA': 'Saint Kitts and Nevis', 'KOR': 'Korea', 'KRE': 'North Korea', 'KWT': 'Kuwait',
    'LAO': 'Lao', 'LBN': 'Lebanon', 'LBR': 'Liberia', 'LBY': 'Libya', 'LCA': 'Saint Lucia',
    'LIE': 'Liechtenstein', 'LSO': 'Lesotho', 'LTU': 'Lithuania', 'LUX': 'Luxembourg', 'LVA': 'Latvia',
    'MAU': 'Mauritius', 'MCO': 'Monaco', 'MDA': 'Moldova', 'MDG': 'Madagascar', 'MEX': 'Mexico',
    'MHL': 'Marshall Islands', 'MKD': 'North Macedonia', 'MLA': 'Malaysia', 'MLD': 'Maldives', 'MLI': 'Mali',
    'MLT': 'Malta', 'MNE': 'Montenegro', 'MNG': 'Mongolia', 'MOZ': 'Mozambique', 'MRC': 'Morocco',
    'MTN': 'Mauritania', 'MWI': 'Malawi', 'NCG': 'Nicaragua', 'NGR': 'Niger', 'NIG': 'Nigeria',
    'NMB': 'Namibia', 'NOR': 'Norway', 'NPL': 'Nepal', 'NRU': 'Nauru', 'NZL': 'New Zealand',
    'OMA': 'Oman', 'PAK': 'Pakistan', 'PHL': 'Philippines', 'PLW': 'Palau', 'PNG': 'Papua New Guinea',
    'PNR': 'Panama', 'POL': 'Poland', 'POR': 'Portugal', 'PRG': 'Paraguay', 'PRU': 'Peru',
    'QAT': 'Qatar', 'ROU': 'Romania', 'RRW': 'Rwanda', 'RUS': 'Russia', 'S': 'Sweden',
    'SDN': 'Sudan', 'SEN': 'Senegal', 'SEY': 'Seychelles', 'SLM': 'Solomon Islands', 'SLV': 'El Salvador',
    'SMO': 'Samoa', 'SMR': 'San Marino', 'SNG': 'Singapore', 'SOM': 'Somalia', 'SRB': 'Serbia',
    'SRL': 'Sierra Leone', 'SSD': 'South Sudan', 'STP': 'Sao Tome and Principe', 'SUI': 'Switzerland', 'SUR': 'Suriname',
    'SVK': 'Slovakia', 'SVN': 'Slovenia', 'SWZ': 'Eswatini', 'SYR': 'Syria', 'TCD': 'Chad',
    'TGO': 'Togo', 'THA': 'Thailand', 'TJK': 'Tajikistan', 'TKM': 'Turkmenistan', 'TLS': 'Timor-Leste',
    'TON': 'Tonga', 'TRD': 'Trinidad and Tobago', 'TUN': 'Tunisia', 'TUR': 'Türkiye', 'TUV': 'Tuvalu',
    'TZA': 'Tanzania', 'UAE': 'UAE', 'UGA': 'Uganda', 'UKR': 'Ukraine', 'URG': 'Uruguay',
    'USA': 'USA', 'UZB': 'Uzbekistan', 'VCT': 'Saint Vincent', 'VEN': 'Venezuela', 'VTN': 'Viet Nam',
    'VUT': 'Vanuatu', 'YEM': 'Yemen', 'ZMB': 'Zambia', 'ZWE': 'Zimbabwe'
}

# Mapping ITU codes to 2-letter ISO for flags
ISO_MAP = {
    'EGY': 'eg', 'ARS': 'sa', 'TUR': 'tr', 'CYP': 'cy', 'GRC': 'gr', 'ISR': 'il', 'USA': 'us', 'F': 'fr', 'D': 'de', 'I': 'it', 'G': 'gb', 'RUS': 'ru', 'UAE': 'ae', 'JOR': 'jo', 'LBN': 'lb', 'QAT': 'qa', 'KWT': 'kw', 'OMA': 'om', 'BHR': 'bh', 'IRQ': 'iq'
    # سيتم تكملة الباقي ديناميكياً في العرض قدر الإمكان
}

STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

CAT_MAP = {
    'DAB': ['GS1','GS2','DS1','DS2'],
    'TV': ['T02','G02','GT1','GT2','DT1','DT2'],
    'FM': ['T01','T03','T04']
}

COUNTRY_MAP = {code: [name.lower(), code.lower()] for code, name in ADM_LIST.items()}
# إضافة الأسماء العربية للدول المشهورة لضمان دقة البحث
COUNTRY_MAP['EGY'].extend(['مصر', 'المصرية'])
COUNTRY_MAP['ARS'].extend(['السعودية', 'المملكة'])

SYNONYMS = {
    'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات', 'allot', 'allots'],
    'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات', 'assig', 'assigs', 'تردد', 'ترددات', 'مstation', 'مستقبل'],
    'DAB_KEY': ['dab', 'داب', 'صوتية', 'صوتيه', 'digital audio'],
    'TV_KEY': ['tv', 'television', 'تلفزيون', 'تلفزيونية', 'مرئية', 'مرئيه'],
    'FM_KEY': ['fm', 'radio', 'راديو'],
    'EXCEPT_KEY': ['except', 'ma3ada', 'ماعدا', 'بدون', 'without', 'excluding'],
    'GE06_KEY': ['ge06', 'geneva06', 'geneva 06', 'geneva o 6', 'جنيف 06', 'جي إي 06', 'ge06d'],
    'GE84_KEY': ['ge84', 'geneva84', 'geneva 84', 'جنيف 84', 'جي إي 84', 'اربعة وثمانين', '84']
}

# --- 3. UTILITIES ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or not isinstance(dms_str, str): return None
        clean_str = re.sub(r'[^0-9.NSEW ]', ' ', dms_str).strip().upper()
        parts = re.findall(r"(\d+)", clean_str)
        direction = re.findall(r"([NSEW])", clean_str)
        if len(parts) >= 3 and direction:
            deg, mn, sec = map(float, parts[:3])
            decimal = deg + (mn / 60.0) + (sec / 3600.0)
            if direction[0] in ['S', 'W']: decimal *= -1
            return decimal
    except: return None
    return None

def apply_phonetic_correction(text):
    if not text: return text
    corrections = {
        r'\bدياب\b': 'داب', r'\bدب\b': 'داب', r'\bباب\b': 'داب',
        r'\bناصيف\b': 'مصر', r'\bناصر\b': 'مصر', r'\bمتر\b': 'مصر',
        r'\bزومبايل\b': 'إسرائيل', r'\bعزرائيل\b': 'إسرائيل'
    }
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def speech_to_text_robust(audio_data):
    if audio_data is None: return None
    r = sr.Recognizer()
    try:
        webm_audio = io.BytesIO(audio_data['bytes'])
        audio_segment = AudioSegment.from_file(webm_audio, format="webm")
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.record(source)
        try:
            english_text = r.recognize_google(audio, language="en-US")
            if any(word in english_text.lower() for word in ['how', 'many', 'egypt', 'assignment', 'allotment', 'ge06']):
                return english_text
        except: pass
        raw_text = r.recognize_google(audio, language="ar-EG")
        return apply_phonetic_correction(raw_text)
    except Exception: return None

async def generate_audio_stream(text):
    try:
        is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in text)
        voice = "ar-EG-ShakirNeural" if is_ar else "en-US-AndrewNeural"
        clean_text = re.sub(r'<[^>]*>', '', text).replace("|", " . ").replace(":", " , ")
        communicate = edge_tts.Communicate(clean_text, voice, rate="-5%")
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_data.write(chunk["data"])
        audio_data.seek(0)
        return audio_data
    except: return None

def speak_text(text):
    if text:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(generate_audio_stream(text))
        if data: st.audio(data, format="audio/mp3", autoplay=True)

# --- 4. ENGINE CORE V18.6 ---
@st.cache_data
def load_db():
    main_df = pd.DataFrame()
    target_main = "Data.xlsx"
    if os.path.exists(target_main):
        df1 = pd.read_excel(target_main)
        df1.columns = df1.columns.str.strip()
        df1['Source_Plan'] = 'GE06'
        main_df = df1
    target_fm = "FM.xlsx"
    if os.path.exists(target_fm):
        df2 = pd.read_excel(target_fm)
        df2.columns = df2.columns.str.strip()
        df2['Source_Plan'] = 'GE84'
        main_df = pd.concat([main_df, df2], ignore_index=True)
    if not main_df.empty:
        mapping = {'Adm': ['Administration', 'Adm', 'Country'], 'Notice Type': ['Notice Type', 'NT']}
        for std_name, synonyms in mapping.items():
            for col in main_df.columns:
                if col in synonyms:
                    main_df = main_df.rename(columns={col: std_name})
                    break
        if 'Geographic Coordinates' in main_df.columns:
            coords_split = main_df['Geographic Coordinates'].astype(str).str.split(expand=True)
            if coords_split.shape[1] >= 2:
                main_df['lon_dec'] = coords_split[0].apply(dms_to_decimal)
                main_df['lat_dec'] = coords_split[1].apply(dms_to_decimal)
        if 'Assigned Frequency' in main_df.columns:
            def clean_freq(f):
                try:
                    num = re.findall(r"[-+]?\d*\.\d+|\d+", str(f))
                    return float(num[0]) if num else 0.0
                except: return 0.0
            main_df['freq_val'] = main_df['Assigned Frequency'].apply(clean_freq)
        return main_df
    return None

def engine_v18_6(q, data):
    q_low = q.lower().strip()
    is_ar = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    freq_numbers = re.findall(r"(\d+\.?\d*)", q_low)
    if any(key in q_low for key in ['تردد', 'frequency']):
        if len(freq_numbers) == 1:
            return None, [], "Please write the frequency range / برجاء كتابة نطاق التردد", 0, False

    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    selected_adms = list(dict.fromkeys(selected_adms))
    
    if not selected_adms:
        return None, [], "Country is not in database", 0, False

    f_start, f_stop = (None, None)
    if len(freq_numbers) >= 2:
        nums = sorted([float(n) for n in freq_numbers])
        f_start, f_stop = nums[0], nums[1]

    filter_plan = None
    if any(x in q_low for x in SYNONYMS['GE06_KEY']): filter_plan = 'GE06'
    elif any(x in q_low for x in SYNONYMS['GE84_KEY']): filter_plan = 'GE84'

    is_allot_only = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    is_assig_only = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    comp_type = "Assignments" if is_assig_only else ("Allotments" if is_allot_only else "Total")

    wanted_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): wanted_codes.extend(CAT_MAP['DAB'])
    if any(x in q_low for x in SYNONYMS['TV_KEY']): wanted_codes.extend(CAT_MAP['TV'])
    if any(x in q_low for x in SYNONYMS['FM_KEY']): wanted_codes.extend(CAT_MAP['FM'])
    
    if not wanted_codes: 
        wanted_codes = CAT_MAP['DAB'] + CAT_MAP['TV'] + CAT_MAP['FM'] + ['G01']

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_full = data[data['Adm'] == adm].copy()
        if filter_plan: adm_full = adm_full[adm_full['Source_Plan'] == filter_plan]
        if f_start and f_stop: adm_full = adm_full[(adm_full['freq_val'] >= f_start) & (adm_full['freq_val'] <= f_stop)]
        
        adm_filtered = adm_full[adm_full['Notice Type'].isin(wanted_codes)]
        a_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ASSIG)])
        l_count = len(adm_filtered[adm_filtered['Notice Type'].isin(STRICT_ALLOT)])
        
        reports.append({
            "Adm": adm, "Assignments": a_count, "Allotments": l_count, "Total": a_count + l_count,
            "Stats": {'DAB': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['DAB'])]),
                      'TV': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['TV'])]),
                      'FM': len(adm_filtered[adm_filtered['Notice Type'].isin(CAT_MAP['FM'])])},
            "DisplayName": ADM_LIST[adm]
        })
        final_df = pd.concat([final_df, adm_filtered], ignore_index=True)

    msg = ""
    for r in reports:
        val = r[comp_type] if comp_type in r else r['Total']
        msg += f"{r['DisplayName']}: {val} Records. "
    
    return final_df, reports, msg, 100, True

# --- 5. UI FLOW ---
db = load_db()

# --- Search & Inputs ---
with st.container(border=True):
    col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
    with col_v1:
        voice_raw = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key="v186_mic")
    
    if 'query_input' not in st.session_state: st.session_state.query_input = ""
    
    input_val = speech_to_text_robust(voice_raw) if voice_raw else ""
    if input_val: st.session_state.query_input = input_val

    with col_v2:
        query = st.text_input("Spectrum Inquiry:", value=st.session_state.query_input, key="main_input")
        st.session_state.query_input = query
    with col_v3:
        if st.button("👂"): speak_text(query)

# --- NEW: SCROLLING LIST OF ALL ADMs ---
st.write("🌍 **Quick Country Lookup:**")
# نستخدم Container مع CSS مخصص للـ Scrolling
st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
cols = st.columns(len(ADM_LIST))
for i, (adm_code, adm_name) in enumerate(ADM_LIST.items()):
    with cols[i]:
        # استخراج رمز الدولة للعلم
        iso = ISO_MAP.get(adm_code, adm_code[:2].lower())
        flag_url = f"https://flagcdn.com/w80/{iso}.png"
        
        # إنشاء زر يحمل صورة العلم واسم الدولة
        if st.button(f"{adm_name}", key=f"btn_scroll_{adm_code}"):
            st.session_state.query_input = f"{adm_name} services comparison"
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- Engine Execution ---
active_query = st.session_state.query_input

if active_query and db is not None:
    res_df, reports, msg, conf, success = engine_v18_6(active_query, db)
    
    if not success:
        st.markdown(f'<div class="centered-msg">{msg}</div>', unsafe_allow_html=True)
    else:
        st.success(msg)
        
        if len(reports) == 1:
            r = reports[0]
            iso = ISO_MAP.get(r["Adm"], r["Adm"][:2].lower())
            st.markdown(f'<div class="flag-container"><img src="https://flagcdn.com/w160/{iso}.png" class="flag-img"></div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("DAB", r['Stats']['DAB'])
            col2.metric("TV", r['Stats']['TV'])
            col3.metric("FM", r['Stats']['FM'])
            
            c1, c2 = st.columns(2)
            with c1:
                map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
                if not map_data.empty:
                    st.plotly_chart(px.scatter_mapbox(map_data, lat="lat_dec", lon="lon_dec", color="Notice Type", zoom=4, height=400, mapbox_style="carto-positron"), use_container_width=True)
            with c2:
                svc_data = pd.DataFrame({'Service': list(r['Stats'].keys()), 'Count': list(r['Stats'].values())})
                st.plotly_chart(px.pie(svc_data, values='Count', names='Service', hole=0.4, title="Distribution"), use_container_width=True)
        else:
            # Comparison View
            st.plotly_chart(px.bar(pd.DataFrame(reports), x="DisplayName", y=["Assignments", "Allotments"], barmode="group"), use_container_width=True)

        with st.expander("Technical Records"): st.dataframe(res_df, use_container_width=True)
