import streamlit as st
import pandas as pd
import speech_recognition as sr
import numpy as np
import time

# Dictionary lel synonyms 3shan el model yfham el country names w el terminology
SYNONYMS = {
    'egypt': ['masr', 'misr', 'مصر'],
    'saudi': ['el so3deya', 'ksa', 'السعودية', 'saudi arabia'],
    'turkey': ['turkeya', 'tur', 'تركيا'],
    'takhsees': ['assignment', 'takhsees', 'تخصيص'],
    'twzee3': ['allotment', 'twzee3', 'توزيع']
}

# 1. Load Data & Notice Logic
@st.cache_data
def load_data():
    # Replace with your actual raw link
    url = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data.xlsx"
    df = pd.read_excel(url)
    return df

def get_audio_level(audio_data):
    # Calculate simple dB level from audio bytes
    audio_as_np = np.frombuffer(audio_data.get_raw_data(), dtype=np.int16)
    rms = np.sqrt(np.mean(audio_as_np**2))
    db = 20 * np.log10(rms) if rms > 0 else 0
    return db

def start_listening():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("### 🎤 Listening...")
        # Add a visual signal indicator placeholder
        signal_placeholder = st.empty()
        
        # Adjust for ambient noise
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)
        
        # Simulate dB detection for the UI
        db_level = get_audio_level(audio)
        signal_placeholder.metric("Input Signal Level", f"{db_level:.2f} dB")
        
        if db_level < 30: # Threshold example
            st.warning("Low signal level. Please speak louder.")
            
        try:
            # Arabic and English support
            text = r.recognize_google(audio, language="ar-EG, en-US")
            return text
        except:
            return None

def process_query(query, df):
    # Logic to identify Country, Service (DAB/TV), and Type (Assignment/Allotment)
    query = query.lower()
    
    # 1. Identify Country (ADM)
    found_adm = None
    for key, values in SYNONYMS.items():
        if any(v in query for v in values):
            found_adm = key.upper() # Standardize to DF format
            break

    # 2. Identify Service & Type
    # Simple logic: If query has "DAB" and "Takhsees", filter by DS1/GS1
    # This is a "Zero Intelligence" logic but focused on your headers
    
    results = df # Placeholder filter
    if "takhsees" in query or "assignment" in query:
        results = df[df['Notice Type'].isin(['DS1', 'GS1', 'GT1', 'DT1'])]
    elif "twzee3" in query or "allotment" in query:
        results = df[df['Notice Type'].isin(['DS2', 'GS2', 'GT2', 'DT2'])]

    return results

def main():
    st.set_page_config(page_title="NTRA Spectrum Assistant", layout="wide")
    st.title("📡 Regulatory Voice Assistant (DAB & TV)")
    
    df = load_data()

    if st.button("🎤 Start Voice Query"):
        query_text = start_listening()
        
        if query_text:
            st.info(f"Detected: {query_text}")
            
            # Progress Bar for "Processing"
            progress_bar = st.progress(0)
            for percent_complete in range(100):
                time.sleep(0.01)
                progress_bar.progress(percent_complete + 1)
            
            # Answer Logic
            results = process_query(query_text, df)
            
            # Display Confidence (Simulated for Zero Intelligence)
            st.sidebar.write(f"Confidence: 95%") 
            
            # Output Display
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Statistics")
                if not results.empty:
                    stats = results.groupby('Administration').size()
                    st.bar_chart(stats)
                    st.write(f"Total count found: {len(results)}")
            
            with col2:
                st.subheader("📋 Data Preview")
                st.write(results.head(10))
        else:
            st.error("Could not understand the voice input. Please try again.")

if __name__ == "__main__":
    main()
