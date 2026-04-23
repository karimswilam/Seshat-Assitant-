import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_mic_recorder import speech_to_text
import time

# --- 1. CONFIGURATION & MOCK DATA ---
# (استبدل المسار بملف الإكسيل الخاص بك)
EXCEL_PATH = "spectrum_data.xlsx" 

FLAGS = {
    "EGY": "https://flagcdn.com/w320/eg.png",
    "ARS": "https://flagcdn.com/w320/sa.png",
    "CYP": "https://flagcdn.com/w320/cy.png",
    "GRC": "https://flagcdn.com/w320/gr.png",
    "TUR": "https://flagcdn.com/w320/tr.png",
    "ISR": "https://flagcdn.com/w320/il.png"
}

st.set_page_config(page_title="Seshat Master Precision v17.6", layout="wide")

# --- 2. CORE ENGINE ---
def engine_v17_6(query, df):
    """
    محرك البحث المطور مع حماية ضد البيانات الناقصة
    """
    query_l = query.lower()
    res_df = pd.DataFrame()
    reports = []
    
    # منطق الفلترة (مثال مبسط يعتمد على اسم الدولة)
    adms_found = [adm for adm in FLAGS.keys() if adm.lower() in query_l or adm in query]
    
    if not adms_found:
        # البحث بالأسماء العربية/الإنجليزية الشائعة
        mapping = {"مصر": "EGY", "السعودية": "ARS", "قبرص": "CYP", "اليونان": "GRC", "تركيا": "TUR", "اسرائيل": "ISR"}
        for k, v in mapping.items():
            if k in query: adms_found.append(v)

    if adms_found:
        res_df = df[df['Adm'].isin(adms_found)]
        for adm in adms_found:
            count = len(res_df[res_df['Adm'] == adm])
            reports.append({'Adm': adm, 'Total': count})
        
        msg = f"تم العثور على {len(res_df)} سجلات للدول المطلوبة."
        return res_df, reports, msg, True
    
    return pd.DataFrame(), [], "لم يتم التعرف على معايير البحث.", False

# --- 3. DATA LOADING ---
@st.cache_data
def load_data():
    try:
        # تأكد من وجود الأعمدة المطلوبة لتجنب الـ KeyError اللي ظهر في الصورة
        df = pd.read_excel(EXCEL_PATH)
        required_cols = ['Adm', 'lat_dec', 'lon_dec', 'Site/Allotment Name']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0 if 'dec' in col else "Unknown"
        return df
    except:
        # بيانات تجريبية في حالة عدم وجود الملف
        data = {
            'Adm': ['EGY', 'ARS', 'CYP', 'GRC'],
            'lat_dec': [30.04, 24.71, 35.12, 37.98],
            'lon_dec': [31.23, 46.67, 33.37, 23.72],
            'Site/Allotment Name': ['Cairo', 'Riyadh', 'Nicosia', 'Athens']
        }
        return pd.DataFrame(data)

db = load_data()

# --- 4. UI HEADER ---
st.title("Seshat Master Precision v17.6")
st.caption("Project BASIRA | Spectrum Intelligence & Governance")
st.markdown("---")

# --- 5. MULTI-INPUT CONTROL (VOICE/TEXT) ---
if 'voice_text' not in st.session_state:
    st.session_state.voice_text = ""

st.markdown("### 🎙️ BASIRA Spectrum Sensing")
col_mic, col_txt = st.columns([1, 4])

with col_mic:
    # مكون الصوت المطور
    audio_value = speech_to_text(
        language='ar-EG',
        start_prompt="🔴 Click to Speak",
        stop_prompt="🟢 Stop & Analyze",
        key='speech'
    )
    if audio_value:
        st.session_state.voice_text = audio_value

with col_txt:
    # الـ Text Input مرتبط بالـ Session State
    query = st.text_input(
        "Spectrum Query Box:", 
        value=st.session_state.voice_text, 
        placeholder="Waiting for voice or type here...",
        key="main_input"
    )

# --- 6. EXECUTION & VISUAL INDICATORS ---
if query:
    # مؤشرات التحميل لضمان عدم وجود "ولا الهوا"
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.warning("📡 Processing Signal...")
        progress_bar.progress(30)
        
        # استدعاء المحرك
        res_df, reports, msg, success = engine_v17_6(query, db)
        
        progress_bar.progress(60)
        status_text.info("🧠 Analyzing Regulatory Records...")
        
        if success and not res_df.empty:
            progress_bar.progress(100)
            status_text.success("✅ Analysis Complete.")
            
            # عرض الـ Metrics
            st.markdown("### 📊 Distribution Analysis")
            m_cols = st.columns(len(reports) if reports else 1)
            for i, r in enumerate(reports):
                with m_cols[i]:
                    st.image(FLAGS.get(r['Adm'], ""), width=120)
                    st.metric(label=f"Administration: {r['Adm']}", value=r['Total'])
            
            # عرض الخريطة مع حماية ضد الـ Coordinates الخاطئة
            st.markdown("### 🗺️ Geospatial Spectrum Distribution")
            try:
                # تنظيف البيانات من الـ NaNs في الإحداثيات
                map_df = res_df.dropna(subset=['lat_dec', 'lon_dec'])
                # تحويل الإحداثيات لـ numeric لضمان عدم حدوث TypeError
                map_df['lat_dec'] = pd.to_numeric(map_df['lat_dec'], errors='coerce')
                map_df['lon_dec'] = pd.to_numeric(map_df['lon_dec'], errors='coerce')
                
                fig = px.scatter_mapbox(
                    map_df, 
                    lat="lat_dec", 
                    lon="lon_dec", 
                    hover_name="Site/Allotment Name",
                    color="Adm",
                    zoom=4,
                    height=500,
                    mapbox_style="carto-positron"
                )
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Map Rendering Error: {e}")
            
            # عرض الجدول
            with st.expander("Detailed Technical Records"):
                st.write(res_df)
                
        else:
            status_text.error(f"❌ No records found for: {query}")

    except Exception as e:
        st.error(f"⚡ Critical Engine Error: {str(e)}")
else:
    st.write("Waiting for input to start analysis...")

# --- 7. FOOTER & LOGS ---
st.markdown("---")
with st.expander("System Logs (Debug Mode)"):
    st.write(f"Input Detected: {query}")
    st.write(f"Session State Voice: {st.session_state.voice_text}")
    st.write(f"Database Records: {len(db)}")
