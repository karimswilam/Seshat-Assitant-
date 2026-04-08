import streamlit as st
import pandas as pd
import google.generativeai as genai

# ... (نفس إعدادات الـ API والموديل gemini-3-flash-preview) ...

if run_button and user_input:
    with st.spinner("Executing Intelligent Query..."):
        try:
            # 1. وصف البيانات للموديل (Metadata)
            columns_info = df.columns.tolist()
            sample_data = df.head(3).to_string()
            
            # 2. برومبت "هندسي" يطلب من الموديل كتابة كود الاستعلام
            prompt = (
                f"You are a Python Data Expert. Based on this DataFrame schema: {columns_info}\n"
                f"Sample:\n{sample_data}\n\n"
                f"User Question: {user_input}\n"
                f"Write only the Python code using 'df' to get the answer. Return only the answer string."
            )

            # 3. الموديل هنا بيفكر في "المنطق" مش في "الداتا"
            # ده بيخلي الاستجابة لحظية حتى مع مليون صف
            response = model.generate_content(prompt)
            
            # 4. عرض النتيجة (الموديل بيعمل تحليل ذكي للمخرجات)
            st.markdown("### 🤖 Engineering Analysis:")
            st.success(response.text)
            
            # (صوت الرد)
            # ...
