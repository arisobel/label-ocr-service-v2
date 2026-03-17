# Label OCR Service v2

Microserviço para detectar etiquetas em amostras de tecido, aplicar OCR, fazer parsing local e, opcionalmente, complementar a extração com Gemini.

## Estrutura real do projeto

```text
label-ocr-service-v2/
├── app/
│   ├── main.py
│   ├── vision.py
│   ├── ocr.py
│   ├── parser.py
│   ├── gemini_client.py
│   └── config.py
├── docs/
│   ├── README_technical.md
│   └── README_llm_guide.md
├── requirements.txt
├── Dockerfile
├── captain-definition
└── README.md
```

## Pipeline

### Via imagem (`POST /extract`)

1. recebe imagem
2. detecta etiqueta com OpenCV
3. aplica OCR com Tesseract
4. gera `raw_text`, `raw_lines`, `confidence`
5. faz parsing local (inclui derivação de `main_fiber`)
6. opcionalmente chama Gemini para complementar ou corrigir campos
7. faz merge entre parser local e LLM
8. recomputa `main_fiber` a partir da composição final

### Via texto extraído (`POST /extract-text`)

1. recebe `raw_text` (obrigatório) e `raw_lines` (opcional) já extraídos via OCR externo
2. faz parsing local (inclui derivação de `main_fiber`)
3. opcionalmente chama Gemini para complementar ou corrigir campos
4. faz merge entre parser local e LLM
5. recomputa `main_fiber` a partir da composição final

**Exemplo de requisição:**

```json
{
  "raw_text": "ARTICLE NO. AF0123 COMP 54%C 46%T WIDTH 160CM WEIGHT 205GSM",
  "raw_lines": [
    "ARTICLE NO. AF0123",
    "COMP 54%C 46%T",
    "WIDTH 160CM",
    "WEIGHT 205GSM"
  ]
}
```

## Variáveis de ambiente

- `GOOGLE_API_KEY`
- `USE_GEMINI_FALLBACK`
- `GEMINI_MODEL`
- `GEMINI_MIN_CONFIDENCE`
- `TESSERACT_CMD`

## Rodar localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Campo main_fiber

Derivado automaticamente do campo `composition`. Retorna a fibra com **maior percentual** na composição.

```json
"main_fiber": {
  "id": 1,
  "name": "Poliester",
  "acronym": "P"
}
```

| id | name             | acronym |
|----|------------------|---------|
|  1 | Poliester        | P       |
|  2 | Cotton           | C       |
|  3 | Linen            | L       |
|  4 | Nylon            | N       |
|  5 | Viscose          | V       |
|  6 | Rayon            | R       |
|  7 | Acetate          | A       |
|  8 | Silk             | S       |
|  9 | Tencel / Lyocell | T       |
| 10 | Wool             | W       |

Observações importantes:
- `T` isolado na composição → **Polyester** (id=1), convenção de mercado asiático
- `TENCEL` / `LYOCELL` por extenso → id=9
- `MODAL` → Viscose (id=5)
- Se `composition` for `null`, `main_fiber` será `null`
- Suporta 3 formatos de composição: `54%C`, `N:59.8%`, `POLYESTER 60%`

## Swagger

`http://localhost:8000/docs`
