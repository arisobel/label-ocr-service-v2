# README_technical.md

## Project Name
Fabric Label OCR Service v2

## Real Project Structure

```text
label-ocr-service-v2/
├── app/
│   ├── config.py
│   ├── gemini_client.py
│   ├── main.py
│   ├── ocr.py
│   ├── parser.py
│   └── vision.py
├── docs/
│   ├── README_llm_guide.md
│   └── README_technical.md
├── captain-definition
├── Dockerfile
├── README.md
└── requirements.txt
```

## Purpose

This service receives an image of a textile sample label, detects the label, performs OCR, applies rule-based extraction, and optionally enriches or corrects the result with Gemini.

## Processing Stages

1. image upload
2. label detection with OpenCV
3. ROI crop
4. OCR with Tesseract
5. build `raw_text` and `raw_lines`
6. local parsing with regex and heuristics
7. optional Gemini fallback
8. merge local and LLM outputs

## Output Contract

The API returns:
- `success`
- `confidence`
- `raw_text`
- `raw_lines`
- `parsed_local`
- `parsed_llm`
- `final_parsed`
- `debug`
