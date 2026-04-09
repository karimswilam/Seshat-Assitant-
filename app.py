# ... (نفس المكتبات)

# 1. تحسين الـ Regex لضمان قراءة كل الإحداثيات صح
def dms_to_decimal(dms):
    if pd.isna(dms): return None, None
    try:
        # Regex مرن يقبل مسافات اختيارية
        parts = re.findall(r"(\d+)°\s*(\d+)'\s*(\d+)\"?\s*([NSEW])", str(dms).upper())
        lat, lon = None, None
        for d, m, s, dirc in parts:
            dec = float(d) + float(m)/60 + float(s)/3600
            if dirc in ["S", "W"]: dec *= -1
            if dirc in ["N", "S"]: lat = dec
            if dirc in ["E", "W"]: lon = dec
        return lat, lon
    except: return None, None

@st.cache_data
def load_data():
    df = pd.read_csv("Data.csv", low_memory=False)
    df.columns = [c.lower().strip() for c in df.columns]
    
    # تنظيف شامل للداتا قبل أي حسابات
    for col in ["adm", "station_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    
    # إضافة عمود الـ Service فوراً
    df["service"] = df["station_class"].map({"BC": "SOUND", "BT": "TV"})
    
    if "location" in df.columns:
        coords = df["location"].apply(dms_to_decimal)
        df["lat"], df["lon"] = zip(*coords)
    return df

df = load_data()

# ... (detect_intent & extract functions)

if query:
    intent = detect_intent(query)
    adms = extract_adms(query)
    service = extract_service(query)

    # --- التصحيح الجوهري هنا: الفلترة التراكمية ---
    f_df = df.copy()
    if adms:
        f_df = f_df[f_df["adm"].isin(adms)]
    if service:
        f_df = f_df[f_df["service"] == service]

    # --- حساب الرد من الداتا المفلترة فقط (f_df) ---
    total_found = len(f_df)
    
    if intent == "COUNT" and adms:
        res_parts = []
        for adm in adms:
            count = len(f_df[f_df["adm"] == adm])
            res_parts.append(f"{adm} فيها {count}")
        response_text = " و ".join(res_parts) + f" محطة {service if service else ''}."
    
    elif intent == "COMPARE" and len(adms) >= 2:
        res_parts = [f"{adm} ({len(f_df[f_df['adm'] == adm])})" for adm in adms]
        response_text = "المقارنة: " + " مقابل ".join(res_parts)
    
    else:
        # رد هندسي مختصر
        serv_label = service if service else "إجمالية"
        adm_label = " و ".join(adms) if adms else "النطاق الكامل"
        response_text = f"لقيت {total_found} محطة {serv_label} في {adm_label}."

    # الإخراج الصوتي (بنفس طريقتك بس تأكد من الـ f_df)
    # ... (st.audio)
    
    st.success(response_text)

    # الرسوم البيانية لازم تستخدم f_df
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📡 Service Dist.")
        st.bar_chart(f_df["service"].value_counts())
    with col2:
        st.subheader("📝 Notice Types")
        st.bar_chart(f_df["notice type"].value_counts())

    # الخريطة من f_df
    map_df = f_df.dropna(subset=["lat", "lon"])
    # ... (HeatMap code)
