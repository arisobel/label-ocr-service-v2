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

1. recebe imagem
2. detecta etiqueta com OpenCV
3. aplica OCR com Tesseract
4. gera `raw_text`, `raw_lines`, `confidence`
5. faz parsing local
6. opcionalmente chama Gemini para complementar ou corrigir campos
7. faz merge entre parser local e LLM

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

## Swagger

`http://localhost:8000/docs`
