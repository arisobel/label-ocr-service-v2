import re

FIELD_BOUNDARY = r'(?=\s*(?:ARTICLE\s*NO|NO\.?|ITEM|COMP(?:OSITION)?|WEIGHT|WIDTH|PRICE|SPEC)\s*[:.\-]|$)'

# ---------------------------------------------------------------------------
# Fiber catalog — mirrors the main_fiber table in the database
# ---------------------------------------------------------------------------
FIBER_CATALOG = {
    1:  {"name": "Poliester",        "acronym": "P"},
    2:  {"name": "Cotton",           "acronym": "C"},
    3:  {"name": "Linen",            "acronym": "L"},
    4:  {"name": "Nylon",            "acronym": "N"},
    5:  {"name": "Viscose",          "acronym": "V"},
    6:  {"name": "Rayon",            "acronym": "R"},
    7:  {"name": "Acetate",          "acronym": "A"},
    8:  {"name": "Silk",             "acronym": "S"},
    9:  {"name": "Tencel / Lyocell", "acronym": "T"},
    10: {"name": "Wool",             "acronym": "W"},
}

# Maps every known label token (uppercase) -> fiber_id.
# Rules applied when building:
#   - "T" alone = Polyester (id=1)  — dominant Asian/Chinese market convention
#   - "TENCEL" / "LYOCELL" by full name = id=9
#   - "MODAL" = Viscose (id=5)
#   - Single-letter aliases only added where unambiguous at the end of the list
FIBER_ALIASES = {
    # ── Poliester (id=1) ────────────────────────────────────────────────────
    "POLYESTER": 1, "POLIESTER": 1, "POLIÉSTER": 1, "POLYÉSTER": 1,
    "POLYESTERE": 1, "DACRON": 1, "TERGAL": 1, "TERYLENE": 1, "FORTREL": 1,
    "TREVIRA": 1, "PES": 1, "PL": 1, "PET": 1, "PER": 1,
    "POLY": 1, "POLIETER": 1,
    "T": 1,   # Asian/Chinese convention: T = Terylene/Polyester
    "P": 1,

    # ── Cotton (id=2) ───────────────────────────────────────────────────────
    "COTTON": 2, "ALGODÃO": 2, "ALGODAO": 2, "ALGODÓN": 2, "ALGODON": 2,
    "COTON": 2, "COTONE": 2, "BAUMWOLLE": 2,
    "COT": 2, "CO": 2, "C": 2,

    # ── Linen (id=3) ────────────────────────────────────────────────────────
    "LINEN": 3, "LINHO": 3, "LINO": 3, "LIN": 3, "LEINEN": 3, "FLAX": 3,
    "LI": 3, "LN": 3, "L": 3,

    # ── Nylon / Polyamide (id=4) ─────────────────────────────────────────────
    "NYLON": 4, "POLYAMIDE": 4, "POLIAMIDA": 4, "POLYAMID": 4,
    "PA6": 4, "PA66": 4, "PA66/6": 4, "PA6/66": 4, "PA6.6": 4,
    "CORDURA": 4, "TACTEL": 4,
    "NYL": 4, "NY": 4, "PA": 4, "N": 4,

    # ── Viscose / Modal (id=5) ───────────────────────────────────────────────
    "VISCOSE": 5, "VISCOSA": 5, "VISCOSIO": 5,
    "MODAL": 5, "LENZING": 5,
    "CV": 5,   # Cupro-Viscose
    "VI": 5, "VIS": 5, "MD": 5, "V": 5,

    # ── Rayon (id=6) ─────────────────────────────────────────────────────────
    "RAYON": 6, "RAIOM": 6, "RAY": 6, "RA": 6, "R": 6,

    # ── Acetate (id=7) ──────────────────────────────────────────────────────
    "ACETATE": 7, "ACETATO": 7, "CELANESE": 7,
    "CTA": 7, "ACE": 7, "AC": 7, "CA": 7, "A": 7,

    # ── Silk (id=8) ──────────────────────────────────────────────────────────
    "SILK": 8, "SEDA": 8, "SOIE": 8, "SETA": 8, "SEIDE": 8,
    "SIL": 8, "SI": 8, "SE": 8, "S": 8,

    # ── Tencel / Lyocell (id=9) ───────────────────────────────────────────────
    # NOTE: "T" is NOT here — it maps to Polyester above (Asian convention).
    # Only resolve id=9 when the full word TENCEL/LYOCELL is present.
    "TENCEL": 9, "LYOCELL": 9, "LYOCELLE": 9,
    "CLY": 9, "LYO": 9, "TL": 9, "LY": 9,

    # ── Wool (id=10) ─────────────────────────────────────────────────────────
    "WOOL": 10, "LÃ": 10, "LA": 10, "LANA": 10, "LAINE": 10,
    "WOLLE": 10, "MERINO": 10, "CASHMERE": 10, "KASHMIR": 10,
    "ANGORA": 10, "ALPACA": 10,
    "WOL": 10, "WO": 10, "WS": 10, "W": 10,

    # ── Elastane / Spandex — no id in catalog, used to skip unknowns cleanly ─
    # (intentionally not mapped so it doesn't pollute main_fiber)
}

# ---------------------------------------------------------------------------
# Composition parser helpers
# ---------------------------------------------------------------------------
_COMP_PATTERNS = [
    # "54%C"  /  "60% POLYESTER"  /  "46.5%T"
    re.compile(r'(\d+(?:\.\d+)?)\s*%\s*([A-Z][A-Z0-9/\.]*)', re.IGNORECASE),
    # "N:59.8%"  /  "CO: 40%"
    re.compile(r'([A-Z][A-Z0-9/\.]*)\s*:\s*(\d+(?:\.\d+)?)\s*%', re.IGNORECASE),
    # "POLYESTER 60%"
    re.compile(r'([A-Z]{3,}[A-Z0-9]*)\s+(\d+(?:\.\d+)?)\s*%', re.IGNORECASE),
    # "100T" / "54C 46T"
    re.compile(r'(\d+(?:\.\d+)?)\s*([A-Z][A-Z0-9/\.]*)', re.IGNORECASE),
]

def _parse_composition_parts(composition):
    """Return [(percentage, TOKEN_UPPER), ...] from a composition string.
    Tries all regex patterns and returns the result set that resolves
    the most tokens in FIBER_ALIASES — this handles both '60%POLYESTER' and
    'N:59.8% R:32.2%' formats (including compact forms like '100T') correctly
    even when a greedier pattern would
    accidentally match wrong tokens from the other format.
    """
    if not composition:
        return []

    best_results = []
    best_score = -1

    for pattern in _COMP_PATTERNS:
        matches = pattern.findall(composition)
        if not matches:
            continue
        results = []
        for a, b in matches:
            try:
                pct = float(a)
                token = b.strip().upper()
            except ValueError:
                try:
                    pct = float(b)
                    token = a.strip().upper()
                except ValueError:
                    continue
            if pct > 0:
                results.append((pct, token))

        if not results:
            continue

        # Pick the pattern whose tokens resolve the most fibers in the catalog
        score = sum(1 for _, tok in results if tok in FIBER_ALIASES)
        if score > best_score:
            best_score = score
            best_results = results

    return best_results


def extract_main_fiber(composition):
    """Derive the main (dominant) fiber from a composition string.

    Returns a dict  {"id": int, "name": str, "acronym": str}
    or None if the composition is absent or no fiber can be resolved.

    The fiber with the HIGHEST percentage wins.
    If two fibers share the same percentage the first one in the string wins.
    """
    if not composition:
        return None

    parts = _parse_composition_parts(composition)
    if not parts:
        return None

    # Sort descending by percentage; stable sort preserves original order on ties
    parts_sorted = sorted(parts, key=lambda x: x[0], reverse=True)

    for _pct, token in parts_sorted:
        fiber_id = FIBER_ALIASES.get(token)
        if fiber_id is not None:
            entry = FIBER_CATALOG[fiber_id]
            return {"id": fiber_id, "name": entry["name"], "acronym": entry["acronym"]}

    return None

def normalize_measurement_noise(s: str) -> str:
    s = s.replace("|", "")
    s = re.sub(r'(?<=\d)CV\b', 'CM', s, flags=re.IGNORECASE)
    s = re.sub(r'(?<=\d)GV\b', 'GM', s, flags=re.IGNORECASE)
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
    return bool(
        re.search(r'\d+(?:\.\d+)?%\s*[A-Z]+', s, re.IGNORECASE)
        or re.search(r'\b\d{1,3}(?:\.\d+)?\s*[A-Z]{1,5}\b', s, re.IGNORECASE)
    )

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

def extract_supplier_code(raw_text):
    patterns = [
        r'ITEM\s*NO\.?\s*[:.\-]?\s*([A-Z0-9§\-]+)',
        r'ARTICLE\s*NO\.?\s*[:.\-]?\s*([A-Z0-9§\-]+)',
        r'\bNO\.?\s*[:.\-]?\s*([A-Z0-9§\-]{4,})',
        r'\bART\.?\s*[:.\-]?\s*([A-Z0-9§\-]{4,})',
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            return normalize_article(m.group(1))
    return None

def extract_article(raw_text):
    patterns = [
        r'ARTICLE\s*(?!NO\b)[:.\-]?\s*([A-Z0-9\-]{2,})',
        r'\bART\.?\s*[:.\-]?\s*([A-Z0-9\-]{2,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return clean_value(match.group(1))
    return None

def extract_composition(raw_text):
    patterns = [
        rf'COMP(?:OSITION)?\s*[:.\-]?\s*(.+?){FIELD_BOUNDARY}',
        r'((?:[A-Z]{1,4}\s*:\s*)?\d+(?:\.\d+)?%\s*[A-Z]+(?:\s+(?:[A-Z]{1,4}\s*:\s*)?\d+(?:\.\d+)?%\s*[A-Z]+)+)',
        r'((?:[A-Z]{1,4}\s*:\s*)?\d{1,3}(?:\.\d+)?\s*[A-Z]{1,5}(?:\s+(?:[A-Z]{1,4}\s*:\s*)?\d{1,3}(?:\.\d+)?\s*[A-Z]{1,5})+)'
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
        "supplier_code": None,
        "article": None,
        "item": None,
        "composition": None,
        "main_fiber": None,
        "weight": None,
        "width": None,
        "price": None,
        "spec": None,
        "grade_or_mark": None,
        "notes": None,
    }

    result["supplier_code"] = extract_supplier_code(raw_text)
    result["article"] = extract_from_lines(raw_lines, [r'\bARTICLE\b', r'品名']) or extract_article(raw_text)
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
    result["main_fiber"] = extract_main_fiber(result["composition"])

    return result
