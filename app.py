# ======================================================
# 📡 Seshat AI – Final Voice Engineering Assistant
# ======================================================

import streamlit as st
import pandas as pd
import os
import time
import re
import speech_recognition as sr
import pyttsx3

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Seshat AI – Engineering Assistant",
    layout="wide",
    page_icon="📡"
)

st.title("📡 Seshat AI – Voice Engineering Assistant")

# ======================================================
# DOMAIN KNOWLEDGE
# ======================================================
SERVICE_KNOWLEDGE = {
    'DAB': ['GS1', 'GS2', 'DS1', 'DS2'],
    'TV': ['T02', 'G02', 'GT1', 'GT2', 'DT1', 'DT2'],
    'FM': ['T01'],
    'AM': ['T03', 'T04']
}

COUNTRIES = {
    'EGY': ['egy', 'masr', 'مصر'],
    'ARS': ['ksa', 'saudi', 'سعودية', 'ars']
}

# ======================================================
# VOICE ENGINE
# ======================================================
engine = pyttsx3.init()
engine.setProperty('rate', 170)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙 Listening...")
        audio = r.listen(source, timeout=5)
    try:
        return r.recognize_google(audio)
    except:
        return ""

# ======================================================
# DATA LOADING
# ======================================================
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target:
        return pd.DataFrame()

    df = pd.read_excel(target)
    df.columns = [str(c).strip() for c in df.columns]
    df['Adm'] = df['Adm'].astype(str).str.strip()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip()
    return df

uploaded_file = st.file_uploader("📂 Upload Excel (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

# ======================================================
# 🧠 INTELLIGENCE LAYER (ENHANCED)
# ======================================================
def smart_intelligence(query):
    q = query.lower()
    intel = {
        "entities": {},
        "intent": None,
        "unsupported": None,
        "conf_boost": 0.0
    }

    # 1. Supported countries (white‑list)
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            intel['entities']['country'] = code
            intel['conf_boost'] += 0.3
            break

    # 2. Regex guard: any 3‑letter country‑like code
    potential_codes = re.findall(r'\b[a-z]{3}\b', q)
    for p_code in potential_codes:
        p_code_upper = p_code.upper()
        if p_code_upper not in COUNTRIES and p_code_upper != 'DAB':
            intel['unsupported'] = p_code_upper
            intel['conf_boost'] += 0.15
            return intel

    # 3. Services
    if any(w in q for w in ['dab', 'digital', 'gs1', 'ds1']):
        intel['entities']['service'] = 'DAB'
        intel['conf_boost'] += 0.3

    if any(w in q for w in ['fm', 'radio', 'broadcast']):
        intel['entities']['service'] = 'FM'
        intel['conf_boost'] += 0.3

    if any(w in q for w in ['tv', 'television']):
        intel['entities']['service'] = 'TV'
        intel['conf_boost'] += 0.3

    # 4. Intent
    if any(w in q for w in ['kam', '3dd', 'count', 'how many', 'عدد', 'total']):
        intel['intent'] = 'count'
        intel['conf_boost'] += 0.2

    return intel

# ======================================================
# ⚙️ QUERY ENGINE
# ======================================================
def process_query(query, df):
    intel = smart_intelligence(query)

    # Unsupported country detected → polite refusal
    if intel['unsupported']:
        return (
            pd.DataFrame(),
            False,
            [f"Unsupported Country: {intel['unsupported']}"],
            min(0.6 + intel['conf_boost'], 1.0),
            f"I understood your question, but I don't have data for {intel['unsupported']}."
        )

    fdf = df.copy()
    intent_log = []
    confidence = min(0.35 + intel['conf_boost'], 1.0)

    # Country filter
    country = intel['entities'].get('country')
    if country:
        fdf = fdf[fdf['Adm'] == country]
        intent_log.append(f"Country={country}")

    # Service filter
    service = intel['entities'].get('service')
    if service and service in SERVICE_KNOWLEDGE:
        fdf = fdf[fdf['Notice Type'].isin(SERVICE_KNOWLEDGE[service])]
        intent_log.append(f"Service={service}")

    is_count = intel['intent'] == 'count'

    return fdf, is_count, intent_log, confidence, None

# ======================================================
# SESSION MEMORY
# ======================================================
if "history" not in st.session_state:
    st.session_state.history = []

# ======================================================
# UI
# ======================================================
if df.empty:
    st.warning("⚠️ No data loaded.")
else:
    col1, col2 = st.columns([3, 1])

    with col1:
        user_query = st.text_input("💬 Ask Seshat (Text or Voice)")

    with col2:
        if st.button("🎙 Speak"):
            user_query = listen()
            if user_query:
                st.success(user_query)

    if user_query:
        start = time.time()
        result, is_count, intent_log, conf, refusal = process_query(user_query, df)
        elapsed = time.time() - start

        st.session_state.history.append(user_query)

        st.subheader("🧠 AI Understanding")
        st.write("Detected:", ", ".join(intent_log) if intent_log else "General Query")
        st.progress(conf)
        st.caption(f"Confidence: {int(conf*100)}% | Time: {elapsed:.2f}s")

        if refusal:
            st.warning(refusal)
            speak(refusal)
            st.stop()

        if is_count:
            msg = f"I found {len(result)} matching records."
            st.metric("📊 Result Count", len(result))
            speak(msg)
        else:
            msg = f"I found {len(result)} records. Showing preview."
            speak(msg)
            st.dataframe(result.head(50), use_container_width=True)

        if not result.empty:
            st.bar_chart(result['Notice Type'].value_counts())

# ======================================================
# HISTORY
# ======================================================
st.subheader("📁 Session History")
for i, h in enumerate(st.session_state.history[-5:], 1):
    st.write(f"{i}. {h}")
