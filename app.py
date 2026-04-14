import streamlit as st
import pandas as pd
import os
import time
import re
from gtts import gTTS
import io

# ======================================================
# 📡 PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Seshat AI – Engineering Assistant", layout="wide", page_icon="📡")
st.title("📡 Seshat AI – Voice Engineering Assistant")

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
    'EGY': ['egy', 'masr', 'مصر'],
    'ARS': ['ksa', 'saudi', 'سعودية', 'ars']
}

# ======================================================
# 🔊 SERVER-SIDE VOICE ENGINE (Fixed)
# ======================================================
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"Voice Error: {e}")

# ======================================================
# 📂 DATA LOADING
# ======================================================
@st.cache_data(ttl=600)
def load_data(uploaded_file, default="Data.xlsx"):
    target = uploaded_file if uploaded_file else default if os.path.exists(default) else None
    if not target: return pd.DataFrame()
    df = pd.read_excel(target)
    df.columns = [str(c).strip() for c in df.columns]
    df['Adm'] = df['Adm'].astype(str).str.strip()
    df['Notice Type'] = df['Notice Type'].astype(str).str.strip()
    return df

uploaded_file = st.file_uploader("📂 Upload Excel (Optional)", type=["xlsx"])
df = load_data(uploaded_file)

# ======================================================
# 🧠 INTELLIGENCE LAYER (With Your Regex Guard)
# ======================================================
def smart_intelligence(query):
    q = query.lower()
    intel = {"entities": {}, "intent": None, "unsupported": None, "conf_boost": 0.0}

    # 1. Supported countries
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            intel['entities']['country'] = code
            intel['conf_boost'] += 0.3
            break

    # 2. Your Regex Guard (Preventing ISR/UAE Hallucination)
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
    elif any(w in q for w in ['fm', 'radio', 'broadcast']):
        intel['entities']['service'] = 'FM'
        intel['conf_boost'] += 0.3
    elif any(w in q for w in ['tv', 'television']):
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
    
    if intel['unsupported']:
        msg = f"I understood your question about {intel['unsupported']}, but I don't have data for it."
        return pd.DataFrame(), False, [f"Blocked: {intel['unsupported']}"], 1.0, msg

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

    return fdf, (intel['intent'] == 'count'), intent_log, min(0.35 + intel['conf_boost'], 1.0), None

# ======================================================
# UI & HISTORY
# ======================================================
if "history" not in st.session_state: st.session_state.history = []

if df.empty:
    st.warning("⚠️ No data loaded. Please upload Data.xlsx.")
else:
    user_query = st.text_input("💬 Ask Seshat (e.g., 'KSA DAB count'):")

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
            st.error(refusal)
            speak(refusal)
        else:
            if is_count:
                msg = f"I found {len(result)} matching records."
                st.metric("📊 Result Count", len(result))
                speak(msg)
            else:
                st.dataframe(result.head(50), use_container_width=True)
                speak(f"Found {len(result)} records.")
            
            if not result.empty:
                st.bar_chart(result['Notice Type'].value_counts())

st.sidebar.subheader("📁 Session History")
for h in st.session_state.history[-5:]:
    st.sidebar.write(f"• {h}")
