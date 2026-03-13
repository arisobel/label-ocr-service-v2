# README_llm_guide.md

## Purpose

This file helps LLMs and AI-assisted coding tools understand the real architecture and intent of this project.

This project is a textile-specific extraction pipeline with deterministic local parsing and optional LLM fallback.

## Actual Folder Structure

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

## System Goal

Convert photos of textile label cards into structured JSON.

Typical fields:
- company
- article
- item
- composition
- weight
- width
- price
- spec
- grade_or_mark
- notes

## Core Philosophy

Prefer:
- deterministic extraction
- lightweight image processing
- explainable heuristics
- incremental improvement

Avoid:
- replacing the whole parser with a black box
- overengineering
- hardcoding one supplier layout unless explicitly requested

## Real Pipeline

```text
image
-> detect label ROI
-> OCR
-> raw_text + raw_lines
-> local parser
-> optional Gemini fallback
-> merge results
```

## Responsibilities by File

### `app/main.py`
Pipeline orchestration.

### `app/vision.py`
Label ROI detection. Keep lightweight.

### `app/ocr.py`
Runs Tesseract and builds:
- `raw_text`
- `raw_lines`
- `confidence`

### `app/parser.py`
Primary deterministic extraction layer.

### `app/gemini_client.py`
Second semantic layer. Only used when local extraction is weak.

### `app/config.py`
Configuration via environment variables.

## Typical OCR Noise

Common artifacts:
- `CV` may mean `CM`
- `GV` may mean `GM`
- `§` may mean `S`
- `AFO519§` may really be `AF0519S`
- separators such as `|` are noise
- `O` and `0` may be swapped

## Important Extraction Heuristics

### Article
Usually appears near:
- `Article No`
- `No`
- `Art`

### Composition
Usually contains multiple percentages:
- `54%C 46%T`
- `N:59.8% R:32.2% SP:8%`

### Width
Usually looks like:
- `160CM`
- `165cm`

### Weight
Usually looks like:
- `205g/m2`
- `400GSM`

## How to Improve Safely

Prefer this order:
1. improve normalization in `parser.py`
2. improve line grouping in `ocr.py`
3. improve ROI detection in `vision.py`
4. improve fallback criteria in `gemini_client.py`

Do not jump directly to a large ML redesign unless requested.

## When to Use Gemini

Good triggers:
- missing article
- missing width
- missing weight
- low confidence
- contaminated local field

The LLM should complement the local parser, not replace it blindly.

## Merge Policy

The local parser has priority when a field looks clean.
The LLM should fill:
- null values
- empty values
- clearly contaminated values
