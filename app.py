# --- 1. تحديث دالة تحميل البيانات لضمان وجود الأعمدة ---
@st.cache_data
def load_db():
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    target = "Data.xlsx" if "Data.xlsx" in files else (files[0] if files else None)
    if target:
        df = pd.read_excel(target)
        df.columns = df.columns.str.strip()
        
        # Mapping الاحترافي لضمان عدم حدوث KeyError
        mapping = {
            'Adm': ['Administration', 'Adm', 'Country', 'اسم الدولة'],
            'Notice Type': ['Notice Type', 'NT', 'نوع الإخطار'],
            'Site/Allotment Name': ['Site/Allotment Name', 'Site Name', 'اسم الموقع'],
            'Geographic Coordinates': ['Geographic Coordinates', 'Coordinates', 'الإحداثيات']
        }
        
        for std_name, synonyms in mapping.items():
            for col in df.columns:
                if col.lower() in [s.lower() for s in synonyms]:
                    df = df.rename(columns={col: std_name})
                    break

        # التأكد من وجود عمود Adm عشان الكود ميفصلش
        if 'Adm' not in df.columns:
            st.error("Error: 'Adm' column not found in Excel!")
            return None

        # تحويل الإحداثيات مع تنظيف البيانات (Drop NaN لضمان عمل الخريطة)
        if 'Geographic Coordinates' in df.columns:
            # تنظيف المسافات الزائدة
            df['Geographic Coordinates'] = df['Geographic Coordinates'].astype(str).str.strip()
            coords = df['Geographic Coordinates'].str.split(expand=True)
            if coords.shape[1] >= 2:
                df['lon_dec'] = coords[0].apply(dms_to_decimal)
                df['lat_dec'] = coords[1].apply(dms_to_decimal)
        
        return df
    return None

# --- 2. تحديث عرض الخريطة ليكون مستقراً ---
def display_map(res_df):
    if PLOTLY_AVAILABLE and not res_df.empty:
        # تصفية البيانات اللي مفيهاش إحداثيات صحيحة عشان Plotly ميهنجش
        map_data = res_df.dropna(subset=['lat_dec', 'lon_dec'])
        
        if not map_data.empty:
            st.markdown("### 🌍 Geospatial Spectrum Distribution")
            fig_map = px.scatter_mapbox(
                map_data, 
                lat="lat_dec", 
                lon="lon_dec", 
                hover_name="Site/Allotment Name", 
                hover_data={"Adm": True, "Notice Type": True, "lat_dec": False, "lon_dec": False},
                color="Adm", 
                zoom=3, 
                mapbox_style="carto-positron", 
                height=550,
                template="plotly_white"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("⚠️ No valid coordinates found for the selected results to display on map.")

# --- 3. تعديل في Engine لضمان خروج الرسائل باللغتين صح ---
# تأكد إن الـ msg بيتبني بشكل سليم قبل تمريره للـ Voice
def engine_v16_8(q, data):
    # ... (نفس لوجيك v15.9 المظبوط) ...
    # تأكد من إضافة التحقق من اللغة في الرد
    is_arabic_query = any(c in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for c in q)
    
    if is_arabic_query:
        msg = " | ".join([f"{COUNTRY_DISPLAY[r['Adm']]['ar']}: " + 
                          (f"{r['Assignments']} تخصيص " if "Assignments" in r else "") + 
                          (f"{r['Allotments']} توزيع" if "Allotments" in r else "") for r in reports])
    else:
        msg = " | ".join([f"{r['Adm']}: " + 
                          (f"{r['Assignments']} Assig " if "Assignments" in r else "") + 
                          (f"{r['Allotments']} Allot" if "Allotments" in r else "") for r in reports])
    
    return final_df, reports, msg, 100, True
