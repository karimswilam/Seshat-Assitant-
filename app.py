import streamlit as st  # تأكد إن ده السطر رقم 1
import pandas as pd
import io
import os

# =====================================================
# 1. نظام تتبع الأخطاء (Error Tracing Flags)
# =====================================================
st.set_page_config(page_title="Seshat Debugging Mode", layout="wide")
st.title("📡 Seshat Precision Engineering Hub")

# تفقد وجود الملف في السيرفر
if not os.path.exists("Data.csv"):
    st.error("🚨 FLAG 1: ملف Data.csv مش موجود في الفولدر الرئيسي على GitHub!")
else:
    st.info("✅ FLAG 1: ملف Data.csv موجود وجاري فحصه...")

# =====================================================
# 2. تحميل البيانات مع Debugging Info
# =====================================================
@st.cache_data
def load_data_with_trace():
    try:
        # تجربة القراءة مع معالجة الـ Encoding
        try:
            raw_df = pd.read_csv("Data.csv", encoding='utf-8-sig')
            st.write("📊 FLAG 2: تم القراءة بترميز UTF-8")
        except:
            raw_df = pd.read_csv("Data.csv", encoding='cp1252')
            st.write("📊 FLAG 2: تم القراءة بترميز CP1252 (Excel Legacy)")

        # فحص أسماء الأعمدة وتنظيفها
        st.write("🔍 الأعمدة الأصلية في الملف:", list(raw_df.columns))
        
        # تنظيف شامل للأعمدة (إزالة مسافات، تحويل لنص، إزالة علامات غريبة)
        raw_df.columns = [str(c).strip().replace('\ufeff', '') for c in raw_df.columns]
        st.write("✨ الأعمدة بعد التنظيف (Stripped):", list(raw_df.columns))

        return raw_df
    except Exception as e:
        st.error(f"❌ FLAG 3: فشل ذريع في قراءة الملف: {e}")
        return pd.DataFrame()

# تشغيل الفحص
df = load_data_with_trace()

if not df.empty:
    target = 'Notice Type'
    if target in df.columns:
        st.success(f"🎯 FLAG 4: عمود '{target}' تم إيجاده بنجاح!")
        # هنا نعرض أول 5 صفوف للتأكد
        st.write("👀 عينة من البيانات:", df.head())
    else:
        st.error(f"⚠️ FLAG 4: فشل في إيجاد '{target}'. المتاح هو: {list(df.columns)}")
        st.warning("نصيحة: اتأكد إنك سيفت الملف كـ CSV UTF-8 (Comma delimited) مش أي نوع تاني.")
