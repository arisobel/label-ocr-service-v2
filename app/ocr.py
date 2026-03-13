import cv2
import pytesseract

from app.config import TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def run_ocr(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=15)

    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    data = pytesseract.image_to_data(
        thresh,
        lang="eng+chi_sim",
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT
    )

    words = []
    confs = []
    lines_map = {}

    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue

        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1

        if conf >= 0:
            confs.append(conf)

        words.append(txt)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines_map.setdefault(key, []).append(txt)

    raw_text = " ".join(words).strip()
    raw_lines = [" ".join(lines_map[k]) for k in sorted(lines_map.keys())]
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    return raw_text, avg_conf, {"raw_lines": raw_lines, "ocr_words": len(words)}
