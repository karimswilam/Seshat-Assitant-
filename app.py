def engine_v16_2(q, data):
    q_low = q.lower()
    
    # 1. تعريف الكلمات المفتاحية بدقة (المنطق الهندسي)
    COUNTRY_MAP = {
        'EGY': ['egypt', 'egy', 'مصر'], 'ARS': ['saudi', 'ars', 'ksa'],
        'TUR': ['turkey', 'tur', 'تركيا'], 'ISR': ['israel', 'isr', 'اسرائيل']
    }
    SYNONYMS = {
        'ALLOT_KEY': ['allotment', 'allotments', 'توزيع', 'توزيعات'],
        'ASSIG_KEY': ['assignment', 'assignments', 'تخصيص', 'تخصيصات'],
        'DAB_KEY': ['dab', 'داب', 'صوتية']
    }
    STRICT_ASSIG = ['T01', 'T03', 'T04', 'GS1', 'DS1', 'GT1', 'DT1', 'G01']
    STRICT_ALLOT = ['T02', 'G02', 'GT2', 'DT2', 'GS2', 'DS2']

    selected_adms = [code for code, keys in COUNTRY_MAP.items() if any(k in q_low for k in keys)]
    if not selected_adms: return None, [], "ADM Error", 0, False

    # 2. تحديد نوع الخدمة (DAB, TV, etc.)
    svc_codes = []
    if any(x in q_low for x in SYNONYMS['DAB_KEY']): svc_codes = ['GS1','GS2','DS1','DS2']

    # 3. الفلترة الذكية (الحل الحقيقي للمشكلة)
    is_assig_requested = any(x in q_low for x in SYNONYMS['ASSIG_KEY'])
    is_allot_requested = any(x in q_low for x in SYNONYMS['ALLOT_KEY'])
    
    # لو مسألش عن حاجة محددة، بنعتبره سأل عن الاثنين
    if not is_assig_requested and not is_allot_requested:
        is_assig_requested = is_allot_requested = True

    reports = []; final_df = pd.DataFrame()
    for adm in selected_adms:
        adm_df = data[data['Adm'] == adm].copy()
        if svc_codes: adm_df = adm_df[adm_df['Notice Type'].isin(svc_codes)]
        
        # فلترة البيانات بناءً على الطلب الدقيق
        a_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]) if is_assig_requested else 0
        l_count = len(adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]) if is_allot_requested else 0
        
        # بناء التقرير بناءً على الفلترة
        res = {"Adm": adm, "Assignments": a_count, "Allotments": l_count}
        reports.append(res)
        
        # تجميع الـ Dataframe النهائي للعرض في Technical Records
        temp_filtered = pd.DataFrame()
        if is_assig_requested: temp_filtered = pd.concat([temp_filtered, adm_df[adm_df['Notice Type'].isin(STRICT_ASSIG)]])
        if is_allot_requested: temp_filtered = pd.concat([temp_filtered, adm_df[adm_df['Notice Type'].isin(STRICT_ALLOT)]])
        final_df = pd.concat([final_df, temp_filtered], ignore_index=True)

    # بناء الرسالة الصوتية بدقة
    msg_parts = []
    for r in reports:
        part = f"{r['Adm']}: "
        if is_assig_requested: part += f"{r['Assignments']} Assignments "
        if is_allot_requested: part += f"{r['Allotments']} Allotments"
        msg_parts.append(part)
    
    return final_df, reports, " | ".join(msg_parts), 100, True
