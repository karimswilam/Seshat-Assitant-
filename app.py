import streamlit as st
import pandas as pd
import os
import io
import re
import asyncio
import edge_tts
from rapidfuzz import process, fuzz

# محاولة استدعاء Plotly بأمان
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- كود v15.1 اللي فات هيفضل زي ما هو تماماً ---
# مع إضافة شرط بسيط عند رسم الـ Donut Chart:

# ... (جزء الـ UI والـ Logic) ...

        with m1:
            st.metric("Confidence Score", f"{conf}%")
            if len(reports) > 0 and PLOTLY_AVAILABLE:
                fig_pie = px.pie(values=[reports[0]['Assignments'], reports[0]['Allotments']], 
                               names=['Assignments', 'Allotments'], hole=.4, 
                               color_discrete_sequence=['#1E3A8A', '#94A3B8'])
                st.plotly_chart(fig_pie, use_container_width=True)
            elif not PLOTLY_AVAILABLE:
                st.warning("Plotly not installed. Please check requirements.txt")

# ... (باقي الكود) ...
