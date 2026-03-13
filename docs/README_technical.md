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

### parsed_local / final_parsed fields

| field        | type         | description                                      |
|--------------|--------------|--------------------------------------------------|
| company      | string\|null  | supplier name detected in first lines            |
| article      | string\|null  | article/style code                               |
| item         | string\|null  | item description                                 |
| composition  | string\|null  | raw composition string as read from label        |
| main_fiber   | object\|null  | dominant fiber derived from composition (see below) |
| weight       | string\|null  | e.g. `205GSM`, `400G/M2`                         |
| width        | string\|null  | e.g. `160CM`, `165CM`                            |
| price        | string\|null  | price as printed on label                        |
| spec         | string\|null  | spec / construction detail                       |
| grade_or_mark| string\|null  | quality grade or mark                            |
| notes        | string\|null  | additional notes                                 |

### main_fiber object

```json
{
  "id": 1,
  "name": "Poliester",
  "acronym": "P"
}
```

Derived deterministically from `composition` by `extract_main_fiber()` in `parser.py`.
The fiber with the **highest percentage** wins. On tie, the first in the string wins.
`main_fiber` is **not sent to Gemini** — it is always a computed field.
After the Gemini merge, `main_fiber` is recomputed from the final `composition`.

#### Fiber catalog

| id | name             | acronym | Key aliases                                 |
|----|------------------|---------|---------------------------------------------|
|  1 | Poliester        | P       | POLYESTER, PES, PET, PER, TERGAL, T         |
|  2 | Cotton           | C       | COTTON, ALGODÃO, ALGODAO, CO, COT           |
|  3 | Linen            | L       | LINEN, LINHO, LINO, LIN, FLAX, LI           |
|  4 | Nylon            | N       | NYLON, POLYAMIDE, POLIAMIDA, PA6, PA66, NY  |
|  5 | Viscose          | V       | VISCOSE, MODAL, MD, CV, VI                  |
|  6 | Rayon            | R       | RAYON, RAY, RA                              |
|  7 | Acetate          | A       | ACETATE, ACETATO, CTA, CA                   |
|  8 | Silk             | S       | SILK, SEDA, SOIE, SETA                      |
|  9 | Tencel / Lyocell | T       | TENCEL, LYOCELL, CLY, LYO                   |
| 10 | Wool             | W       | WOOL, MERINO, CASHMERE, ANGORA, ALPACA, WO  |
