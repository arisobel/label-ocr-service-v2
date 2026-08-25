import logging
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app.gemini_client import GeminiRequestError, call_gemini, merge_parsed
from app.ocr import run_ocr_candidates
from app.parser import extract_main_fiber, parse_label_text


def test_main_fiber_for_compact_composition():
    assert extract_main_fiber("54%P 39%R 7%SP")["name"] == "Poliester"


def test_width_and_weight_are_not_confused_with_meter():
    parsed = parse_label_text("WIDTH 160CM METER 1.8M WEIGHT 320GSM")
    assert parsed["width"] == "160CM"
    assert parsed["weight"] == "320GSM"


def test_ocr_prefers_rotation_with_best_confidence():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    results = iter([
        ("a", 20.0, {"raw_lines": ["a"], "ocr_words": 1}),
        ("best", 91.0, {"raw_lines": ["best"], "ocr_words": 1}),
    ])
    with patch("app.ocr._run_ocr_once", side_effect=results):
        text, confidence, debug = run_ocr_candidates([("crop", 0, image), ("crop", 90, image)])
    assert text == "best"
    assert confidence == 91.0
    assert debug["chosen_rotation"] == 90


def test_gemini_http_error_is_logged_without_key(caplog, monkeypatch):
    import app.gemini_client as gemini

    monkeypatch.setattr(gemini, "GOOGLE_API_KEY", "secret-key")
    response = Mock()
    response.json.return_value = {"error": {"message": "bad request secret-key"}}
    error = RuntimeError("https://example.test?key=secret-key")
    error.code, error.response = 400, response
    client = Mock()
    client.models.generate_content.side_effect = error
    with patch("app.gemini_client.genai.Client", return_value=client), caplog.at_level(logging.ERROR):
        with pytest.raises(GeminiRequestError, match="inspect server logs"):
            call_gemini("", [], 0)
    assert "status=400" in caplog.text
    assert "secret-key" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_confident_gemini_value_replaces_wrong_local_value():
    local = {"article": "WRONG", "composition": None, "main_fiber": None, "width": "160CM"}
    llm = {"article": "AF0123", "width": "150CM", "field_confidence": {"article": 0.90, "width": 0.4}}
    merged = merge_parsed(local, llm)
    assert merged["article"] == "AF0123"
    assert merged["width"] == "160CM"


def test_item_no_is_treated_as_article_code():
    parsed = parse_label_text("ITEM NO: TWM-RDM444 COMP: 20D+26D*50D")
    assert parsed["article"] == "TWM-RDM444"


def test_compact_composition_without_percent_is_supported():
    parsed = parse_label_text("COMP: 100T")
    assert parsed["composition"] == "100T"
    assert parsed["main_fiber"]["name"] == "Poliester"
