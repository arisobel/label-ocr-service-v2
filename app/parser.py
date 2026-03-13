import re

FIELD_BOUNDARY = r'(?=\s*(?:ARTICLE\s*NO|NO\.?|ITEM|COMP(?:OSITION)?|WEIGHT|WIDTH|PRICE|SPEC)\s*[:.\-]|$)'

def normalize_measurement_noise(s: str) -> str:
    s = s.replace("|", "")
    s = re.sub(r'(?<=\d)CV\b', 'CM', s, flags=re.IGNORECASE)
    s = re.sub(r'(?<=\d)GV\b', 'GM', s, flags=re.IGNORECASE)
    s = re.sub(r'^\s*1(?=\d{2,3}\s*C[MV]\b)', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^\s*1(?=\d{2,4}\s*(?:GSM|GM|G/M2|G/M²)\b)', '', s, flags=re.IGNORECASE)
    return s.strip()

def clean_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r'^[^\w%]+', '', value)
    value = re.sub(r'[|]+', ' ', value)
    value = re.sub(r'\s+', ' ', value)
    value = normalize_measurement_noise(value)
    return value.strip(" :-.")

def looks_like_width(s: str) -> bool:
    s = normalize_measurement_noise(s)
    return bool(re.search(r'\b\d{2,3}\s*C[MV]\b', s, re.IGNORECASE))

def looks_like_weight(s: str) -> bool:
    s = normalize_measurement_noise(s)
    return bool(re.search(r'\b\d{2,4}\s*(?:GSM|GM|G/M2|G/M²)\b', s, re.IGNORECASE))

def looks_like_composition(s: str) -> bool:
    return bool(re.search(r'\d+(?:\.\d+)?%\s*[A-Z]+', s, re.IGNORECASE))

def find_company(raw_lines):
    blocked = ["COMP", "COMPOSITION", "WEIGHT", "WIDTH", "PRICE", "ARTICLE", "NO.", "ITEM", "SPEC"]
    for line in raw_lines[:6]:
        up = line.upper()
        if any(b in up for b in blocked):
            continue
        if any(token in up for token in ["TEXTILE", "IMP", "EXP", "CO", "LTD"]):
            return clean_value(line)
    return None

def extract_from_lines(raw_lines, keys, validator=None):
    for i, line in enumerate(raw_lines):
        for key in keys:
            if re.search(key, line, re.IGNORECASE):
                m = re.search(rf'{key}\s*[:.\-]?\s*(.+)$', line, re.IGNORECASE)
                if m:
                    val = clean_value(m.group(1))
                    if val and (validator is None or validator(val)):
                        return val
                if i + 1 < len(raw_lines):
                    val = clean_value(raw_lines[i + 1])
                    if val and (validator is None or validator(val)):
                        return val
    return None

def normalize_article(value: str) -> str:
    value = value.strip()
    value = value.replace("§", "S")
    value = re.sub(r'[^A-Z0-9\-]', '', value.upper())
    value = re.sub(r'^AFO(?=\d)', 'AF0', value)
    return value

def extract_article(raw_text):
    patterns = [
        r'ARTICLE\s*NO\.?\s*[:.\-]?\s*([A-Z0-9§\-]+)',
        r'\bNO\.?\s*[:.\-]?\s*([A-Z0-9§\-]{4,})',
        r'\bART\.?\s*[:.\-]?\s*([A-Z0-9§\-]{4,})',
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            return normalize_article(m.group(1))
    return None

def extract_composition(raw_text):
    patterns = [
        rf'COMP(?:OSITION)?\s*[:.\-]?\s*(.+?){FIELD_BOUNDARY}',
        r'((?:[A-Z]{1,4}\s*:\s*)?\d+(?:\.\d+)?%\s*[A-Z]+(?:\s+(?:[A-Z]{1,4}\s*:\s*)?\d+(?:\.\d+)?%\s*[A-Z]+)+)'
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            val = clean_value(m.group(1))
            if looks_like_composition(val):
                return val
    return None

def extract_width_from_lines(raw_lines):
    for line in raw_lines:
        candidate = normalize_measurement_noise(line)
        m = re.search(r'(\d{2,3}\s*C[MV])', candidate, re.IGNORECASE)
        if m:
            return m.group(1).upper().replace("CV", "CM")
    return None

def extract_width(raw_text):
    raw_text = normalize_measurement_noise(raw_text)
    patterns = [
        rf'WIDTH\s*[:.\-]?\s*(.+?){FIELD_BOUNDARY}',
        r'\b(\d{2,3}\s*C[MV])\b'
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            val = clean_value(m.group(1))
            val = normalize_measurement_noise(val)
            m2 = re.search(r'\b(\d{2,3}\s*C[MV])\b', val, re.IGNORECASE)
            if m2:
                return m2.group(1).upper().replace("CV", "CM")
    return None

def extract_weight(raw_text):
    raw_text = normalize_measurement_noise(raw_text)
    patterns = [
        rf'WEIGHT\s*[:.\-]?\s*(.+?){FIELD_BOUNDARY}',
        r'\b(\d{2,4}\s*(?:GSM|GM|G/M2|G/M²|G/M))\b'
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            val = clean_value(m.group(1))
            m2 = re.search(r'\b(\d{2,4}\s*(?:GSM|GM|G/M2|G/M²|G/M))\b', val, re.IGNORECASE)
            if m2:
                return clean_value(m2.group(1))
    return None

def extract_price(raw_text):
    m = re.search(rf'PRICE\s*[:.\-]?\s*(.+?){FIELD_BOUNDARY}', raw_text, re.IGNORECASE)
    if m:
        val = clean_value(m.group(1))
        return val or None
    return None

def parse_label_text(raw_text: str, raw_lines=None):
    if raw_lines is None:
        raw_lines = []

    raw_text = re.sub(r'\s+', ' ', raw_text).strip()

    result = {
        "company": find_company(raw_lines),
        "article": None,
        "item": None,
        "composition": None,
        "weight": None,
        "width": None,
        "price": None,
        "spec": None,
        "grade_or_mark": None,
        "notes": None,
    }

    result["article"] = extract_article(raw_text)
    result["composition"] = extract_from_lines(
        raw_lines, [r'COMP(?:OSITION)?'], validator=looks_like_composition
    ) or extract_composition(raw_text)
    result["width"] = extract_from_lines(
        raw_lines, [r'WIDTH', r'WID'], validator=looks_like_width
    ) or extract_width_from_lines(raw_lines) or extract_width(raw_text)
    result["weight"] = extract_from_lines(
        raw_lines, [r'WEIGHT'], validator=looks_like_weight
    ) or extract_weight(raw_text)
    result["price"] = extract_price(raw_text)

    return result
