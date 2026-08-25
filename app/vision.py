import cv2
import numpy as np


def _order_corners(points):
    points = points.reshape(4, 2).astype("float32")
    ordered = np.zeros((4, 2), dtype="float32")
    sums, diffs = points.sum(axis=1), np.diff(points, axis=1).ravel()
    ordered[0], ordered[2] = points[np.argmin(sums)], points[np.argmax(sums)]
    ordered[1], ordered[3] = points[np.argmin(diffs)], points[np.argmax(diffs)]
    return ordered


def _perspective_crop(image, quad):
    tl, tr, br, bl = _order_corners(quad)
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if width < 80 or height < 40:
        return None
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    return cv2.warpPerspective(image, cv2.getPerspectiveTransform(_order_corners(quad), target), (width, height))


def detect_label_region(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    threshold = cv2.adaptiveThreshold(cv2.GaussianBlur(gray, (5, 5), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    contours, _ = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area, best, best_score = image.shape[0] * image.shape[1], None, 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(3000, image_area * 0.01) or area > image_area * 0.9:
            continue
        perimeter = cv2.arcLength(contour, True)
        quad = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        x, y, width, height = cv2.boundingRect(contour)
        if width < 100 or height < 50:
            continue
        score = (area / max(width * height, 1)) * area
        if score > best_score:
            best, best_score = (x, y, width, height, quad), score
    if best is None:
        return None, {"detected": False, "crop_applied": False, "crop_dimensions": None, "perspective_corrected": False}
    x, y, width, height, quad = best
    crop = image[y:y + height, x:x + width]
    perspective_corrected = len(quad) == 4 and cv2.isContourConvex(quad)
    if perspective_corrected:
        corrected = _perspective_crop(image, quad)
        if corrected is not None:
            crop = corrected
        else:
            perspective_corrected = False
    return crop, {
        "detected": True, "crop_applied": True, "box": {"x": x, "y": y, "w": width, "h": height},
        "crop_dimensions": {"width": int(crop.shape[1]), "height": int(crop.shape[0])},
        "perspective_corrected": perspective_corrected,
    }
