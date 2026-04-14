def process_query(query, df):
    fdf = df.copy()
    intent = []
    conf = 0.4
    q = query.lower()

    # 1. فلتر الدولة - لو ذكر دولة مش عندنا، لازم نصفر النتائج
    detected_country = False
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            fdf = fdf[fdf['Adm'] == code]
            intent.append(f"Country: {code}")
            conf += 0.3
            detected_country = True
            break
    
    # حتة "مكافحة التأليف": لو فيه كلمة تدل على دولة تانية أو ملقيناش دولتنا
    if not detected_country and any(word in q for word in ['israel', 'jordan', 'uae', 'qatar']):
        return pd.DataFrame(), False, ["Unknown Country"], 0.0

    # 2. فلتر الخدمة
    if 'dab' in q:
        fdf = fdf[fdf['Notice Type'].isin(SERVICE_KNOWLEDGE['DAB'])]
        intent.append("Service: DAB")
        conf += 0.3
    # ... كمل باقي الكود
