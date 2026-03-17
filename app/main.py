from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import cv2

from app.vision import detect_label_region
from app.ocr import run_ocr
from app.parser import parse_label_text
from app.gemini_client import call_gemini, merge_parsed, should_use_llm
from app.parser import extract_main_fiber
from app.config import USE_GEMINI_FALLBACK

app = FastAPI(title="Label OCR Service v2")

class ExtractTextRequest(BaseModel):
    raw_text: str
    raw_lines: Optional[List[str]] = None

def read_image(file_bytes):
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")
    return img

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = read_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    cropped, vision_debug = detect_label_region(image)
    if cropped is None:
        cropped = image

    raw_text, conf, ocr_debug = run_ocr(cropped)
    raw_lines = ocr_debug.get("raw_lines", [])

    parsed_local = parse_label_text(raw_text=raw_text, raw_lines=raw_lines)
    parsed_llm = None
    llm_error = None
    final_parsed = dict(parsed_local)

    if USE_GEMINI_FALLBACK and should_use_llm(parsed_local, conf):
        try:
            parsed_llm = call_gemini(raw_text=raw_text, raw_lines=raw_lines, confidence=conf)
            final_parsed = merge_parsed(parsed_local, parsed_llm)
            # Recompute main_fiber from the (possibly LLM-corrected) composition
            final_parsed["main_fiber"] = extract_main_fiber(final_parsed.get("composition"))
        except Exception as exc:
            llm_error = str(exc)

    return {
        "success": True,
        "confidence": conf,
        "raw_text": raw_text,
        "raw_lines": raw_lines,
        "parsed_local": parsed_local,
        "parsed_llm": parsed_llm,
        "final_parsed": final_parsed,
        "debug": {
            **vision_debug,
            **ocr_debug,
            "llm_enabled": USE_GEMINI_FALLBACK,
            "llm_error": llm_error
        }
    }

@app.post("/extract-text")
async def extract_text(body: ExtractTextRequest):
    raw_text = body.raw_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text must not be empty")

    raw_lines = body.raw_lines if body.raw_lines is not None else []

    # Pre-extracted text is treated as high-confidence (no OCR noise)
    conf = 100.0

    parsed_local = parse_label_text(raw_text=raw_text, raw_lines=raw_lines)
    parsed_llm = None
    llm_error = None
    final_parsed = dict(parsed_local)

    if USE_GEMINI_FALLBACK and should_use_llm(parsed_local, conf):
        try:
            parsed_llm = call_gemini(raw_text=raw_text, raw_lines=raw_lines, confidence=conf)
            final_parsed = merge_parsed(parsed_local, parsed_llm)
            # Recompute main_fiber from the (possibly LLM-corrected) composition
            final_parsed["main_fiber"] = extract_main_fiber(final_parsed.get("composition"))
        except Exception as exc:
            llm_error = str(exc)

    return {
        "success": True,
        "confidence": conf,
        "raw_text": raw_text,
        "raw_lines": raw_lines,
        "parsed_local": parsed_local,
        "parsed_llm": parsed_llm,
        "final_parsed": final_parsed,
        "debug": {
            "llm_enabled": USE_GEMINI_FALLBACK,
            "llm_error": llm_error
        }
    }
