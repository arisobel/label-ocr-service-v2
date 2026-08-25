"""Gemini integration for textile-label extraction."""
import json
import logging
import re
from typing import Any, Iterable, Optional

from google import genai
from google.genai import types

from app.config import GEMINI_MIN_CONFIDENCE, GEMINI_MODEL, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

TEXTILE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "company": {"type": "STRING", "nullable": True}, "article": {"type": "STRING", "nullable": True},
        "item": {"type": "STRING", "nullable": True}, "composition": {"type": "STRING", "nullable": True},
        "weight": {"type": "STRING", "nullable": True}, "width": {"type": "STRING", "nullable": True},
        "price": {"type": "STRING", "nullable": True}, "spec": {"type": "STRING", "nullable": True},
        "grade_or_mark": {"type": "STRING", "nullable": True}, "notes": {"type": "STRING", "nullable": True},
        "field_confidence": {"type": "OBJECT", "properties": {
            name: {"type": "NUMBER", "nullable": True}
            for name in ("article", "item", "composition", "weight", "width")
        }},
    },
}


class GeminiRequestError(RuntimeError):
    """Safe error intended for API debug output."""


def should_use_llm(parsed_local: dict, confidence: float) -> bool:
    if confidence < GEMINI_MIN_CONFIDENCE:
        return True
    return any(not parsed_local.get(key) for key in ("article", "width", "weight", "composition"))


def build_prompt(raw_text: str, raw_lines: list, confidence: float, multimodal: bool = False) -> str:
    source = "the supplied label image(s), with OCR as secondary evidence" if multimodal else "the supplied OCR text"
    return f"""
Extract data from a textile sample label using {source}.
Return only the structured JSON requested by the response schema.
Never invent data: use null when there is insufficient visible evidence.
Preserve readable Chinese characters exactly.
Do not infer main_fiber; it is calculated deterministically by the service.

Field rules:
- A label code may be marked No, Number, Code, Article, or 编号.
- Width is a fabric width (for example 160CM); do not confuse it with Meter/length (for example 1.8M).
- Weight must be a fabric weight such as GSM or g/m², never a length or price.
- Composition must preserve percentages and fiber abbreviations (for example 54%P 39%R 7%SP).
- field_confidence values are numbers from 0.0 to 1.0 and reflect visual/textual evidence.

Tesseract confidence: {confidence}
OCR raw text:
{raw_text}
OCR raw lines:
{json.dumps(raw_lines, ensure_ascii=False)}
""".strip()


def _safe_error_text(value: Any) -> str:
    text = str(value)
    if GOOGLE_API_KEY:
        text = text.replace(GOOGLE_API_KEY, "[REDACTED]")
    return re.sub(r"([?&]key=)[^&\s]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)


def _provider_error_details(exc: Exception) -> tuple[Optional[Any], str]:
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.json() if callable(getattr(response, "json", None)) else response
        except Exception:
            body = getattr(response, "text", response)
    else:
        body = getattr(exc, "message", None) or str(exc)
    return status, _safe_error_text(body)


def _image_parts(images: Iterable[bytes]) -> list[types.Part]:
    return [types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in images if image]


def call_gemini(raw_text: str, raw_lines: list, confidence: float, images: Optional[Iterable[bytes]] = None) -> dict:
    if not GOOGLE_API_KEY:
        raise GeminiRequestError("Gemini is not configured")
    image_data = list(images or [])
    contents: list[Any] = [build_prompt(raw_text, raw_lines, confidence, multimodal=bool(image_data)), *_image_parts(image_data)]
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=contents,
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json", response_schema=TEXTILE_SCHEMA),
        )
        if not response.text:
            raise GeminiRequestError("Gemini returned no structured content")
        result = json.loads(response.text)
        if not isinstance(result, dict):
            raise GeminiRequestError("Gemini returned an invalid structured response")
        return result
    except GeminiRequestError:
        raise
    except Exception as exc:
        status, body = _provider_error_details(exc)
        logger.error("Gemini request failed status=%s model=%s response=%s", status, GEMINI_MODEL, body)
        raise GeminiRequestError("Gemini request failed; inspect server logs for details") from exc


def _has_value(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def merge_parsed(local: dict, llm: dict) -> dict:
    """Use confident multimodal data to correct OCR; weak data fills blanks only."""
    final_parsed = dict(local)
    confidences = llm.get("field_confidence") or {}
    for key in final_parsed:
        if key == "main_fiber":
            continue
        candidate = llm.get(key)
        if not _has_value(candidate):
            continue
        llm_confidence = confidences.get(key)
        if not _has_value(final_parsed.get(key)) or (isinstance(llm_confidence, (int, float)) and llm_confidence >= 0.75):
            final_parsed[key] = candidate
    return final_parsed
