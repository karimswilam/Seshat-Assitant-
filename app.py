def process_query_hybrid(query, df):
    q = query.lower()
    
    # 1. منع الـ Block العشوائي (الـ Stop Words)
    # ضيفنا دي عشان "how" متقفلش السؤال
    stop_words = ['how', 'the', 'for', 'any']
    
    # 2. فحص الأكواد المجهولة (الـ Regex Guard)
    potential_codes = re.findall(r'\b[a-z]{3}\b', q)
    for code in potential_codes:
        if code not in stop_words and code.upper() not in COUNTRIES and code.upper() not in SERVICE_KNOWLEDGE:
            return None, f"Entity '{code.upper()}' is not in our engineering database.", 1.0

    # 3. إجبار السيستم على الـ Explicit Match (حل مشكلة Turkey/Israel)
    country = next((c for c, k in COUNTRIES.items() if any(key in q for key in k)), None)
    service = next((s for s in SERVICE_KNOWLEDGE if s.lower() in q), None)

    # القاعدة الذهبية: لو اليوزر سأل عن "مكان" بس أنا ملقيتش دولة، لازم أرفض
    if not country and any(prep in q for prep in ['for ', 'in ', 'at ']):
        return None, "I detected a location request, but the country is not supported yet.", 0.0

    if not country or not service:
        return None, "Please specify both Country and Service explicitly to avoid data errors.", 0.0

    # الباقي زي ما هو...
    fdf = df[(df['Adm'] == country) & (df['Notice Type'].isin(SERVICE_KNOWLEDGE[service]))]
    return (fdf, True, country, service), None, 1.0
