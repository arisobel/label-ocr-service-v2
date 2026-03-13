import cv2

def detect_label_region(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21, 10
    )

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    best = None
    best_area = 0

    for c in contours:
        area = cv2.contourArea(c)
        if area > best_area:
            x, y, w, h = cv2.boundingRect(c)
            if w > 100 and h > 50:
                best_area = area
                best = (x, y, w, h)

    if best is None:
        return None, {"detected": False}

    x, y, w, h = best
    crop = image[y:y+h, x:x+w]

    return crop, {
        "detected": True,
        "box": {"x": x, "y": y, "w": w, "h": h}
    }
