import cv2
import pytesseract

from app.config import TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def _run_ocr_once(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=15)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    data = pytesseract.image_to_data(thresh, lang="eng+chi_sim", config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)
    words, confs, lines_map = [], [], {}
    for i, value in enumerate(data["text"]):
        text = (value or "").strip()
        if not text:
            continue
        try:
            word_confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            word_confidence = -1
        if word_confidence >= 0:
            confs.append(word_confidence)
        words.append(text)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines_map.setdefault(key, []).append(text)
    raw_text = " ".join(words).strip()
    raw_lines = [" ".join(lines_map[key]) for key in sorted(lines_map)]
    confidence = sum(confs) / len(confs) if confs else 0.0
    return raw_text, confidence, {"raw_lines": raw_lines, "ocr_words": len(words)}


def run_ocr_candidates(candidates):
    """OCR each in-memory candidate and choose confidence, then useful text."""
    results = []
    for name, rotation, image in candidates:
        raw_text, confidence, debug = _run_ocr_once(image)
        useful_chars = sum(char.isalnum() or char == "%" for char in raw_text)
        results.append((confidence, useful_chars, name, rotation, raw_text, debug))
    if not results:
        return "", 0.0, {"raw_lines": [], "ocr_words": 0, "chosen_rotation": 0, "ocr_candidates": []}
    confidence, _, name, rotation, raw_text, debug = max(results, key=lambda value: (value[0], value[1]))
    return raw_text, confidence, {
        **debug, "chosen_candidate": name, "chosen_rotation": rotation,
        "ocr_candidates": [{"name": result[2], "rotation": result[3], "confidence": result[0]} for result in results],
    }


def run_ocr(image):
    return run_ocr_candidates([("image", 0, image)])
