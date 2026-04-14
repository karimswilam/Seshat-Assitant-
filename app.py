# أضفنا دالة للبحث عن أي كود دولة محتمل في السؤال
import re

def smart_intelligence(query):
    q = query.lower()
    intel = {"entities": {}, "intent": None, "unsupported": None, "conf_boost": 0.0}

    # 1. البحث عن الدول المدعومة
    for code, keywords in COUNTRIES.items():
        if any(k in q for k in keywords):
            intel['entities']['country'] = code
            intel['conf_boost'] += 0.3
            break

    # 2. حماية ضد "تخريف" الدول: لو فيه كود 3 حروف مش تبعنا
    potential_codes = re.findall(r'\b[a-z]{3}\b', q) # بيدور على أي 3 حروف
    for p_code in potential_codes:
        p_code_upper = p_code.upper()
        # لو الكود مش ARS ولا EGY يبقى دولة غريبة
        if p_code_upper not in COUNTRIES and p_code_upper != 'DAB': 
             intel['unsupported'] = p_code_upper
             return intel 

    # باقي منطق الخدمة...
