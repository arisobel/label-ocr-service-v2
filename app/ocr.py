import re

import cv2
import numpy as np
import pytesseract

from app.config import TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def _scale_for_ocr(image):
    """Enlarge small table cells without modifying the request image."""
    height, width = image.shape[:2]
    factor = 3 if min(height, width) < 220 else 2 if min(height, width) < 700 else 1
    if factor == 1:
        return image
    return cv2.resize(image, (width * factor, height * factor), interpolation=cv2.INTER_CUBIC)


def _run_ocr_once(image, psm=6):
    image = _scale_for_ocr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=15)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    data = pytesseract.image_to_data(
        thresh,
        lang="eng+chi_sim",
        config=f"--oem 3 --psm {psm}",
        output_type=pytesseract.Output.DICT,
    )
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
    return raw_text, confidence, {"raw_lines": raw_lines, "ocr_words": len(words), "psm": psm}


def _mask_qr_code(image):
    """Return a copy with a detected QR area whitened, plus its bounds."""
    detector = cv2.QRCodeDetector()
    try:
        _data, corners, _straight = detector.detectAndDecode(image)
    except cv2.error:
        corners = None
    if corners is None or len(corners) == 0:
        return image, None
    points = np.asarray(corners, dtype=np.int32).reshape(-1, 2)
    x, y, width, height = cv2.boundingRect(points)
    padding = max(4, int(min(width, height) * 0.05))
    x, y = max(0, x - padding), max(0, y - padding)
    right, bottom = min(image.shape[1], x + width + 2 * padding), min(image.shape[0], y + height + 2 * padding)
    masked = image.copy()
    cv2.rectangle(masked, (x, y), (right, bottom), (255, 255, 255), thickness=-1)
    return masked, {"x": int(x), "y": int(y), "w": int(right - x), "h": int(bottom - y)}


def build_ocr_candidates(original, label):
    """Make in-memory reading candidates for tabular labels with possible QR codes."""
    masked_label, qr_box = _mask_qr_code(label)
    height, width = label.shape[:2]
    # Most textile labels put the QR at right; retain the fields/values to its left.
    left_edge = qr_box["x"] - 6 if qr_box else int(width * 0.68)
    left_edge = max(int(width * 0.45), min(width, left_edge))
    left_label = masked_label[:, :left_edge]

    candidates = [("original", 0, original, 6)]
    for rotation, operation in ((0, None), (90, cv2.ROTATE_90_CLOCKWISE), (180, cv2.ROTATE_180), (270, cv2.ROTATE_90_COUNTERCLOCKWISE)):
        image = label if operation is None else cv2.rotate(label, operation)
        candidates.append(("label_crop", rotation, image, 6))
    if qr_box:
        candidates.append(("label_without_qr", 0, masked_label, 6))
    candidates.extend([
        ("label_left", 0, left_label, 6),
        ("label_left_sparse", 0, left_label, 11),
    ])

    # This cell contains the value paired with NO in the common two-column label layout.
    code_top, code_bottom = int(height * 0.18), int(height * 0.43)
    code_left = int(width * 0.32)
    code_region = masked_label[code_top:code_bottom, code_left:width]
    if code_region.size:
        candidates.extend([("supplier_code", 0, code_region, 6), ("supplier_code_line", 0, code_region, 7)])
    return candidates, {"qr_detected": qr_box is not None, "qr_box": qr_box, "left_crop_width": int(left_edge)}


def _supplier_code_from_text(text):
    """Conservative code pattern: letters/digits plus a meaningful hyphen suffix."""
    match = re.search(r"\b[A-Z][A-Z0-9]{3,}(?:-[A-Z0-9]{2,})+\b", text.upper())
    return match.group(0) if match else None


def run_ocr_candidates(candidates):
    """OCR candidates and preserve a reliable NO-cell code as separate evidence."""
    results, supplier_codes = [], []
    for candidate in candidates:
        name, rotation, image = candidate[:3]
        psm = candidate[3] if len(candidate) > 3 else 6
        raw_text, confidence, debug = _run_ocr_once(image, psm)
        useful_chars = sum(char.isalnum() or char == "%" for char in raw_text)
        code = _supplier_code_from_text(raw_text) if name.startswith("supplier_code") else None
        if code:
            supplier_codes.append((confidence, code))
        results.append((confidence, useful_chars, name, rotation, raw_text, debug, psm))
    if not results:
        return "", 0.0, {"raw_lines": [], "ocr_words": 0, "chosen_rotation": 0, "ocr_candidates": []}
    confidence, _, name, rotation, raw_text, debug, _psm = max(results, key=lambda value: (value[0], value[1]))
    supplier_code = max(supplier_codes, default=(0, None), key=lambda value: value[0])[1]
    return raw_text, confidence, {
        **debug,
        "chosen_candidate": name,
        "chosen_rotation": rotation,
        "supplier_code_candidate": supplier_code,
        "ocr_candidates": [
            {"name": result[2], "rotation": result[3], "psm": result[6], "confidence": result[0]}
            for result in results
        ],
    }


def run_ocr(image):
    return run_ocr_candidates([("image", 0, image, 6)])
