import streamlit as st
import pandas as pd
import os
import time
from gtts import gTTS
import io

# ======================================================
# 📡 PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Seshat AI – Engineering Assistant", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Professional Voice Assistant")

# ======================================================
# 📚 DOMAIN KNOWLEDGE
# ======================================================
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

COUNTRIES = {
    'EGY': ['egy', 'masr', 'مصر', 'egypt'],
    'ARS': ['ksa', 'saudi', 'سعودية', 'ars', 'saudia']
}

UNSUPPORTED_COUNTRIES = ['israel', 'jordan', 'uae', 'qatar', 'france', 'morocco']

# ======================================================
# 🔊 SERVER-SIDE VOICE ENGINE (gTTS)
# ======================================================
def speak_server(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"Audio Error: {e}")

# ======================================================
# 📂 DATA LOADING
# ======================================================
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    try:
        df = pd.read_excel(target)
        df.columns = [str(c).strip() for c in df.columns]
        for col in ['Adm', 'Notice Type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return pd.DataFrame()

uploaded_file = st.file_uploader("📂 Upload Data.xlsx", type=["xlsx"])
df = load_data(uploaded_file)

# ======================================================
# 🧠 INTELLIGENCE LAYER (Enhanced)
# ======================================================
def smart_intelligence(query):
    q = query.lower()
    intel = {"entities": {}, "intent": None, "unsupported": None, "conf_boost": 0.0}

    # 1. Country Detect
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            intel['entities']['country'] = code
            intel['conf_boost'] += 0.3
            break

    # 2. Anti-Hallucination for Unsupported
    for w in UNSUPPORTED_COUNTRIES:
        if w in q:
            intel['unsupported'] = w.upper()
            return intel # قطع الطريق فوراً

    # 3. Service Detect (Franco + Engineering Terms)
    if any(w in q for w in ['dab', 'digital', 'gs1', 'ds1', 'm7tat', 'stations']):
        intel['entities']['service'] = 'DAB'
        intel['conf_boost'] += 0.3
    elif any(w in q for w in ['tv', 'television', 'gt1', 'dt1']):
        intel['entities']['service'] = 'TV'
        intel['conf_boost'] += 0.3

    # 4. Intent Detect (Franco Support)
    if any(w in q for w in ['kam', '3dd', 'count', 'how many', 'عدد', 'total']):
        intel['intent'] = 'count'
        intel['conf_boost'] += 0.2

    return intel

# ======================================================
# ⚙️ QUERY ENGINE
# ======================================================
def process_query(query, df):
    intel = smart_intelligence(query)
    
    if intel['unsupported']:
        msg = f"I understood your question about {intel['unsupported']}, but I don't have its data."
        return pd.DataFrame(), False, ["Refusal"], 1.0, msg

    fdf = df.copy()
    intent_log = []
    
    country = intel['entities'].get('country')
    if country:
        fdf = fdf[fdf['Adm'] == country]
        intent_log.append(f"Country={country}")
    
    service = intel['entities'].get('service')
    if service:
        fdf = fdf[fdf['Notice Type'].isin(SERVICE_KNOWLEDGE[service])]
        intent_log.append(f"Service={service}")

    return fdf, (intel['intent'] == 'count'), intent_log, min(0.2 + intel['conf_boost'], 1.0), None

# ======================================================
# UI & MAIN LOGIC
# ======================================================
if "history" not in st.session_state: st.session_state.history = []

if df.empty:
    st.info("👋 Welcome! Please upload your Data.xlsx file to start analysis.")
else:
    user_query = st.text_input("💬 Ask Seshat (e.g., 'KSA DAB count'):")

    if user_query:
        start = time.time()
        result, is_count, log, conf, refusal = process_query(user_query, df)
        elapsed = time.time() - start
        st.session_state.history.append(user_query)

        if refusal:
            st.warning(refusal)
            speak_server(refusal)
        else:
            st.subheader("🧠 Intelligence Analysis")
            c1, c2, c3 = st.columns(3)
            c1.metric("Detected Intent", log[0] if log else "General")
            c2.metric("Records Found", len(result))
            c3.progress(conf, text=f"Confidence: {int(conf*100)}%")

            if is_count:
                msg = f"Found {len(result)} records."
                st.success(msg)
                speak_server(msg)
            else:
                st.dataframe(result.head(100), use_container_width=True)
                speak_server(f"Found {len(result)} records. Here is a preview.")
            
            if not result.empty:
                st.bar_chart(result['Notice Type'].value_counts())

# ======================================================
# HISTORY
# ======================================================
with st.sidebar:
    st.subheader("📁 Session History")
    for h in st.session_state.history[-5:]:
        st.caption(f"• {h}")
