# SubmitSure
Flask + vanilla JS app: notification analysis (PyMuPDF + optional Groq), copy-ready form answers, document checks, JPG/PNG resize/compress, TXT readiness report.

## Run locally
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # set GROQ_API_KEY and GROQ_MODEL (a model enabled on your Groq account)
    python app.py          # http://localhost:5000
    pytest

## Deploy on Render
1. Push to GitHub. 2. Render > New > Blueprint (uses render.yaml) or Web Service with build `pip install -r requirements.txt`, start `gunicorn app:app --bind 0.0.0.0:$PORT`.
3. Set GROQ_API_KEY and GROQ_MODEL in Environment. 4. Health check path: /api/health.

## Limitations
No OCR (scanned PDFs fall back to manual text entry), no auto-submission; PDF compression is lossless/structural only; no canvas crop tool. ZIP contains the report, answers and processed image only (originals are never bundled). Files are processed in memory, nothing persisted.
