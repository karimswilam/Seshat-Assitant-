import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
import base64
import numpy as np
from rapidfuzz import process, fuzz
from streamlit_mic_recorder import mic_recorder

try:
import plotly.express as px
PLOTLY_AVAILABLE = True
except ImportError:
PLOTLY_AVAILABLE = False

# =========================

# 🎙️ SIMPLE VISUAL METER (NO sounddevice)

# =========================

def estimate_audio_level(audio_bytes):
try:
audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
if len(audio_array) == 0:
return 0
amplitude = np.abs(audio_array).mean()
level = min(amplitude / 3000, 1.0)
return level
except:
return 0

def render_audio_meter(level):
color = "#22c55e"
if level > 0.6:
color = "#ef4444"
elif level > 0.3:
color = "#eab308"

```
bar_html = f"""
<div style="width:100%; background:#222; border-radius:10px; padding:5px;">
    <div style="width:{int(level*100)}%; height:20px; 
                background:{color};
                border-radius:10px; transition: width 0.3s;">
    </div>
</div>
"""
st.markdown(bar_html, unsafe_allow_html=True)
```

# =========================

# 🎙️ SPEECH TO TEXT

# =========================

def speech_to_text(audio_bytes):
import requests
try:
response = requests.post(
"https://api.openai.com/v1/audio/transcriptions",
headers={"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"},
files={"file": ("audio.wav", audio_bytes, "audio/wav")},
data={"model": "gpt-4o-mini-transcribe"}
)
return response.json().get("text", "")
except:
return ""

# =========================

# 🎙️ TEXT TO SPEECH

# =========================

async def generate_audio(text):
try:
voice = "ar-EG-ShakirNeural"
communicate = edge_tts.Communicate(text, voice)
audio_data = io.BytesIO()
async for chunk in communicate.stream():
if chunk["type"] == "audio":
audio_data.write(chunk["data"])
audio_data.seek(0)
return audio_data
except:
return None

def play_audio(text):
try:
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
data = loop.run_until_complete(generate_audio(text))
if data:
st.audio(data, format="audio/mp3")
except:
pass

# =========================

# 📊 LOAD DATA (FIXED)

# =========================

@st.cache_data
def load_db():
files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
if files:
df = pd.read_excel(files[0])
df.columns = df.columns.str.strip()  # ✅ FIX KeyError
return df
return None

# =========================

# 🧠 SIMPLE ENGINE

# =========================

def simple_engine(q, df):
q = q.lower()

```
if 'israel' in q or 'اسرائيل' in q:
    df = df[df['Adm'] == 'ISR']
elif 'egypt' in q or 'مصر' in q:
    df = df[df['Adm'] == 'EGY']
else:
    return None, "❌ مش قادر أحدد الدولة"

return df, f"✅ عدد النتائج: {len(df)}"
```

# =========================

# 🎨 UI

# =========================

st.set_page_config(layout="wide", page_title="Seshat AI v21.5")

st.title("🎙️ Voice Assistant (Cloud Safe Mode)")

# 🎤 Recorder

audio = mic_recorder(
start_prompt="🎤 Start Recording",
stop_prompt="⏹ Stop",
key="recorder"
)

st.markdown("### 🔊 Voice Signal Indicator")

if audio:
level = estimate_audio_level(audio['bytes'])
render_audio_meter(level)

```
if level < 0.05:
    st.warning("⚠️ مفيش صوت واضح")
else:
    st.success("✅ الصوت وصل")

st.markdown("### ⚙️ Processing...")
text = speech_to_text(audio['bytes'])

if not text.strip():
    st.error("❌ لم يتم التعرف على أي كلام")
else:
    st.success(f"📝 النص: {text}")
    play_audio(text)

    query = text

    db = load_db()

    if db is not None:
        res_df, msg = simple_engine(query, db)

        st.markdown("### 🔊 الرد")
        st.success(msg)
        play_audio(msg)

        if res_df is not None and not res_df.empty:
            st.dataframe(res_df)

            if PLOTLY_AVAILABLE:
                chart_df = res_df.groupby("Adm").size().reset_index(name="count")
                if not chart_df.empty:  # ✅ FIX Plotly crash
                    fig = px.bar(chart_df, x="Adm", y="count")
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("❌ مفيش داتا")
```

else:
st.info("🎤 اضغط Start Recording وابدأ الكلام")

# ⌨️ TEXT FALLBACK

st.divider()
text_query = st.text_input("⌨️ أو اكتب سؤالك")

if text_query:
db = load_db()
if db is not None:
res_df, msg = simple_engine(text_query, db)
st.success(msg)
if res_df is not None:
st.dataframe(res_df)
