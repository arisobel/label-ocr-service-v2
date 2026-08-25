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

This service receives either an image or pre-extracted OCR text of a textile sample label, performs parsing, and optionally enriches or corrects the result with Gemini.

## Endpoints

| Method | Path            | Input                        | Description                                      |
|--------|-----------------|------------------------------|--------------------------------------------------|
| GET    | `/health`       | —                            | Health check                                     |
| POST   | `/extract`      | image file (multipart)       | Full pipeline: vision → OCR → parse → (Gemini)  |
| POST   | `/extract-text` | JSON `{raw_text, raw_lines}` | Parse pre-extracted OCR text → (Gemini)          |

## Processing Stages

### `/extract` (image upload)

1. image upload
2. label detection with OpenCV
3. ROI crop
4. OCR with Tesseract
5. build `raw_text` and `raw_lines`
6. local parsing with regex and heuristics
7. optional Gemini fallback
8. merge local and LLM outputs

### `/extract-text` (pre-extracted text)

1. receive `raw_text` (required) and `raw_lines` (optional) already extracted externally
2. local parsing with regex and heuristics
3. optional Gemini fallback
4. merge local and LLM outputs

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

---

## Deploy (CapRover)

O projeto usa dois scripts PowerShell para gerar e publicar o artefato de deploy.

### Pré-requisitos

- Node.js instalado e `caprover` CLI disponível globalmente:
  ```powershell
  npm install -g caprover
  ```
- Arquivo `.env` na raiz do projeto com as credenciais (veja `.env` de exemplo):
  ```
  CAPROVER_URL=https://captain.<seu-servidor>
  CAPROVER_APP=<nome-do-app-no-caprover>
  CAPROVER_APP_TOKEN=<token-gerado-em-Apps-Deployment>
  ```
  O `.env` é ignorado pelo Git. O app token é gerado em **CapRover → Apps → seu app → Deployment**.

### Fluxo completo

```powershell
# 1. Gera o tarball em ./dist/deploy-<timestamp>.tar
.\build-caprover.ps1

# 2. Envia o tarball mais recente para o CapRover
.\deploy-caprover.ps1
```

### Opções do deploy-caprover.ps1

| Parâmetro        | Padrão                   | Descrição                                              |
|------------------|--------------------------|--------------------------------------------------------|
| `-CapRoverUrl`   | `$env:CAPROVER_URL`      | URL do painel CapRover (lido do `.env` se omitido)     |
| `-App`           | `$env:CAPROVER_APP`      | Nome do app no CapRover (lido do `.env` se omitido)    |
| `-AppToken`      | `$env:CAPROVER_APP_TOKEN`| App token (lido do `.env` se omitido; pede senha se ausente) |
| `-TarFile`       | último `deploy-*.tar`    | Caminho explícito para um tarball específico           |
| `-UseSavedConfig`| —                        | Usa a configuração salva pela CLI (`caprover login`)   |

### Exemplos

```powershell
# Deploy com credenciais explícitas (sem .env)
.\deploy-caprover.ps1 -CapRoverUrl https://captain.exemplo.com -App ocr-samples -AppToken <token>

# Deploy de um tarball específico
.\deploy-caprover.ps1 -TarFile .\dist\deploy-20260825-120000.tar

# Deploy usando configuração salva da CLI do CapRover
.\deploy-caprover.ps1 -UseSavedConfig
```

### Conteúdo do tarball

O `build-caprover.ps1` empacota apenas os arquivos necessários para o build no servidor:

```
captain-definition
Dockerfile
requirements.txt
README.md
app/
docs/
```

Arquivos excluídos: `__pycache__`, `*.pyc`, `*.pyo`, `dist/`, `.env`, `venv/`.
