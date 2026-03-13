import json
import requests

from app.config import GOOGLE_API_KEY, GEMINI_MODEL

def should_use_llm(parsed_local: dict, confidence: float) -> bool:
    if confidence < 70:
        return True

    critical_missing = not parsed_local.get("article") or not parsed_local.get("width") or not parsed_local.get("weight")
    contaminated = any(
        isinstance(parsed_local.get(k), str) and f"{k}:" in parsed_local.get(k).lower()
        for k in ["composition", "weight", "width", "price"]
    )
    return critical_missing or contaminated

def build_prompt(raw_text: str, raw_lines: list, confidence: float) -> str:
    return f"""
You are extracting data from OCR text of textile sample labels.

Return only valid JSON.
Do not use markdown.
Do not explain anything.
Do not invent values.
If a field is not confidently present, return null.

Important OCR normalization rules:
- "CV" may mean "CM"
- "GV" may mean "GM"
- "§" may mean "S"
- "AFO" may actually be "AF0" when followed by digits
- Width is usually something like 150CM, 160CM, 165cm
- Weight is usually something like 180GSM, 205g/m2, 400GSM
- Composition usually contains percentages like 54%C 46%T or N:59.8% R:32.2% SP:8%

Expected JSON fields:
{{
  "company": string|null,
  "article": string|null,
  "item": string|null,
  "composition": string|null,
  "weight": string|null,
  "width": string|null,
  "price": string|null,
  "spec": string|null,
  "grade_or_mark": string|null,
  "notes": string|null
}}

OCR confidence: {confidence}

OCR raw text:
{raw_text}

OCR raw lines:
{json.dumps(raw_lines, ensure_ascii=False, indent=2)}
""".strip()

def call_gemini(raw_text: str, raw_lines: list, confidence: float):
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    prompt = build_prompt(raw_text, raw_lines, confidence)

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    resp = requests.post(url, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
    if not text:
        raise RuntimeError("Gemini returned no text content")

    return json.loads(text)

def merge_parsed(local: dict, llm: dict) -> dict:
    final_parsed = dict(local)
    for key in final_parsed.keys():
        local_val = final_parsed.get(key)
        llm_val = llm.get(key)

        bad_local = (
            local_val is None
            or str(local_val).strip() == ""
            or (isinstance(local_val, str) and any(tag in local_val.lower() for tag in [f"{key}:", "composition:", "weight:", "width:", "price:"]))
        )

        if bad_local and llm_val is not None:
            final_parsed[key] = llm_val
    return final_parsed
