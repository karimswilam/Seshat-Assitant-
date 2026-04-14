```python
import streamlit as st
import pandas as pd
import io
from gtts import gTTS

st.set_page_config(page_title="Seshat Engineering Hub", layout="wide")
st.title("📡 Seshat AI - Data Analytics Mode")

# --- Mapping ---
mapping_dict = {
    'GS1': 'T-DAB Assignment',
    'GS2': 'T-DAB Allotment',
    'DS1': 'Digital Sound Assignment',
    'DS2': 'Digital Sound Allotment'
}

# --- Load Data ---
@st.cache_data(ttl=600)
def load_data(file):
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]

        if 'Notice Type' in df.columns:
            df['Notice_Description'] = df['Notice Type'].map(mapping_dict)

        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        return pd.DataFrame()

# --- Upload بدل hardcode ---
uploaded_file = st.file_uploader("📂 Upload Excel File", type=["xlsx"])

df = load_data(uploaded_file) if uploaded_file else pd.DataFrame()

# --- Query ---
query = st.text_input(
    "💬 اسأل عن أي بيانات (Franko/Arabic/English):",
    placeholder="مثلاً: ars 3ndha kam record?"
)

if query and not df.empty:
    with st.spinner("🔍 Processing..."):
        q = query.lower()
        f_df = df.copy()

        # --- Safety checks ---
        has_adm = 'Adm' in f_df.columns
        has_notice = 'Notice Type' in f_df.columns

        # --- Country Filter ---
        country_filters = {
            'ARS': ['ars', 'سعودية', 'saudi', 'ksa'],
            'EGY': ['egy', 'مصر', 'egypt']
        }

        if has_adm:
            for code, words in country_filters.items():
                if any(w in q for w in words):
                    f_df = f_df[f_df['Adm'] == code]

        # --- Notice Type Filter ---
        if has_notice:
            for n_type in mapping_dict.keys():
                if n_type.lower() in q:
                    f_df = f_df[f_df['Notice Type'] == n_type]

        # --- Query Type Detection ---
        is_count_query = any(w in q for w in [
            'kam', '3dd', 'count', 'total', 'كم', 'عدد', 'إجمالي'
        ])

        # --- Response ---
        if is_count_query:
            result_count = len(f_df)

            st.metric("📊 Total Records", result_count)

            # --- Voice ---
            try:
                tts_text = f"العدد الإجمالي هو {result_count}"
                tts = gTTS(text=tts_text, lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io.getvalue(), format="audio/mp3")
            except:
                st.warning("⚠️ الصوت غير متاح حالياً")

        else:
            st.write(f"🤖 Found {len(f_df)} records")

            cols_to_show = [c for c in [
                'Adm',
                'Site/Allotment Name',
                'Notice Type',
                'Notice_Description'
            ] if c in f_df.columns]

            st.dataframe(f_df[cols_to_show].head(100))

        # --- Chart ---
        if not f_df.empty and has_notice:
            st.subheader("📊 Distribution")
            st.bar_chart(f_df['Notice Type'].value_counts())

else:
    st.info("💡 Upload a file and start asking questions.")
```
